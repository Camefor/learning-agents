from dotenv import load_dotenv
# 加载 .env 文件中的环境变量
load_dotenv()

import os
from serpapi import SerpApiClient
from typing import Dict, Any

# 如果说大语言模型是智能体的大脑，
# 那么工具 (Tools) 就是其与外部世界交互的“手和脚”。
# 为了让ReAct范式能够真正解决我们设定的问题，智能体需要具备调用外部工具的能力。

# 一个联网搜索的工具：

def search(query: str) -> str:
    """
    一个基于SerpApi的实战网页搜索引擎工具。
    它会智能地解析搜索结果，优先返回直接答案或知识图谱信息。
    """
    print(f"🔍 正在执行 [SerpApi] 网页搜索: {query}")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "错误：SERPAPI_API_KEY 未在 .env 文件中配置。"

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "gl": "cn",  # 国家代码
            "hl": "zh-cn", # 语言代码
        }
        
        client = SerpApiClient(params)
        results = client.get_dict()
        
        # 智能解析：优先寻找最直接的答案
        if "answer_box_list" in results:
            return "\n".join(results["answer_box_list"])
        if "answer_box" in results and "answer" in results["answer_box"]:
            return results["answer_box"]["answer"]
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            # 如果没有直接答案，则返回前三个有机结果的摘要
            snippets = [
                f"[{i+1}] {res.get('title', '')}\n{res.get('snippet', '')}"
                for i, res in enumerate(results["organic_results"][:3])
            ]
            return "\n\n".join(snippets)
        
        return f"对不起，没有找到关于 '{query}' 的信息。"

    except Exception as e:
        return f"搜索时发生错误: {e}"




# 当智能体需要使用多种工具时（例如，除了搜索，还可能需要计算、查询数据库等），
# 我们需要一个统一的管理器来注册和调度这些工具。
# 为此，我们创建一个 ToolExecutor 类。

from typing import Dict,Any

class ToolExecutor:
    """
    一个工具执行器，负责管理和执行工具。
    """

    def __init__(self):
        self.tools:Dict[str,Dict[str,Any]] = {}

    def registerTool(self,name:str,description:str,func:callable):
        """
        向工具箱中注册一个新工具。
        :param name: 工具名称
        :param description: 工具描述
        :param func: 工具的执行函数
        """

        if name in self.tools:
            print(f"⚠️ 工具 '{name}' 已存在，将被覆盖。")

        self.tools[name] = {"description": description, "func": func}
        print(f"✅ 工具 '{name}' 已注册。")


    def getTool(self,name:str) -> callable:
        """
        根据工具名称获取工具的执行函数。
        :param name: 工具名称
        :return: 工具的执行函数
        """
        if name not in self.tools:
            raise ValueError(f"工具 '{name}' 未注册。")

        return self.tools.get(name, {}).get("func")


    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
                f"- {name}: {info['description']}" 
                for name, info in self.tools.items()
            ])




# 现在，我们将 search 工具注册到 ToolExecutor 中，并模拟一次调用，
# 以验证整个流程是否正常工作。


# --- 工具初始化与使用示例 ---
if __name__ == "__main__":
    # 1. 初始化工具执行器
    toolExecutor  = ToolExecutor()

    # 2. 注册我们的实战搜索工具
    toolExecutor.registerTool(
        name="Search",
        description="一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。",
        func=search
    )

    # 显示所有可用工具
    print("\n📦 可用工具列表:")
    print(toolExecutor.getAvailableTools())

    # 智能体的Action调用，这次我们问一个实时性的问题
    # 模拟调用 search 工具

    tool_name = "Search"
    tool_input = "英伟达最新的GPU型号是什么？"

    tool_function = toolExecutor.getTool(tool_name);
    if  tool_function:
        observation = tool_function(tool_input)
        print(f"\n📝 工具 '{tool_name}' 的执行结果:\n{observation}")
    else:
        print(f"❌ 工具 '{tool_name}' 未找到。")

