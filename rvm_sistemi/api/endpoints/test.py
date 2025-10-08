"""
Test Senaryoları API Endpoint'leri
Motor test senaryoları için endpoint'ler
"""

from fastapi import APIRouter, HTTPException
from ..modeller.schemas import SuccessResponse, ErrorResponse
from ...makine.seri.motor_karti import MotorKart
from ...makine.seri.sensor_karti import SensorKart
from ...makine.modbus.modbus_kontrol import MotorKontrol
from ...utils.logger import log_motor, log_sensor, log_error, log_success, log_warning
import asyncio
import time

router = APIRouter(prefix="/test", tags=["Test"])

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

def get_ac_motor_kontrol():
    """AC Motor kontrol referansını al"""
    try:
        from ...makine import kart_referanslari
        return kart_referanslari.ac_motor_kontrol_al()
    except Exception as e:
        print(f"AC Motor kontrol alınamadı: {e}")
        return None

@router.post("/plastik-senaryo")
async def plastik_senaryo():
    """Plastik test senaryosunu çalıştırır"""
    try:
        motor = get_motor_kart()
        sensor = get_sensor_kart()
        ac_kontrol = get_ac_motor_kontrol()
        
        if not motor or not sensor:
            raise HTTPException(status_code=500, detail="Motor veya sensör kartı bağlantısı yok")
        
        # Plastik senaryosu
        # 1. Konveyör ileri
        motor.konveyor_ileri()
        await asyncio.sleep(3)
        motor.konveyor_dur()
        
        # 2. Yönlendirici plastik konumuna
        motor.yonlendirici_plastik()
        await asyncio.sleep(2)
        
        # 3. Klape plastik konumuna
        motor.klape_plastik()
        await asyncio.sleep(1)
        
        # 4. Ezici motor çalıştır
        if ac_kontrol:
            ac_kontrol.ezici_ileri()
            await asyncio.sleep(3)
            ac_kontrol.ezici_dur()
        
        # 5. Konumları sıfırla
        motor.yonlendirici_plastik()
        motor.klape_plastik()
        
        return SuccessResponse(message="Plastik test senaryosu tamamlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plastik senaryo hatası: {str(e)}")

@router.post("/metal-senaryo")
async def metal_senaryo():
    """Metal test senaryosunu çalıştırır"""
    try:
        motor = get_motor_kart()
        sensor = get_sensor_kart()
        ac_kontrol = get_ac_motor_kontrol()
        
        if not motor or not sensor:
            raise HTTPException(status_code=500, detail="Motor veya sensör kartı bağlantısı yok")
        
        # Metal senaryosu
        # 1. Konveyör ileri
        motor.konveyor_ileri()
        await asyncio.sleep(3)
        motor.konveyor_dur()
        
        # 2. Yönlendirici plastik konumuna (metal de plastik haznesine gider)
        motor.yonlendirici_plastik()
        await asyncio.sleep(2)
        
        # 3. Klape metal konumuna
        motor.klape_metal()
        await asyncio.sleep(1)
        
        # 4. Ezici motor çalıştır
        if ac_kontrol:
            ac_kontrol.ezici_ileri()
            await asyncio.sleep(3)
            ac_kontrol.ezici_dur()
        
        # 5. Konumları sıfırla
        motor.yonlendirici_plastik()
        motor.klape_plastik()
        
        return SuccessResponse(message="Metal test senaryosu tamamlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metal senaryo hatası: {str(e)}")

@router.post("/cam-senaryo")
async def cam_senaryo():
    """Cam test senaryosunu çalıştırır"""
    try:
        motor = get_motor_kart()
        sensor = get_sensor_kart()
        ac_kontrol = get_ac_motor_kontrol()
        
        if not motor or not sensor:
            raise HTTPException(status_code=500, detail="Motor veya sensör kartı bağlantısı yok")
        
        # Cam senaryosu
        # 1. Konveyör ileri
        motor.konveyor_ileri()
        await asyncio.sleep(3)
        motor.konveyor_dur()
        
        # 2. Yönlendirici cam konumuna
        motor.yonlendirici_cam()
        await asyncio.sleep(2)
        
        # 3. Klape plastik konumuna (cam için)
        motor.klape_plastik()
        await asyncio.sleep(1)
        
        # 4. Kırıcı motor çalıştır
        if ac_kontrol:
            ac_kontrol.kirici_ileri()
            await asyncio.sleep(3)
            ac_kontrol.kirici_dur()
        
        # 5. Konumları sıfırla
        motor.yonlendirici_plastik()
        motor.klape_plastik()
        
        return SuccessResponse(message="Cam test senaryosu tamamlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cam senaryo hatası: {str(e)}")

@router.post("/durum")
async def test_durum():
    """Test durumunu döndürür"""
    try:
        motor = get_motor_kart()
        sensor = get_sensor_kart()
        ac_kontrol = get_ac_motor_kontrol()
        
        return {
            "status": "success",
            "motor_bagli": motor is not None,
            "sensor_bagli": sensor is not None,
            "ac_motor_bagli": ac_kontrol is not None,
            "test_hazir": motor is not None and sensor is not None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Test durum hatası: {str(e)}",
            "motor_bagli": False,
            "sensor_bagli": False,
            "ac_motor_bagli": False,
            "test_hazir": False
        }
