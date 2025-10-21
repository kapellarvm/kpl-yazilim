"""
Uyku Modu API Endpoints
Makine uyku modu durumu ve kontrolü için API endpoint'leri
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from ..servisler.uyku_modu_servisi import uyku_modu_servisi
from ...utils.logger import log_system, log_success, log_warning
from ...utils.terminal import ok, warn, info

router = APIRouter(prefix="/api/v1/uyku", tags=["Uyku Modu"])


class UykuDurumuResponse(BaseModel):
    """Uyku modu durumu yanıt modeli"""
    uyku_modu_aktif: bool
    son_aktivite: str
    uyku_suresi_dakika: int
    uyku_modu_sayisi: int
    toplam_uyku_suresi_saat: float
    enerji_tasarrufu_kwh: float
    kalan_sure_dakika: int


class UykuIstatistikleriResponse(BaseModel):
    """Uyku modu istatistikleri yanıt modeli"""
    toplam_uyku_modu: int
    toplam_uyku_suresi_saat: float
    toplam_enerji_tasarrufu_kwh: float
    ortalama_uyku_suresi_dakika: float
    enerji_tasarrufu_yuzde: float


class UykuAyarlariRequest(BaseModel):
    """Uyku ayarları güncelleme modeli"""
    uyku_suresi_dakika: int


@router.get("/durum", response_model=UykuDurumuResponse)
async def uyku_durumu_al():
    """Uyku modu durumunu al"""
    try:
        durum = uyku_modu_servisi.uyku_durumu_al()
        log_system("Uyku modu durumu sorgulandı")
        return UykuDurumuResponse(**durum)
    except Exception as e:
        log_warning(f"Uyku durumu alma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Uyku durumu alınamadı: {str(e)}")


@router.get("/istatistikler", response_model=UykuIstatistikleriResponse)
async def uyku_istatistikleri_al():
    """Uyku modu istatistiklerini al"""
    try:
        istatistikler = uyku_modu_servisi.uyku_istatistikleri_al()
        log_system("Uyku modu istatistikleri sorgulandı")
        return UykuIstatistikleriResponse(**istatistikler)
    except Exception as e:
        log_warning(f"Uyku istatistikleri alma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Uyku istatistikleri alınamadı: {str(e)}")


@router.post("/ayarlar")
async def uyku_ayarlari_guncelle(request: UykuAyarlariRequest):
    """Uyku modu ayarlarını güncelle"""
    try:
        if request.uyku_suresi_dakika < 5 or request.uyku_suresi_dakika > 60:
            raise HTTPException(
                status_code=400, 
                detail="Uyku süresi 5-60 dakika arasında olmalıdır"
            )
        
        uyku_modu_servisi.uyku_ayarlari_guncelle(request.uyku_suresi_dakika)
        
        ok("UYKU", f"Uyku süresi {request.uyku_suresi_dakika} dakikaya güncellendi")
        log_success(f"Uyku modu ayarları güncellendi: {request.uyku_suresi_dakika} dakika")
        
        return {"status": "success", "message": f"Uyku süresi {request.uyku_suresi_dakika} dakikaya güncellendi"}
    except HTTPException:
        raise
    except Exception as e:
        log_warning(f"Uyku ayarları güncelleme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Uyku ayarları güncellenemedi: {str(e)}")


@router.post("/aktivite")
async def aktivite_kaydet():
    """Manuel aktivite kaydetme (uyku modundan çıkış için)"""
    try:
        uyku_modu_servisi.aktivite_kaydet()
        
        info("UYKU", "Manuel aktivite kaydedildi")
        log_system("Manuel aktivite kaydedildi - uyku modu sıfırlandı")
        
        return {"status": "success", "message": "Aktivite kaydedildi"}
    except Exception as e:
        log_warning(f"Aktivite kaydetme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Aktivite kaydedilemedi: {str(e)}")


@router.post("/zorla-uyku")
async def zorla_uyku_modu():
    """Zorla uyku moduna geç (test/manuel kontrol için)"""
    try:
        if uyku_modu_servisi.uyku_modu_aktif:
            warn("UYKU", "Zaten uyku modunda")
            return {"status": "warning", "message": "Zaten uyku modunda"}
        
        uyku_modu_servisi.uyku_moduna_gir()
        
        ok("UYKU", "Zorla uyku modu aktifleştirildi")
        log_success("Zorla uyku modu aktifleştirildi")
        
        return {"status": "success", "message": "Uyku modu aktifleştirildi"}
    except Exception as e:
        log_warning(f"Zorla uyku modu hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Uyku modu aktifleştirilemedi: {str(e)}")


@router.post("/uyku-cik")
async def uyku_modundan_cik():
    """Zorla uyku modundan çık (test/manuel kontrol için)"""
    try:
        if not uyku_modu_servisi.uyku_modu_aktif:
            warn("UYKU", "Zaten uyku modunda değil")
            return {"status": "warning", "message": "Zaten uyku modunda değil"}
        
        uyku_modu_servisi.uyku_modundan_cik()
        
        ok("UYKU", "Zorla uyku modundan çıkıldı")
        log_success("Zorla uyku modundan çıkıldı")
        
        return {"status": "success", "message": "Uyku modundan çıkıldı"}
    except Exception as e:
        log_warning(f"Uyku modundan çıkma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Uyku modundan çıkılamadı: {str(e)}")


@router.get("/test")
async def uyku_test():
    """Uyku modu test endpoint'i"""
    try:
        durum = uyku_modu_servisi.uyku_durumu_al()
        istatistikler = uyku_modu_servisi.uyku_istatistikleri_al()
        
        test_sonucu = {
            "durum": durum,
            "istatistikler": istatistikler,
            "test_zamani": uyku_modu_servisi.son_aktivite_zamani.strftime('%Y-%m-%d %H:%M:%S'),
            "thread_aktif": uyku_modu_servisi.uyku_thread_aktif,
            "sistem_referans": uyku_modu_servisi.sistem_referans is not None
        }
        
        info("UYKU", "Uyku modu test endpoint'i çağrıldı")
        log_system("Uyku modu test endpoint'i çağrıldı")
        
        return {"status": "success", "data": test_sonucu}
    except Exception as e:
        log_warning(f"Uyku test hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Uyku test başarısız: {str(e)}")
