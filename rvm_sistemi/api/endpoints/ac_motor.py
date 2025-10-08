"""
AC Motor Kontrol API Endpoint'leri
GA500 Modbus motor kontrolü için endpoint'ler
"""

from fastapi import APIRouter, HTTPException
from ..modeller.schemas import SuccessResponse, ErrorResponse
from ...makine.modbus.modbus_kontrol import MotorKontrol
from ...utils.logger import log_motor, log_error, log_success, log_warning
import asyncio

router = APIRouter(prefix="/ac-motor", tags=["AC Motor"])

# AC Motor kontrol referansı
ac_motor_kontrol = None

def get_ac_motor_kontrol():
    """AC Motor kontrol referansını al"""
    try:
        from ...makine import kart_referanslari
        return kart_referanslari.ac_motor_kontrol_al()
    except Exception as e:
        print(f"AC Motor kontrol alınamadı: {e}")
        log_error(f"AC Motor kontrol alınamadı: {e}")
        return None

@router.post("/ezici-ileri")
async def ezici_ileri():
    """Ezici motoru ileri çalıştırır"""
    try:
        kontrol = get_ac_motor_kontrol()
        if not kontrol:
            raise HTTPException(status_code=500, detail="AC Motor kontrol bağlantısı yok")
        
        result = kontrol.ezici_ileri()
        if result:
            return SuccessResponse(message="Ezici motor ileri çalıştırıldı")
        else:
            raise HTTPException(status_code=500, detail="Ezici motor başlatılamadı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ezici ileri hatası: {str(e)}")

@router.post("/ezici-geri")
async def ezici_geri():
    """Ezici motoru geri çalıştırır"""
    try:
        kontrol = get_ac_motor_kontrol()
        if not kontrol:
            raise HTTPException(status_code=500, detail="AC Motor kontrol bağlantısı yok")
        
        result = kontrol.ezici_geri()
        if result:
            return SuccessResponse(message="Ezici motor geri çalıştırıldı")
        else:
            raise HTTPException(status_code=500, detail="Ezici motor başlatılamadı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ezici geri hatası: {str(e)}")

@router.post("/ezici-dur")
async def ezici_dur():
    """Ezici motoru durdurur"""
    try:
        kontrol = get_ac_motor_kontrol()
        if not kontrol:
            raise HTTPException(status_code=500, detail="AC Motor kontrol bağlantısı yok")
        
        result = kontrol.ezici_dur()
        if result:
            return SuccessResponse(message="Ezici motor durduruldu")
        else:
            raise HTTPException(status_code=500, detail="Ezici motor durdurulamadı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ezici dur hatası: {str(e)}")

@router.post("/kirici-ileri")
async def kirici_ileri():
    """Kırıcı motoru ileri çalıştırır"""
    try:
        kontrol = get_ac_motor_kontrol()
        if not kontrol:
            raise HTTPException(status_code=500, detail="AC Motor kontrol bağlantısı yok")
        
        result = kontrol.kirici_ileri()
        if result:
            return SuccessResponse(message="Kırıcı motor ileri çalıştırıldı")
        else:
            raise HTTPException(status_code=500, detail="Kırıcı motor başlatılamadı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kırıcı ileri hatası: {str(e)}")

@router.post("/kirici-geri")
async def kirici_geri():
    """Kırıcı motoru geri çalıştırır"""
    try:
        kontrol = get_ac_motor_kontrol()
        if not kontrol:
            raise HTTPException(status_code=500, detail="AC Motor kontrol bağlantısı yok")
        
        result = kontrol.kirici_geri()
        if result:
            return SuccessResponse(message="Kırıcı motor geri çalıştırıldı")
        else:
            raise HTTPException(status_code=500, detail="Kırıcı motor başlatılamadı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kırıcı geri hatası: {str(e)}")

@router.post("/kirici-dur")
async def kirici_dur():
    """Kırıcı motoru durdurur"""
    try:
        kontrol = get_ac_motor_kontrol()
        if not kontrol:
            raise HTTPException(status_code=500, detail="AC Motor kontrol bağlantısı yok")
        
        result = kontrol.kirici_dur()
        if result:
            return SuccessResponse(message="Kırıcı motor durduruldu")
        else:
            raise HTTPException(status_code=500, detail="Kırıcı motor durdurulamadı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kırıcı dur hatası: {str(e)}")

@router.post("/tum-motorlar-dur")
async def tum_motorlar_dur():
    """Tüm AC motorları durdurur"""
    try:
        kontrol = get_ac_motor_kontrol()
        if not kontrol:
            raise HTTPException(status_code=500, detail="AC Motor kontrol bağlantısı yok")
        
        result = kontrol.tum_motorlar_dur()
        if result:
            return SuccessResponse(message="Tüm AC motorlar durduruldu")
        else:
            raise HTTPException(status_code=500, detail="AC motorlar durdurulamadı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tüm motorlar dur hatası: {str(e)}")

@router.get("/durum")
async def ac_motor_durum():
    """AC Motor durumlarını döndürür"""
    try:
        kontrol = get_ac_motor_kontrol()
        if not kontrol:
            return {
                "status": "error",
                "message": "AC Motor kontrol bağlantısı yok",
                "data": None
            }
        
        # Motor durumlarını al
        durum_raporu = kontrol.durum_raporu()
        
        return {
            "status": "success",
            "data": durum_raporu
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"AC Motor durum hatası: {str(e)}",
            "data": None
        }
