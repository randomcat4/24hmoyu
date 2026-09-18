# Example commands

## mbox

```bash
24hmyself collect mbox ~/Downloads/All\ mail.mbox --output ./corpus
```

## Feishu

```bash
export FEISHU_ACCESS_TOKEN='...'

24hmyself collect feishu \
  --chat oc_xxx \
  --doc doxc_xxx \
  --drive-file boxcn_xxx=report.pdf \
  --download-message-attachments \
  --output ./corpus
```

## DingTalk DWS

First complete DingTalk's official authorization:

```bash
dws auth login
dws auth status --format json
```

Then collect explicitly selected sources:

```bash
24hmyself collect dingtalk \
  --group cid_xxx \
  --direct-user user123 \
  --doc 'https://alidocs.dingtalk.com/i/nodes/xxx' \
  --drive-file node_xxx \
  --time '2026-01-01 00:00:00' \
  --output ./corpus
```
