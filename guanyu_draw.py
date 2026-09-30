import io
import sys
import os
import random
import threading
import tkinter as tk
from tkinter import messagebox
import urllib.request

try:
    from PIL import Image, ImageTk

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def get_resource_path(relative_path):
    """获取程序运行时的资源绝对路径（兼容开发环境与 PyInstaller 打包环境）"""
    try:
        # PyInstaller 单文件打包解压的临时路径
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# 关公神像图片配置
GUANYU_IMG_URL = ""
# 修改 LOCAL_IMG_FILE 的定义：
LOCAL_IMG_FILE = get_resource_path("guanyu.png")


class GuanYuDrawApp:
    def __init__(self, root):
        self.root = root
        self.root.title("关圣帝君 · 灵签摇号")
        self.root.geometry("480x760")
        self.root.resizable(False, False)
        self.root.configure(bg="#1A0808")

        self.is_rolling = False
        self.journal_entries = []
        self.bg_photo = None

        self._init_ui()
        self._load_guanyu_image()

    def _init_ui(self):
        # 1. 关公神像展示区
        self.header_canvas = tk.Canvas(
            self.root,
            width=440,
            height=230,
            bg="#2B0505",
            highlightthickness=2,
            highlightbackground="#C59B27",
        )
        self.header_canvas.pack(pady=(14, 8), padx=20)
        self._draw_fallback_banner()

        # 2. 推荐投稿期刊展示卡片
        self.result_frame = tk.Frame(
            self.root,
            bg="#2D0606",
            bd=2,
            relief="ridge",
            highlightbackground="#E5B338",
            highlightthickness=1,
        )
        self.result_frame.pack(fill="x", padx=20, pady=6)

        tk.Label(
            self.result_frame,
            text="【 帝君指引 · 推荐投稿期刊 】",
            font=("SimSun", 10),
            fg="#A89476",
            bg="#2D0606",
        ).pack(pady=(6, 2))

        self.result_label = tk.Label(
            self.result_frame,
            text="静 待 开 签",
            font=("SimHei", 20, "bold"),
            fg="#FFE066",
            bg="#2D0606",
        )
        self.result_label.pack(pady=(2, 8))

        # 3. 期刊设置区 (2-10个)
        setting_frame = tk.Frame(self.root, bg="#2B1111", bd=1, relief="solid")
        setting_frame.pack(fill="both", expand=True, padx=20, pady=6)

        bar = tk.Frame(setting_frame, bg="#381515")
        bar.pack(fill="x", padx=4, pady=4)

        self.count_label = tk.Label(
            bar,
            text="备选期刊列表 (7/10)",
            font=("SimHei", 10),
            fg="#D1B48C",
            bg="#381515",
        )
        self.count_label.pack(side="left", padx=8, pady=4)

        self.btn_add = tk.Button(
            bar,
            text="+ 添加期刊",
            font=("SimHei", 9, "bold"),
            bg="#6A1A15",
            fg="#F7D358",
            activebackground="#8A231C",
            activeforeground="#FFE066",
            command=self.add_journal_field,
            bd=1,
            relief="raised",
        )
        self.btn_add.pack(side="right", padx=6, pady=4)

        # 滚动列表区域
        self.scroll_canvas = tk.Canvas(
            setting_frame, bg="#2B1111", highlightthickness=0
        )
        self.scrollbar = tk.Scrollbar(
            setting_frame, orient="vertical", command=self.scroll_canvas.yview
        )
        self.list_frame = tk.Frame(self.scroll_canvas, bg="#2B1111")

        self.list_frame.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.configure(
                scrollregion=self.scroll_canvas.bbox("all")
            ),
        )
        self.scroll_canvas.create_window(
            (0, 0), window=self.list_frame, anchor="nw", width=410
        )
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_canvas.pack(
            side="left", fill="both", expand=True, padx=(4, 0), pady=4
        )
        self.scrollbar.pack(side="right", fill="y", pady=4)

        # 4. 底部求签操作按钮
        self.draw_btn = tk.Button(
            self.root,
            text="诚 心 求 签",
            font=("SimHei", 16, "bold"),
            bg="#9E1911",
            fg="#FFF2A8",
            activebackground="#C22318",
            activeforeground="#FFFFFF",
            relief="raised",
            bd=3,
            cursor="hand2",
            command=self.start_draw,
        )
        self.draw_btn.pack(fill="x", padx=20, pady=(6, 14), ipady=8)

        # 预设的 7 本目标期刊列表
        preset_journals = [
            "AIChE Journal",
            "Chemical Engineering Science",
            "Applied Energy",
            "Separation and Purification Technology",
            "Energy",
            "Renewable and Sustainable Energy Reviews",
            "Applied Thermal Engineering",
        ]

        for name in preset_journals:
            self._add_row(name)
        self._update_counter()

    def _load_guanyu_image(self):
        """加载关二爷神像图片"""
        if not HAS_PIL:
            return

        def _task():
            img_data = None
            if os.path.exists(LOCAL_IMG_FILE):
                try:
                    img = Image.open(LOCAL_IMG_FILE)
                    img_data = img.copy()
                except Exception:
                    pass

            if img_data is None:
                try:
                    req = urllib.request.Request(
                        GUANYU_IMG_URL, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        content = resp.read()
                        with open(LOCAL_IMG_FILE, "wb") as f:
                            f.write(content)
                        img_data = Image.open(io.BytesIO(content))
                except Exception:
                    img_data = None

            if img_data:
                self.root.after(0, lambda: self._apply_header_image(img_data))

        threading.Thread(target=_task, daemon=True).start()

    def _apply_header_image(self, pil_img):
        """自适应裁剪到 440x230 并渲染图层与文字遮罩"""
        target_w, target_h = 440, 230
        img = pil_img.convert("RGBA")

        src_w, src_h = img.size
        scale = max(target_w / src_w, target_h / src_h)
        new_w, new_h = int(src_w * scale), int(src_h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        img = img.crop((left, top, left + target_w, top + target_h))

        self.bg_photo = ImageTk.PhotoImage(img)
        self.header_canvas.delete("all")
        self.header_canvas.create_image(0, 0, anchor="nw", image=self.bg_photo)

        # 底部暗红半透明遮罩与烫金文字
        self.header_canvas.create_rectangle(
            0, 160, 440, 230, fill="#120202", stipple="gray75", outline=""
        )
        self.header_canvas.create_text(
            220,
            180,
            text="关 圣 帝 君 · 灵 签 摇 号",
            fill="#F7D358",
            font=("SimHei", 16, "bold"),
        )
        self.header_canvas.create_text(
            220,
            208,
            text="心 诚 则 灵  ·  公 平 自 显",
            fill="#DFBA73",
            font=("KaiTi", 11),
        )

    def _draw_fallback_banner(self):
        """纯代码中国风古风兜底"""
        self.header_canvas.delete("all")
        self.header_canvas.create_rectangle(8, 8, 432, 222, outline="#8B1E1E", width=2)
        self.header_canvas.create_text(
            220, 75, text="義", fill="#5A1515", font=("KaiTi", 70, "bold")
        )
        self.header_canvas.create_text(
            220,
            175,
            text="关 圣 帝 君 · 灵 签 摇 号",
            fill="#F7D358",
            font=("SimHei", 16, "bold"),
        )
        self.header_canvas.create_text(
            220,
            205,
            text="心 诚 则 灵  ·  公 平 自 显",
            fill="#DFBA73",
            font=("KaiTi", 11),
        )

    def _add_row(self, text=""):
        row_idx = len(self.journal_entries)
        row = tk.Frame(self.list_frame, bg="#1E0909", bd=1, relief="ridge")
        row.pack(fill="x", pady=3, padx=2)

        lbl = tk.Label(
            row,
            text=f"{row_idx + 1}.",
            font=("SimHei", 10, "bold"),
            fg="#C59B27",
            bg="#1E0909",
            width=3,
        )
        lbl.pack(side="left", padx=4)

        entry = tk.Entry(
            row,
            font=("Microsoft YaHei", 10),
            bg="#2E1212",
            fg="#FFFFFF",
            insertbackground="#FFF",
            relief="flat",
        )
        entry.insert(0, text)
        entry.pack(side="left", fill="x", expand=True, padx=4, ipady=3)

        btn_del = tk.Button(
            row,
            text="✕",
            font=("SimHei", 9),
            bg="#441717",
            fg="#D08888",
            activebackground="#661C1C",
            relief="flat",
            command=lambda r=row: self.delete_journal_field(r),
        )
        btn_del.pack(side="right", padx=4)

        self.journal_entries.append((row, entry, lbl, btn_del))

    def add_journal_field(self):
        if len(self.journal_entries) >= 10:
            messagebox.showwarning("数量上限", "最多只支持配置 10 本备选期刊！")
            return
        self._add_row()
        self._update_counter()

    def delete_journal_field(self, target_row):
        if len(self.journal_entries) <= 2:
            messagebox.showwarning("数量下限", "摇号需保证至少 2 本期刊！")
            return

        for idx, (row, entry, lbl, btn_del) in enumerate(self.journal_entries):
            if row == target_row:
                row.destroy()
                self.journal_entries.pop(idx)
                break

        for idx, (_, _, lbl, _) in enumerate(self.journal_entries):
            lbl.config(text=f"{idx + 1}.")
        self._update_counter()

    def _update_counter(self):
        total = len(self.journal_entries)
        self.count_label.config(text=f"备选期刊列表 ({total}/10)")
        self.btn_add.config(state="disabled" if total >= 10 else "normal")

    def start_draw(self):
        if self.is_rolling:
            return

        candidates = [
            entry.get().strip()
            for _, entry, _, _ in self.journal_entries
            if entry.get().strip()
        ]

        if len(candidates) < 2:
            messagebox.showerror("有效期刊不足", "请至少完整输入 2 个期刊名称！")
            return

        self.is_rolling = True
        self.draw_btn.config(state="disabled", text="正在开签...", bg="#551111")

        # 严格等概率抽选目标
        final_selected = random.choice(candidates)
        self._roll_animation(
            candidates, final_selected, frame=0, total_frames=22, speed=60
        )

    def _roll_animation(self, candidates, final_choice, frame, total_frames, speed):
        """滚动跳动动画"""
        if frame < total_frames:
            temp_pick = random.choice(candidates)
            self.result_label.config(text=temp_pick)
            next_speed = speed + (frame * 5)
            self.root.after(
                next_speed,
                lambda: self._roll_animation(
                    candidates, final_choice, frame + 1, total_frames, next_speed
                ),
            )
        else:
            self.result_label.config(text=final_choice)
            self.is_rolling = False
            self.draw_btn.config(state="normal", text="诚 心 求 签", bg="#9E1911")

            messagebox.showinfo(
                "灵签已显",
                f"关公灵签所定推荐投稿期刊：\n\n【 {final_choice} 】\n\n祝：投稿顺利，一击即中！",
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = GuanYuDrawApp(root)
    root.mainloop()
