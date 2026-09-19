# Example commands

## mbox

```bash
24hmoyu collect mbox ~/Downloads/All\ mail.mbox --output ./corpus
```

## Feishu

```bash
export FEISHU_ACCESS_TOKEN='...'

24hmoyu collect feishu \
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
24hmoyu collect dingtalk \
  --group cid_xxx \
  --direct-user user123 \
  --doc 'https://alidocs.dingtalk.com/i/nodes/xxx' \
  --drive-file node_xxx \
  --time '2026-01-01 00:00:00' \
  --output ./corpus
```


## Recall and memory

Query raw corpus records directly for a time range:

~~~bash
24hmoyu recall \
  --corpus ./corpus \
  --since 2026-09-14 \
  --until 2026-09-20 \
  --json
~~~

Search durable memory only when long-lived context is useful:

~~~bash
24hmoyu memory search "支付项目" --corpus ./corpus --json
~~~

Consolidate new corpus events into durable memory:

~~~bash
export MOYU_LLM_MODEL='your-model'
export MOYU_LLM_API_KEY='...'
export MOYU_LLM_BASE_URL='https://api.openai.com/v1'

24hmoyu dream --corpus ./corpus --all
~~~

Preview dream operations without changing memory or checkpoint:

~~~bash
24hmoyu dream --corpus ./corpus --dry-run
~~~

No weekly-context file is generated or maintained.
