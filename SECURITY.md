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

## Reporting

If you find a vulnerability, avoid including real enterprise data or credentials in a public issue. Provide a minimal reproduction with synthetic data.
