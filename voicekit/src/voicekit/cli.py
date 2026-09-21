from __future__ import annotations

import argparse
import json
from pathlib import Path

from .corpus import discover_text_files, split_items
from .distance import candidate_typicality
from .lineup import Document, build_lineup
from .measure import measure_text, profile_paths
from .repetition import audit_documents


def _dump(payload: object, path: str | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path:
        Path(path).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def cmd_measure(args: argparse.Namespace) -> int:
    profile = profile_paths(args.files)
    _dump(profile, args.out)
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    files = discover_text_files(args.root)
    split = split_items(
        [str(path) for path in files],
        profile_ratio=args.profile_ratio,
        dev_ratio=args.dev_ratio,
        seed=args.seed,
    )
    _dump({"schema_version": 1, "seed": args.seed, "splits": split}, args.out)
    return 0


def cmd_distance(args: argparse.Namespace) -> int:
    profile = json.loads(Path(args.profile).read_text("utf-8"))
    candidate = measure_text(Path(args.candidate).read_text("utf-8", errors="replace"))
    docs = [row["metrics"] for row in profile.get("documents", [])]
    result = candidate_typicality(candidate, docs)
    _dump(result, args.out)
    return 0


def cmd_lineup(args: argparse.Namespace) -> int:
    fake_path = Path(args.fake)
    fake = Document(fake_path.stem, fake_path.read_text("utf-8", errors="replace"))
    reals = [
        Document(Path(path).stem, Path(path).read_text("utf-8", errors="replace"))
        for path in args.real
    ]
    lineup, key = build_lineup(fake, reals, seed=args.seed)
    Path(args.out).write_text(lineup, encoding="utf-8")
    Path(args.key).write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    texts = [Path(path).read_text("utf-8", errors="replace") for path in args.files]
    _dump(audit_documents(texts), args.out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voicekit",
        description="Portable author-voice profiling and adversarial evaluation primitives.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    measure = sub.add_parser("measure", help="measure a corpus and retain per-document metrics")
    measure.add_argument("files", nargs="+", help="Markdown/text files")
    measure.add_argument("--out")
    measure.set_defaults(func=cmd_measure)

    split = sub.add_parser("split", help="create profile/dev/final holdout manifest")
    split.add_argument("root")
    split.add_argument("--profile-ratio", type=float, default=0.6)
    split.add_argument("--dev-ratio", type=float, default=0.2)
    split.add_argument("--seed", type=int, default=42)
    split.add_argument("--out")
    split.set_defaults(func=cmd_split)

    distance = sub.add_parser("distance", help="place a candidate in the real-real distance distribution")
    distance.add_argument("profile", help="JSON produced by voicekit measure")
    distance.add_argument("candidate")
    distance.add_argument("--out")
    distance.set_defaults(func=cmd_distance)

    lineup = sub.add_parser("lineup", help="build a 7-real + 1-fake blind lineup")
    lineup.add_argument("--fake", required=True)
    lineup.add_argument("--real", nargs="+", required=True)
    lineup.add_argument("--out", required=True)
    lineup.add_argument("--key", required=True)
    lineup.add_argument("--seed", type=int, default=42)
    lineup.set_defaults(func=cmd_lineup)

    audit = sub.add_parser("audit", help="measure cross-document repetition")
    audit.add_argument("files", nargs="+")
    audit.add_argument("--out")
    audit.set_defaults(func=cmd_audit)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
