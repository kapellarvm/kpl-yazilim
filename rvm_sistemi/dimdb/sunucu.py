from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uuid
import time
import asyncio
from contextlib import asynccontextmanager

# Projenin diğer modüllerini doğru paket yolundan import et
from ..makine.dogrulama import DogrulamaServisi
from . import istemci

# --- UYGULAMA KURULUMU VE KUYRUK SİSTEMİ ---

# Gelen paket isteklerini tutmak için bir kuyruk (bekleme odası)
package_queue = asyncio.Queue()

async def package_worker():
    """
    Kuyruğu sürekli dinleyen ve gelen paketleri sırayla işleyen
    arka plan çalışanı.
    """
    print("Paket işleme çalışanı aktif, yeni paketler bekleniyor...")
    while True:
        try:
            # Kuyruktan bir paket al (eğer boşsa burada bekler)
            package_data = await package_queue.get()
            print(f"Kuyruktan yeni paket alındı, işleniyor: {package_data.barcode}")
            
            # Paketi işleyen ana fonksiyonu çağır
            await process_package_and_send_result(package_data)
            
            # Kuyruğa bu görevin tamamlandığını bildir
            package_queue.task_done()
        except Exception as e:
            print(f"Paket işleme çalışanında hata oluştu: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI uygulaması başlarken ve kapanırken çalışacak olan olay yöneticisi.
    """
    # Uygulama başlarken, paket işleme çalışanını başlat
    asyncio.create_task(package_worker())
    yield
    # Uygulama kapandığında yapılacaklar (varsa)
    print("Uygulama kapatılıyor.")

# FastAPI uygulamasını, lifespan yöneticisi ile birlikte oluştur
app = FastAPI(title="RVM Sunucusu", lifespan=lifespan)


# --- Pydantic Modelleri ---
class SessionStartRequest(BaseModel):
    guid: str; sessionId: str; userId: str

class AcceptPackageRequest(BaseModel):
    guid: str; uuid: str; sessionId: str; barcode: str

class SessionEndRequest(BaseModel):
    guid: str; sessionId: str; slipData: str

class StopOperationRequest(BaseModel):
    guid: str; barcode: str

class UpdateProductsRequest(BaseModel):
    guid: str; rvm: str; timestamp: str
    
class ResetRvmRequest(BaseModel):
    guid: str; rvm: str; timestamp: str

# --- UYGULAMA BAŞLANGICINDA BAŞLATILACAKLAR ---
dogrulama_servisi = DogrulamaServisi()
aktif_oturum = {
    "aktif": False,
    "sessionId": None,
    "userId": None,
    "kabul_edilen_urunler": []
}

# --- Arka Plan İşlem Fonksiyonları ---

async def process_package_and_send_result(data: AcceptPackageRequest):
    """Gelen paketi doğrular ve sonucu gönderir."""
    
    dogrulama_sonucu = dogrulama_servisi.paketi_dogrula(data.barcode)

    if dogrulama_sonucu["kabul_edildi"]:
        materyal_id = dogrulama_sonucu["materyal_id"]
        result_message = "Ambalaj Kabul Edildi"
        aktif_oturum["kabul_edilen_urunler"].append({"barcode": data.barcode, "material": materyal_id})
    else:
        materyal_id = -1
        result_message = "Ambalaj Reddedildi"
    
    pet_sayisi = sum(1 for u in aktif_oturum["kabul_edilen_urunler"] if u.get('material') == 1)
    cam_sayisi = sum(1 for u in aktif_oturum["kabul_edilen_urunler"] if u.get('material') == 2)
    alu_sayisi = sum(1 for u in aktif_oturum["kabul_edilen_urunler"] if u.get('material') == 3)
        
    result_payload = {
        "guid": str(uuid.uuid4()), "uuid": data.uuid, "sessionId": data.sessionId,
        "barcode": data.barcode, "measuredPackWeight": 0.0, "measuredPackHeight": 0.0,
        "measuredPackWidth": 0.0, "binId": materyal_id, "result": dogrulama_sonucu["sebep_kodu"],
        "resultMessage": result_message, "acceptedPetCount": pet_sayisi, 
        "acceptedGlassCount": cam_sayisi, "acceptedAluCount": alu_sayisi
    }
    
    await istemci.send_accept_package_result(result_payload)
    print(f"Paket işleme tamamlandı: {data.barcode}")


async def handle_graceful_shutdown():
    """Aktif oturumun işlem özetini DİM-DB'ye gönderir."""
    global aktif_oturum
    if not aktif_oturum["aktif"]: return

    print("Oturum sonlandırılıyor, işlem özeti hazırlanıyor...")
    
    containers = {}
    for urun in aktif_oturum["kabul_edilen_urunler"]:
        barcode = urun["barcode"]
        if barcode not in containers:
            containers[barcode] = {"barcode": barcode, "material": urun["material"], "count": 0, "weight": 0}
        containers[barcode]["count"] += 1

    transaction_payload = {
        "guid": str(uuid.uuid4()), "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "rvm": istemci.RVM_ID, "id": aktif_oturum["sessionId"] + "-tx",
        "firstBottleTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "endTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "sessionId": aktif_oturum["sessionId"], "userId": aktif_oturum["userId"],
        "created": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "containerCount": len(aktif_oturum["kabul_edilen_urunler"]),
        "containers": list(containers.values())
    }
    await istemci.send_transaction_result(transaction_payload)
    
    aktif_oturum = {"aktif": False, "sessionId": None, "userId": None, "kabul_edilen_urunler": []}
    print("Yerel oturum temizlendi.")

# --- FastAPI ENDPOINTLERİ ---

@app.post("/sessionStart")
async def session_start(data: SessionStartRequest):
    global aktif_oturum
    print(f"Gelen /sessionStart isteği: {data.model_dump_json()}")
    
    if aktif_oturum["aktif"]:
        return {"errorCode": 2, "errorMessage": "Aktif oturum var."}
    
    aktif_oturum = {"aktif": True, "sessionId": data.sessionId, "userId": data.userId, "kabul_edilen_urunler": []}
    print(f"✅ /sessionStart isteği kabul edildi. Yeni oturum: {aktif_oturum['sessionId']}")
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/acceptPackage")
async def accept_package(data: AcceptPackageRequest):
    print(f"Gelen /acceptPackage isteği, kuyruğa ekleniyor: {data.barcode}")
    if not aktif_oturum["aktif"]:
        return {"errorCode": 2, "errorMessage": "Aktif Oturum Yok"}

    # Gelen isteği doğrudan işlemek yerine kuyruğa koy
    await package_queue.put(data)
    
    return {"errorCode": 0, "errorMessage": "Package queued for processing"}

@app.post("/sessionEnd")
async def session_end(data: SessionEndRequest, background_tasks: BackgroundTasks):
    print(f"Gelen /sessionEnd isteği: {data.model_dump_json()}")
    if not aktif_oturum["aktif"] or aktif_oturum["sessionId"] != data.sessionId:
        return {"errorCode": 2, "errorMessage": "Aktif veya geçerli bir oturum bulunamadı."}
    
    background_tasks.add_task(handle_graceful_shutdown)
    print("✅ /sessionEnd isteği kabul edildi, arka planda işleniyor.")
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/stopOperation")
async def stop_operation(data: StopOperationRequest):
    print(f"Gelen /stopOperation isteği: {data.model_dump_json()}")
    print("✅ /stopOperation isteği kabul edildi.")
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/updateProducts")
async def update_products(data: UpdateProductsRequest, background_tasks: BackgroundTasks):
    print(f"Gelen /updateProducts isteği: {data.model_dump_json()}")
    background_tasks.add_task(istemci.get_all_products_and_save)
    print("✅ /updateProducts isteği kabul edildi, arka planda işleniyor.")
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/resetRvm")
async def reset_rvm(data: ResetRvmRequest):
    print(f"Gelen /resetRvm isteği: {data.model_dump_json()}")
    print("✅ /resetRvm isteği kabul edildi.")
    return {"errorCode": 0, "errorMessage": ""}

