import sys
import os
import time
import threading
import traceback
import customtkinter as ctk
from PIL import Image

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class SmartSplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Скрываем окно при старте (отрисовываем только если будет задержка или ошибка)
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

        icon_path = get_resource_path("AutoBlureFace_icon.png")
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

        lbl_sub = ctk.CTkLabel(self.main_frame, text="Версия 0.7 — Загрузка системы...", font=("Helvetica", 11), text_color="#8a8f9d")
        lbl_sub.pack(pady=(0, 10))

        self.txt_error = ctk.CTkTextbox(
            self.main_frame, 
            height=90, 
            fg_color="#181a1f", 
            text_color="#ff5555", 
            font=("Consolas", 10), 
            border_width=1, 
            border_color="#442222"
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

        # Показываем SplashScreen только если загрузка длится дольше 400 мс
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
        self.reveal_if_slow()
        last_line = [line for line in err_msg.splitlines() if line.strip()][-1]
        self.lbl_status.configure(text=f"⚠️ {last_line}", text_color="#e54e38")
        
        self.txt_error.pack(padx=20, pady=(0, 8), fill="x")
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
    app_splash = SmartSplashScreen()
    app_splash.mainloop()