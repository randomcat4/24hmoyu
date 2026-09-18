# 24hmyself

A privacy-first, local-first collector layer for turning **officially authorized enterprise data** into a normalized local corpus.

24hmyself is intentionally narrower than a "digital immortality" system. Its job is to answer three questions reliably:

1. what data can be read through an official interface;
2. who must authorize that read;
3. how to normalize the result without leaking provider-specific details downstream.

```text
Feishu official OpenAPI
          │
DingTalk DWS / documented OpenAPI
          │
Email mbox exports
          │
          ▼
   BaseCollector adapters
          │
          ▼
Message / Document / Attachment
          │
          ▼
      local corpus
          │
          ▼
downstream distillation / skills / memory
```

This repository is an independent implementation. It is not a GitHub fork and does not copy credential/session extraction techniques from chat clients.

## Safety boundary

24hmyself accepts only:

- documented official APIs;
- documented official authorization flows;
- user-initiated local exports such as mbox.

It deliberately does **not** use:

- Playwright/Selenium to scrape authenticated chat pages;
- browser cookies or copied browser login state;
- local WeChat/DingTalk/Feishu chat databases;
- undocumented private endpoints;
- techniques that bypass enterprise administrator approval;
- silent device/account collection.

If a provider says an enterprise administrator must approve a capability, the collector reports that boundary instead of trying to work around it.

## What is implemented

| Source | Messages | Documents | Files / attachments | Authorization model |
|---|---|---|---|---|
| Email mbox | Yes | — | Yes | user-provided file |
| Feishu OpenAPI | explicit-chat history | docx raw content | message resources + ordinary Drive files | official access token; effective app/document permissions apply |
| DingTalk DWS | group/direct/cross-conversation history | online docs | Drive files; chat resource IDs are recorded conservatively | DWS organization access must be enabled/approved |

See [`docs/authorization-matrix.md`](docs/authorization-matrix.md) for the deliberately conservative capability matrix.

## Current DingTalk conclusion

DingTalk DWS provides real historical-message capabilities, including group/direct history and message search. However, DWS itself requires organization-level CLI access to be enabled or approved.

Therefore 24hmyself does **not** treat "a normal employee OAuths once and bulk-downloads all DingTalk chats/docs" as a public capability.

Without administrator approval, ordinary OpenAPI/JSAPI capabilities must be evaluated endpoint by endpoint. They are not assumed to be equivalent to Workspace/DWS historical-data access.

See [`docs/dingtalk.md`](docs/dingtalk.md).

## Installation

Python 3.11+:

```bash
git clone https://github.com/randomcat4/24hmyself.git
cd 24hmyself
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Run tests:

```bash
pytest
```

Inspect the capability matrix:

```bash
24hmyself capabilities
24hmyself capabilities --json
```

## Local corpus

Every collector writes the same source-independent records:

```text
Message
├── source
├── external_id
├── channel_id
├── sender_id / sender_name
├── timestamp
├── text
├── attachment_refs[]
└── metadata

Document
├── source
├── external_id
├── title
├── content
├── owner_id
├── created_at / updated_at
├── attachment_refs[]
└── metadata

Attachment
├── source
├── external_id
├── filename
├── mime_type
├── size
├── local_path
├── parent_ref
└── metadata
```

Corpus layout:

```text
corpus/
├── records.jsonl
├── manifest.json
└── attachments/
```

Records are de-duplicated by:

```text
<source>:<kind>:<external_id>
```

The corpus contains normalized data, not access tokens or application secrets.

## Email: mbox

Recommended low-risk first path:

```text
Gmail Takeout / Thunderbird / another explicit export
                         │
                         ▼
                        mbox
                         │
                         ▼
                   MboxCollector
```

Run:

```bash
24hmyself collect mbox ~/Downloads/mail.mbox --output ./corpus
```

Attachments are extracted locally by default. Disable extraction with:

```bash
24hmyself collect mbox ~/Downloads/mail.mbox \
  --no-attachments \
  --output ./corpus
