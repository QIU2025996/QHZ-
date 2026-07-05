"""
快乐8 AI 协同分析 - 现代桌面聊天应用
三个 AI (Mimo → Agnes AI → Claude) 按顺序接力分析
"""
import json
import urllib.request
import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import shutil
from datetime import datetime

# ── API 配置 ──
MIMO_URL = "https://api.xiaomimimo.com/anthropic/v1/messages"
AGNES_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
STEPFUN_URL = "https://api.stepfun.com/step_plan/v1/chat/completions"
PROXY = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

# ── 颜色主题 ──
C = {
    "bg": "#1a1a2e", "panel": "#16213e", "card": "#0f3460",
    "accent": "#e94560", "text": "#eaeaea", "muted": "#8888aa",
    "mimo": "#00d2ff", "agnes": "#ffa502", "claude": "#ff6b81",
    "user": "#7bed9f", "system": "#5352ed", "input_bg": "#1a1a2e",
    "border": "#2a2a4a",
}


def load_key(name):
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{name}="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get(name, "")


def call_api(ai_name, messages, keys):
    try:
        if ai_name == "Mimo":
            return _call_mimo(messages, keys)
        elif ai_name == "Agnes AI":
            return _call_agnes(messages, keys)
        elif ai_name == "Claude":
            return _call_stepfun(messages, keys)
    except Exception as e:
        return f"[{ai_name} 调用失败: {e}]"


def _call_mimo(messages, keys):
    key = keys.get("MIMO_API_KEY", "")
    if not key:
        return "[错误: 未设置 MIMO_API_KEY，请点击「配置 API Key」]"
    headers = {"Content-Type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"}
    system_msg = ""
    user_msgs = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            user_msgs.append({"role": m["role"], "content": m["content"]})
    payload = json.dumps({"model": "mimo-v2.5-pro", "max_tokens": 4000, "system": system_msg, "messages": user_msgs}).encode()
    req = urllib.request.Request(MIMO_URL, data=payload, headers=headers, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(PROXY), urllib.request.HTTPSHandler)
    with opener.open(req, timeout=120) as resp:
        return json.loads(resp.read())["content"][0]["text"]


def _call_agnes(messages, keys):
    key = keys.get("AGNES_API_KEY", "")
    if not key:
        return "[错误: 未设置 AGNES_API_KEY，请点击「配置 API Key」]"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    payload = json.dumps({"model": "agnes-2.0-flash", "max_tokens": 4000, "messages": messages}).encode()
    req = urllib.request.Request(AGNES_URL, data=payload, headers=headers, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(PROXY), urllib.request.HTTPSHandler)
    with opener.open(req, timeout=120) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def _call_stepfun(messages, keys):
    key = keys.get("STEPFUN_API_KEY", "")
    if not key:
        return "[错误: 未设置 STEPFUN_API_KEY，请点击「配置 API Key」]"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    payload = json.dumps({"model": "step-3.7-flash", "max_tokens": 4000, "messages": messages}).encode()
    req = urllib.request.Request(STEPFUN_URL, data=payload, headers=headers, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(PROXY), urllib.request.HTTPSHandler)
    with opener.open(req, timeout=120) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


class ModernChatApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("快乐8 AI 协同分析")
        self.root.geometry("900x650")
        self.root.minsize(700, 500)

        self.data_summary = ""
        self.history = []
        self.is_running = False
        self.keys = {
            "MIMO_API_KEY": load_key("MIMO_API_KEY"),
            "AGNES_API_KEY": load_key("AGNES_API_KEY"),
            "STEPFUN_API_KEY": load_key("STEPFUN_API_KEY"),
        }

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.history_file = os.path.join(base_dir, "lottery_chat_history.json")
        self.data_dir = os.path.join(base_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)

        self._load_history()
        self._build_ui()
        self._show_welcome()

    def _build_ui(self):
        self._setup_theme()
        main = tk.Frame(self.root, bg=C["bg"])
        main.pack(fill=tk.BOTH, expand=True)

        # ── 侧边栏 ──
        sidebar = tk.Frame(main, bg=C["panel"], width=180)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="🎱", font=("Segoe UI", 32), bg=C["panel"], fg=C["accent"]).pack(pady=(15, 0))
        tk.Label(sidebar, text="快乐8 AI", font=("Microsoft YaHei", 14, "bold"), bg=C["panel"], fg=C["text"]).pack(pady=(0, 2))
        tk.Label(sidebar, text="协同分析", font=("Microsoft YaHei", 10), bg=C["panel"], fg=C["muted"]).pack(pady=(0, 15))

        # AI 状态
        status_frame = tk.Frame(sidebar, bg=C["panel"])
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        self.ai_status_labels = {}
        for name, color, key_name in [("Mimo", C["mimo"], "MIMO_API_KEY"),
                                       ("Agnes", C["agnes"], "AGNES_API_KEY"),
                                       ("Claude", C["claude"], "STEPFUN_API_KEY")]:
            row = tk.Frame(status_frame, bg=C["panel"])
            row.pack(fill=tk.X, pady=3)
            dot = tk.Canvas(row, width=10, height=10, bg=C["panel"], highlightthickness=0)
            dot.pack(side=tk.LEFT, padx=(5, 8))
            dot.create_oval(2, 2, 8, 8, fill=color if self.keys.get(key_name) else "#555", outline="")
            lbl = tk.Label(row, text=name, font=("Microsoft YaHei", 10), bg=C["panel"],
                           fg=C["text"] if self.keys.get(key_name) else C["muted"])
            lbl.pack(side=tk.LEFT)
            self.ai_status_labels[name] = (dot, lbl, key_name)

        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=15)

        # 按钮
        btn_cfg = {"font": ("Microsoft YaHei", 10), "bg": C["card"], "fg": C["text"],
                    "bd": 0, "padx": 10, "pady": 6, "anchor": tk.W, "cursor": "hand2"}
        tk.Button(sidebar, text="📁 加载数据", command=self._load_data, **btn_cfg).pack(fill=tk.X, padx=10, pady=2)
        tk.Button(sidebar, text="💾 保存对话", command=self._export_chat, **btn_cfg).pack(fill=tk.X, padx=10, pady=2)
        tk.Button(sidebar, text="🗑️ 清空历史", command=self._clear_history, **btn_cfg).pack(fill=tk.X, padx=10, pady=2)
        tk.Button(sidebar, text="⚙️ 配置 API Key", command=self._config_keys, **btn_cfg).pack(fill=tk.X, padx=10, pady=2)

        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=15)

        tk.Label(sidebar, text="📊 数据状态", font=("Microsoft YaHei", 10, "bold"), bg=C["panel"], fg=C["text"]).pack(anchor=tk.W, padx=10)
        self.data_info = tk.Label(sidebar, text="未加载", font=("Microsoft YaHei", 9), bg=C["panel"], fg=C["muted"], justify=tk.LEFT)
        self.data_info.pack(anchor=tk.W, padx=10, pady=(0, 10))

        self.round_label = tk.Label(sidebar, text="对话: 0 轮", font=("Microsoft YaHei", 9), bg=C["panel"], fg=C["muted"])
        self.round_label.pack(anchor=tk.W, padx=10)

        tk.Label(sidebar, text="v2.0 · 桌面端", font=("Microsoft YaHei", 8), bg=C["panel"], fg="#444").pack(side=tk.BOTTOM, pady=10)

        # ── 聊天区域 ──
        chat_area = tk.Frame(main, bg=C["bg"])
        chat_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        chat_container = tk.Frame(chat_area, bg=C["bg"])
        chat_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        self.chat = tk.Text(chat_container, wrap=tk.WORD, bg=C["bg"], fg=C["text"],
                            font=("Microsoft YaHei", 11), relief=tk.FLAT, bd=0,
                            spacing1=8, spacing3=8, cursor="arrow", state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(chat_container, orient=tk.VERTICAL, command=self.chat.yview)
        self.chat.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat.pack(fill=tk.BOTH, expand=True)

        # 文字样式
        self.chat.tag_config("user", foreground=C["user"], font=("Microsoft YaHei", 11, "bold"))
        self.chat.tag_config("mimo", foreground=C["mimo"], font=("Microsoft YaHei", 11, "bold"))
        self.chat.tag_config("agnes", foreground=C["agnes"], font=("Microsoft YaHei", 11, "bold"))
        self.chat.tag_config("claude", foreground=C["claude"], font=("Microsoft YaHei", 11, "bold"))
        self.chat.tag_config("system", foreground=C["muted"], font=("Microsoft YaHei", 9, "italic"))
        self.chat.tag_config("timestamp", foreground="#444466", font=("Microsoft YaHei", 8))
        self.chat.tag_config("body", foreground=C["text"], font=("Microsoft YaHei", 10))
        self.chat.tag_config("divider", foreground="#2a2a4a", font=("Microsoft YaHei", 8))

        # 输入区
        input_area = tk.Frame(chat_area, bg=C["panel"], height=80)
        input_area.pack(fill=tk.X, padx=10, pady=10)
        input_area.pack_propagate(False)

        top_input = tk.Frame(input_area, bg=C["panel"])
        top_input.pack(fill=tk.X, padx=10, pady=(8, 0))
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(top_input, textvariable=self.status_var, font=("Microsoft YaHei", 9), bg=C["panel"], fg=C["muted"]).pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(top_input, mode="indeterminate", length=120)
        self.progress.pack(side=tk.RIGHT, padx=(10, 0))

        bottom_input = tk.Frame(input_area, bg=C["panel"])
        bottom_input.pack(fill=tk.X, padx=10, pady=(5, 8))
        self.input_var = tk.StringVar()
        self.entry = tk.Entry(bottom_input, textvariable=self.input_var, font=("Microsoft YaHei", 11),
                              bg=C["input_bg"], fg=C["text"], relief=tk.FLAT, insertbackground=C["text"])
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=6)
        self.entry.bind("<Return>", lambda e: self.send())
        self.send_btn = tk.Button(bottom_input, text="发送", command=self.send,
                                  bg=C["accent"], fg="white", font=("Microsoft YaHei", 11, "bold"),
                                  bd=0, padx=20, pady=3, cursor="hand2", activebackground="#c73e54")
        self.send_btn.pack(side=tk.RIGHT)

    def _setup_theme(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Vertical.TScrollbar", background=C["card"], troughcolor=C["bg"], bordercolor=C["bg"], arrowcolor=C["muted"])
        style.configure("TProgressbar", background=C["accent"], troughcolor=C["bg"])

    # ── 历史管理 ──
    def _load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
        except:
            self.history = []

    def _save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history[-50:], f, ensure_ascii=False, indent=2)
        except:
            pass

    def _show_welcome(self):
        self._append_msg("system", "欢迎使用快乐8 AI 协同分析！")
        self._append_msg("system", "流程：加载数据 → 输入问题 → 三个 AI 按顺序分析（Mimo → Agnes → Claude）")
        self._append_msg("system", f"记忆文件: {os.path.basename(self.history_file)}")
        if self.history:
            self._append_msg("system", f"已恢复 {len(self.history)} 条历史记录")
        self._check_keys()

    def _check_keys(self):
        for name, _, key_name in [("Mimo", C["mimo"], "MIMO_API_KEY"), ("Agnes", C["agnes"], "AGNES_API_KEY"), ("Claude", C["claude"], "STEPFUN_API_KEY")]:
            dot, lbl, _ = self.ai_status_labels[name]
            has_key = bool(self.keys.get(key_name))
            dot.itemconfig(1, fill=C["mimo"] if name == "Mimo" else C["agnes"] if name == "Agnes" else C["claude"] if has_key else "#555")
            lbl.config(fg=C["text"] if has_key else C["muted"])

    # ── 消息显示 ──
    def _append_msg(self, tag, text):
        self.chat.config(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M")
        icons = {"user": "👤 你", "mimo": "🔵 Mimo", "agnes": "🟠 Agnes AI", "claude": "🔴 Claude", "system": "⚙️ 系统"}
        label = icons.get(tag, "📢")
        self.chat.insert(tk.END, f"\n{label}  [{ts}]\n", tag)
        self.chat.insert(tk.END, "─" * 55 + "\n", "divider")
        for line in text.split("\n"):
            self.chat.insert(tk.END, line + "\n", "body")
        self.chat.insert(tk.END, "\n", "body")
        self.chat.config(state=tk.DISABLED)
        self.chat.see(tk.END)

    # ── 功能 ──
    def _load_data(self):
        path = filedialog.askopenfilename(title="选择快乐8数据文件", initialdir=self.data_dir,
                                          filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            periods = [l.strip() for l in lines if len(l.strip().split(",")) >= 21]
            recent = periods[-50:] if len(periods) > 50 else periods
            self.data_summary = "\n".join(recent)
            self.data_info.config(text=f"总期数: {len(periods)}\n最近: {len(recent)} 期\n最新: {periods[-1][:20] if periods else 'N/A'}...")
            self._append_msg("system", f"已加载 {len(periods)} 期数据（显示最近 {len(recent)} 期）")
            shutil.copy2(path, os.path.join(self.data_dir, "happy8_data.csv"))
        except Exception as e:
            messagebox.showerror("加载失败", str(e))

    def _export_chat(self):
        if not self.history:
            messagebox.showinfo("提示", "没有对话可导出")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")],
                                            initialfile=f"lottery_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for item in self.history:
                    f.write(f"\n{'=' * 60}\n[{item['tag']}]\n{'=' * 60}\n")
                    f.write(item["text"] + "\n")
            messagebox.showinfo("导出成功", f"已保存到: {path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _clear_history(self):
        if messagebox.askyesno("确认", "确定清空所有对话历史？"):
            self.history = []
            self._save_history()
            self.chat.config(state=tk.NORMAL)
            self.chat.delete("1.0", tk.END)
            self.chat.config(state=tk.DISABLED)
            self._show_welcome()
            self.round_label.config(text="对话: 0 轮")

    def _config_keys(self):
        win = tk.Toplevel(self.root)
        win.title("配置 API Key")
        win.geometry("520x310")
        win.configure(bg=C["bg"])
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="⚙️ API Key 配置", font=("Microsoft YaHei", 14, "bold"), bg=C["bg"], fg=C["text"]).pack(pady=15)
        tk.Label(win, text="Key 会保存到同目录的 .env 文件", font=("Microsoft YaHei", 9), bg=C["bg"], fg=C["muted"]).pack()

        entries = {}
        for key_name, label in [("MIMO_API_KEY", "Mimo (mimo-v2.5-pro)"),
                                 ("AGNES_API_KEY", "Agnes AI (agnes-2.0-flash)"),
                                 ("STEPFUN_API_KEY", "Claude via StepFun (step-3.7-flash)")]:
            row = tk.Frame(win, bg=C["bg"])
            row.pack(fill=tk.X, padx=20, pady=8)
            tk.Label(row, text=label, font=("Microsoft YaHei", 10), bg=C["bg"], fg=C["text"], width=28, anchor=tk.W).pack(side=tk.LEFT)
            var = tk.StringVar(value=self.keys.get(key_name, ""))
            tk.Entry(row, textvariable=var, font=("Consolas", 10), width=28, show="*").pack(side=tk.RIGHT)
            entries[key_name] = var

        def save():
            for k, v in entries.items():
                self.keys[k] = v.get().strip()
            env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
            with open(env_file, "w", encoding="utf-8") as f:
                for k, _ in [("MIMO_API_KEY", ""), ("AGNES_API_KEY", ""), ("STEPFUN_API_KEY", "")]:
                    f.write(f"{k}={self.keys.get(k, '')}\n")
            self._check_keys()
            messagebox.showinfo("已保存", "API Key 已保存")
            win.destroy()

        tk.Button(win, text="保存", command=save, bg=C["accent"], fg="white",
                  font=("Microsoft YaHei", 11, "bold"), bd=0, padx=30, pady=5).pack(pady=15)

    # ── 发送与分析 ──
    def send(self):
        question = self.input_var.get().strip()
        if not question or self.is_running:
            return
        self.input_var.set("")
        self._append_msg("user", question)

        if not any(self.keys.values()):
            self._append_msg("system", "请先配置 API Key（点击左侧「配置 API Key」）")
            self._config_keys()
            return

        self.is_running = True
        self.send_btn.config(state=tk.DISABLED, text="分析中...")
        self.progress.start(10)
        threading.Thread(target=self._run_analysis, args=(question,), daemon=True).start()

    def _run_analysis(self, question):
        try:
            if not self.data_summary:
                self.root.after(0, lambda: self._append_msg("system", "请先加载数据文件！"))
                return

            history_text = ""
            if self.history:
                history_text = "## 之前的对话记忆（最近几轮）：\n"
                for item in self.history[-6:]:
                    history_text += f"### {item['tag']}:\n{item['text'][:1200]}\n\n"

            # Round 1: Mimo
            self.root.after(0, lambda: self.status_var.set("🔵 Mimo 数据分析中..."))
            mimo_prompt = f"""你是一位专业的中文快乐8彩票数据分析专家。你必须用中文回答，禁止使用英文。你只负责第一阶段的数据规律分析，Agnes AI 和 Claude 会在你的基础上继续深入。

{history_text}
## 历史数据（最近50期）：
{self.data_summary}

## 用户问题：
{question}

请用中文详细分析：1.尾数分布规律 2.连号/组号模式 3.热号冷号 4.网格位置规律 5.推荐号码"""

            mimo_resp = call_api("Mimo", [{"role": "user", "content": mimo_prompt}], self.keys)
            self.history.append({"tag": "Mimo", "text": mimo_resp})
            self.root.after(0, lambda: self._append_msg("mimo", mimo_resp))

            # Round 2: Agnes AI
            self.root.after(0, lambda: self.status_var.set("🟠 Agnes AI 验证分析中..."))
            agnes_prompt = f"""你是一位专业的中文快乐8彩票数据分析专家。你必须用中文回答，禁止使用英文。以下是 Mimo 的分析，请独立验证和补充。

{history_text}
## Mimo 的分析：
{mimo_resp[:3000]}
## 历史数据（最近50期）：
{self.data_summary}
## 用户问题：
{question}
请给出独立见解、验证或修正，补充 Mimo 可能遗漏的规律。"""

            agnes_resp = call_api("Agnes AI", [{"role": "user", "content": agnes_prompt}], self.keys)
            self.history.append({"tag": "Agnes AI", "text": agnes_resp})
            self.root.after(0, lambda: self._append_msg("agnes", agnes_resp))

            # Round 3: Claude 综合
            self.root.after(0, lambda: self.status_var.set("🔴 Claude 综合分析中..."))
            claude_prompt = f"""你是一位专业的中文快乐8彩票数据分析专家。你必须用中文回答，禁止使用英文。综合前两个 AI 的分析，给出最终结论。

{history_text}
## Mimo 的分析：
{mimo_resp[:2000]}
## Agnes AI 的分析：
{agnes_resp[:2000]}
## 历史数据（最近50期）：
{self.data_summary}
## 用户问题：
{question}
请综合给出：1.共识规律总结 2.分歧点说明 3.最终推荐号码（10-15个）4.风险提醒"""

            claude_resp = call_api("Claude", [{"role": "user", "content": claude_prompt}], self.keys)
            self.history.append({"tag": "Claude", "text": claude_resp})
            self.root.after(0, lambda: self._append_msg("claude", claude_resp))

            self._save_history()
            self.root.after(0, lambda: self.status_var.set("✅ 分析完成"))
            self.root.after(0, lambda: self.round_label.config(text=f"对话: {len(self.history) // 3} 轮"))
        except Exception as e:
            self.root.after(0, lambda: self._append_msg("system", f"错误: {e}"))
            self.root.after(0, lambda: self.status_var.set("❌ 出错"))
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.send_btn.config(state=tk.NORMAL, text="发送"))
            self.root.after(0, lambda: self.progress.stop())

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ModernChatApp().run()
