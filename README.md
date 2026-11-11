
## 目前值得关注的 Agent 开发框架


| 框架 / 方案 | 主要定位 | 学习价值 | 我的判断 |
|--------|--------|--------|--------|
| LangGraph | 有状态、可恢复、复杂流程编排 | 很高 | **优先学习** |
| Microsoft Agent Framework | 企业级 Agent、工作流、多智能体 | 很高 | **\.NET 开发者重点关注** |
| OpenAI Agents SDK | 工具调用、交接、Agent 协作 | 高 | 快速上手的好选择 |
| CrewAI | 角色分工、任务协作 | 中高 | 快速搭建多 Agent 原型 |
| AutoGen | 多 Agent 对话与协作 | 中 | 适合学习旧架构，不建议新项目主学 |
| AgentScope | 多智能体应用、运行时和评估 | 中高 | 值得关注，尤其是想深入 Agent 系统时 |
| CAMEL | 多 Agent 协作、研究与实验 | 中 | 对多智能体原理感兴趣时再深入 |
| LangChain | 模型、工具、检索与应用集成 | 高 | 适合补充生态知识，不必先学全家桶 |


## 优先推荐 LangGraph
LangGraph 的核心价值不是让多个 AI 互相聊天，而是让你**精确控制 AI 应用的执行过程**。

(通用 Agent 工程能力),进入更广泛的 Agent 开发生态、研究复杂工作流、未来用 Python 构建 AI 服务。

主要学习：状态图、检查点、条件路由、工具调用、人工审批、持久化执行。

它把流程建模成一个图：

- **State：** 当前任务状态和共享数据。
- **Node：** 一个执行步骤，可以是 LLM、工具调用或普通代码。
- **Edge：** 决定下一步走向的连接。
- **Conditional routing：** 根据执行结果选择分支。
- **Checkpoint：** 持久化执行状态，支持中断后恢复。
- **Human-in-the-loop：** 在关键节点暂停，等待人工批准或输入。

这些能力尤其适合需要可靠执行的长流程。 [GitHub](https://github.com/langchain-ai/docs/blob/main/src/oss/langgraph/overview.mdx?utm_source=chatgpt.com)

例如设计工作流：

**1\. 任务规划**

读取需求，生成任务清单

**2\. 编码 Agent**

调用 Claude Code / Codex 执行任务

**3\. 验证与审查**

运行测试、检查差异、判断是否通过

**通过**

记录结果，进入下一任务

**失败**

定位问题，修复并重试

这类场景里，关键问题不是让多少个 Agent 参与，而是怎样保证流程可恢复、结果可验证、失败不失控。

不过有一个边界要明确：LangGraph 不会自动把 Claude Code 或 Codex 变成它的内部 Agent。你仍然需要通过 CLI、SDK 或其他合适的接口集成它们，并设计好权限、超时、状态记录和错误处理。

官方文档：[LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)。

## Microsoft Agent Framework

**路线 Microsoft Agent Framework + C\#**

把 Agent 能力融入现有 .NET Web API、后台任务、企业服务和业务系统的人。

主要学习：Agent、Workflow、工具、会话状态、中间件、人工介入、检查点和持久化。

Microsoft Agent Framework 已有 Python 和 .NET 的开发文档，包含 Agent、工作流、工具、记忆、检查点及人工介入等能力。 [Microsoft Learn](https://learn.microsoft.com/en-us/agent-framework/?utm_source=chatgpt.com) [Microsoft Learn](https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/?utm_source=chatgpt.com)

官方入口：[Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/)。



### 📚《从零开始构建智能体》

- **电子书：** [Hello-Agents 官方教程](https://hello-agents.datawhale.cc/)
