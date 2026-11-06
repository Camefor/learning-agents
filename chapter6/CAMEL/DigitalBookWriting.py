# CAMEL最初的核心目标是探索如何在最少的人类干预下，让两个智能体通过“角色扮演”自主协作解决复杂任务
# CAMEL 实现自主协作的基石是两大核心概念：角色扮演 (Role-Playing) 和 引导性提示 (Inception Prompting)。


# AI科普电子书 案例

from colorama import Fore
from camel.societies import RolePlaying
from camel.utils import print_text_animated
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from dotenv import load_dotenv
import os

load_dotenv()
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL_ID")

# 创建模型：
# API参考：https://docs.camel-ai.org/reference/camel.models.model_factory#camel-models-model-factory
#         https://docs.camel-ai.org/key_modules/models#using-openai-compatible-models
model = ModelFactory.create(
    # model_platform=ModelPlatformType.OPENAI,
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type=LLM_MODEL,
    url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
    # model_config_dict={
    #     "temperature": 0.2,                   # 采样温度
    #     "max_tokens": 1024,                   # 最大生成 Token 数
    #     # 也可以传入其他后端支持的参数，如 top_p, seed 等
    # },
)

# 定义协作任务
task_prompt = """
使用中文，创作一本关于"拖延症心理学"的短篇电子书，目标读者是对心理学感兴趣的普通大众。
要求：
1. 内容科学严谨，基于实证研究
2. 语言通俗易懂，避免过多专业术语
3. 包含实用的改善建议和案例分析
4. 篇幅控制在800-1000字
5. 结构清晰，包含引言、核心章节和总结
"""

print(Fore.YELLOW + f"协作任务:\n{task_prompt}\n")

# task_prompt 是整个协作的“任务说明书”。它不仅是我们要完成的目标，也将在幕后被 CAMEL 用来生成“引导性提示”，确保两位智能体的对话始终围绕这个核心目标展开。


# 开始角色扮演
# 初始化角色扮演“社会”

# AI 作家作为 "user"，负责提出写作结构和要求
# AI 心理学家作为 "assistant"，负责提供专业知识和内容

#  RolePlaying 会话实例。
#  这是 CAMEL 的核心操作，它根据我们提供的角色和任务，快速构建一个双智能体协作“社会”。CAMEL 提供的高级 API，它封装了复杂的提示工程。
#  API 参考：https://docs.camel-ai.org/cookbooks/multi_agent_society/agents_society#2-1-roleplaying
role_play_session = RolePlaying(
    user_role_name="作家", #user 角色是对话的“推动者”和“需求方”
    user_agent_kwargs=dict(model=model),
    assistant_role_name="心理学家", #assistant 角色是“执行者”和“方案提供方”
    assistant_agent_kwargs=dict(model=model),
    task_prompt=task_prompt,
    model=model,
    with_task_specify=False, # 在本例中，我们直接使用给定的task_prompt; 
    # 自定义大模型提供商抽疯了，两个ai开始算加减乘除法。。。
    # 用了千问的模型发现可以 
    # with_task_specify=True,
    # task_specify_agent_kwargs=dict(model=model),
    output_language = "中文"
)

print(Fore.CYAN + f"具体任务描述:\n{role_play_session.task_prompt}\n")


# 开始协作对话

chat_turn_limit,n = 30,0

# 调用 init_chat() 方法，来获得由AI生成的初始化消息
# https://docs.camel-ai.org/reference/camel.societies.role_playing#init_chat
input_msg = role_play_session.init_chat()

while n < chat_turn_limit:
    n +=1
    # step() 方法驱动一轮完整的对话，AI 用户和 AI 助理各发言一次
    assistant_response,user_response = role_play_session.step(input_msg)

    #检查是否有消息返回，防止对话提前终止
    if assistant_response.msg is None or user_response.msg is None:
        break

    print_text_animated(Fore.BLUE + f"作家 (AI User):\n\n{user_response.msg.content}\n")
    print_text_animated(Fore.GREEN + f"心理学家 (AI Assistant):\n\n{assistant_response.msg.content}\n")

    # 检查任务完成标志
    if "<CAMEL_TASK_DONE>" in user_response.msg.content or "<CAMEL_TASK_DONE>" in assistant_response.msg.content:
        print(Fore.MAGENTA + "✅ 电子书创作完成！")
        break

    # 将助理的回复作为下一轮对话的输入
    input_msg = assistant_response.msg

print(Fore.YELLOW + f"总共进行了 {n} 轮协作对话")

"""
这段 while 循环是自动化协作的核心。对话由 init_chat() 方法基于任务和角色自动开启，无需人工编写开场白。循环的每一步都通过调用 step() 来驱动一轮完整的交互（作家提需求、心理学家给内容），并将上一轮心理学家的输出作为下一轮的输入，形成环-环相扣的创作链。整个过程将持续进行，直到达到预设的对话轮次上限，或任一智能体输出任务完成标志 <CAMEL_TASK_DONE> 后自动终止。
"""

