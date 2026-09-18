# 24hmyself

A privacy-first, local-first collector pipeline for turning **officially authorized enterprise data** into a structured personal corpus.

The project focuses on the **data acquisition layer**: what can be collected, under which authorization boundary, and how to normalize it safely before any later distillation into skills, memory, persona, or other derived artifacts.

> Status: early research / implementation. API coverage is intentionally conservative. Unsupported or unverified access paths are not treated as features.

## Architecture

```text
Feishu official APIs
        │
DingTalk DWS / documented OpenAPI
        │
Email mbox / later OAuth
        │
        ▼
  Unified Collectors
        │
        ▼
Message / Document / Attachment
        │
        ▼
    Local corpus
        │
        ▼
Downstream distillation / skill generation
```

The collector layer is the product boundary. Downstream generation should not need to know whether a record originally came from Feishu, DingTalk, Gmail, Outlook, Thunderbird, or an exported mailbox.

## Design principles

1. **Official interfaces only**  
   Use documented APIs, documented authorization flows, or user-initiated exports.

2. **Explicit authorization**  
   Every collector must state whether it requires:
   - only the end user's action,
   - delegated user authorization,
   - or enterprise administrator approval.

3. **Least privilege**  
   Request only scopes required for the selected data type.

4. **Local-first processing**  
   Normalize collected content into a local corpus before downstream processing.

5. **No credential or session reuse**  
   Do not reuse browser cookies, browser login state, local chat databases, or hidden client credentials.

6. **No permission bypass**  
   If an enterprise capability requires administrator approval, the collector reports that boundary instead of attempting to work around it.

7. **Independent implementation**  
   This repository is implemented independently and is not maintained as a GitHub fork.

## Data sources

### Feishu

Accepted path: **official Feishu APIs and official authorization flows only**.

Research and implementation are split by data type:

- group and conversation messages;
- documents and document content;
- files and downloadable resources;
- user-level versus administrator-gated permissions;
- attachment/resource resolution.

The collector must expose the authorization requirements for each operation rather than treating all Feishu content as one permission domain.

### DingTalk

Accepted paths:

- DingTalk Workspace / DWS capabilities where officially available;
- documented DingTalk OpenAPI;
- official user authorization and enterprise authorization flows.

The DingTalk adapter will not assume that a generic "messages" endpoint is equivalent to historical-message access.

The implementation will treat the following as separate capabilities:

- historical conversation messages;
- individual chat messages;
- message search;
- chat attachment/resource download;
- DingTalk Drive / DingPan files;
- online documents;
- metadata accessible through ordinary OpenAPI.

Each capability must be tagged with its real authorization boundary.

#### Key research question: no administrator approval

A major goal is to document exactly what a normal employee can automate through official mechanisms when an enterprise administrator does **not** approve privileged Workspace / DWS access.

Working assumption until verified endpoint-by-endpoint:

> A personal DingTalk account should not be treated as having a public "OAuth once, bulk-export all chats and documents" capability.

If a capability is unavailable without administrator approval, 24hmyself should say so clearly and continue with the remaining lawful user-level sources.

### Email

Initial low-risk path:

```text
Gmail Takeout / Thunderbird / other user export
                    │
                    ▼
                   mbox
                    │
                    ▼
             local parser
                    │
                    ▼
            normalized corpus
```

Later adapters may add official OAuth integrations for Gmail and Microsoft/Outlook.

Code comments or partial stubs do not count as implemented API support. An integration is considered supported only after its authorization flow, pagination, data mapping, attachment behavior, and failure modes are tested.

## Explicit non-goals

24hmyself does **not** use:

- Playwright or browser automation to scrape chat pages;
- browser cookies or copied login sessions;
- local WeChat/chat application databases;
- undocumented private endpoints;
- techniques intended to bypass enterprise access control;
- silent collection from accounts or devices without the user's explicit action.

WeChat and similar local-client extraction paths are intentionally out of scope.

## Authorization model

Every collector capability should be classified into one of these tiers:

| Tier | Authorization boundary | Example |
|---|---|---|
| 0 | User-provided file | mbox imported from a user export |
| 1 | User-delegated official authorization | OAuth / official user authorization for user-accessible data |
| 2 | Enterprise administrator approval | Workspace or enterprise-scoped data requiring admin consent |

Collectors must not silently escalate from one tier to another.

A run should be able to answer:

- What data was requested?
- Which scopes or permissions were used?
- Who authorized it?
- Which capabilities were unavailable?
- Which records were actually collected?

## Unified data model

The first implementation target is a small source-independent model.

### Message

```text
Message
├── source
├── message_id
├── channel_id / conversation_id
├── sender
├── timestamp
├── text
├── attachment_refs[]
└── metadata
```

### Document

```text
Document
├── source
├── document_id
├── title
├── content
├── owner / author
├── created_at
├── updated_at
├── attachment_refs[]
└── metadata
```

### Attachment

```text
Attachment
├── source
├── attachment_id
├── filename
├── mime_type
├── size
├── local_path
├── parent_ref
└── metadata
```

Source-specific API payloads should remain inside adapter metadata or raw snapshots rather than leaking into downstream corpus consumers.

## Collector contract

The collector architecture should remain simple:

```text
BaseCollector
    │
    ├── FeishuCollector
    ├── DingTalkDWSCollector
    └── MboxCollector
            │
            ▼
      normalized records
            │
            ▼
         corpus
```

A collector is responsible for:

- authentication / authorization;
- capability detection;
- pagination;
- rate-limit handling;
- downloading permitted resources;
- normalization;
- provenance;
- deterministic IDs;
- explicit partial-failure reporting.

It is **not** responsible for persona generation, long-term memory synthesis, or skill distillation.

## Planned repository layout

```text
24hmyself/
├── src/
│   └── twentyfour_myself/
│       ├── models.py
│       ├── corpus.py
│       └── collectors/
│           ├── base.py
│           ├── feishu.py
│           ├── dingtalk_dws.py
│           └── mbox.py
├── tests/
│   ├── collectors/
│   └── fixtures/
├── docs/
│   ├── authorization-matrix.md
│   ├── feishu.md
│   └── dingtalk.md
├── README.md
└── LICENSE
```

The exact package layout may change as the official APIs are validated.

## Research priorities

### 1. DingTalk without administrator approval

Build a tested capability matrix answering, for a normal employee using only official/legal mechanisms:

- Can historical group messages be read?
- Can one-to-one chat history be read?
- Can messages be searched?
- Can chat attachments be downloaded?
- Can DingPan files be listed/downloaded?
- Can online documents be read?
- Which operations require administrator approval?
- Which operations require DWS / Workspace rather than ordinary OpenAPI?

Unknown means **unknown**, not supported.

### 2. Clean DingTalk DWS adapter

Implement a new DingTalk adapter around the official Workspace / DWS authorization model while preserving the source-independent collector boundary:

```text
DingTalk official auth
        │
        ▼
DingTalkDWSCollector
        │
        ├── messages
        ├── documents
        └── attachments
        │
        ▼
Message / Document / Attachment
        │
        ▼
      corpus
```

No downstream code should depend on DingTalk-specific response objects.

## Development rules

- Prefer fixtures captured from documented API responses with secrets removed.
- Keep raw API payloads optional and local.
- Never commit tokens, cookies, exported mailboxes, chat history, or downloaded enterprise documents.
- Add tests for pagination and permission-denied behavior before treating a collector as stable.
- Record API version / capability assumptions in adapter documentation.
- Treat "permission denied" as a normal product state, not an error to bypass.

## Project status

The initial milestone is **not** "collect everything."

It is:

> Build a trustworthy collector layer that knows what it is allowed to read, obtains it through official channels, preserves provenance, and clearly reports what it cannot access.

Once that layer is stable, downstream corpus distillation can evolve independently.

## License

MIT. See [LICENSE](LICENSE).
