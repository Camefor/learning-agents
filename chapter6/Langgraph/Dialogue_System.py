
"""
LangGraph 将智能体的执行流程建模为一种状态机（State Machine），并将其表示为有向图（Directed Graph）。
在这种范式中，图的节点（Nodes）代表一个具体的计算步骤（如调用 LLM、执行工具），而边（Edges）则定义了从一个节点到另一个节点的跳转逻辑。
这种设计的革命性之处在于它天然支持循环，使得构建能够进行迭代、反思和自我修正的复杂智能体工作流变得前所未有的直观和简单。

#  LangGraph，三个基本构成要素。

# 一： 全局状态（State）。整个图的执行过程都围绕一个共享的状态对象进行。
# 这个状态通常被定义为一个 Python 的 TypedDict，它可以包含任何你需要追踪的信息，如对话历史、中间结果、迭代次数等。
# 所有的节点都能读取和更新这个中心状态。

# 二：节点（Nodes）。每个节点都是一个接收当前状态作为输入、并返回一个更新后的状态作为输出的 Python 函数。
# 节点是执行具体工作的单元。

# 三：边（Edges）。边负责连接节点，定义工作流的方向。最简单的边是常规边，它指定了一个节点的输出总是流向另一个固定的节点。
# 而 LangGraph 最强大的功能在于条件边（Conditional Edges）。它通过一个函数来判断当前的状态，然后动态地决定下一步应该跳转到哪个节点。
# 这正是实现循环和复杂逻辑分支的关键。

"""

"""
案例
智能搜索助手 - 基于 LangGraph + Tavily API 的真实搜索系统
1. 理解用户需求
2. 使用Tavily API真实搜索信息  
3. 生成基于搜索结果的回答
"""

# 遵循一个清晰、固定的三步流程来回答用户的问题：

# 理解 (Understand)：首先，分析用户的查询意图。
# 搜索 (Search)：然后，模拟搜索与意图相关的信息。
# 回答 (Answer)：最后，基于意图和搜索到的信息，生成最终答案。
# 这个案例将清晰地展示如何定义状态、创建节点以及将它们线性地连接成一个完整的工作流。
# 我们将代码分解为四个核心步骤：定义状态、创建节点、构建图、以及运行应用。


import asyncio
from typing import TypedDict, Annotated
import os
from dotenv import load_dotenv
from tavily import TavilyClient

from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from langgraph.graph import StateGraph,START,END
from langgraph.checkpoint.memory import InMemorySaver


# 定义状态结构
# 这是一个共享的数据结构，它在图的每个节点之间传递，作为工作流的持久化上下文。
class SearchState(TypedDict):
    messages: Annotated[list,add_messages]
    user_query: str # 经过LLM理解后的用户需求总结
    search_query: str # 优化后用于Tavily API的搜索查询
    search_results: str # Tavily搜索返回的结果
    final_answer: str # 最终生成的答案
    step:   str # 标记当前步骤

"""
# 定义工作流节点
"""

# 加载 .env 文件中的环境变量
load_dotenv()

# 初始化模型
llm = ChatOpenAI(
    model = os.getenv("LLM_MODEL_ID"),
    api_key = os.getenv("LLM_API_KEY"),
    base_url = os.getenv("LLM_BASE_URL"),
    temperature = 0.7
)
# 初始化 Tavily 客户端
tavily_client = TavilyClient(
    api_key = os.getenv("TAVILY_API_KEY")
)

#第一个节点：理解与查询节点

def understand_query_node(state: SearchState) -> dict:
    """步骤1：理解用户查询并生成搜索关键词"""
    user_message = state['messages'][-1].content  # 获取用户的最新消息

    understand_prompt = f"""分析用户的查询："{user_message}"
请完成两个任务：
1. 简洁总结用户想要了解什么
2. 生成最适合搜索引擎的关键词（中英文均可，要精准）

格式：
理解：[用户需求总结]
搜索词：[最佳搜索关键词]"""

    response = llm.invoke([SystemMessage(content=understand_prompt)])
    response_text = response.content

    # 解析 LLM 的输出,提取搜索关键词
    search_query = user_message  # 默认使用用户的原始输入作为搜索查询
    if "搜索词：" in response_text:
        search_query = response_text.split("搜索词：")[1].strip() #大模型给整的
    elif "搜索关键词：" in response_text:
        search_query = response_text.split("搜索关键词：")[1].strip()

    # 该节点通过一个结构化的提示，要求 LLM 同时完成“意图理解”和“关键词生成”两个任务，
    # 并将解析出的专用搜索关键词更新到状态的 search_query 字段中，为下一步的精确搜索做好准备。

    return {
        "user_query": response_text,
        "search_query": search_query,
        "step": "understood",
        "messages":[AIMessage(content=f"我理解您的需求: {response_text}")]
    }



# 第二个节点：搜索节点

