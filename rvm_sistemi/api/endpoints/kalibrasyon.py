"""
Kalibrasyon API Endpoint'leri
Motor ve sensör kalibrasyonu için endpoint'ler
"""

from fastapi import APIRouter, HTTPException
from ..modeller.schemas import SuccessResponse, ErrorResponse
from ...makine.seri.motor_karti import MotorKart
from ...makine.seri.sensor_karti import SensorKart
from ...utils.logger import log_motor, log_sensor, log_error, log_success, log_warning
import asyncio
import time

router = APIRouter(prefix="/kalibrasyon", tags=["Kalibrasyon"])

def get_motor_kart():
    """Motor kartı referansını al"""
    try:
        from ...makine import kart_referanslari
        return kart_referanslari.motor_al()
    except Exception as e:
        print(f"Motor kartı alınamadı: {e}")
        return None

def get_sensor_kart():
    """Sensör kartı referansını al"""
    try:
        from ...makine import kart_referanslari
        return kart_referanslari.sensor_al()
    except Exception as e:
        print(f"Sensör kartı alınamadı: {e}")
        return None

@router.post("/yonlendirici")
async def yonlendirici_kalibrasyon():
    """Yönlendirici motor kalibrasyonu yapar"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        # Yönlendirici motor kalibrasyonu
        # Gerçek implementasyonda motor kartından kalibrasyon komutu gönderilecek
        motor.yonlendirici_plastik()  # Plastik konumuna git
        await asyncio.sleep(2)  # 2 saniye bekle
        motor.yonlendirici_cam()      # Cam konumuna git
        await asyncio.sleep(2)  # 2 saniye bekle
        motor.yonlendirici_plastik()  # Tekrar plastik konumuna dön
        
        return SuccessResponse(message="Yönlendirici motor kalibrasyonu tamamlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Yönlendirici kalibrasyon hatası: {str(e)}")

@router.post("/klape")
async def klape_kalibrasyon():
    """Klape motor kalibrasyonu yapar"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        # Klape motor kalibrasyonu
        # Gerçek implementasyonda motor kartından kalibrasyon komutu gönderilecek
        motor.klape_plastik()  # Plastik konumuna git
        await asyncio.sleep(1)  # 1 saniye bekle
        motor.klape_metal()    # Metal konumuna git
        await asyncio.sleep(1)  # 1 saniye bekle
        motor.klape_plastik()  # Tekrar plastik konumuna dön
        
        return SuccessResponse(message="Klape motor kalibrasyonu tamamlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Klape kalibrasyon hatası: {str(e)}")

@router.post("/yonlendirici-sensor")
async def yonlendirici_sensor_kalibrasyon():
    """Yönlendirici sensör kalibrasyonu yapar"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # Yönlendirici sensör kalibrasyonu
        # Gerçek implementasyonda sensör kartından teach komutu gönderilecek
        sensor.teach()  # Gyro sensör teach işlemi
        
        return SuccessResponse(message="Yönlendirici sensör kalibrasyonu tamamlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Yönlendirici sensör kalibrasyon hatası: {str(e)}")

@router.post("/tum")
async def tum_kalibrasyon():
    """Tüm sistem kalibrasyonu yapar"""
    try:
        motor = get_motor_kart()
        sensor = get_sensor_kart()
        
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # Tüm kalibrasyonları sırayla yap
        # Yönlendirici motor
        motor.yonlendirici_plastik()
        await asyncio.sleep(1)
        motor.yonlendirici_cam()
        await asyncio.sleep(1)
        motor.yonlendirici_plastik()
        
        # Klape motor
        motor.klape_plastik()
        await asyncio.sleep(0.5)
        motor.klape_metal()
        await asyncio.sleep(0.5)
        motor.klape_plastik()
        
        # Sensör teach
        sensor.teach()
        
        return SuccessResponse(message="Tüm sistem kalibrasyonu tamamlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tüm kalibrasyon hatası: {str(e)}")

@router.get("/durum")
async def kalibrasyon_durum():
    """Kalibrasyon durumunu döndürür"""
    try:
        motor = get_motor_kart()
        sensor = get_sensor_kart()
        
        motor_bagli = motor is not None
        sensor_bagli = sensor is not None
        
        return {
            "status": "success",
            "motor_bagli": motor_bagli,
            "sensor_bagli": sensor_bagli,
            "kalibrasyon_hazir": motor_bagli and sensor_bagli
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Kalibrasyon durum hatası: {str(e)}",
            "motor_bagli": False,
            "sensor_bagli": False,
            "kalibrasyon_hazir": False
        }
