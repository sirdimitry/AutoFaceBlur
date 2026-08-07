import os
import sys
import time
import threading
import traceback
import logging
import multiprocessing

# 1. Отключение фона Matplotlib и YOLO до импорта библиотек
os.environ["MPLCONFIGDIR"] = os.path.expanduser("~/Library/Caches/FaceBlurStudio_Matplotlib")
os.environ["YOLO_VERBOSE"] = "False"

# 2. Определение пути к лог-файлу
if getattr(sys, 'frozen', False):
    log_dir = os.path.expanduser('~/Library/Logs/FaceBlurStudio')
    os.makedirs(log_dir, exist_ok=True)
    LOG_FILE = os.path.join(log_dir, 'debug_app.log')
else:
    LOG_FILE = 'debug_app.log'

# 3. Детальное логирование старта каждого процесса
pid = os.getpid()
ppid = os.getppid()
args = sys.argv
exe = sys.executable

try:
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"\n--- [PROCESS START] PID: {pid} | PPID: {ppid} ---\n")
        f.write(f"  sys.executable: {exe}\n")
        f.write(f"  sys.argv: {args}\n")
        f.write(f"  PyInstaller _MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}\n")
except Exception:
    pass

# 4. Автоматическое добавление путей Homebrew в PATH для macOS
if sys.platform == "darwin":
    extra_paths = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    current_path = os.environ.get("PATH", "")
    for p in extra_paths:
        if p not in current_path and os.path.exists(p):
            current_path = f"{p}:{current_path}"
    os.environ["PATH"] = current_path

# 5. Настройка стандартного логгера
APP_VERSION = "1.1.21"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8',
    force=True
)

logging.getLogger('matplotlib').setLevel(logging.WARNING)

# 6. Фиксация корня проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import customtkinter as ctk
from PIL import Image

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(PROJECT_ROOT, relative_path)

class SmartSplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.withdraw()
        self.overrideredirect(True)
        
        width, height = 520, 320
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.configure(fg_color="#121316")

        self.main_frame = ctk.CTkFrame(self, fg_color="#121316", border_width=1, border_color="#2b2e36")
        self.main_frame.pack(fill="both", expand=True)

        icon_path = get_resource_path("AutoBlureFaca_icon.png")
        if not os.path.exists(icon_path):
            icon_path = get_resource_path("app_icon.icns")

        if os.path.exists(icon_path):
            try:
                pil_img = Image.open(icon_path)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(64, 64))
                lbl_img = ctk.CTkLabel(self.main_frame, image=ctk_img, text="")
                lbl_img.pack(pady=(20, 5))
            except Exception:
                pass

        lbl_title = ctk.CTkLabel(self.main_frame, text="FaceBlur Studio", font=("Helvetica", 20, "bold"), text_color="#ffffff")
        lbl_title.pack(pady=(2, 2))

        lbl_sub = ctk.CTkLabel(self.main_frame, text=f"Версия {APP_VERSION} — Загрузка системы...", font=("Helvetica", 11), text_color="#8a8f9d")
        lbl_sub.pack(pady=(0, 10))

        self.txt_error = ctk.CTkTextbox(
            self.main_frame, 
            height=160, 
            fg_color="#181a1f", 
            text_color="#ff5555", 
            font=("Consolas", 10), 
            border_width=1, 
            border_color="#442222",
            activate_scrollbars=True
        )

        self.btn_close = ctk.CTkButton(
            self.main_frame, 
            text="Закрыть", 
            width=110, 
            height=28, 
            fg_color="#e54e38", 
            hover_color="#c43d28", 
            command=self.destroy
        )

        self.status_bar = ctk.CTkFrame(self.main_frame, height=30, corner_radius=0, fg_color="#16171a", border_width=1, border_color="#262930")
        self.status_bar.pack(side="bottom", fill="x")

        self.lbl_status = ctk.CTkLabel(
            self.status_bar, 
            text="⏳ Инициализация компонентов...", 
            font=("Helvetica", 11), 
            text_color="#8a8f9d", 
            anchor="w"
        )
        self.lbl_status.pack(side="left", padx=12, pady=4, fill="x", expand=True)

        self.is_splash_visible = False
        self.start_time = time.time()

        self.after(400, self.reveal_if_slow)
        
        threading.Thread(target=self.load_application, daemon=True).start()

    def reveal_if_slow(self):
        if not self.is_splash_visible:
            self.is_splash_visible = True
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)

    def update_status(self, text: str):
        self.lbl_status.configure(text=text, text_color="#8a8f9d")

    def show_error(self, err_msg: str):
        self.overrideredirect(False)
        
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 680, 480
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self.reveal_if_slow()
        last_line = [line for line in err_msg.splitlines() if line.strip()][-1]
        self.lbl_status.configure(text=f"⚠️ {last_line}", text_color="#e54e38")
        
        self.txt_error.pack(padx=20, pady=(0, 8), fill="both", expand=True)
        self.txt_error.insert("1.0", err_msg)
        self.txt_error.configure(state="disabled")
        
        self.btn_close.pack(pady=(0, 10))

    def load_application(self):
        try:
            self.update_status("⚙️ Проверка библиотек Python...")
            import customtkinter as ctk_lib
            import cv2
            import PIL

            self.update_status("🔍 Проверка весов YOLOv8...")
            model_path = get_resource_path("yolov8s-face.pt")
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Файл весов 'yolov8s-face.pt' не найден по пути: {model_path}")

            self.update_status("🎨 Инициализация интерфейса...")
            from ui.main_window import MainWindow

            self.after(0, lambda: self.finish_loading(MainWindow))

        except Exception:
            err = traceback.format_exc()
            self.after(0, lambda: self.show_error(err))

    def finish_loading(self, main_window_cls):
        try:
            app = main_window_cls()
            self.destroy()
            app.mainloop()
        except Exception:
            err = traceback.format_exc()
            self.show_error(err)

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # Фильтрация и мгновенное завершение любых фоновых/дочерних процессов без создания GUI
    if len(sys.argv) > 1 or any(k in str(sys.argv) for k in ["--multiprocessing-fork", "parent_pid", "spawn", "fork"]):
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(f"  => [BLOCKED] Процесс PID {pid} отфильтрован как воркер и завершен.\n")
        except Exception:
            pass
        sys.exit(0)

    app_splash = SmartSplashScreen()
    app_splash.mainloop()