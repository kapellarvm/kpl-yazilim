import threading
import platform


SLAVE_ID = 1
TARGET_SERIAL = "B0046HHJA"
# TODO: bu locklar asyncio lock olacak.
modbus_lock = threading.Lock()

class ImageProcessingService:
    def __init__(self):
        # Mac'te YOLO modelini yükleme
        if platform.system() != "Darwin":
            from app.services.image_processing_service.image import YOLOProcessor
            self.processor = YOLOProcessor()
        else:
            self.processor = None
            
        # YOLO model type'larını BinType enum'larına çeviren mapping
        self.type_mapping = {
            # PET türleri
            "bottle": PackageType.PET,
            "pet": PackageType.PET,
            "pet_bottle": PackageType.PET,
            "plastic_bottle": PackageType.PET,
            "plastik": PackageType.PET,  # Türkçe plastik
            "plastic": PackageType.PET,  # İngilizce plastic
            
            # Cam türleri
            "glass": PackageType.GLASS,
            "glass_bottle": PackageType.GLASS,
            "cam": PackageType.GLASS,  # Türkçe cam
            
            # Alüminyum türleri  
            "can": PackageType.ALUMINUM,
            "aluminum": PackageType.ALUMINUM,
            "aluminum_can": PackageType.ALUMINUM,
            "metal_can": PackageType.ALUMINUM,
            "alüminyum": PackageType.ALUMINUM,  # Türkçe alüminyum
            "metal": PackageType.ALUMINUM,
        }
    
    def _map_yolo_type_to_bin_type(self, yolo_type: str) -> PackageType:
        """YOLO type'ını PackageType enum değerine çevirir"""
        # Küçük harfe çevir ve mapping'de ara
        yolo_type_lower = yolo_type.lower()
        bin_type = self.type_mapping.get(yolo_type_lower)
        
        if bin_type:
            return bin_type  # "1", "2", veya "3" döndürür
        else:
            # Eğer mapping'de yoksa, varsayılan olarak "0" (UNKNOWN) döndür
            app_logger.warning(f"Uyarı: Bilinmeyen YOLO type: {yolo_type}")
            return PackageType.UNKNOWN

    def capture_and_process(self):
        # Mac'te mock data kullan
        if platform.system() == "Darwin":
            return self._get_mock_result()
            
        result = self.processor.capture_and_process()
        if "error" in result:
            app_logger.error(f"HATA: {result['error']}")
        else:
            app_logger.info(f"YOLO işlem süresi: {result['process_time_ms']} ms")
            
            if "message" in result and result["message"] == "nesne yok":
                app_logger.info("Nesne yok")
                return ImageProcessingResult(
                    width_mm=0,
                    height_mm=0,
                    type=PackageType.UNKNOWN,
                    confidence=0,
                    message="nesne yok"
                )
            elif result['detected_objects']:
                app_logger.info("Tespit edilen nesneler:")
                for j, obj in enumerate(result['detected_objects'], 1):
                    # YOLO type'ını BinType'a çevir
                    mapped_type = self._map_yolo_type_to_bin_type(obj['type'])
                    
                    app_logger.info(f"  {j}. Tür: {obj['type']} -> {mapped_type} | "
                            f"Güven: {obj['confidence']} | "
                            f"Yükseklik(mm): {obj['width_mm']} | "
                            f"Genişlik(mm): {obj['height_mm']}")
                    return ImageProcessingResult(
                        width_mm=obj['height_mm'],
                        height_mm=obj['width_mm'],
                        type=mapped_type,  # String'i integer'a çevir
                        confidence=obj['confidence'],
                        message="nesne var"
                    )
            else:
                app_logger.info("Hiç nesne tespit edilmedi.")

    def _get_mock_result(self):
        """Mac için mock sonuç döndürür"""
        import random
        
        app_logger.info("Mac ortamında mock image processing kullanılıyor")
        
        # Rastgele nesne tespit etme simülasyonu
        if random.random() < 0.3:  # %30 ihtimalle nesne tespit et
            object_types = ["bottle", "glass", "can", "plastic"]
            detected_type = random.choice(object_types)
            mapped_type = self._map_yolo_type_to_bin_type(detected_type)
            
            app_logger.info(f"Mock tespit: {detected_type} -> {mapped_type}")
            
            return ImageProcessingResult(
                width_mm=round(random.uniform(80, 200), 2),
                height_mm=round(random.uniform(50, 150), 2),
                type=mapped_type,
                confidence=round(random.uniform(0.75, 0.95), 3),
                message="nesne var"
            )
        else:
            app_logger.info("Mock: Nesne yok")
            return ImageProcessingResult(
                width_mm=0,
                height_mm=0,
                type=PackageType.UNKNOWN,
                confidence=0,
                message="nesne yok"
            )