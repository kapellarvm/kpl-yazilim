"""
Hazne Doluluk API Endpoint'leri
Hazne doluluk sensörleri için endpoint'ler
"""

from fastapi import APIRouter, HTTPException
from ..modeller.schemas import SuccessResponse, ErrorResponse
from ...makine.seri.sensor_karti import SensorKart
from ...utils.logger import log_sensor, log_error, log_success, log_warning
import asyncio

router = APIRouter(prefix="/hazne", tags=["Hazne"])

def get_sensor_kart():
    """Sensör kartı referansını al"""
    try:
        from ...makine import kart_referanslari
        return kart_referanslari.sensor_al()
    except Exception as e:
        print(f"Sensör kartı alınamadı: {e}")
        log_error(f"Sensör kartı alınamadı: {e}")
        return None

@router.get("/doluluk")
async def hazne_doluluk():
    """Tüm hazne doluluk oranlarını döndürür"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            return {
                "status": "error",
                "message": "Sensör kartı bağlantısı yok",
                "data": {
                    "plastik": 0,
                    "metal": 0,
                    "cam": 0
                }
            }
        
        # Bakım durumundan doluluk verilerini al
        from ...makine.senaryolar.bakim import bakim_durumu
        
        return {
            "status": "success",
            "data": {
                "plastik": bakim_durumu.doluluk_plastik,
                "metal": bakim_durumu.doluluk_metal,
                "cam": bakim_durumu.doluluk_cam
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Hazne doluluk hatası: {str(e)}",
            "data": {
                "plastik": 0,
                "metal": 0,
                "cam": 0
            }
        }

@router.get("/plastik")
async def plastik_doluluk():
    """Plastik hazne doluluk oranını döndürür"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            return {"status": "error", "message": "Sensör kartı bağlantısı yok", "doluluk": 0}
        
        # Bakım durumundan plastik doluluk verisini al
        from ...makine.senaryolar.bakim import bakim_durumu
        
        return {
            "status": "success",
            "doluluk": bakim_durumu.doluluk_plastik
        }
    except Exception as e:
        return {"status": "error", "message": f"Plastik hazne hatası: {str(e)}", "doluluk": 0}

@router.get("/metal")
async def metal_doluluk():
    """Metal hazne doluluk oranını döndürür"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            return {"status": "error", "message": "Sensör kartı bağlantısı yok", "doluluk": 0}
        
        # Bakım durumundan metal doluluk verisini al
        from ...makine.senaryolar.bakim import bakim_durumu
        
        return {
            "status": "success",
            "doluluk": bakim_durumu.doluluk_metal
        }
    except Exception as e:
        return {"status": "error", "message": f"Metal hazne hatası: {str(e)}", "doluluk": 0}

@router.get("/cam")
async def cam_doluluk():
    """Cam hazne doluluk oranını döndürür"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            return {"status": "error", "message": "Sensör kartı bağlantısı yok", "doluluk": 0}
        
        # Bakım durumundan cam doluluk verisini al
        from ...makine.senaryolar.bakim import bakim_durumu
        
        return {
            "status": "success",
            "doluluk": bakim_durumu.doluluk_cam
        }
    except Exception as e:
        return {"status": "error", "message": f"Cam hazne hatası: {str(e)}", "doluluk": 0}
