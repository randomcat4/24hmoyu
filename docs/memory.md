# Memory and dreaming

24hmoyu separates three things that should not be collapsed into one file:

1. **corpus / recall** — raw work experience from Feishu, DingTalk, and email;
2. **memory** — compact, mutable knowledge that remains useful across weeks;
3. **skills** — reusable procedures such as weekly-report generation.

This follows the same broad architecture used by modern stateful agents: keep the
experience log searchable, keep long-term memory small and editable, and keep
procedures separate from facts.

## Why there is no weekly-context file

A weekly context file would be a second copy of the corpus with unclear lifetime
and invalidation rules. 24hmoyu queries the corpus directly instead:

~~~bash
24hmoyu recall   --corpus ./corpus   --since 2026-09-14   --until 2026-09-20   --json
~~~

Long-term memory can then be searched only when background context is useful:

~~~bash
24hmoyu memory search "支付改版" --corpus ./corpus --json
~~~

Current-week claims should come from recall records, not from memory.

## Dreaming

dream processes only corpus events after the last successful checkpoint. It sends
those new events plus a small set of existing memories to an OpenAI-compatible
model. The model returns memory operations:

- create
- update
- delete

The operations and checkpoint are committed in one SQLite transaction. A failed
dream does not advance the checkpoint.

~~~bash
export MOYU_LLM_MODEL='your-model'
export MOYU_LLM_API_KEY='...'
export MOYU_LLM_BASE_URL='https://api.openai.com/v1'

24hmoyu dream --corpus ./corpus --all
~~~

Preview without writing memory:

~~~bash
24hmoyu dream --corpus ./corpus --dry-run
~~~

## Privacy boundary

`collect`, `recall`, and local `memory` inspection do not require sending the
corpus to an LLM. `dream` is different: when explicitly invoked, it sends the
current batch of corpus records and a small candidate set of existing memories
to the configured OpenAI-compatible model endpoint.

Use a provider/end-point appropriate for the sensitivity of the corpus. A
`--dry-run` still calls the model; it only prevents local memory/checkpoint
writes.

Corpus text is treated as untrusted data. Dream output is rejected if it tries
to cite corpus refs outside the current batch or modify memories outside the
candidate set supplied to the model.

## What deserves memory

The dream prompt deliberately avoids transcript summarization. Good durable
memories include:

- stable project identity and ownership;
- recurring responsibilities;
- decisions and rationale that remain relevant;
- persistent blockers or dependencies;
- durable working preferences;
- reusable procedures and conventions.

Routine one-off status updates stay in the corpus because they are cheap to
retrieve when needed.

## User control

Memory is inspectable and correctable:

~~~bash
24hmoyu memory list --corpus ./corpus
24hmoyu memory remember "支付项目由客户端组负责" --kind responsibility --corpus ./corpus
24hmoyu memory update <memory-id> "新的准确内容" --corpus ./corpus
24hmoyu memory forget <memory-id> --corpus ./corpus
~~~

The local database is memory.sqlite3 under the corpus directory and is excluded
from git.

## Design lineage

The implementation intentionally borrows a small amount of memory-operation logic
from LangMem's MIT-licensed create/update/delete memory tool and preserves the
required notice in THIRD_PARTY_NOTICES.md.

The architecture is also informed by:

- Letta/Letta Code: keep recall experience separate from editable memory and
  reusable skills, and run background reflection/dreaming over recent experience;
- Mem0: retrieve relevant existing memories before extraction/consolidation.
  Mem0's current v3 documentation describes an ADD-only extraction lifecycle,
  so 24hmoyu does not copy that lifecycle. We keep explicit update/delete
  because enterprise facts and project decisions can be superseded.

24hmoyu does not vendor Letta or Mem0 code and does not require LangGraph, a
vector database, or a hosted memory service.
