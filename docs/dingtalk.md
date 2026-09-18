# DingTalk collector

24hmyself integrates DingTalk through the officially open-sourced **DingTalk Workspace CLI (`dws`)** rather than copying or reimplementing its credential handling.

This is deliberate: `dws` owns OAuth/device-flow login, profile selection, credential storage, domain allowlisting, permission checks, and auditing. 24hmyself only invokes read operations and normalizes their structured JSON results.

Upstream: https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli

## Authorization boundary

DWS requires enterprise CLI access to be enabled/approved. A user login alone is not treated as sufficient when the organization has not enabled DWS.

Typical setup:

```bash
dws auth login
dws auth status --format json
```

If the organization has not enabled CLI access, follow DingTalk's official approval flow. 24hmyself will not attempt a bypass.

## Implemented read paths

### Group history

```bash
dws chat message list \
  --group <openConversationId> \
  --time "2026-09-01 00:00:00" \
  --forward true \
  --limit 100 \
  --format json
```

24hmyself continues pages while `hasMore=true`, advances the time cursor from the last returned `createTime`, and relies on corpus de-duplication at page boundaries.

### Direct-message history

```bash
dws chat message list \
  --user <userId> \
  --time "2026-09-01 00:00:00" \
  --format json
```

or, when already known:

```bash
dws chat message list \
  --open-dingtalk-id <openDingTalkId> \
  --time "2026-09-01 00:00:00" \
  --format json
```

DWS maps group and direct-history reads to distinct underlying Workspace capabilities. 24hmyself intentionally stays on the supported CLI surface instead of reproducing undocumented transport details.

### Cross-conversation history

```bash
dws chat message list-all \
  --start "2026-09-01 00:00:00" \
  --end "2026-09-02 00:00:00" \
  --limit 50 \
  --cursor 0 \
  --format json
```

This path uses cursor pagination.

### Online documents

For explicitly supplied node IDs/URLs:

```bash
dws doc info --node <node> --format json
dws doc read --node <node> --format json
```

24hmyself stores the Markdown/text projection as a normalized `Document`.

### Drive files

For explicitly supplied file nodes:

```bash
dws drive info --node <node> --format json
dws drive download --node <node> --output <local-path> --format json
```

The downloaded file becomes a normalized `Attachment` in the local corpus.

## Message attachments

DWS exposes real message-history capabilities, but message read projections may be lossy for rich/card/file messages. Upstream reports have documented cases where rich structure or complete file metadata is not present in the history projection.

Because of that, 24hmyself does **not** claim a generic "download every chat attachment" capability. When a DWS message projection visibly contains identifiers such as `fileId`, `resourceId`, or `mediaId`, the collector records them as unresolved attachment metadata. It does not invent a download URL or guess an undocumented RPC.

Relevant upstream discussions include:

- https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/243
- https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/797

## Ordinary OpenAPI vs DWS

Do not equate these surfaces:

- ordinary OpenAPI: application-oriented APIs with app permissions/data ranges;
- client JSAPI: user-interface capabilities such as selecting/opening a conversation;
- DWS/Workspace: user/enterprise workspace capabilities, including historical-message reads.

The project will only add a non-DWS adapter when a specific official endpoint has a verified authorization model and data boundary.
