import cv2
from ultralytics import YOLO

class FaceDetector:
    def __init__(self, model_path="yolov8s-face.pt"):
        # Инициализация скачанной модели YOLOv8s-face
        self.model = YOLO(model_path)

    def track_faces(self, frame):
        results = self.model.track(
            frame, 
            persist=True, 
            tracker="botsort.yaml",
            verbose=False,
            conf=0.3
        )
        
        current_faces = []

        if results and results[0].boxes and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()

            for box, t_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = map(int, box)
                current_faces.append({'id': t_id, 'bbox': (x1, y1, x2, y2)})

        return current_faces