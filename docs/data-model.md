# Corpus data model

24hmoyu keeps the normalized schema intentionally small so downstream distillation does not depend on vendor payloads.

## Message

```text
source
external_id
channel_id
sender_id
sender_name
timestamp
text
attachment_refs[]
metadata
```

## Document

```text
source
external_id
title
content
owner_id
created_at
updated_at
attachment_refs[]
metadata
```

## Attachment

```text
source
external_id
filename
mime_type
size
local_path
parent_ref
metadata
```

Each record has a stable de-duplication key:

```text
<source>:<kind>:<external_id>
```

## Corpus layout

```text
corpus/
├── records.jsonl
├── manifest.json
└── attachments/
```

`records.jsonl` is append-oriented and human-inspectable. `manifest.json` contains only corpus-level counts and source names. Raw access tokens are never stored.