def tavily_search_node(state: SearchState) -> dict:
    """步骤2：使用Tavily API进行真实搜索"""
    search_query = state['search_query']

    try:
        # 发起真实的 API 调用
        print(f"🔍 正在搜索: {search_query}")
        response = tavily_client.search(
            query = search_query,
            search_depth = "basic",
            max_results = 5,
            include_answer = True
        )

        # 处理搜索结果
        search_results = ""

        # 优先使用Tavily的综合答案
        if response.get("answer"):
            search_results = f"综合答案：\n{response['answer']}\n\n"

        # 添加具体的搜索结果
        if response.get("results"):
            search_results += "相关信息：\n"
            for i, result in enumerate(response["results"][:3],1):
                title = result.get("title", "")
                content = result.get("content", "")
                url = result.get("url", "")
                search_results += f"{i}. {title}\n{content}\n链接: {url}\n\n"

        if not search_results:
            search_results = "抱歉，未找到相关信息。"

        return {
            "search_results": search_results,
            "step": "searched",
            "messages": [AIMessage(content=f"✅ 搜索完成！找到了相关信息，正在为您整理答案...")]
        }

    except Exception as e:
        print(f"搜索失败: {e}")
        # 如果搜索失败，更新 step 状态为 "search_failed"，这个状态将被下一个节点用来触发备用方案。
        return {
            "search_results": f"搜索失败：{e}",
            "step": "search_failed",
            "messages":[AIMessage(content="❌ 搜索遇到问题...请稍后再试。")]
        }


# 第三个节点：回答节点

def generate_answer_node(state: SearchState) -> SearchState:
    """步骤3：基于搜索结果生成最终回答"""

    # 检查是否有搜索结果
    if state["step"] == "search_failed":
        # 如果搜索失败，基于LLM知识回答
        fallback_prompt = f"""搜索API暂时不可用，请基于您的知识回答用户的问题：

用户问题：{state['user_query']}

请提供一个有用的回答，并说明这是基于已有知识的回答。"""

        # 相当于LLM大模型训练时的知识库回答 肯定不如联网搜索回答的时效性/准确性高
        response = llm.invoke([SystemMessage(content=fallback_prompt)])


        return {
            "final_answer": response.content,
            "step": "completed",
            "messages": [AIMessage(content=response.content)]
        }

    
    # 基于搜索结果生成答案
    # 相当于让ai大模型帮你整理已经联网搜索的准确的，最新的答案。帮你整理，梳理了一下。很奇妙，搁以前都只能程序很死板的处理，这里每次输出的结果可能都不会是完全一样，由llm大模型自主推理输出。很奇妙~
    answer_prompt = f"""基于以下搜索结果为用户提供完整、准确的答案：

用户问题：{state['user_query']}

搜索结果：
{state['search_results']}

请要求：
1. 综合搜索结果，提供准确、有用的回答
2. 如果是技术问题，提供具体的解决方案或代码
3. 引用重要信息的来源
4. 回答要结构清晰、易于理解
5. 如果搜索结果不够完整，请说明并提供补充建议"""

    response = llm.invoke([SystemMessage(content=answer_prompt)])

    return {
        "final_answer": response.content,
        "step": "completed",
        "messages": [AIMessage(content=response.content)]
    }


# 构建图(搜索工作流)  把上面定义的三个节点连接起来

def create_search_assistant():
    # API参考：https://reference.langchain.com/python/langgraph/graph/state/StateGraph
    workflow = StateGraph(SearchState)

    # 添加三个节点
    workflow.add_node("understand", understand_query_node)
    workflow.add_node("search", tavily_search_node)
    workflow.add_node("answer", generate_answer_node)

    # 设置线性流程
    # 很简明，线性/串行的 单一流程（没有复杂的判断）：
    # 开始-->让LLM理解用户的问题-->调用搜索API进行答案搜索-->回答-->结束
    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "search")
    workflow.add_edge("search", "answer")
    workflow.add_edge("answer", END)

    # 编译图
    memory = InMemorySaver()
    app = workflow.compile(checkpointer=memory)

    return app

async def main():
    """主函数：运行智能搜索助手"""

    # 检查API密钥
    if not os.getenv("TAVILY_API_KEY"):
        print("❌ 错误：请在.env文件中配置TAVILY_API_KEY")
        return

    app = create_search_assistant()
    
    print("🔍 智能搜索助手启动！")
    print("我会使用Tavily API为您搜索最新、最准确的信息")
    print("支持各种问题：新闻、技术、知识问答等")
    print("(输入 'quit' 退出)\n")

    session_count = 0

    while True:
        user_input = input("🤔 您想了解什么: ").strip()

        if user_input.lower() in ['quit','q','退出','exit']:
            print("👋 感谢使用智能搜索助手，再见！")
            break

        if not user_input:
            print("⚠️ 请输入有效的问题。")
            continue

        session_count += 1
        config = {"configurable":{"thread_id":f"search-session-{session_count}"}}

        #初始状态
        initial_state = {
            "messages":[HumanMessage(content=user_input)],
            "user_query":"",
            "search_query":"",
            "search_results":"",
            "final_answer":"",
            "step":"start"
        }

        try:
            print("\n" + "="*60)

            # 执行工作流
            async for output in app.astream(initial_state,config=config):
                for node_name, node_output in output.items():
                    if "messages" in node_output and node_output["messages"]:
                        latest_message = node_output["messages"][-1]
                        if isinstance(latest_message, AIMessage):
                            if node_name == "understand":
                                print(f"🧠 理解阶段: {latest_message.content}")
                            elif node_name == "search":
                                print(f"🔍 搜索阶段: {latest_message.content}")
                            elif node_name == "answer":
                                print(f"\n💡 最终回答:\n{latest_message.content}")


            print("\n" + "="*60 + "\n")


        except Exception as e:
            print(f"❌ 发生错误: {e}")
            print("请重新输入您的问题。\n")



if __name__ == "__main__":
    asyncio.run(main())