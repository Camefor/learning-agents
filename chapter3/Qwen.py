import openvino as ov
import openvino_genai as ov_genai


NPU_MODEL_PATH = r"D:\PersonalSpace\ai\LLM in Local\QwenQwen1.5-0.5B-Chat-openvino-fp16"
CPU_MODEL_PATH = r"D:\PersonalSpace\ai\LLM in Local\QwenQwen1.5-0.5B-Chat-openvino-int4"
SYSTEM_PROMPT = "你是一个有帮助的中文助手，请简洁、准确地回答用户的问题。"
EXIT_COMMANDS = {"exit", "quit", "退出"}


def load_pipeline():
    """优先在 Intel NPU 上加载模型，不可用时自动回退到 CPU。"""
    available_devices = ov.Core().available_devices
    device = "NPU" if "NPU" in available_devices else "CPU"
    model_path = NPU_MODEL_PATH if device == "NPU" else CPU_MODEL_PATH
    print(f"可用设备：{', '.join(available_devices)}")
    print(f"正在使用 {device} 编译模型，首次启动可能需要一些时间……")

    try:
        pipeline = ov_genai.LLMPipeline(model_path, device)
    except RuntimeError as error:
        if device != "NPU":
            raise

        # 驱动或模型不兼容时保留 CPU 回退，确保对话程序仍可使用。
        print(f"NPU 加载失败，将回退到 CPU：{error}")
        device = "CPU"
        pipeline = ov_genai.LLMPipeline(CPU_MODEL_PATH, device)

    print(f"模型加载完成，当前推理设备：{device}")
    return pipeline, device


def generate_response(pipeline, history):
    """结合历史消息生成本轮回答及性能指标。"""
    result = pipeline.generate(
        history,
        max_new_tokens=512,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.05,
    )

    perf_metrics = result.perf_metrics
    elapsed_seconds = perf_metrics.get_generate_duration().mean / 1000
    generated_tokens = perf_metrics.get_num_generated_tokens()
    # 使用本轮总生成耗时计算端到端速度，其中包含首 Token 等待时间。
    tokens_per_second = (
        generated_tokens / elapsed_seconds
        if elapsed_seconds > 0
        else 0.0
    )
    return (
        result.texts[0].strip(),
        elapsed_seconds,
        generated_tokens,
        tokens_per_second,
    )


def main():
    pipeline, _ = load_pipeline()
    history = ov_genai.ChatHistory(
        [{"role": "system", "content": SYSTEM_PROMPT}],
    )

    print("\n可以开始对话。输入 /clear 清空上下文，输入 exit、quit 或退出结束。")
    while True:
        try:
            user_input = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n对话已结束。")
            break

        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            print("对话已结束。")
            break
        if user_input.lower() == "/clear":
            history = ov_genai.ChatHistory(
                [{"role": "system", "content": SYSTEM_PROMPT}],
            )
            print("上下文已清空。")
            continue

        history.append({"role": "user", "content": user_input})
        response, elapsed_seconds, generated_tokens, tokens_per_second = (
            generate_response(pipeline, history)
        )
        history.append({"role": "assistant", "content": response})
        print(f"助手：{response}")
        print(
            f"[性能] 耗时：{elapsed_seconds:.2f} 秒 | "
            f"生成：{generated_tokens} Tokens | "
            f"速度：{tokens_per_second:.2f} Tokens/s",
        )


if __name__ == "__main__":
    main()
