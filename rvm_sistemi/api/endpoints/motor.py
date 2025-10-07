"""
Motor Kontrol API Endpoint'leri
Motor kontrolü ve hız ayarlama endpoint'leri
"""

from fastapi import APIRouter, HTTPException
from ..modeller.schemas import MotorHizRequest, SuccessResponse, ErrorResponse
from ...makine.seri.motor_karti import MotorKart
from ...makine.durum_degistirici import durum_makinesi
from ...utils.logger import log_motor, log_error, log_success, log_warning
import asyncio

router = APIRouter(prefix="/motor", tags=["Motor"])

# Motor kartı referansı (ana.py'dan alınacak)
motor_kart = None

def get_motor_kart():
    """Motor kartı referansını al"""
    try:
        # Ana.py'dan oluşturulan motor kartını al
        from ...makine import kart_referanslari
        return kart_referanslari.motor_al()
    except Exception as e:
        print(f"Motor kartı alınamadı: {e}")
        log_error(f"Motor kartı alınamadı: {e}")
        return None

@router.post("/konveyor-ileri")
async def konveyor_ileri():
    """Konveyörü ileri yönde çalıştırır"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        # Konveyör motorunu ileri çalıştır
        motor.konveyor_ileri()
        return SuccessResponse(message="Konveyör ileri çalıştırıldı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Konveyör ileri hatası: {str(e)}")

@router.post("/konveyor-geri")
async def konveyor_geri():
    """Konveyörü geri yönde çalıştırır"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        motor.konveyor_geri()
        return SuccessResponse(message="Konveyör geri çalıştırıldı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Konveyör geri hatası: {str(e)}")

@router.post("/konveyor-dur")
async def konveyor_dur():
    """Konveyörü durdurur"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        motor.konveyor_dur()
        return SuccessResponse(message="Konveyör durduruldu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Konveyör durdurma hatası: {str(e)}")

@router.post("/yonlendirici-plastik")
async def yonlendirici_plastik():
    """Yönlendiriciyi plastik konumuna getirir"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        motor.yonlendirici_plastik()
        return SuccessResponse(message="Yönlendirici plastik konumuna getirildi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Yönlendirici plastik hatası: {str(e)}")

@router.post("/yonlendirici-cam")
async def yonlendirici_cam():
    """Yönlendiriciyi cam konumuna getirir"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        motor.yonlendirici_cam()
        return SuccessResponse(message="Yönlendirici cam konumuna getirildi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Yönlendirici cam hatası: {str(e)}")

@router.post("/klape-plastik")
async def klape_plastik():
    """Klapeyi plastik konumuna getirir"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        motor.klape_plastik()
        return SuccessResponse(message="Klape plastik konumuna getirildi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Klape plastik hatası: {str(e)}")

@router.post("/klape-metal")
async def klape_metal():
    """Klapeyi metal konumuna getirir"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        motor.klape_metal()
        return SuccessResponse(message="Klape metal konumuna getirildi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Klape metal hatası: {str(e)}")

@router.post("/motorlari-aktif")
async def motorlari_aktif():
    """Tüm motorları aktif eder"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        motor.motorlari_aktif_et()
        return SuccessResponse(message="Tüm motorlar aktif edildi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Motorları aktif etme hatası: {str(e)}")

@router.post("/motorlari-iptal")
async def motorlari_iptal():
    """Tüm motorları iptal eder"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        motor.motorlari_iptal_et()
        return SuccessResponse(message="Tüm motorlar iptal edildi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Motorları iptal etme hatası: {str(e)}")

@router.post("/hiz-ayarla")
async def motor_hiz_ayarla(request: MotorHizRequest):
    """Motor hızını ayarlar"""
    try:
        motor = get_motor_kart()
        if not motor:
            raise HTTPException(status_code=500, detail="Motor kartı bağlantısı yok")
        
        # Motor hızını ayarla
        motor.hiz_ayarla(request.motor, request.hiz)
        return SuccessResponse(message=f"{request.motor} motor hızı {request.hiz}% olarak ayarlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hız ayarlama hatası: {str(e)}")

@router.get("/durum")
async def motor_durum():
    """Motor durumunu döndürür"""
    try:
        motor = get_motor_kart()
        if not motor:
            return {"status": "error", "message": "Motor kartı bağlantısı yok", "bagli": False}
        
        return {
            "status": "success",
            "bagli": True,
            "mesaj": "Motor kartı bağlı"
        }
    except Exception as e:
        return {"status": "error", "message": f"Motor durum hatası: {str(e)}", "bagli": False}
