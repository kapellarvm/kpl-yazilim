"""
DİM-DB API Endpoint'leri
Oturum yönetimi ve paket işleme endpoint'leri
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..modeller.schemas import (
    SessionStartRequest, AcceptPackageRequest, SessionEndRequest,
    StopOperationRequest, UpdateProductsRequest, ResetRvmRequest,
    SuccessResponse, ErrorResponse
)
from ..servisler.dimdb_servis import DimdbServis
from ..servisler.oturum_servis import OturumServis
from ...makine.durum_degistirici import durum_makinesi
from ...makine.senaryolar import oturum_var
from ...dimdb import dimdb_istemcisi

router = APIRouter(prefix="/dimdb", tags=["DİM-DB"])


@router.post("/sessionStart", response_model=SuccessResponse)
async def session_start(data: SessionStartRequest):
    """Oturum başlatma endpoint'i"""
    print(f"Gelen /sessionStart isteği: {data.model_dump_json()}")
    
    # oturum_var.py'deki oturum durumunu kontrol et
    if oturum_var.sistem.aktif_oturum["aktif"]:
        return ErrorResponse(errorCode=2, errorMessage="Aktif oturum var.")

    # Oturum başlatma servisini çağır
    OturumServis.oturum_baslat(data.sessionId, data.userId)
    
    # Durum makinesini güncelle
    durum_makinesi.durum_degistir("oturum_var")
    
    print(f"✅ /sessionStart isteği kabul edildi. Yeni oturum: {data.sessionId}")
    return SuccessResponse()


@router.post("/acceptPackage", response_model=SuccessResponse)
async def accept_package(data: AcceptPackageRequest):
    """Paket kabul etme endpoint'i"""
    if durum_makinesi.durum != "oturum_var":
        print(f"UYARI: Makine '{durum_makinesi.durum}' durumundayken paket kabul edilemez.")
        return ErrorResponse(errorCode=3, errorMessage="Makine paket kabul etmeye hazır değil.")

    print(f"Gelen /acceptPackage isteği: {data.barcode}")
    
    # Barkodu oturum_var.py'ye gönder - tüm doğrulama ve DİM-DB bildirimi orada yapılacak
    oturum_var.barkod_verisi_al(data.barcode)
    
    return SuccessResponse(errorMessage="Package processing started")


@router.post("/sessionEnd", response_model=SuccessResponse)
async def session_end(data: SessionEndRequest):
    """Oturum sonlandırma endpoint'i"""
    print(f"Gelen /sessionEnd isteği: {data.model_dump_json()}")
    
    # oturum_var.py'deki oturum durumunu kontrol et
    if not oturum_var.sistem.aktif_oturum["aktif"] or oturum_var.sistem.aktif_oturum["sessionId"] != data.sessionId:
        return ErrorResponse(errorCode=2, errorMessage="Aktif veya geçerli bir oturum bulunamadı.")
    
    # DİM-DB'ye transaction result gönder
    await DimdbServis.send_transaction_result()
    
    # Oturum sonlandırma servisini çağır
    OturumServis.oturum_sonlandir()
    
    # Durum makinesini güncelle
    durum_makinesi.durum_degistir("oturum_yok")
    
    print(f"✅ /sessionEnd isteği kabul edildi. Oturum kapatıldı: {data.sessionId}")
    return SuccessResponse()


@router.post("/maintenanceMode", response_model=SuccessResponse)
async def maintenance_mode():
    """Bakım modu endpoint'i"""
    print("Bakım Modu Aktif")
    durum_makinesi.durum_degistir("bakim")
    return SuccessResponse(errorMessage="Bakım moduna geçildi")


@router.post("/stopOperation", response_model=SuccessResponse)
async def stop_operation(data: StopOperationRequest):
    """Operasyon durdurma endpoint'i"""
    return SuccessResponse()


@router.post("/updateProducts", response_model=SuccessResponse)
async def update_products(data: UpdateProductsRequest):
    """Ürün güncelleme endpoint'i"""
    from fastapi import BackgroundTasks
    background_tasks = BackgroundTasks()
    background_tasks.add_task(dimdb_istemcisi.get_all_products_and_save)
    return SuccessResponse()


@router.post("/resetRvm", response_model=SuccessResponse)
async def reset_rvm(data: ResetRvmRequest):
    """RVM reset endpoint'i"""
    return SuccessResponse()
