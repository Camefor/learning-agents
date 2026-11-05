# 封装基础 LLM 调用函数:
# 为了让代码结构更清晰、更易于复用，我们来定义一个专属的LLM客户端类。
# 这个类将封装所有与模型服务交互的细节，让我们的主逻辑可以更专注于智能体的构建。

import os
from pyexpat.errors import messages 
from openai import OpenAI
from dotenv import load_dotenv
from typing import List,Dict

# 加载 .env 文件中的环境变量
load_dotenv()


class HelloAgentsLLM:
    """
    为本书 "Hello Agents" 定制的LLM客户端。
    它用于调用任何兼容OpenAI接口的服务，并默认使用流式响应。
    """

    def __init__(self,model:str = None,apiKey:str = None,base_url:str = None, timeout: int = None):
        """
        初始化LLM客户端。
        :param model: 模型ID，默认为环境变量中的值。
        :param apiKey: API密钥，默认为环境变量中的值。
        :param base_url: 基础URL，默认为环境变量中的值。
        :param timeout: 请求超时时间，单位为秒，默认为None（无限制）。
        """

        self.model = model or os.getenv("LLM_MODEL_ID")
        apikey = apiKey or os.getenv("LLM_API_KEY")
        baseUrl = base_url or os.getenv("LLM_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))  # 默认超时时间为60秒

        if not all([self.model, apikey, baseUrl]):
            raise ValueError("模型ID、API密钥和服务地址必须被提供或在.env文件中定义。")

        # 初始化OpenAI客户端
        self.client = OpenAI(api_key=apikey, base_url=baseUrl, timeout=timeout)


    def think(self, messages: List[Dict[str,str]], temperature: float = 0) -> str:
        """
        调用LLM进行思考（生成文本）。
        :param messages: 消息列表，每条消息是一个字典，包含角色和内容。
        :param temperature: 控制生成文本的随机性，值越高越随机。
        :return: 模型生成的文本。
        """
        
        print(f"🧠 正在调用 {self.model} 模型...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True
            )
            # 处理流式响应

            print("💡大语言模型响应成功:")
            collected_content = []
            for chunk in response:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content or ""
                print(content, end="", flush=True)  # 实时打印输出
                collected_content.append(content)
            print()  # 在流式输出结束后换行
            return "".join(collected_content)
        except Exception as e:
            print(f"❌ 调用LLM API 时发生错误: {e}")
            return None


# --- 客户端使用示例 ---

if __name__ == "__main__":
    try:

        # 创建LLM客户端实例
        llmClient  = HelloAgentsLLM()

        # 定义消息列表
        exampleMessages = [
            {"role": "system", "content": "You are a helpful assistant that writes Python code."},
            {"role": "user", "content": "请帮我写一首关于春天的诗。"}
        ]

        # 调用think方法获取模型响应
        print("--- 调用LLM ---")
        responseText  = llmClient .think(exampleMessages, temperature=0.7)
        if responseText:
            print("\n\n--- 完整模型响应 ---")
            print(responseText)

    except ValueError as e:
        print(e)