# Feishu collector

The Feishu adapter calls official OpenAPI endpoints directly. It accepts either:

- an access token already obtained through an official authorization flow; or
- an internal-app `app_id`/`app_secret`, exchanged for an official `tenant_access_token`.

Credentials are read from environment variables by the CLI and are never written into the corpus.

## Historical messages

Endpoint:

```text
GET /open-apis/im/v1/messages
```

The collector requires explicit chat IDs and sends `container_id_type=chat`. Optional `start_time` and `end_time` are Unix seconds; pagination uses `page_token`.

This is **not** an account-wide export primitive. Effective visibility is constrained by the app's permissions and data-access scope.

## Message resources

Endpoint:

```text
GET /open-apis/im/v1/messages/{message_id}/resources/{file_key}?type=image|file
```

When `--download-message-attachments` is enabled, resource keys surfaced in message content are downloaded through this endpoint. Feishu's own constraints still apply, including bot/chat/resource restrictions and size limits.

## Documents

Metadata:

```text
GET /open-apis/docx/v1/documents/{document_id}
```

Plain text:

```text
GET /open-apis/docx/v1/documents/{document_id}/raw_content
```

The normalized `Document` deliberately keeps plain text rather than reproducing every block/style detail.

## Drive files

Ordinary files:

```text
GET /open-apis/drive/v1/files/{file_token}/download
```

This path does not cover online docs/sheets/mind maps. Those must use their corresponding OpenAPI/export flows.

## Environment variables

Use one of the following patterns.

Existing official token:

```bash
export FEISHU_ACCESS_TOKEN='...'
```

Internal enterprise app:

```bash
export FEISHU_APP_ID='...'
export FEISHU_APP_SECRET='...'
```

Do not commit these values.

## Official documentation

- https://open.feishu.cn/document/server-docs/im-v1/message/list
- https://open.feishu.cn/document/server-docs/im-v1/message-resource/get
- https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document/raw_content
- https://open.feishu.cn/document/server-docs/docs/drive-v1/download/download
