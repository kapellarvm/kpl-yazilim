import time
import cv2
import os
import platform
from ultralytics import YOLO

# Mac'te kamera servisini kullanma
if platform.system() != "Darwin":  # Darwin = macOS
    from .Kamera_Servis import KameraServis  # Düz isim: Kamera_Servis.py

class YOLOProcessor:
    def __init__(self):
        self.device = "cpu"
        model_path = os.path.join(os.path.dirname(__file__), "b_s_y.pt")
        self.model = YOLO(model_path)
        
        # Mac'te kamera servisini başlatma
        if platform.system() != "Darwin":
            self.kamera = KameraServis()
            self.kamera.baslat()   # 📌 Otomatik başlat
        else:
            self.kamera = None

        self.x_olcek = 0.5510
        self.y_olcek = 0.5110

    def capture_and_process(self):
        # Mac'te mock data döndür
        if platform.system() == "Darwin":
            return self._get_mock_data()
        
        # Normal kamera işlemi
        frame = self.kamera.fotograf_cek()
        if frame is None:
            return {"error": "Fotoğraf alınamadı!"}

        start_time = time.time()
        results = self.model.predict(
            source=frame,
            device=self.device,
            save=False,
            conf=0.75,
            iou=0.5,
            verbose=False,
            stream=False
        )
        end_time = time.time()
        process_time = (end_time - start_time) * 1000

        detected_objects = []

        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy().astype(int)
            classes = result.boxes.cls.cpu().numpy().astype(int)
            confidences = result.boxes.conf.cpu().numpy()

            for box, cls_id, conf in zip(boxes, classes, confidences):
                x1, y1, x2, y2 = box
                label = self.model.names[cls_id]

                width_real = (x2 - x1) * self.x_olcek
                height_real = (y2 - y1) * self.y_olcek

                detected_objects.append({
                    "type": label,
                    "confidence": round(conf, 3),
                    "width_mm": round(width_real, 2),
                    "height_mm": round(height_real, 2)
                })

        if not detected_objects:
            return {
                "success": True,
                "process_time_ms": round(process_time, 2),
                "message": "nesne yok"
            }

        return {
            "success": True,
            "process_time_ms": round(process_time, 2),
            "detected_objects": detected_objects
        }

    def _get_mock_data(self):
        """Mac için mock data döndürür"""
        import random
        
        # Rastgele nesne tespit etme simülasyonu
        if random.random() < 0.3:  # %30 ihtimalle nesne tespit et
            object_types = ["bottle", "glass", "can", "plastic"]
            detected_object = {
                "type": random.choice(object_types),
                "confidence": round(random.uniform(0.75, 0.95), 3),
                "width_mm": round(random.uniform(50, 150), 2),
                "height_mm": round(random.uniform(80, 200), 2)
            }
            
            return {
                "success": True,
                "process_time_ms": round(random.uniform(100, 300), 2),
                "detected_objects": [detected_object]
            }
        else:
            return {
                "success": True,
                "process_time_ms": round(random.uniform(50, 150), 2),
                "message": "nesne yok"
            }

