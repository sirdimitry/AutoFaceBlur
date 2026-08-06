import os
import sys
import webbrowser
import customtkinter as ctk
from PIL import Image

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def show_about_dialog(parent_window, cursor_hand):
    dialog = ctk.CTkToplevel(parent_window)
    dialog.title("О программе")
    dialog.geometry("380x440")
    dialog.configure(fg_color="#181a1f")
    dialog.resizable(False, False)
    dialog.transient(parent_window)
    dialog.grab_set()

    icon_path = get_resource_path("AutoBlureFace_icon.png")
    if os.path.exists(icon_path):
        pil_img = Image.open(icon_path)
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(128, 128))
        lbl_img = ctk.CTkLabel(dialog, image=ctk_img, text="")
        lbl_img.pack(pady=(25, 10))

    lbl_title = ctk.CTkLabel(dialog, text="FaceBlur Studio", font=("Helvetica", 20, "bold"), text_color="#ffffff")
    lbl_title.pack(pady=(5, 2))

    lbl_ver = ctk.CTkLabel(dialog, text="Версия 1.1.0 (Modular Architecture)", font=("Helvetica", 11), text_color="#8a8f9d")
    lbl_ver.pack(pady=(0, 10))

    lbl_desc = ctk.CTkLabel(
        dialog, 
        text="Полностью автоматический локальный\nинструмент защиты приватности на видео\nс использованием YOLOv8-face.", 
        font=("Helvetica", 12),
        text_color="#c2c7d0",
        justify="center"
    )
    lbl_desc.pack(pady=10)

    lbl_author = ctk.CTkLabel(
        dialog, 
        text="© @sirdimitry, 2026", 
        font=("Helvetica", 12, "bold", "underline"), 
        text_color="#e54e38",
        cursor=cursor_hand
    )
    lbl_author.pack(pady=(15, 20))
    lbl_author.bind("<Button-1>", lambda e: webbrowser.open("https://x.com/sirdimitry"))

    btn_close = ctk.CTkButton(
        dialog, 
        text="Закрыть", 
        width=120, 
        fg_color="#2b2e36",
        hover_color="#383c47",
        text_color="#d1d5db",
        command=dialog.destroy, 
        cursor=cursor_hand
    )
    btn_close.pack(pady=(0, 15))