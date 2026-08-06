import math
import subprocess
import json
import cv2
import numpy as np

class FFmpegVideoReader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.cap = cv2.VideoCapture(file_path)
        
        if not self.cap.isOpened():
            raise ValueError(f"Не удалось открыть видеофайл: {file_path}")

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Вычисляем соотношение сторон (Aspect Ratio)
        gcd = math.gcd(self.width, self.height)
        if gcd > 0:
            self.aspect_ratio = f"{self.width // gcd}:{self.height // gcd}"
        else:
            self.aspect_ratio = "16:9"

        # Получаем данные о кодеке и битрейте через ffprobe
        self.codec = "Unknown"
        self.bitrate_str = "N/A"
        self._extract_extended_info()

    def _extract_extended_info(self):
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format", self.file_path
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            data = json.loads(result.stdout)
            
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    self.codec = stream.get("codec_name", "h264").upper()
                    break

            bitrate = data.get("format", {}).get("bit_rate")
            if bitrate:
                mbps = float(bitrate) / 1_000_000
                self.bitrate_str = f"{mbps:.1f} Mbps"
        except Exception:
            pass

    def read_frames(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            yield frame

    def close(self):
        if self.cap:
            self.cap.release()