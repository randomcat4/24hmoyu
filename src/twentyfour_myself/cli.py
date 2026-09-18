from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .collectors.base import CollectorContext, CollectorError
from .collectors.dingtalk_dws import DWSClient, DingTalkCollectRequest, DingTalkDWSCollector
from .collectors.feishu import FeishuCollectRequest, FeishuCollector, FeishuHTTPClient
from .collectors.mbox import MboxCollector
from .corpus import CorpusStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="24hmoyu",
        description="Collect officially authorized enterprise data into a local corpus.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    caps = sub.add_parser("capabilities", help="Print the conservative capability matrix")
    caps.add_argument("--json", action="store_true", dest="as_json")

    collect = sub.add_parser("collect", help="Collect data into a local corpus")
    collectors = collect.add_subparsers(dest="collector", required=True)

    mbox = collectors.add_parser("mbox", help="Parse a user-provided mbox export")
    mbox.add_argument("path", type=Path)
    mbox.add_argument("--output", type=Path, required=True)
    mbox.add_argument("--no-attachments", action="store_true")

    feishu = collectors.add_parser("feishu", help="Collect via official Feishu OpenAPI")
    feishu.add_argument("--output", type=Path, required=True)
    feishu.add_argument("--chat", action="append", default=[], metavar="CHAT_ID")
    feishu.add_argument("--doc", action="append", default=[], metavar="DOCUMENT_ID")
    feishu.add_argument(
        "--drive-file",
        action="append",
        default=[],
        metavar="TOKEN[=FILENAME]",
        help="Download an ordinary Feishu Drive file",
    )
    feishu.add_argument("--start-time", type=int, help="Unix seconds for message history")
    feishu.add_argument("--end-time", type=int, help="Unix seconds for message history")
    feishu.add_argument("--page-size", type=int, default=50)
    feishu.add_argument("--download-message-attachments", action="store_true")
    feishu.add_argument("--access-token-env", default="FEISHU_ACCESS_TOKEN")
    feishu.add_argument("--app-id-env", default="FEISHU_APP_ID")
    feishu.add_argument("--app-secret-env", default="FEISHU_APP_SECRET")

    ding = collectors.add_parser("dingtalk", help="Collect through official DingTalk DWS CLI")
    ding.add_argument("--output", type=Path, required=True)
    ding.add_argument("--group", action="append", default=[], metavar="OPEN_CONVERSATION_ID")
    ding.add_argument("--direct-user", action="append", default=[], metavar="USER_ID")
    ding.add_argument("--direct-open-id", action="append", default=[], metavar="OPEN_DINGTALK_ID")
    ding.add_argument("--doc", action="append", default=[], metavar="NODE_ID_OR_URL")
    ding.add_argument("--drive-file", action="append", default=[], metavar="NODE_ID_OR_URL")
    ding.add_argument("--time", default="1970-01-01 00:00:00")
    ding.add_argument("--backward", action="store_true", help="Read messages before --time")
    ding.add_argument("--limit", type=int, default=100)
    ding.add_argument("--all-start", help="Start time for cross-conversation list-all")
    ding.add_argument("--all-end", help="End time for cross-conversation list-all")
    ding.add_argument("--dws-bin", default="dws")
    ding.add_argument("--profile")

    status = sub.add_parser("dws-status", help="Check the selected DingTalk DWS authorization")
    status.add_argument("--dws-bin", default="dws")
    status.add_argument("--profile")

    return parser


def _print_capabilities(as_json: bool) -> int:
    # Capability methods do not perform network calls.
    feishu = FeishuCollector(FeishuHTTPClient("placeholder"), FeishuCollectRequest())
    dingtalk = DingTalkDWSCollector(DWSClient(runner=lambda _: None), DingTalkCollectRequest())
    mbox = MboxCollector("placeholder")
    matrix = {
        "feishu": [item.to_dict() for item in feishu.capabilities()],
        "dingtalk_dws": [item.to_dict() for item in dingtalk.capabilities()],
        "email_mbox": [item.to_dict() for item in mbox.capabilities()],
    }
    feishu.client.close()
    if as_json:
        print(json.dumps(matrix, ensure_ascii=False, indent=2))
    else:
        for source, items in matrix.items():
            print(source)
            for item in items:
                marker = "yes" if item["supported"] else "no"
                print(f"  {item['name']}: {marker} (tier {item['auth_tier']}) - {item['notes']}")
    return 0


def _write(collector, output: Path) -> int:
    store = CorpusStore(output)
    context = CollectorContext(output)
    stats = store.append(collector.collect(context))
    print(
        json.dumps(
            {
                "output": str(output),
                "added": stats.added,
                "duplicates": stats.duplicates,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _parse_drive_specs(values: list[str]) -> list[tuple[str, str | None]]:
    parsed: list[tuple[str, str | None]] = []
    for value in values:
        if "=" in value:
            token, filename = value.split("=", 1)
            parsed.append((token, filename or None))
        else:
            parsed.append((value, None))
    return parsed


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "capabilities":
            return _print_capabilities(args.as_json)

        if args.command == "dws-status":
            client = DWSClient(args.dws_bin, profile=args.profile)
            print(json.dumps(client.auth_status(), ensure_ascii=False, indent=2))
            return 0

        if args.command == "collect" and args.collector == "mbox":
            collector = MboxCollector(args.path, save_attachments=not args.no_attachments)
            return _write(collector, args.output)

        if args.command == "collect" and args.collector == "feishu":
            token = os.getenv(args.access_token_env, "")
            if token:
                client = FeishuHTTPClient(token)
            else:
                app_id = os.getenv(args.app_id_env, "")
                app_secret = os.getenv(args.app_secret_env, "")
                if not app_id or not app_secret:
                    raise CollectorError(
                        f"Set {args.access_token_env}, or both {args.app_id_env} and {args.app_secret_env}."
                    )
                client = FeishuHTTPClient.from_internal_app(app_id, app_secret)
            try:
                request = FeishuCollectRequest(
                    chat_ids=args.chat,
                    document_ids=args.doc,
                    drive_files=_parse_drive_specs(args.drive_file),
                    start_time=args.start_time,
                    end_time=args.end_time,
                    page_size=args.page_size,
                    download_message_attachments=args.download_message_attachments,
                )
                return _write(FeishuCollector(client, request), args.output)
            finally:
                client.close()

        if args.command == "collect" and args.collector == "dingtalk":
            request = DingTalkCollectRequest(
                group_conversation_ids=args.group,
                direct_user_ids=args.direct_user,
                direct_open_dingtalk_ids=args.direct_open_id,
                document_nodes=args.doc,
                drive_nodes=args.drive_file,
                time=args.time,
                forward=not args.backward,
                limit=args.limit,
                all_start=args.all_start,
                all_end=args.all_end,
            )
            client = DWSClient(args.dws_bin, profile=args.profile)
            return _write(DingTalkDWSCollector(client, request), args.output)

    except (CollectorError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
