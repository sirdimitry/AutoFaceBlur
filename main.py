import os
import sys
import time
import customtkinter as ctk
from PIL import Image
from ui.main_window import MainWindow, get_resource_path

os.environ["TK_SILENCE_DEPRECATION"] = "1"

class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.geometry("480x330")
        self.configure(fg_color="#121316")

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w // 2) - 240
        y = (screen_h // 2) - 165
        self.geometry(f"480x330+{x}+{y}")

        self.card = ctk.CTkFrame(self, corner_radius=12, fg_color="#1e2025", border_width=1, border_color="#2b2e36")
        self.card.pack(fill="both", expand=True, padx=2, pady=2)

        icon_path = get_resource_path("AutoBlureFace_icon.png")
        if os.path.exists(icon_path):
            pil_img = Image.open(icon_path)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(96, 96))
            lbl_img = ctk.CTkLabel(self.card, image=ctk_img, text="")
            lbl_img.pack(pady=(20, 6))

        lbl_title = ctk.CTkLabel(self.card, text="FaceBlur Studio", font=("Helvetica", 22, "bold"), text_color="#ffffff")
        lbl_title.pack(pady=(0, 2))

        lbl_sub_ru = ctk.CTkLabel(
            self.card, 
            text="Полностью автоматический локальный инструмент защиты приватности на видео", 
            font=("Helvetica", 11, "bold"), 
            text_color="#e54e38",
            wraplength=440
        )
        lbl_sub_ru.pack(pady=(0, 2))

        lbl_sub_en = ctk.CTkLabel(
            self.card, 
            text="Fully automated local video privacy protection tool", 
            font=("Helvetica", 10, "italic"), 
            text_color="#8a8f9d",
            wraplength=440
        )
        lbl_sub_en.pack(pady=(0, 10))

        lbl_author = ctk.CTkLabel(
            self.card, 
            text="© @sirdimitry, 2026", 
            font=("Helvetica", 10, "bold"), 
            text_color="#d1d5db"
        )
        lbl_author.pack(pady=(0, 12))

        self.progress = ctk.CTkProgressBar(self.card, width=340, height=4, progress_color="#e54e38", fg_color="#16171a")
        self.progress.set(0)
        self.progress.pack(pady=(0, 15))

    def animate(self):
        for i in range(1, 101):
            self.progress.set(i / 100.0)
            self.update()
            time.sleep(0.012)


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    
    app = MainWindow()
    app.withdraw()

    splash = SplashScreen(app)
    splash.animate()
    splash.destroy()

    app.deiconify()
    app.mainloop()