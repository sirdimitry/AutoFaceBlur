import json
import os
import sys
import threading
import webbrowser
import customtkinter as ctk
import tkinter as tk
from PIL import Image
from core.video_reader import FFmpegVideoReader
from core.detector import FaceDetector
from core.blurrer import FaceBlurrer
from core.video_writer import FFmpegVideoWriter

CONFIG_FILE = "config.json"
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Кроссплатформенный курсор: "pointinghand" для macOS, "hand2" для Windows/Linux
CURSOR_HAND = "pointinghand" if sys.platform == "darwin" else "hand2"

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FaceBlur Studio — v0.8")
        
        # Геометрия с учётом совместимости Windows/macOS
        self.geometry("1100x750")
        if sys.platform == "win32":
            self.state("zoomed")
        self.deiconify()
        self.focus_force()

        self.configure(fg_color="#121316")

        self.settings = self.load_settings()

        self.reader = None
        self.detector = None
        self.blurrer = FaceBlurrer(
            blur_percent=self.settings.get("blur_percent", 70), 
            padding_percent=self.settings.get("padding_percent", 25), 
            fade_percent=self.settings.get("fade_percent", 40),
            shape_percent=self.settings.get("shape_percent", 100)
        )
        self.is_playing = False
        self.current_frame_idx = 0
        
        self.raw_frames = []
        self.blurred_frames_cache = []
        self.detected_boxes_cache = {}
        self.unique_faces = {}
        self.reblur_timer = None

        self.is_analysing = False
        self.is_exporting = False
        self.stop_analysis_flag = False

        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.current_pil_img = None

        # Нижняя строка состояния DaVinci Style
        self.status_bar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color="#16171a", border_width=1, border_color="#262930")
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.bind("<Configure>", self.on_status_bar_resize)

        self.lbl_status_right = ctk.CTkLabel(
            self.status_bar, 
            text="", 
            font=("Helvetica", 11),
            text_color="#8a8f9d",
            anchor="e"
        )
        self.lbl_status_right.pack(side="right", padx=(5, 15), pady=2)

        self.lbl_status_left = ctk.CTkLabel(
            self.status_bar, 
            text="Готов к работе", 
            font=("Helvetica", 11),
            text_color="#8a8f9d",
            anchor="w"
        )
        self.lbl_status_left.pack(side="left", padx=(15, 5), pady=2, fill="x", expand=True)

        # Левая панель (Inspector DaVinci Style)
        self.sidebar = ctk.CTkFrame(self, width=310, corner_radius=0, fg_color="#1e2025", border_width=1, border_color="#2b2e36")
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)

        # Заголовок Инспектора
        self.lbl_inspector_header = ctk.CTkLabel(
            self.sidebar,
            text="INSPECTOR / НАСТРОЙКИ",
            font=("Helvetica", 11, "bold"),
            text_color="#e54e38",
            anchor="w"
        )
        self.lbl_inspector_header.pack(padx=15, pady=(12, 8), fill="x")

        self.btn_open = ctk.CTkButton(
            self.sidebar, 
            text="+ Выбрать видео", 
            height=38, 
            font=("Helvetica", 13, "bold"),
            fg_color="#2b2e36",
            hover_color="#383c47",
            text_color="#d1d5db",
            cursor=CURSOR_HAND,
            border_width=1,
            border_color="#3a3e4a",
            command=self.open_video
        )
        self.btn_open.pack(padx=15, pady=(0, 6), fill="x")

        # Кнопки проекта
        self.project_btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.project_btn_frame.pack(padx=15, pady=(0, 10), fill="x")

        self.btn_save_proj = ctk.CTkButton(
            self.project_btn_frame,
            text="📁 Сохранить",
            height=28,
            font=("Helvetica", 11),
            fg_color="#252830",
            hover_color="#323642",
            text_color="#b0b5c0",
            cursor=CURSOR_HAND,
            border_width=1,
            border_color="#323642",
            command=self.save_project,
            state="disabled"
        )
        self.btn_save_proj.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.btn_load_proj = ctk.CTkButton(
            self.project_btn_frame,
            text="📂 Открыть",
            height=28,
            font=("Helvetica", 11),
            fg_color="#252830",
            hover_color="#323642",
            text_color="#b0b5c0",
            cursor=CURSOR_HAND,
            border_width=1,
            border_color="#323642",
            command=self.load_project
        )
        self.btn_load_proj.pack(side="right", expand=True, fill="x", padx=(2, 0))

        # Разделитель
        self.div1 = ctk.CTkFrame(self.sidebar, height=1, fg_color="#2b2e36")
        self.div1.pack(fill="x", padx=15, pady=5)

        # Настройки слайдеров
        blur_val = self.settings.get("blur_percent", 70)
        self.lbl_blur_title = ctk.CTkLabel(self.sidebar, text=f"Сила размытия: {blur_val}%", font=("Helvetica", 11), text_color="#c2c7d0")
        self.lbl_blur_title.pack(padx=15, pady=(4, 0), anchor="w")

        self.blur_slider = ctk.CTkSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color="#d1d5db", button_hover_color="#ffffff", progress_color="#e54e38", fg_color="#16171a", command=self.on_blur_slider_change)
        self.blur_slider.set(blur_val)
        self.blur_slider.pack(padx=15, pady=(2, 6), fill="x")

        pad_val = self.settings.get("padding_percent", 25)
        self.lbl_pad_title = ctk.CTkLabel(self.sidebar, text=f"Размер маски: {pad_val}%", font=("Helvetica", 11), text_color="#c2c7d0")
        self.lbl_pad_title.pack(padx=15, pady=(4, 0), anchor="w")

        self.pad_slider = ctk.CTkSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color="#d1d5db", button_hover_color="#ffffff", progress_color="#e54e38", fg_color="#16171a", command=self.on_pad_slider_change)
        self.pad_slider.set(pad_val)
        self.pad_slider.pack(padx=15, pady=(2, 6), fill="x")

        fade_val = self.settings.get("fade_percent", 40)
        self.lbl_fade_title = ctk.CTkLabel(self.sidebar, text=f"Мягкость краев (Fade): {fade_val}%", font=("Helvetica", 11), text_color="#c2c7d0")
        self.lbl_fade_title.pack(padx=15, pady=(4, 0), anchor="w")

        self.fade_slider = ctk.CTkSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color="#d1d5db", button_hover_color="#ffffff", progress_color="#e54e38", fg_color="#16171a", command=self.on_fade_slider_change)
        self.fade_slider.set(fade_val)
        self.fade_slider.pack(padx=15, pady=(2, 6), fill="x")

        shape_val = self.settings.get("shape_percent", 100)
        self.lbl_shape_title = ctk.CTkLabel(self.sidebar, text=f"Форма маски: {self.get_shape_text(shape_val)}", font=("Helvetica", 11), text_color="#c2c7d0")
        self.lbl_shape_title.pack(padx=15, pady=(4, 0), anchor="w")

        self.shape_slider = ctk.CTkSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color="#d1d5db", button_hover_color="#ffffff", progress_color="#e54e38", fg_color="#16171a", command=self.on_shape_slider_change)
        self.shape_slider.set(shape_val)
        self.shape_slider.pack(padx=15, pady=(2, 8), fill="x")

        self.div2 = ctk.CTkFrame(self.sidebar, height=1, fg_color="#2b2e36")
        self.div2.pack(fill="x", padx=15, pady=5)

        # Детекция и Стоп
        self.analysis_btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.analysis_btn_frame.pack(padx=15, pady=4, fill="x")

        self.btn_analyze = ctk.CTkButton(
            self.analysis_btn_frame,
            text="⚡ Анализировать",
            height=36,
            font=("Helvetica", 12, "bold"),
            fg_color="#2b2e36",
            hover_color="#383c47",
            text_color="#d1d5db",
            border_width=1,
            border_color="#3a3e4a",
            cursor=CURSOR_HAND,
            command=self.start_analysis_thread,
            state="disabled"
        )
        self.btn_analyze.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_stop = ctk.CTkButton(
            self.analysis_btn_frame,
            text="⏹",
            width=36,
            height=36,
            font=("Helvetica", 12, "bold"),
            fg_color="#2b2e36",
            hover_color="#383c47",
            text_color="#e54e38",
            border_width=1,
            border_color="#3a3e4a",
            cursor=CURSOR_HAND,
            command=self.stop_analysis,
            state="disabled"
        )
        self.btn_stop.pack(side="right")

        # Чекбокс
        self.chk_export_labels = ctk.CTkCheckBox(
            self.sidebar,
            text="Сохранять номера ID в видео",
            font=("Helvetica", 11),
            text_color="#b0b5c0",
            checkmark_color="#ffffff",
            fg_color="#e54e38",
            hover_color="#d9532f",
            cursor=CURSOR_HAND,
            command=self.on_export_labels_toggle
        )
        if self.settings.get("export_labels", False):
            self.chk_export_labels.select()
        else:
            self.chk_export_labels.deselect()
        self.chk_export_labels.pack(padx=15, pady=(6, 4), anchor="w")

        # Кнопка Экспорта
        self.btn_export = ctk.CTkButton(
            self.sidebar,
            text="💾 Экспорт",
            height=36,
            font=("Helvetica", 12, "bold"),
            fg_color="#2b2e36",
            hover_color="#383c47",
            text_color="#717684",
            border_width=1,
            border_color="#3a3e4a",
            cursor=CURSOR_HAND,
            command=self.export_video,
            state="disabled"
        )
        self.btn_export.pack(padx=15, pady=(4, 2), fill="x")

        # Прогресс-бар экспорта (DaVinci Red)
        self.export_progress = ctk.CTkProgressBar(self.sidebar, height=4, progress_color="#e54e38", fg_color="#16171a")
        self.export_progress.set(0)
        self.export_progress.pack(padx=15, pady=(0, 6), fill="x")

        self.lbl_gallery = ctk.CTkLabel(self.sidebar, text="НАЙДЕННЫЕ ОБЪЕКТЫ:", font=("Helvetica", 10, "bold"), text_color="#8a8f9d")
        self.lbl_gallery.pack(padx=15, pady=(4, 2), anchor="w")

        self.gallery_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="#16171a", border_width=1, border_color="#282b33")
        self.gallery_frame.pack(padx=15, pady=5, fill="both", expand=True)

        self.bind_scroll_events(self.gallery_frame)

        # Ошибки
        self.lbl_error_log = ctk.CTkLabel(
            self.sidebar,
            text="",
            font=("Helvetica", 11),
            text_color="#e54e38",
            wraplength=270,
            justify="left",
            anchor="w"
        )
        self.lbl_error_log.pack(padx=15, pady=(2, 2), fill="x", side="bottom")

        # Кнопка "О программе"
        self.btn_about = ctk.CTkButton(
            self.sidebar,
            text="ℹ️ О программе",
            height=28,
            font=("Helvetica", 11),
            fg_color="#252830",
            hover_color="#323642",
            text_color="#9ca3af",
            cursor=CURSOR_HAND,
            command=self.show_about_dialog
        )
        self.btn_about.pack(padx=15, pady=(5, 8), fill="x", side="bottom")

        # Правая часть (Viewer Canvas Container)
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        self.canvas_container = ctk.CTkFrame(self.right_frame, fg_color="#0c0d0f", border_width=1, border_color="#23262e")
        self.canvas_container.pack(expand=True, fill="both", padx=0, pady=(0, 10))

        # Виджет вывода кадров через CTkLabel вместо tk.Canvas для стабильности в Windows
        self.video_display = ctk.CTkLabel(self.canvas_container, text="", fg_color="#0c0d0f")
        self.video_display.pack(expand=True, fill="both")

        self.video_display.bind("<Configure>", self.on_canvas_resize)
        self.video_display.bind("<MouseWheel>", self.on_mouse_wheel)
        self.video_display.bind("<Button-4>", lambda e: self.on_mouse_zoom_step(1.05))
        self.video_display.bind("<Button-5>", lambda e: self.on_mouse_zoom_step(0.95))
        self.video_display.bind("<ButtonPress-1>", self.on_drag_start)
        self.video_display.bind("<B1-Motion>", self.on_drag_motion)
        self.video_display.bind("<Double-Button-1>", self.on_canvas_double_click)

        # Элементы управления плеером
        self.player_controls = ctk.CTkFrame(self.right_frame, height=50, fg_color="#181a1f", border_width=1, border_color="#262930")
        self.player_controls.pack(fill="x", side="bottom", padx=0, pady=0)

        self.btn_play = ctk.CTkButton(
            self.player_controls, 
            text="▶ Play", 
            width=70, 
            height=30,
            font=("Helvetica", 12, "bold"),
            fg_color="#2b2e36",
            hover_color="#383c47",
            text_color="#d1d5db",
            cursor=CURSOR_HAND,
            border_width=1,
            border_color="#3a3e4a",
            command=self.toggle_play,
            state="disabled"
        )
        self.btn_play.pack(side="left", padx=10, pady=10)

        self.time_label = ctk.CTkLabel(self.player_controls, text="00:00 / 00:00", font=("Helvetica", 11), text_color="#8a8f9d")
        self.time_label.pack(side="right", padx=10, pady=10)

        self.slider = ctk.CTkSlider(
            self.player_controls, 
            from_=0, 
            to=100, 
            button_color="#d1d5db",
            button_hover_color="#ffffff",
            progress_color="#e54e38",
            fg_color="#111215",
            command=self.on_slider_seek,
            state="disabled"
        )
        self.slider.pack(side="left", expand=True, fill="x", padx=10, pady=10)

    def bind_scroll_events(self, widget):
        widget.bind_all("<MouseWheel>", self._on_generic_scroll)
        widget.bind_all("<Button-4>", lambda e: self.gallery_frame._parent_canvas.yview_scroll(-1, "units"))
        widget.bind_all("<Button-5>", lambda e: self.gallery_frame._parent_canvas.yview_scroll(1, "units"))

    def _on_generic_scroll(self, event):
        if hasattr(self, 'gallery_frame') and self.gallery_frame.winfo_exists():
            if sys.platform == "darwin":
                self.gallery_frame._parent_canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                self.gallery_frame._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_canvas_double_click(self, event):
        if not self.current_pil_img or not self.raw_frames:
            self.reset_zoom()
            return

        canvas_w = self.video_display.winfo_width()
        canvas_h = self.video_display.winfo_height()
        img_w, img_h = self.current_pil_img.size

        scale = min(canvas_w / img_w, canvas_h / img_h) * self.zoom_factor
        new_w = max(10, int(img_w * scale))
        new_h = max(10, int(img_h * scale))

        center_x = (canvas_w // 2) + self.pan_x
        center_y = (canvas_h // 2) + self.pan_y

        img_x1 = center_x - (new_w // 2)
        img_y1 = center_y - (new_h // 2)

        click_video_x = int((event.x - img_x1) / scale)
        click_video_y = int((event.y - img_y1) / scale)

        faces = self.detected_boxes_cache.get(self.current_frame_idx, [])
        clicked_id = None

        for face in faces:
            x1, y1, x2, y2 = face['bbox']
            pad_w = int((x2 - x1) * self.blurrer.padding_percent)
            pad_h = int((y2 - y1) * self.blurrer.padding_percent)

            bx1 = x1 - pad_w
            by1 = y1 - pad_h
            bx2 = x2 + pad_w
            by2 = y2 + pad_h

            if bx1 <= click_video_x <= bx2 and by1 <= click_video_y <= by2:
                clicked_id = face['id']
                break

        if clicked_id is not None:
            self.toggle_face_blur(clicked_id)
            self.populate_gallery_ui()
        else:
            self.reset_zoom()

    def save_project(self):
        if not self.reader or not self.detected_boxes_cache:
            return

        initial_dir = self.settings.get("last_directory", os.path.expanduser("~"))
        default_name = os.path.splitext(os.path.basename(self.reader.file_path))[0] + ".fbp"

        file_path = ctk.filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".fbp",
            filetypes=[("FaceBlur Project", "*.fbp")]
        )
        if not file_path:
            return

        serializable_cache = {}
        for frame_idx, faces in self.detected_boxes_cache.items():
            serializable_cache[str(frame_idx)] = faces

        active_states = {str(t_id): data['enabled'] for t_id, data in self.unique_faces.items()}

        project_data = {
            "video_path": self.reader.file_path,
            "blur_percent": self.blurrer.kernel_size,
            "padding_percent": self.settings.get("padding_percent", 25),
            "fade_percent": self.settings.get("fade_percent", 40),
            "shape_percent": self.settings.get("shape_percent", 100),
            "export_labels": bool(self.chk_export_labels.get()),
            "detected_boxes_cache": serializable_cache,
            "unique_faces_states": active_states
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            self.btn_save_proj.configure(text="✅ Сохранен")
            self.after(3000, lambda: self.btn_save_proj.configure(text="📁 Сохранить"))
        except Exception as e:
            self.log_error(f"Ошибка сохранения: {e}")

    def load_project(self):
        initial_dir = self.settings.get("last_directory", os.path.expanduser("~"))

        file_path = ctk.filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[("FaceBlur Project", "*.fbp")]
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                project_data = json.load(f)

            video_path = project_data.get("video_path")
            if not os.path.exists(video_path):
                self.log_error("Видео из проекта не найдено по пути!")
                return

            if self.reader:
                self.reader.close()

            self.reader = FFmpegVideoReader(video_path)
            self.update_status_bar_text()
            self.raw_frames = list(self.reader.read_frames())

            total = len(self.raw_frames)
            if total == 0:
                return

            raw_cache = project_data.get("detected_boxes_cache", {})
            self.detected_boxes_cache = {int(k): v for k, v in raw_cache.items()}
            active_states = {int(k): v for k, v in project_data.get("unique_faces_states", {}).items()}

            self.blur_slider.set(project_data.get("blur_percent", 70))
            self.on_blur_slider_change(project_data.get("blur_percent", 70))

            self.pad_slider.set(project_data.get("padding_percent", 25))
            self.on_pad_slider_change(project_data.get("padding_percent", 25))

            self.fade_slider.set(project_data.get("fade_percent", 40))
            self.on_fade_slider_change(project_data.get("fade_percent", 40))

            self.shape_slider.set(project_data.get("shape_percent", 100))
            self.on_shape_slider_change(project_data.get("shape_percent", 100))

            self.clear_gallery_ui()
            self.unique_faces.clear()

            for frame in self.raw_frames:
                for face in self.detected_boxes_cache.values():
                    for f in face:
                        t_id = f['id']
                        if t_id not in self.unique_faces:
                            x1, y1, x2, y2 = f['bbox']
                            crop = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
                            if crop.size > 0:
                                crop_rgb = crop[:, :, ::-1]
                                pil_img = Image.fromarray(crop_rgb)
                                pil_img.thumbnail((50, 50))
                                
                                is_enabled = active_states.get(t_id, True)
                                self.unique_faces[t_id] = {
                                    'pil_image': pil_img,
                                    'enabled': is_enabled,
                                    'widget': None
                                }

            self.slider.configure(state="normal", from_=0, to=total - 1, number_of_steps=total)
            self.slider.set(0)
            self.btn_play.configure(state="normal")
            
            self.btn_analyze.configure(
                text="✅ Проект загружен", 
                text_color="#38ef7d",
                state="normal"
            )
            self.btn_save_proj.configure(state="normal")
            self.btn_export.configure(
                text="💾 Экспорт", 
                state="normal", 
                text_color="#d1d5db"
            )
            
            self.populate_gallery_ui()
            self.rebuild_blur_cache()
            self.show_frame(0)

        except Exception as e:
            self.log_error(f"Ошибка загрузки: {e}")

    def log_error(self, message: str):
        self.lbl_error_log.configure(text=f"⚠️ {message}")

    def clear_error_log(self):
        self.lbl_error_log.configure(text="")

    def show_about_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("О программе")
        dialog.geometry("380x440")
        dialog.configure(fg_color="#181a1f")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        icon_path = get_resource_path("AutoBlureFace_icon.png")
        if os.path.exists(icon_path):
            pil_img = Image.open(icon_path)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(128, 128))
            lbl_img = ctk.CTkLabel(dialog, image=ctk_img, text="")
            lbl_img.pack(pady=(25, 10))

        lbl_title = ctk.CTkLabel(dialog, text="FaceBlur Studio", font=("Helvetica", 20, "bold"), text_color="#ffffff")
        lbl_title.pack(pady=(5, 2))

        lbl_ver = ctk.CTkLabel(dialog, text="Версия 0.8 (Cross-Platform Native)", font=("Helvetica", 11), text_color="#8a8f9d")
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
            cursor=CURSOR_HAND
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
            cursor=CURSOR_HAND
        )
        btn_close.pack(pady=(0, 15))

    def get_shape_text(self, val: int) -> str:
        if val >= 90:
            return f"Овал ({val}%)"
        elif val <= 10:
            return f"Квадрат ({val}%)"
        return f"Скругление ({val}%)"

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "blur_percent": 70, 
            "padding_percent": 25, 
            "fade_percent": 40,
            "shape_percent": 100,
            "export_labels": False,
            "last_directory": os.path.expanduser("~")
        }

    def save_settings(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.settings, f)
        except Exception:
            pass

    def on_export_labels_toggle(self):
        self.settings["export_labels"] = bool(self.chk_export_labels.get())
        self.save_settings()

    def stop_analysis(self):
        if self.is_analysing:
            self.stop_analysis_flag = True
            self.btn_stop.configure(state="disabled")

    def reset_zoom(self, event=None):
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.render_canvas_image()

    def on_mouse_wheel(self, event):
        if event.delta > 0:
            factor = 1.05
        else:
            factor = 0.95
        self.zoom_factor = max(1.0, min(4.0, self.zoom_factor * factor))
        if self.zoom_factor == 1.0:
            self.pan_x = 0
            self.pan_y = 0
        self.render_canvas_image()

    def on_mouse_zoom_step(self, factor):
        self.zoom_factor = max(1.0, min(4.0, self.zoom_factor * factor))
        if self.zoom_factor == 1.0:
            self.pan_x = 0
            self.pan_y = 0
        self.render_canvas_image()

    def on_drag_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag_motion(self, event):
        if self.zoom_factor > 1.0:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            self.pan_x += dx
            self.pan_y += dy
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.render_canvas_image()

    def on_canvas_resize(self, event):
        if self.current_pil_img:
            self.render_canvas_image()

    def on_status_bar_resize(self, event):
        if self.reader:
            self.update_status_bar_text()

    def update_status_bar_text(self):
        if not self.reader:
            self.lbl_status_left.configure(text="Готов к работе")
            self.lbl_status_right.configure(text="")
            return

        right_text = (
            f"Разрешение: {self.reader.width}x{self.reader.height} ({self.reader.aspect_ratio})  |  "
            f"Кодек: {self.reader.codec} ({self.reader.bitrate_str})  |  "
            f"FPS: {self.reader.fps:.2f}  |  "
            f"Кадров: {self.reader.total_frames}"
        )
        self.lbl_status_right.configure(text=right_text)

        total_width = self.status_bar.winfo_width()
        right_width = self.lbl_status_right.winfo_reqwidth()
        available_left_px = max(100, total_width - right_width - 40)

        orig_filename = os.path.basename(self.reader.file_path)
        max_chars = max(10, int(available_left_px / 8))
        if len(orig_filename) > max_chars:
            ext = orig_filename.split('.')[-1]
            name_no_ext = orig_filename[:-len(ext)-1]
            short_name = name_no_ext[:max_chars - 3] + "..." + "." + ext
        else:
            short_name = orig_filename

        self.lbl_status_left.configure(text=f"Файл: {short_name}")

    def render_canvas_image(self):
        if not self.current_pil_img:
            return

        canvas_w = self.video_display.winfo_width()
        canvas_h = self.video_display.winfo_height()

        if canvas_w < 50 or canvas_h < 50:
            return

        img_w, img_h = self.current_pil_img.size
        scale = min(canvas_w / img_w, canvas_h / img_h) * self.zoom_factor

        new_w = max(10, int(img_w * scale))
        new_h = max(10, int(img_h * scale))

        # Стабильное отображение кадров через CTkImage (без Pillow PhotoImage)
        ctk_img = ctk.CTkImage(light_image=self.current_pil_img, dark_image=self.current_pil_img, size=(new_w, new_h))
        self.video_display.configure(image=ctk_img)

    def on_blur_slider_change(self, value):
        val = int(value)
        self.blurrer.set_blur_percent(val)
        self.lbl_blur_title.configure(text=f"Сила размытия: {val}%")
        self.settings["blur_percent"] = val
        self.save_settings()
        self.trigger_live_reblur()

    def on_pad_slider_change(self, value):
        val = int(value)
        self.blurrer.set_padding_percent(val)
        self.lbl_pad_title.configure(text=f"Размер маски: {val}%")
        self.settings["padding_percent"] = val
        self.save_settings()
        self.trigger_live_reblur()

    def on_fade_slider_change(self, value):
        val = int(value)
        self.blurrer.set_fade_percent(val)
        self.lbl_fade_title.configure(text=f"Мягкость краев (Fade): {val}%")
        self.settings["fade_percent"] = val
        self.save_settings()
        self.trigger_live_reblur()

    def on_shape_slider_change(self, value):
        val = int(value)
        self.blurrer.set_shape_percent(val)
        self.lbl_shape_title.configure(text=f"Форма маски: {self.get_shape_text(val)}")
        self.settings["shape_percent"] = val
        self.save_settings()
        self.trigger_live_reblur()

    def trigger_live_reblur(self):
        if self.detected_boxes_cache:
            self.show_frame(self.current_frame_idx)
            if self.reblur_timer:
                self.after_cancel(self.reblur_timer)
            self.reblur_timer = self.after(300, self.schedule_full_reblur)

    def schedule_full_reblur(self):
        threading.Thread(target=self.rebuild_blur_cache, daemon=True).start()

    def open_video(self):
        self.clear_error_log()
        try:
            if self.is_analysing:
                self.stop_analysis_flag = True

            initial_dir = self.settings.get("last_directory", os.path.expanduser("~"))

            file_path = ctk.filedialog.askopenfilename(
                initialdir=initial_dir,
                filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi")]
            )
            if not file_path:
                return

            self.settings["last_directory"] = os.path.dirname(file_path)
            self.save_settings()

            if self.reader:
                self.reader.close()

            self.is_playing = False
            self.btn_play.configure(text="▶ Play")
            self.blurred_frames_cache.clear()
            self.detected_boxes_cache.clear()
            self.unique_faces.clear()
            self.reset_zoom()
            self.export_progress.set(0)
            self.clear_gallery_ui()

            self.reader = FFmpegVideoReader(file_path)
            self.update_status_bar_text()

            self.raw_frames = list(self.reader.read_frames())
            total = len(self.raw_frames)

            if total > 0:
                self.slider.configure(state="normal", from_=0, to=total - 1, number_of_steps=total)
                self.slider.set(0)
                self.btn_play.configure(state="normal")
                self.btn_analyze.configure(
                    text="⚠️ Требуется анализ", 
                    text_color="#e54e38",
                    state="normal"
                )
                self.btn_save_proj.configure(state="disabled")
                self.btn_stop.configure(state="disabled")
                
                self.btn_export.configure(
                    text="💾 Экспорт", 
                    state="disabled", 
                    text_color="#717684"
                )
                self.show_frame(0)
        except Exception as e:
            self.log_error(str(e))

    def export_video(self):
        if not self.raw_frames or self.is_exporting:
            return

        initial_dir = self.settings.get("last_directory", os.path.expanduser("~"))
        default_name = "blurred_" + os.path.basename(self.reader.file_path)

        output_path = ctk.filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")]
        )
        if not output_path:
            return

        self.settings["last_directory"] = os.path.dirname(output_path)
        self.save_settings()

        self.is_exporting = True
        self.export_progress.set(0)
        
        self.btn_export.configure(
            state="disabled", 
            text="⏳ Экспорт: 0%", 
            text_color="#ffffff"
        )
        threading.Thread(target=self._run_export, args=(output_path,), daemon=True).start()

    def _run_export(self, output_path):
        try:
            writer = FFmpegVideoWriter(
                output_path=output_path,
                width=self.reader.width,
                height=self.reader.height,
                fps=self.reader.fps,
                source_audio_path=self.reader.file_path
            )

            active_blur_ids = self.get_active_blur_ids()
            total_frames = len(self.raw_frames)
            save_labels = bool(self.chk_export_labels.get())

            for i, frame in enumerate(self.raw_frames):
                faces_data = self.detected_boxes_cache.get(i, [])
                
                if save_labels:
                    out_frame = self.blurrer.apply_blur_and_labels(frame, faces_data, active_blur_ids)
                else:
                    out_frame = self.blurrer.apply_blur_only(frame, faces_data, active_blur_ids)

                writer.write_frame(out_frame)
                
                progress_ratio = (i + 1) / total_frames
                self.export_progress.set(progress_ratio)
                progress_percent = int(progress_ratio * 100)
                self.btn_export.configure(text=f"⏳ Экспорт: {progress_percent}% ({i+1}/{total_frames})")

            writer.close()
            self.after(0, self._on_export_finished_ui)
        except Exception as e:
            self.after(0, lambda: self.log_error(str(e)))

    def _on_export_finished_ui(self):
        self.is_exporting = False
        self.export_progress.set(1.0)
        self.btn_export.configure(
            text="✅ Сохранено", 
            text_color="#38ef7d",
            state="normal"
        )
        self.after(5000, self._reset_export_button_ui)

    def _reset_export_button_ui(self):
        if not self.is_exporting:
            self.export_progress.set(0)
            self.btn_export.configure(
                text="💾 Экспорт",
                text_color="#d1d5db",
                state="normal"
            )

    def clear_gallery_ui(self):
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

    def start_analysis_thread(self):
        self.is_analysing = True
        self.stop_analysis_flag = False
        self.btn_analyze.configure(state="disabled", text="⏳ Детекция...", text_color="#d1d5db")
        self.btn_stop.configure(state="normal")
        self.btn_play.configure(state="disabled")
        
        self.btn_export.configure(state="disabled", text_color="#717684")
        self.export_progress.set(0)
        self.clear_gallery_ui()
        self.unique_faces.clear()
        threading.Thread(target=self._run_full_analysis, daemon=True).start()

    def _run_full_analysis(self):
        try:
            if not self.detector:
                model_path = get_resource_path("yolov8s-face.pt")
                self.detector = FaceDetector(model_path=model_path)

            self.detected_boxes_cache.clear()
            total_frames = len(self.raw_frames)

            for i, frame in enumerate(self.raw_frames):
                if self.stop_analysis_flag:
                    break

                tracked_faces = self.detector.track_faces(frame)
                self.detected_boxes_cache[i] = tracked_faces

                for face in tracked_faces:
                    t_id = face['id']
                    if t_id not in self.unique_faces:
                        x1, y1, x2, y2 = face['bbox']
                        crop = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
                        if crop.size > 0:
                            crop_rgb = crop[:, :, ::-1]
                            pil_img = Image.fromarray(crop_rgb)
                            pil_img.thumbnail((50, 50))
                            
                            self.unique_faces[t_id] = {
                                'pil_image': pil_img,
                                'enabled': True,
                                'widget': None
                            }

                progress = int(((i + 1) / total_frames) * 100)
                self.btn_analyze.configure(text=f"⏳ Анализ: {progress}%")

            self.rebuild_blur_cache()
            self.after(0, self._on_analysis_finished_ui)
        except Exception as e:
            self.after(0, lambda: self.log_error(str(e)))

    def _on_analysis_finished_ui(self):
        self.is_analysing = False
        self.btn_stop.configure(state="disabled")
        
        if self.stop_analysis_flag:
            self.btn_analyze.configure(
                text="⚠️ Остановлен", 
                text_color="#e54e38", 
                state="normal"
            )
        else:
            self.btn_analyze.configure(
                text="✅ Анализ актуален", 
                text_color="#38ef7d", 
                state="normal"
            )

        self.btn_save_proj.configure(state="normal")
        self.btn_play.configure(state="normal")
        
        self.btn_export.configure(
            text="💾 Экспорт",
            state="normal", 
            text_color="#d1d5db"
        )
        self.populate_gallery_ui()
        self.show_frame(self.current_frame_idx)

    def populate_gallery_ui(self):
        self.clear_gallery_ui()
        for t_id, data in self.unique_faces.items():
            row = ctk.CTkFrame(self.gallery_frame, fg_color="#21242c", border_width=1, border_color="#2f333e")
            row.pack(fill="x", pady=3, padx=2)
            data['widget'] = row

            pil_img = data['pil_image']
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)

            lbl_img = ctk.CTkLabel(row, image=ctk_img, text="")
            lbl_img.pack(side="left", padx=5)

            chk = ctk.CTkCheckBox(
                row, 
                text=f"Объект #{t_id:02d}", 
                font=("Helvetica", 11),
                text_color="#d1d5db",
                checkmark_color="#ffffff",
                fg_color="#e54e38",
                hover_color="#d9532f",
                cursor=CURSOR_HAND,
                command=lambda id_=t_id: self.toggle_face_blur(id_)
            )
            if data['enabled']:
                chk.select()
            else:
                chk.deselect()
            chk.pack(side="left", padx=5)

    def toggle_face_blur(self, track_id):
        if track_id in self.unique_faces:
            curr = self.unique_faces[track_id]['enabled']
            self.unique_faces[track_id]['enabled'] = not curr
            self.trigger_live_reblur()

    def get_active_blur_ids(self):
        return {t_id for t_id, data in self.unique_faces.items() if data['enabled']}

    def rebuild_blur_cache(self):
        active_ids = self.get_active_blur_ids()
        new_cache = []
        for i, frame in enumerate(self.raw_frames):
            faces_data = self.detected_boxes_cache.get(i, [])
            blurred_frame = self.blurrer.apply_blur_and_labels(self.raw_frames[i], faces_data, active_ids)
            new_cache.append(blurred_frame)
        self.blurred_frames_cache = new_cache

    def update_gallery_highlighting(self, active_frame_ids):
        for t_id, data in self.unique_faces.items():
            widget = data.get('widget')
            if widget:
                if t_id in active_frame_ids:
                    widget.configure(border_color="#e54e38", border_width=1)
                else:
                    widget.configure(border_color="#2f333e", border_width=1)

    def show_frame(self, frame_idx: int):
        if not self.raw_frames or frame_idx >= len(self.raw_frames):
            return

        self.current_frame_idx = frame_idx
        faces_in_current_frame = self.detected_boxes_cache.get(frame_idx, [])
        frame_active_ids = {f['id'] for f in faces_in_current_frame}

        self.update_gallery_highlighting(frame_active_ids)
        active_blur_ids = self.get_active_blur_ids()

        if self.detected_boxes_cache and frame_idx in self.detected_boxes_cache:
            frame_bgr = self.blurrer.apply_blur_and_labels(self.raw_frames[frame_idx], faces_in_current_frame, active_blur_ids)
        elif self.blurred_frames_cache and frame_idx < len(self.blurred_frames_cache):
            frame_bgr = self.blurred_frames_cache[frame_idx]
        else:
            frame_bgr = self.raw_frames[frame_idx]

        frame_rgb = frame_bgr[:, :, ::-1]
        self.current_pil_img = Image.fromarray(frame_rgb)
        self.render_canvas_image()

        curr_sec = int(frame_idx / self.reader.fps)
        total_sec = int(len(self.raw_frames) / self.reader.fps)
        self.time_label.configure(
            text=f"{curr_sec // 60:02d}:{curr_sec % 60:02d} / {total_sec // 60:02d}:{total_sec % 60:02d}"
        )

    def on_slider_seek(self, value):
        self.is_playing = False
        self.btn_play.configure(text="▶ Play")
        idx = int(value)
        self.show_frame(idx)

    def toggle_play(self):
        if not self.raw_frames:
            return
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.configure(text="⏸ Pause")
            self.play_loop()
        else:
            self.btn_play.configure(text="▶ Play")

    def play_loop(self):
        if not self.is_playing:
            return
        
        if self.current_frame_idx < len(self.raw_frames) - 1:
            self.current_frame_idx += 1
            self.slider.set(self.current_frame_idx)
            self.show_frame(self.current_frame_idx)
            delay = int(1000 / self.reader.fps)
            self.after(delay, self.play_loop)
        else:
            self.is_playing = False
            self.btn_play.configure(text="▶ Play")