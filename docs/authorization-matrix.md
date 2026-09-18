# Authorization matrix

Last reviewed: 2026-09-18.

This document intentionally separates **API existence** from **who is allowed to authorize it**. A capability is not considered usable merely because an endpoint or CLI command exists.

Authorization tiers used by 24hmoyu:

| Tier | Meaning |
|---|---|
| 0 | User explicitly provides a local export/file |
| 1 | User completes an official delegated authorization flow for data the platform permits that user to delegate |
| 2 | Enterprise/application access requires administrator enablement, approval, installation, or enterprise-scoped permission |

## Current matrix

| Source | Capability | Implemented | Tier | Notes |
|---|---|---:|---:|---|
| Email | Parse mbox | Yes | 0 | Gmail Takeout, Thunderbird, or another user-created mbox export |
| Email | Extract mbox attachments | Yes | 0 | Local-only |
| Gmail/Outlook | Live OAuth mailbox sync | No | 1 | Deliberately deferred |
| Feishu | Historical messages for an explicit chat | Yes | 2 | Official `GET /im/v1/messages`; application scope/data range still applies |
| Feishu | Message resource download | Yes | 2 | Official resource endpoint; resource/chat/bot restrictions apply |
| Feishu | Read docx raw content | Yes | 1/2 | Official API supports authorized tokens; effective access still depends on document/app permissions |
| Feishu | Download ordinary Drive file | Yes | 1/2 | Online documents use document/export APIs instead |
| Feishu | "OAuth once, export all account data" | No | — | Not treated as a public capability |
| DingTalk DWS | Historical group messages | Yes | 2 | Organization must enable/approve DWS/CLI access |
| DingTalk DWS | Historical direct messages | Yes | 2 | Same DWS authorization boundary |
| DingTalk DWS | Cross-conversation message listing | Yes | 2 | Implemented through DWS list-all with cursor pagination |
| DingTalk DWS | Message search | No (upstream capability exists) | 2 | Not exposed by this collector version |
| DingTalk DWS | Read online document | Yes | 2 | `dws doc info` + `dws doc read` |
| DingTalk DWS | Download Drive file | Yes | 2 | `dws drive info` + `dws drive download` |
| DingTalk DWS | Generic chat attachment download | Not claimed | 2 | Message read projections may not expose enough stable resource metadata |
| DingTalk without DWS/admin approval | Bulk personal chat history | No verified public path | — | Do not infer one from ordinary OAuth/OpenAPI |
| DingTalk without DWS/admin approval | Bulk personal docs/files | No verified account-wide path | — | Explicit app/user-scoped capabilities must be evaluated endpoint by endpoint |

## DingTalk: what remains without admin approval?

The conservative answer is: **not DWS**. DingTalk's DWS documentation states that organization CLI access must be enabled/approved by an administrator. Therefore this repository does not present DWS as a user-only authorization path.

Ordinary OpenAPI and client JSAPI still exist, but they are not equivalent to DWS historical-data access. For example, client-side conversation selection/navigation can return or use conversation identifiers, yet that does not itself expose historical message content. Application OpenAPI capabilities remain limited to the permissions and data range actually granted to that application.

For this project, an endpoint is only moved into the "no-admin" column after all of the following are verified:

1. it is documented by DingTalk;
2. an ordinary employee can complete the required authorization without enterprise-admin approval;
3. the endpoint reads existing user data rather than only data created by the app/bot;
4. pagination and time/history semantics are tested;
5. attachment/document behavior is tested separately;
6. the result does not depend on browser cookies, local databases, or undocumented endpoints.

Until then, `unknown` stays `unknown`.

## Sources

- DingTalk Workspace CLI: https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli
- DingTalk Open Platform: https://open.dingtalk.com/
- Feishu Open Platform: https://open.feishu.cn/
