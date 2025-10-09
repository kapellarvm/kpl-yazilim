"""
Sensör Kontrol API Endpoint'leri
Sensör kontrolü ve ölçüm endpoint'leri
"""

from fastapi import APIRouter, HTTPException
from ..modeller.schemas import SuccessResponse, ErrorResponse
from ...makine.seri.sensor_karti import SensorKart
from ...makine.durum_degistirici import durum_makinesi
from ...utils.logger import log_sensor, log_error, log_success, log_warning
import asyncio

router = APIRouter(prefix="/sensor", tags=["Sensör"])

# Sensör kartı referansı (ana.py'dan alınacak)
sensor_kart = None

def get_sensor_kart():
    """Sensör kartı referansını al"""
    try:
        # Ana.py'dan oluşturulan sensör kartını al
        from ...makine import kart_referanslari
        return kart_referanslari.sensor_al()
    except Exception as e:
        print(f"Sensör kartı alınamadı: {e}")
        log_error(f"Sensör kartı alınamadı: {e}")
        return None

@router.post("/teach")
async def sensor_teach():
    """Gyro sensör teach işlemini başlatır"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # Gyro sensör teach işlemi
        sensor.gyro_teach()
        return SuccessResponse(message="Gyro sensör teach tamamlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Teach hatası: {str(e)}")

@router.post("/agirlik-olc")
async def agirlik_olc():
    """Ağırlık ölçümü yapar - Yeni sistem: 'lo' komutu gönderir"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # Yeni sistem: 'lo' komutu gönder, ağırlık callback ile gelecek
        result = sensor.agirlik_olc()
        if result:
            return {
                "status": "success",
                "message": "Ağırlık ölçüm komutu gönderildi, sonuç callback ile gelecek"
            }
        else:
            raise HTTPException(status_code=500, detail="Ağırlık ölçüm komutu gönderilemedi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ağırlık ölçüm hatası: {str(e)}")

@router.post("/tare")
async def sensor_tare():
    """Loadcell tare işlemini yapar"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # Tare işlemi
        #sensor.tare()
        return SuccessResponse(message="Loadcell tare tamamlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tare hatası: {str(e)}")

@router.post("/led-ac")
async def led_ac():
    """LED'i açar"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # LED'i aç
        sensor.led_ac()
        return SuccessResponse(message="LED açıldı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LED açma hatası: {str(e)}")

@router.post("/led-kapat")
async def led_kapat():
    """LED'i kapatır"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # LED'i kapat
        sensor.led_kapat()
        return SuccessResponse(message="LED kapatıldı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LED kapatma hatası: {str(e)}")

@router.get("/son-deger")
async def sensor_son_deger():
    """Son sensör değerlerini döndürür"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            return {
                "status": "error",
                "message": "Sensör kartı bağlantısı yok",
                "data": None
            }
        
        # Son değerleri al
        agirlik = sensor.son_agirlik_degeri()
        mesaj = sensor.son_mesaj()
        
        return {
            "status": "success",
            "data": {
                "agirlik": agirlik,
                "mesaj": mesaj
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Sensör değer alma hatası: {str(e)}",
            "data": None
        }

@router.get("/durum")
async def sensor_durum():
    """Sensör durumunu döndürür"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            return {"status": "error", "message": "Sensör kartı bağlantısı yok", "bagli": False}
        
        return {
            "status": "success",
            "bagli": True,
            "mesaj": "Sensör kartı bağlı"
        }
    except Exception as e:
        return {"status": "error", "message": f"Sensör durum hatası: {str(e)}", "bagli": False}
