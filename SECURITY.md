# Security policy

24hmoyu handles potentially sensitive enterprise and personal data. Treat a collected corpus as private by default.

## Supported collection rules

Only use:

- documented official APIs;
- documented official authorization flows;
- user-initiated exports such as mbox.

Do not add collectors that depend on:

- copied browser cookies or session state;
- Playwright/Selenium scraping of authenticated chat pages;
- local chat application databases;
- undocumented private endpoints;
- permission bypasses or privilege escalation.

## Secrets

Never commit:

- access/refresh tokens;
- app secrets;
- DWS credential/config directories;
- exported mailboxes;
- collected chat history;
- downloaded enterprise documents/files.

Use environment variables or the platform's official credential store.

## Local memory

`memory.sqlite3` is derived from private corpus data and should be treated as equally sensitive as the raw chat/mail corpus. It is local-only by default, ignored by git, and created with restrictive file permissions on platforms that support POSIX permissions.

Do not publish or commit `memory.sqlite3`, its WAL/SHM sidecars, dream prompts containing corpus excerpts, or model request/response logs that contain private work data.

## Reporting

If you find a vulnerability, avoid including real enterprise data or credentials in a public issue. Provide a minimal reproduction with synthetic data.


## Dream model boundary

Collection and recall are local operations. The `dream` command is opt-in and
sends a batch of corpus records plus selected existing memories to the model
endpoint configured by `MOYU_LLM_BASE_URL`. Choose an endpoint whose data
handling is acceptable for the corpus.

`--dry-run` still sends that data to the configured model; it only disables
local writes.

Treat corpus content as untrusted input. The dream engine validates model
operations before committing them and rejects references to records or memory
IDs outside the data supplied for that dream batch.
