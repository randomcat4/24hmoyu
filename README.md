# 24hmoyu

把散落在邮件、飞书和钉钉里的工作记录收回来，留成可检索的本地经验，再让记忆和技能继续加工。

现在有三层：

~~~text
官方数据源 / 用户导出
        ↓
      corpus          原始经验，可直接 recall
        ↓
      memory          做梦后形成的长期、可修改记忆
        ↓
      skills          周报等可复用流程
~~~

我们现在能干这些事：

- **收工作资料**：读取你主动导出的邮箱文件，也能通过官方授权读取飞书、钉钉里的消息、文档和部分附件。
- **保留原始经验**：相同消息或文档如果后来发生变化，会作为新 revision 追加，不再被简单当 duplicate 丢掉。
- **直接回忆**：按日期、来源、类型或关键词动态查询 corpus，不生成 weekly-context.md/json 之类的平行副本。
- **做梦形成长期记忆**：后台整理新 corpus，对长期记忆执行 create / update / delete。
- **自动写周报**：周报事实直接来自指定时间范围的 corpus；memory 只补充项目背景、长期决定等上下文。
- **按心情选周报风格**：默认正经版；赶时间可用省事模板；明确要求时可用黑话娱乐版。
- **把数据留在本地**：corpus 和 memory 默认都在本地，不把访问令牌和应用密钥混进资料库。

## 直接查这一周

~~~bash
24hmoyu recall   --corpus ./corpus   --since 2026-09-14   --until 2026-09-20   --json
~~~

这一步只查询，不额外维护一份“周报上下文”文件。

## 记忆 / 做梦

长期记忆存放在 corpus 目录下的 memory.sqlite3。原始记录仍是事实来源，memory 是可修改的学习结果。

~~~bash
export MOYU_LLM_MODEL='your-model'
export MOYU_LLM_API_KEY='...'
# 兼容千问、本地网关或其他 OpenAI-compatible endpoint 时可覆盖：
export MOYU_LLM_BASE_URL='https://api.openai.com/v1'

24hmoyu dream --corpus ./corpus --all
24hmoyu memory list --corpus ./corpus
24hmoyu memory search "支付项目" --corpus ./corpus
~~~

dream 只处理上次成功 checkpoint 之后的新 corpus。记忆修改和 checkpoint 在同一 SQLite 事务里提交；失败不会把进度提前。

设计细节见 [docs/memory.md](docs/memory.md)。

## 周报怎么用

周报技能放在 [skills/zhoubao](skills/zhoubao)。你可以直接给它工作记录；在能访问本地 24hmoyu corpus 的环境里，它也应直接使用 24hmoyu recall 拉取本周事实，需要长期背景时再查询 24hmoyu memory search。

例如：

> 这周修了登录问题，做完支付页改版，和运营开了两次需求会。下周准备开始做数据看板。

它会整理成本周完成、进行中、卡点和下周计划。你也可以说“简版”“省事版”或“黑话版”；没有明确要求时，它不会擅自写成黑话。

## 资料能从哪里来

| 来源 | 能做什么 |
|---|---|
| 邮箱导出的 mbox 文件 | 整理邮件正文和附件 |
| 飞书官方接口 | 读取指定会话、文档和有权限的文件 |
| 钉钉官方 DWS 能力 | 读取获准访问的群聊、私聊、文档和网盘文件 |

我们只使用官方接口、官方授权流程和你主动提供的导出文件。需要管理员批准的权限会如实提示，不会绕过权限，也不会读取浏览器登录状态或本地聊天数据库。

## 想继续了解

- [记忆与做梦](docs/memory.md)
- [权限和能力说明](docs/authorization-matrix.md)
- [飞书接入说明](docs/feishu.md)
- [钉钉接入说明](docs/dingtalk.md)
- [常用命令示例](examples/commands.md)

## 第三方代码

少量记忆操作语义由 MIT 许可的 LangMem 代码改写而来，许可信息见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。Letta 与 Mem0 只作为架构参考，没有直接 vendoring 其代码。

## 许可证

项目自有代码使用 MIT，详见 [LICENSE](LICENSE)。第三方适配代码按其原许可保留 notice。