```

Live Gmail/Outlook OAuth is intentionally deferred until its authorization, pagination, attachment behavior, and refresh-token storage are implemented and tested as a separate adapter.

## Feishu

The Feishu collector uses official OpenAPI endpoints for:

- historical messages in explicitly supplied chat IDs;
- message resource downloads;
- docx plain-text content;
- ordinary Drive file downloads.

See [`docs/feishu.md`](docs/feishu.md) for endpoint details.

### Authentication

Option A: provide an access token already obtained through an official flow:

```bash
export FEISHU_ACCESS_TOKEN='...'
```

Option B: internal enterprise app credentials, exchanged through Feishu's official tenant-token endpoint:

```bash
export FEISHU_APP_ID='...'
export FEISHU_APP_SECRET='...'
```

Never commit these values.

### Collect

```bash
24hmyself collect feishu \
  --chat oc_xxx \
  --doc doxc_xxx \
  --drive-file boxcn_xxx=report.pdf \
  --download-message-attachments \
  --output ./corpus
```

Message history is scoped to chat IDs you explicitly provide; this command is not an account-wide export primitive.

## DingTalk DWS

24hmyself delegates DingTalk credential handling to the officially open-sourced DingTalk Workspace CLI rather than reading DWS credential files itself.

Install/configure DWS according to its upstream documentation:

https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli

Authorize:

```bash
dws auth login
dws auth status --format json
```

If the organization has not enabled DWS/CLI access, use DingTalk's official administrator approval flow. 24hmyself will stop rather than bypass it.

Check from 24hmyself:

```bash
24hmyself dws-status
```

### Group history

```bash
24hmyself collect dingtalk \
  --group cid_xxx \
  --time '2026-01-01 00:00:00' \
  --output ./corpus
```

### Direct-message history

```bash
24hmyself collect dingtalk \
  --direct-user user123 \
  --time '2026-01-01 00:00:00' \
  --output ./corpus
```

or:

```bash
24hmyself collect dingtalk \
  --direct-open-id DINGTALK_OPEN_ID \
  --time '2026-01-01 00:00:00' \
  --output ./corpus
```

### Cross-conversation window

```bash
24hmyself collect dingtalk \
  --all-start '2026-09-01 00:00:00' \
  --all-end '2026-09-02 00:00:00' \
  --output ./corpus
```

### Documents and Drive files

```bash
24hmyself collect dingtalk \
  --doc 'https://alidocs.dingtalk.com/i/nodes/xxx' \
  --drive-file node_xxx \
  --output ./corpus
```

The adapter uses `dws doc info/read` and `dws drive info/download`.

### Chat attachment limitation

DWS history reads can expose a lossy projection for some rich/card/file messages. 24hmyself records visible `fileId` / `resourceId` / `mediaId` values as unresolved attachment metadata, but does not claim that every historical chat attachment can be generically downloaded.

That boundary is intentional: an incomplete official projection is safer than inventing a private download path.

## Collector contract

All collectors inherit the same boundary:

```text
BaseCollector
    │
    ├── MboxCollector
    ├── FeishuCollector
    └── DingTalkDWSCollector
            │
            ▼
      normalized records
            │
            ▼
        CorpusStore
```

Collectors own:

- official authentication/authorization integration;
- capability reporting;
- pagination;
- provider error handling;
- permitted resource downloads;
- normalization;
- provenance metadata.

Collectors do not own:

- persona generation;
- long-term memory synthesis;
- skill generation;
- model prompting/distillation.

Those stages consume the corpus later.

## Repository layout

```text
24hmyself/
├── src/twentyfour_myself/
│   ├── models.py
│   ├── corpus.py
│   ├── cli.py
│   └── collectors/
│       ├── base.py
│       ├── mbox.py
│       ├── feishu.py
│       └── dingtalk_dws.py
├── docs/
│   ├── authorization-matrix.md
│   ├── data-model.md
│   ├── feishu.md
│   └── dingtalk.md
├── examples/
│   └── commands.md
├── tests/
├── SECURITY.md
├── CONTRIBUTING.md
└── LICENSE
```

## Development rules

- Unknown means unknown, not supported.
- "Permission denied" is a normal product state, not a signal to bypass access control.
- Never commit real tokens, mbox exports, chats, documents, attachments, or DWS credential state.
- Add pagination and denied-permission tests before declaring a collector stable.
- Prefer official provider documentation as the source of truth.
- Keep provider payload details in metadata; downstream corpus consumers should depend on the normalized model.

## Status

`v0.1.0` is a working collector foundation, not a promise to collect every artifact from every provider.

The next research milestone is to move DingTalk capabilities from `unknown` to either `verified user-delegated` or `verified admin-gated` endpoint by endpoint, without adding any local-client extraction path.

## License

MIT. See [`LICENSE`](LICENSE).
