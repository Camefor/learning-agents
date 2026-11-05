
● 三国狼人杀 Demo 调用链路与 AgentScope 用法详解

  先给你一个整体心智模型，再一层层往下拆。

  ---
  一、先用一个类比理解整个项目

  把项目想象成一场三国狼人杀剧组：

  ┌──────────┬────────────────────────────┬─────────────────────────────────┐
  │ 剧组角色 │        代码里的对象        │              职责               │
  ├──────────┼────────────────────────────┼─────────────────────────────────┤
  │ 导演/裁  │ GameModerator + run_game() │ 掌握全局真相、安排流程、宣布结  │
  │ 判       │                            │ 果                              │
  ├──────────┼────────────────────────────┼─────────────────────────────────┤
  │ 演员     │ 6 个 ReActAgent            │ 每人一个 LLM 大脑 +             │
  │          │                            │ 一本私人日记（Memory）          │
  ├──────────┼────────────────────────────┼─────────────────────────────────┤
  │ 台词/通  │ Msg                        │ 所有信息传递的统一载体          │
  │ 告       │                            │                                 │
  ├──────────┼────────────────────────────┼─────────────────────────────────┤
  │ 群聊房间 │ MsgHub                     │ 让房间里的演员互相听见发言      │
  ├──────────┼────────────────────────────┼─────────────────────────────────┤
  │ 导演口令 │ sequential_pipeline /      │ 轮流发言 / 同时投票             │
  │          │ fanout_pipeline            │                                 │
  ├──────────┼────────────────────────────┼─────────────────────────────────┤
  │ 决策表格 │ structured_model（Pydantic │ 强制演员按格式给出投票、用药等  │
  │          │ ）                         │ 决定                            │
  └──────────┴────────────────────────────┴─────────────────────────────────┘

  最重要的一句话：

  ▎ 引擎掌握真相，Agent 只掌握自己看到的消息。

  self.roles 里存着每个人的真实身份，但 Agent 永远不能直接读它；Agent
  只能通过主持人发给它的 Msg 做判断。这是 Agent
  开发里非常经典的“确定性业务状态”与“LLM 信念状态”分离模式。

  ---
  二、项目文件分工

  AgentScopeDemo/
  ├── main_cn.py              # 游戏主循环 + AgentScope 编排（核心）
  ├── game_roles.py           # 角色定义、阵营、6/8/9 人标准配置
  ├── prompt_cn.py            # 每个角色的 system prompt（人设）
  ├── structured_output_cn.py # Pydantic 结构化输出模型
  ├── utils_cn.py             # 主持人、投票统计、胜负判断
  ├── requirements.txt
  └── .env                    # DASHSCOPE_API_KEY

  ---
  三、宏观调用链：从 python main_cn.py 到游戏结束

  __main__
  └─ asyncio.run(main())                          main_cn.py:405
     └─ main()                                    main_cn.py:394
        ├─ 检查 DASHSCOPE_API_KEY
        ├─ game = ThreeKingdomsWherewolfGame()    main_cn.py:400
        └─ await game.run_game()                  main_cn.py:403
           │
           ├─ await setup_game()                  main_cn.py:90
           │   └─ for 每个角色:
           │       └─ await create_player()       main_cn.py:61
           │           ├─ 创建 DashScopeChatModel
           │           ├─ 创建 ReActAgent
           │           └─ await agent.observe(身份公告)   ← 只有该玩家知道
           │
           └─ for round in 1..10:                 main_cn.py:337
               │
               ├── 夜晚
               │   ├─ werewold_phase()            main_cn.py:128
               │   │   ├─ MsgHub(狼人)             ← 狼人互相能听见
               │   │   ├─ 狼人讨论 × 3 轮
               │   │   └─ 狼人投票击杀
               │   ├─ seer_phase()                main_cn.py:177
               │   ├─ witch_phase()               main_cn.py:206
               │   ├─ update_alive_players()
               │   ├─ death_announcement()
               │   └─ check_winning_cn()
               │
               └── 白天
                   ├─ day_phase()                 main_cn.py:294
                   │   ├─ MsgHub(所有存活玩家)
                   │   ├─ sequential_pipeline()   ← 顺序发言
                   │   └─ fanout_pipeline()       ← 全体投票
                   ├─ hunter_phase()              main_cn.py:247
                   ├─ update_alive_players()
                   └─ check_winning_cn()

  ---
  四、AgentScope 核心概念速查

  ┌──────────────┬─────────────────────────────┬─────────────────────────────┐
  │     概念     │      本 demo 中的对象       │       你可以这样理解        │
  ├──────────────┼─────────────────────────────┼─────────────────────────────┤
  │ AgentBase    │ ReActAgent、GameModerator   │ Agent 基类，提供            │
  │              │                             │ observe/reply/print 和钩子  │
  ├──────────────┼─────────────────────────────┼─────────────────────────────┤
  │ Msg          │ 主持人公告、玩家发言        │ 统一消息：name/content/role │
  │              │                             │ /metadata                   │
  ├──────────────┼─────────────────────────────┼─────────────────────────────┤
  │ Model        │ DashScopeChatModel          │ LLM 接入层，屏蔽不同厂商    │
  │              │                             │ API                         │
  ├──────────────┼─────────────────────────────┼─────────────────────────────┤
  │ Formatter    │ DashScopeMultiAgentFormatte │ 把内部 Msg 转成厂商要求的   │
  │              │ r                           │ messages                    │
  ├──────────────┼─────────────────────────────┼─────────────────────────────┤
  │ Memory       │ 默认 InMemoryMemory         │ 每个 Agent 的私人对话历史   │
  ├──────────────┼─────────────────────────────┼─────────────────────────────┤
  │ Toolkit      │ 默认空 Toolkit              │ 工具注册表；本 demo         │
  │              │                             │ 没注册业务工具              │
  ├──────────────┼─────────────────────────────┼─────────────────────────────┤
  │ MsgHub       │ 狼人群聊 / 白天全体会议     │ 订阅+广播，让 Agent         │
  │              │                             │ 互相听见                    │
  ├──────────────┼─────────────────────────────┼─────────────────────────────┤
  │ Pipeline     │ sequential_pipeline、fanout │ 多 Agent 编排语法糖         │
  │              │ _pipeline                   │                             │
  ├──────────────┼─────────────────────────────┼─────────────────────────────┤
  │ structured_m │ 各种 Pydantic 模型          │ 强制 Agent                  │
  │ odel         │                             │ 输出机器可读的决策          │
  └──────────────┴─────────────────────────────┴─────────────────────────────┘

  ---
  五、微观调用栈：一次 await wolf(...) 到底发生了什么

  这是整个项目最值得吃透的一段。以狼人讨论为例：

  await wolf(structured_model=DiscussionModelCN)   # main_cn.py:149

  展开后：

  AgentBase.__call__                         agentscope/agent/_agent_base.py:228
  ├─ ReActAgent.reply(msg=None, structured_model=...)   _react_agent.py:199
  │  ├─ memory.add(None)                     ← msg 为 None，直接忽略
  │  ├─ toolkit.set_extended_model(
  │  │      "generate_response", DiscussionModelCN)      ← 关键！
  │  └─ for iter in range(max_iters=10):
  │     ├─ ReActAgent._reasoning()                       _react_agent.py:287
  │     │  ├─ formatter.format([
  │     │  │      Msg("system", sys_prompt),
  │     │  │      *await memory.get_memory()
  │     │  │  ])
  │     │  ├─ model(prompt, tools=toolkit.get_json_schemas())
  │     │  │  └─ 调 DashScope API（默认流式）
  │     │  └─ 如果模型只回了纯文本：
  │     │     把它包装成一次 generate_response 工具调用
  │     ├─ ReActAgent._acting(tool_call)                 _react_agent.py:363
  │     │  └─ toolkit.call_tool_function(...)
  │     │     └─ ReActAgent.generate_response(**kwargs)  _react_agent.py:487
  │     │        ├─ Msg(name, response, "assistant")
  │     │        └─ metadata = structured_model.model_validate(kwargs)
  │     └─ 拿到 Msg → 跳出循环
  │  ├─ memory.add(reply_msg)
  │  └─ return reply_msg
  └─ finally: __call__ 把 reply_msg 广播给 subscribers
     └─ for 其他狼人: await other.observe(reply_msg)     _agent_base.py:249

  几个关键点：

  1. await agent(...) 不是一次 LLM 调用，而是 AgentBase.__call__。
  2. __call__ 内部调用 reply()，reply() 是一个 ReAct 循环，最多 max_iters=10
  次。
  3. 本 demo 没有注册任何业务工具，所以“Act”阶段通常只有内置的
  generate_response（终止函数），一般一轮就结束。
  4. reply() 返回后，__call__ 才把消息广播给 MsgHub 里的其他 Agent。

  ---
  六、三个编排原语的精确语义

  6.1 MsgHub：订阅 + 广播，不是“聊天记录仓库”

  async with MsgHub(
      self.werewolves,
      enable_auto_broadcast=True,
      announcement=await self.moderator.announce("狼人们请讨论...")
  ) as hub:
      ...

  进入 async with 时：

  MsgHub.__aenter__                      _msghub.py:71
  ├─ _reset_subscriber()
  │  └─ 每个狼人的 _subscribers[hub] = 其他狼人（排除自己）
  └─ broadcast(announcement)
     └─ for 每个狼人: await wolf.observe(announcement)
        └─ memory.add(announcement)

  之后任何狼人执行 await wolf(...)，__call__ 的 finally 会：

  _broadcast_to_subscribers(reply_msg)
  └─ 其他狼人.observe(reply_msg)   ← 只写记忆，不触发 LLM

  所以 MsgHub 本身不存消息，它只负责给别人订阅、把消息塞进别人的 Memory。

  投票前调用：

  hub.set_auto_broadcast(False)   # main_cn.py:153

  这一步会移除订阅。之后狼人的投票消息不会被其他狼人看到——这就是“暗票”的实现方式
  。

  6.2 sequential_pipeline：传话游戏

  async def sequential_pipeline(agents, msg=None):
      for agent in agents:
          msg = await agent(msg)
      return msg

  - 第一个 Agent 收到 None，靠 Memory 里的上下文发言。
  - 前一个 Agent 的输出会成为后一个 Agent 的显式输入。
  - 在 MsgHub 自动广播开启时，前一个 Agent 的输出同时也会通过 observe 进入后一个
   Agent 的记忆。
  - 不用担心重复：InMemoryMemory.add() 会按 Msg.id
  去重（_in_memory_memory.py:111）。

  6.3 fanout_pipeline：同一张卷子发给所有人

  return [await agent(deepcopy(msg), **kwargs) for agent in agents]

  或并发版本：

  tasks = [asyncio.create_task(agent(deepcopy(msg), **kwargs)) for agent in
  agents]
  return await asyncio.gather(*tasks)

  - 每个 Agent 收到同一消息的深拷贝，互不影响。
  - enable_gather=False 时顺序执行（本 demo 的投票采用这种方式，避免并发调用
  API）。
  - 返回值顺序与 agents 顺序一致，所以可以用 vote_msgs[i] 对应
  alive_players[i]。

  ---
  七、structured_model 的底层实现（重点）

  很多初学者以为 structured_model 是给模型加了个“JSON 模式”。在 AgentScope 1.0.2
   的 ReActAgent 里，实际机制是：

  structured_model = DiscussionModelCN
          │
          ▼
  toolkit.set_extended_model("generate_response", DiscussionModelCN)
          │
          ▼
  内置工具 generate_response 的 JSON Schema 被扩展：
  {
    "response": "string",
    "reach_agreement": "boolean",
    "confidence_level": "integer",
    "key_evidence": "string"
  }
          │
          ▼
  模型必须调用 generate_response(...) 并填这些字段
          │
          ▼
  generate_response() 用 Pydantic 校验 kwargs
          │
          ▼
  Msg.metadata = { ...结构化结果... }

  所以：

  - 结构化结果在 msg.metadata，不在 msg.content。
  - 代码里读取投票的方式是 vote_msg.metadata.get("vote")，这是对的。
  - 如果模型不调用工具、只回一段普通文本，框架会把它包装成
  generate_response(response="...")；此时结构化字段缺失，Pydantic
  校验失败，模型会被要求重试，最多 max_iters 次。这会额外消耗 token。
  - prompt_cn.py 里要求“严格输出 JSON”，和工具调用机制略有重复；更稳妥的写法是让
   system prompt 专注人设，把格式要求交给 structured_model。

  ---
  八、逐阶段业务链路

  8.1 建局：setup_game()（main_cn.py:90）

  GameRoles.get_standard_setup(6)
    → ["狼人", "狼人", "预言家", "女巫", "村民", "村民"]

  random.sample(9 个三国人物, 6)
    → 例如 ["刘备", "赵云", "司马懿", "孙权", "诸葛亮", "关羽"]

  zip(roles, characters)
    → 逐个 create_player()

  create_player() 做了三件事：

  1. 记录真实身份：self.roles[name] = role
  2. 创建 Agent：
  ReActAgent(
      name=name,
      sys_prompt=ChinesePrompts.get_role_prompt(role, character),
      model=DashScopeChatModel(...),
      formatter=DashScopeMultiAgentFormatter(),
  )
  3. 把身份公告 observe 给这个 Agent——只有他自己知道。

  注意：6 人局没有猎人，所以 self.hunter 为空，hunter_phase()
  在这个配置下不会产生任何效果。

  另外，setup_game() 里“游戏开始”的公告写在了 for
  循环内部（main_cn.py:121），会随玩家人数重复打印；而且它的返回值没有被任何
  Agent observe，所以只是控制台输出。

  8.2 夜晚

  狼人阶段 werewold_phase()（main_cn.py:128）

  MsgHub(狼人, announcement="狼人们请讨论...")
  ├─ 讨论 3 轮：
  │    每个狼人 await wolf(structured_model=DiscussionModelCN)
  │    → 发言自动广播给其他狼人
  ├─ set_auto_broadcast(False)
  └─ fanout_pipeline(狼人, msg="请选择击杀目标",
                     structured_model=WerewolfKillModelCN,
                     enable_gather=False)
        → 每个狼人返回 Msg，metadata["target"] 是击杀目标
        → majority_vote_cn() 统计票数

  预言家阶段（main_cn.py:177）

  主持人私发："预言家请睁眼..."
  seer_agent.observe(...)
  seer_agent(structured_model=get_seer_model_cn(alive_players))
    → metadata["target"]
  引擎查 self.roles[target]（真实身份）
  主持人私发查验结果 → seer_agent.observe(...)

  女巫阶段（main_cn.py:206）

  主持人私发死亡信息 → witch_agent.observe(...)
  witch_agent(structured_model=WitchActionModelCN)
    → metadata["use_antidote"], metadata["use_poison"], metadata["target_name"]
  更新解药/毒药状态，返回最终死亡名单

  结算

  night_deaths = [final_killed, poisoned_player]
  update_alive_players(night_deaths)
  death_announcement(night_deaths)   # 只打印，不进 Agent 记忆
  check_winning_cn(...)

  8.3 白天

  讨论 day_phase()（main_cn.py:294）

  MsgHub(所有存活玩家, announcement="现在开始自由讨论...")
  ├─ sequential_pipeline(alive_players)
  │    按顺序发言，每个人的发言自动广播给所有人
  ├─ set_auto_broadcast(False)
  └─ fanout_pipeline(所有存活玩家, msg="请投票...",
                     structured_model=get_vote_model_cn(alive_players),
                     enable_gather=False)
        → metadata["vote"] 统计票数
        → majority_vote_cn() 得到被淘汰者

  猎人阶段（main_cn.py:247）

  如果 voted_out 正好是猎人：
    主持人私发："猎人发动技能..."
    hunter_agent(structured_model=get_hunter_model_cn(alive_players))
      → metadata["shoot"], metadata["target"]

  结算

  day_deaths = [voted_out, hunter_shot]
  update_alive_players(day_deaths)
  check_winning_cn(...)

  8.4 胜负判断（utils_cn.py:49）

  alive_roles = [roles.get(p.name, "村民") for p in alive_players]
  werewolf_count = alive_roles.count("狼人")
  villager_count = len(alive_roles) - werewolf_count

  if werewolf_count == 0:                 # 好人胜
  elif werewolf_count >= villager_count:  # 狼人胜

  ---
  九、初学者最容易误解的 10 件事

  1. observe() 不会调用 LLM。
  它只是 memory.add(msg)（_react_agent.py:423）。真正触发 LLM 的是 agent(...) /
  reply()。
  2. agent(...) 不只是 reply()。
  AgentBase.__call__ 会在 reply() 之后，把回复广播给订阅者。这是 MsgHub
  能工作的关键。
  3. Agent 之间不共享记忆。
  它们只共享“被广播的消息”。每个 Agent 有自己的 InMemoryMemory。
  4. 结构化结果在 metadata，不在 content。
  msg.content 是自然语言，msg.metadata 才是 Pydantic 校验后的字典。
  5. MsgHub 里默认所有发言都会被其他人听见。
  投票、私密行动前必须 set_auto_broadcast(False)，否则暗票会变成明票。
  6. “主持人公告”不一定进了 Agent 的记忆。
  moderator.announce() 只负责打印并返回 Msg；只有把返回值交给 observe、MsgHub 或
   pipeline，Agent 才真正“看到”。
  7. 这个 demo 的 Agent 没有业务工具。
  ReAct 的“Act”阶段基本只有内置的 generate_response。它更像“带记忆的结构化决策器
  ”，而不是会查数据库、算票数的工具型 Agent。
  8. 记忆会无限增长。
  DashScopeMultiAgentFormatter() 没有设置
  max_tokens，长局可能超出模型上下文。生产环境要配置截断或摘要。
  9. 每个 Agent 都新建了一个 Model 和 Formatter。
  它们本身不保存对话状态，可以安全地共享一份 DashScopeChatModel 和
  DashScopeMultiAgentFormatter，减少对象创建。
  10. enable_thinking=True 会增加延迟和费用。
  它适合需要推理的模型；不是所有模型都支持，配置前要确认。

  ---
  十、这个 demo 本身可以改进的地方

  ┌───────────────────────────┬────────────────────────┬────────────────────┐
  │           问题            │          位置          │        建议        │
  ├───────────────────────────┼────────────────────────┼────────────────────┤
  │ 狼人击杀目标用            │ structured_output_cn.p │ 改成               │
  │ str，可投给任何人         │ y:106                  │ Literal[存活玩家]  │
  ├───────────────────────────┼────────────────────────┼────────────────────┤
  │ 角色性格 CHARACTER_TRAITS │ game_roles.py:48       │ 拼进               │
  │  没被使用                 │                        │ get_role_prompt()  │
  ├───────────────────────────┼────────────────────────┼────────────────────┤
  │ 死亡/投票结果只打印，不进 │                        │ 需要时用           │
  │  Agent 记忆               │ run_game / day_phase   │ MsgHub.broadcast() │
  │                           │                        │  广播              │
  ├───────────────────────────┼────────────────────────┼────────────────────┤
  │ 平票处理是确定性的        │ utils_cn.py:40         │ 明确随机平票或重新 │
  │                           │                        │ 投票               │
  ├───────────────────────────┼────────────────────────┼────────────────────┤
  │                           │                        │ 默认配置下         │
  │ 6 人局没有猎人            │ game_roles.py:88       │ hunter_phase       │
  │                           │                        │ 是死代码           │
  ├───────────────────────────┼────────────────────────┼────────────────────┤
  │ MAX_DISCUSSION_ROUND=3 ×  │ main_cn.py /           │ 注意 API           │
  │ 6 人 × 10 轮              │ utils_cn.py            │ 调用量和费用       │
  ├───────────────────────────┼────────────────────────┼────────────────────┤
  │ 异常直接终止整局          │ run_game 的 except     │ 可记录状态后继续或 │
  │                           │                        │ 重开               │
  └───────────────────────────┴────────────────────────┴────────────────────┘

  ---
  十一、如果你想继续扩展

  加一个业务工具（让 Agent 真的能“查身份”）：

  from agentscope.tool import Toolkit

  def get_alive_players() -> list[str]:
      """返回当前存活玩家姓名列表。"""
      ...

  toolkit = Toolkit(tools=[get_alive_players])
  agent = ReActAgent(..., toolkit=toolkit)

  加了工具后，ReAct
  循环才真正有意义：模型会先调用工具、拿到结果、再继续推理，直到调用
  generate_response。

  共享模型和 Formatter：

  model = DashScopeChatModel(...)
  formatter = DashScopeMultiAgentFormatter()

  agent = ReActAgent(..., model=model, formatter=formatter)

  限制记忆长度：

  formatter = DashScopeMultiAgentFormatter(max_tokens=32000)

  并发投票：

  fanout_pipeline(..., enable_gather=True)

  前提是 API 能承受并发，并且你不依赖投票顺序。

  ---
  十二、一页速查总结

  ① 引擎（GameModerator + run_game）掌握真相和规则
  ② 每个 ReActAgent = LLM + 私人 Memory + 统一 Msg 接口
  ③ observe = 只听；agent(...) = 说；__call__ 自动广播
  ④ MsgHub = 订阅 + 广播；set_auto_broadcast(False) = 暗票
  ⑤ sequential = 传话；fanout = 同一张卷子发给所有人
  ⑥ structured_model 通过扩展 generate_response 工具 Schema 实现
  ⑦ 结构化结果读 msg.metadata，不读 msg.content
  ⑧ Agent 只知道自己收到过的消息，不共享记忆
  ⑨ 长局要截断记忆；enable_thinking 要算成本
  ⑩ 让 LLM 做决策，让引擎做状态变更和规则裁决

  如果你愿意，下一步我可以带你逐行读一次 ReActAgent.reply() 的源码，或者基于这个
   demo 加一个自定义工具，让你亲手体验完整的 ReAct 循环。

✻ Baked for 2m 59s