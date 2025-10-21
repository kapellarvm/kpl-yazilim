"""
Tolerans Ayarları API Endpoint'leri
Tolerans değerlerini yönetmek için endpoint'ler
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any
import json
import os

router = APIRouter(prefix="/tolerans", tags=["Tolerans"])

# Tolerans ayarları dosya yolu
TOLERANS_DOSYA_YOLU = "/home/sshuser/projects/kpl-yazilim/tolerans_ayarlari.json"

# Varsayılan tolerans sabitleri
VARSAYILAN_TOLERANSLAR = {
    "uzunluk_toleransi": 10,  # mm
    "genislik_toleransi": 10, # mm
    "metal_agirlik_toleransi": 5,  # gr
    "plastik_agirlik_toleransi": 5, # gr
    "cam_agirlik_toleransi": 10,  # gr
}

class ToleransAyarlari(BaseModel):
    """Tolerans ayarları modeli"""
    uzunluk_toleransi: int = Field(default=VARSAYILAN_TOLERANSLAR["uzunluk_toleransi"], ge=0, le=10000)
    genislik_toleransi: int = Field(default=VARSAYILAN_TOLERANSLAR["genislik_toleransi"], ge=0, le=10000)
    metal_agirlik_toleransi: int = Field(default=VARSAYILAN_TOLERANSLAR["metal_agirlik_toleransi"], ge=0, le=10000)
    plastik_agirlik_toleransi: int = Field(default=VARSAYILAN_TOLERANSLAR["plastik_agirlik_toleransi"], ge=0, le=10000)
    cam_agirlik_toleransi: int = Field(default=VARSAYILAN_TOLERANSLAR["cam_agirlik_toleransi"], ge=0, le=10000)

def tolerans_ayarlari_yukle() -> Dict[str, Any]:
    """Tolerans ayarlarını dosyadan yükle"""
    try:
        if os.path.exists(TOLERANS_DOSYA_YOLU):
            with open(TOLERANS_DOSYA_YOLU, 'r', encoding='utf-8') as f:
                ayarlar = json.load(f)
                # Sadece tanımlı sabitleri al, 0 değerini kabul et
                return {k: ayarlar[k] if k in ayarlar and ayarlar[k] is not None else VARSAYILAN_TOLERANSLAR[k] for k in VARSAYILAN_TOLERANSLAR}
        else:
            # Varsayılan ayarları döndür
            return VARSAYILAN_TOLERANSLAR.copy()
    except Exception as e:
        print(f"❌ Tolerans ayarları yükleme hatası: {e}")
        return VARSAYILAN_TOLERANSLAR.copy()

def tolerans_ayarlari_kaydet(ayarlar: Dict[str, Any]) -> bool:
    """Tolerans ayarlarını dosyaya kaydet"""
    try:
        # Dizin yoksa oluştur
        os.makedirs(os.path.dirname(TOLERANS_DOSYA_YOLU), exist_ok=True)
        
        # Sadece tanımlı sabitleri kaydet, 0 değerini kabul et
        kaydedilecek_ayarlar = {}
        for k in VARSAYILAN_TOLERANSLAR:
            if k in ayarlar and ayarlar[k] is not None:
                kaydedilecek_ayarlar[k] = ayarlar[k]
            else:
                kaydedilecek_ayarlar[k] = VARSAYILAN_TOLERANSLAR[k]
        
        with open(TOLERANS_DOSYA_YOLU, 'w', encoding='utf-8') as f:
            json.dump(kaydedilecek_ayarlar, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Tolerans ayarları kaydedildi: {kaydedilecek_ayarlar}")
        return True
    except Exception as e:
        print(f"❌ Tolerans ayarları kaydetme hatası: {e}")
        return False

@router.get("/ayarlar")
async def tolerans_ayarlari_al():
    """Mevcut tolerans ayarlarını getir"""
    try:
        ayarlar = tolerans_ayarlari_yukle()
        return {
            "status": "success",
            "message": "Tolerans ayarları başarıyla yüklendi",
            "ayarlar": ayarlar
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tolerans ayarları yükleme hatası: {str(e)}")

@router.post("/ayarlar")
async def tolerans_ayarlari_guncelle(ayarlar: ToleransAyarlari):
    """Tolerans ayarlarını güncelle"""
    try:
        # Değer kontrolü
        ayarlar_dict = ayarlar.dict()
        for key, value in ayarlar_dict.items():
            if value < 0 or value > 10000:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Geçersiz değer: {key} = {value}. Değer 0-10000 arasında olmalıdır."
                )
        
        # Ayarları kaydet
        if tolerans_ayarlari_kaydet(ayarlar_dict):
            return {
                "status": "success",
                "message": "Tolerans ayarları başarıyla güncellendi",
                "ayarlar": ayarlar_dict
            }
        else:
            raise HTTPException(status_code=500, detail="Tolerans ayarları kaydedilemedi")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tolerans ayarları güncelleme hatası: {str(e)}")

@router.get("/durum")
async def tolerans_durumu():
    """Tolerans sistemi durumunu getir"""
    try:
        ayarlar = tolerans_ayarlari_yukle()
        dosya_var = os.path.exists(TOLERANS_DOSYA_YOLU)
        
        return {
            "status": "success",
            "message": "Tolerans sistemi durumu",
            "durum": {
                "dosya_var": dosya_var,
                "dosya_yolu": TOLERANS_DOSYA_YOLU,
                "mevcut_ayarlar": ayarlar,
                "toplam_tolerans_sayisi": len(ayarlar)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tolerans durumu sorgulama hatası: {str(e)}")
