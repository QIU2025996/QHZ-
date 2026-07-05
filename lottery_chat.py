"""
快乐8 本地聊天窗口 - 直接跟三个 AI 对话
用法：python lottery_chat.py
"""
import json
import urllib.request
import os
import sys
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import re

# API 配置
MIMO_URL = "https://api.xiaomimimo.com/anthropic/v1/messages"
MIMO_KEY = os.environ.get("MIMO_API_KEY", "")
MIMO_MODEL = "mimo-v2.5-pro"

AGNES_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
AGNES_KEY = os.environ.get("AGNES_API_KEY", "")
AGNES_MODEL = "agnes-2.0-flash"

STEPFUN_URL = "https://api.stepfun.com/step_plan/v1/chat/completions"
STEPFUN_KEY = os.environ.get("STEPFUN_API_KEY", "")
STEPFUN_MODEL = "step-3.7-flash"

PROXY = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}


def call_api(ai_name, messages):
    """调用单个 AI 的 API"""
    try:
        if ai_name == "Mimo":
            return call_mimo(messages)
        elif ai_name == "Agnes AI":
            return call_agnes(messages)
        elif ai_name == "Claude":
            return call_stepfun(messages)
    except Exception as e:
        return f"[{ai_name} 调用失败: {e}]"


def call_mimo(messages):
    """Mimo - Anthropic 兼容格式"""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": MIMO_KEY,
        "anthropic-version": "2023-06-01"
    }
    # 转换为 Anthropic 格式
    system_msg = ""
    user_messages = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            user_messages.append({"role": m["role"], "content": m["content"]})

    payload = json.dumps({
        "model": MIMO_MODEL,
        "max_tokens": 4000,
        "system": system_msg,
        "messages": user_messages
    }).encode("utf-8")

    req = urllib.request.Request(MIMO_URL, data=payload, headers=headers, method="POST")
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(PROXY),
        urllib.request.HTTPSHandler
    )
    with opener.open(req, timeout=60) as resp:
        result = json.loads(resp.read())
        return result["content"][0]["text"]


def call_agnes(messages):
    """Agnes AI - OpenAI 兼容格式"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AGNES_KEY}"
    }
    payload = json.dumps({
        "model": AGNES_MODEL,
        "max_tokens": 4000,
        "messages": messages
    }).encode("utf-8")

    req = urllib.request.Request(AGNES_URL, data=payload, headers=headers, method="POST")
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(PROXY),
        urllib.request.HTTPSHandler
    )
    with opener.open(req, timeout=60) as resp:
        result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"]


def call_stepfun(messages):
    """Claude via StepFun - OpenAI 兼容格式"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {STEPFUN_KEY}"
    }
    payload = json.dumps({
        "model": STEPFUN_MODEL,
        "max_tokens": 4000,
        "messages": messages
    }).encode("utf-8")

    req = urllib.request.Request(STEPFUN_URL, data=payload, headers=headers, method="POST")
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(PROXY),
        urllib.request.HTTPSHandler
    )
    with opener.open(req, timeout=60) as resp:
        result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"]


class ChatApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("快乐8 AI 协同分析")
        self.root.geometry("800x600")

        # 对话历史（持久化）
        self.history = []
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lottery_chat_history.json")
        self._load_history()

        # 界面
        self._build_ui()
        self._show_history()

    def _build_ui(self):
        # 顶部：数据文件选择
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(top, text="数据文件:").pack(side=tk.LEFT)
        self.data_path = tk.StringVar(value="happy8_data.csv")
        tk.Entry(top, textvariable=self.data_path, width=40).pack(side=tk.LEFT, padx=5)

        tk.Button(top, text="加载数据", command=self.load_data, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)

        # 聊天区域
        self.chat = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, font=("Microsoft YaHei", 11))
        self.chat.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.chat.tag_config("user", foreground="#2196F3")
        self.chat.tag_config("mimo", foreground="#4CAF50")
        self.chat.tag_config("agnes", foreground="#FF9800")
        self.chat.tag_config("claude", foreground="#9C27B0")
        self.chat.tag_config("system", foreground="#888", font=("Microsoft YaHei", 9, "italic"))

        # 底部：输入框
        bottom = tk.Frame(self.root)
        bottom.pack(fill=tk.X, padx=10, pady=10)

        self.input_var = tk.StringVar()
        self.entry = tk.Entry(bottom, textvariable=self.input_var, font=("Microsoft YaHei", 11))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.entry.bind("<Return>", lambda e: self.send())

        tk.Button(bottom, text="发送", command=self.send, bg="#2196F3", fg="white", font=("Microsoft YaHei", 11)).pack(side=tk.RIGHT)

        # 状态栏
        self.status = tk.StringVar(value="就绪")
        tk.Label(self.root, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM)

        # 数据缓存
        self.data_summary = ""

    def load_data(self):
        path = self.data_path.get().strip()
        if not os.path.exists(path):
            messagebox.showerror("错误", f"文件不存在: {path}")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            periods = []
            for line in lines:
                parts = line.strip().split(",")
                if len(parts) >= 21:
                    periods.append(line.strip())

            # 取最近50期
            recent = periods[-50:] if len(periods) > 50 else periods
            self.data_summary = "\n".join(recent)

            self._append("system", f"已加载 {len(periods)} 期数据（显示最近 {len(recent)} 期）")
        except Exception as e:
            messagebox.showerror("错误", f"加载失败: {e}")

    def _load_history(self):
        """从文件加载历史对话"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except:
                self.history = []

    def _save_history(self):
        """保存历史对话到文件"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history[-50:], f, ensure_ascii=False, indent=2)
        except:
            pass

    def _show_history(self):
        """显示历史对话"""
        if not self.history:
            self._append("system", "欢迎！请先点击「加载数据」，然后输入问题开始分析。")
            return
        self._append("system", f"已恢复 {len(self.history)} 轮历史对话")
        for item in self.history:
            self._append(item["tag"], item["text"][:2000])

    def _append(self, tag, text):
        self.chat.insert(tk.END, text + "\n\n", tag)
        self.chat.see(tk.END)

    def send(self):
        question = self.input_var.get().strip()
        if not question:
            return

        self.input_var.set("")
        self._append("user", f"你: {question}")

        # 在后台线程中运行 AI
        thread = threading.Thread(target=self._run_ai_chain, args=(question,), daemon=True)
        thread.start()

    def _run_ai_chain(self, question):
        """三个 AI 按顺序接力分析"""
        if not self.data_summary:
            self.root.after(0, lambda: self._append("system", "请先加载数据文件！"))
            return

        # 构建历史上下文
        history_text = ""
        if self.history:
            history_text = "## 之前的对话记忆（最近几轮）：\n"
            for item in self.history[-6:]:
                history_text += f"### {item['tag']}:\n{item['text'][:1500]}\n\n"

        # Round 1: Mimo
        self.root.after(0, lambda: self.status.set("Mimo 分析中..."))
        mimo_prompt = f"""你是一位专业的中文快乐8彩票数据分析专家。你必须用中文回答，禁止使用英文。

你将在与其他两个 AI（Agnes AI 和 Claude）的协作中进行分析。
你只负责第一阶段的数据规律分析，其他 AI 会在你的基础上继续深入。

{history_text}

## 历史数据（最近50期）：
{self.data_summary}

## 用户问题：
{question}

请用中文详细分析，包括：
1. 尾数分布规律
2. 连号/组号模式
3. 热号冷号
4. 网格位置规律
5. 推荐号码"""

        messages = [{"role": "user", "content": mimo_prompt}]
        mimo_response = call_api("Mimo", messages)
        self.root.after(0, lambda: self._append("mimo", f"Mimo:\n{mimo_response[:2000]}"))
        self.history.append({"tag": "Mimo", "text": mimo_response[:3000]})

        # Round 2: Agnes AI（基于 Mimo 的结果）
        self.root.after(0, lambda: self.status.set("Agnes AI 分析中..."))
        agnes_prompt = f"""你是一位专业的中文快乐8彩票数据分析专家。你必须用中文回答，禁止使用英文。

以下是 Mimo 的分析结果，请在此基础上进行独立验证和补充分析：

{history_text}

## Mimo 的分析：
{mimo_response[:3000]}

## 历史数据（最近50期）：
{self.data_summary}

## 用户问题：
{question}

请基于 Mimo 的分析，给出你的独立见解、验证或修正，并补充 Mimo 可能遗漏的规律。"""

        messages = [{"role": "user", "content": agnes_prompt}]
        agnes_response = call_api("Agnes AI", messages)
        self.root.after(0, lambda: self._append("agnes", f"Agnes AI:\n{agnes_response[:2000]}"))
        self.history.append({"tag": "Agnes AI", "text": agnes_response[:3000]})

        # Round 3: Claude（综合前两个 AI）
        self.root.after(0, lambda: self.status.set("Claude 综合分析中..."))
        claude_prompt = f"""你是一位专业的中文快乐8彩票数据分析专家。你必须用中文回答，禁止使用英文。

以下是前面两个 AI 的分析结果，请综合它们的观点，给出最终的分析结论和推荐。

{history_text}

## Mimo 的分析：
{mimo_response[:2000]}

## Agnes AI 的分析：
{agnes_response[:2000]}

## 历史数据（最近50期）：
{self.data_summary}

## 用户问题：
{question}

请综合以上所有分析，给出最终结论，包括：
1. 共识规律总结
2. 分歧点说明
3. 最终推荐号码（10-15个）
4. 风险提醒"""

        messages = [{"role": "user", "content": claude_prompt}]
        claude_response = call_api("Claude", messages)
        self.root.after(0, lambda: self._append("claude", f"Claude（综合）:\n{claude_response[:3000]}"))
        self.history.append({"tag": "Claude", "text": claude_response[:3000]})

        # 保存历史
        self._save_history()
        self.root.after(0, lambda: self.status.set("分析完成"))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ChatApp()
    app.run()
