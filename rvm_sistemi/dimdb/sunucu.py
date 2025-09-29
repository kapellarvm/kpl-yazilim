from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uuid
import time
import asyncio
from contextlib import asynccontextmanager

# Projenin diğer modüllerini doğru paket yolundan import et
from ..makine.dogrulama import DogrulamaServisi
from ..makine.seri.sensor_karti import SensorKart
from ..makine.seri.motor_karti import MotorKart
from ..makine.seri.port_yonetici import KartHaberlesmeServis
from ..makine.mod_degistirici import durum_makinesi # Merkezi durum makinesini import et
from . import istemci

# --- Donanım ve Kuyruk Sistemi ---
sensor = None
motor = None
package_queue = asyncio.Queue()



async def package_worker():
    print("Paket işleme çalışanı aktif, yeni paketler bekleniyor...")
    while True:
        try:
            package_data = await package_queue.get()
            await process_package_and_send_result(package_data)
            package_queue.task_done()
        except Exception as e:
            print(f"Paket işleme çalışanında hata oluştu: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global sensor, motor
    print("Uygulama başlatılıyor: Donanım bağlantıları kuruluyor...")
    
    yonetici = KartHaberlesmeServis()
    basarili, mesaj, portlar = yonetici.baglan()
    print(f"🛈 {mesaj}")
    print(f"🛈 Bulunan portlar: {portlar}")

    if "sensor" in portlar:
        sensor = SensorKart(portlar["sensor"])
        sensor.dinlemeyi_baslat()
        print("✅ Sensör kartı dinleniyor...")
    else:
        print("❌ Sensör kartı bulunamadı.")


        
    asyncio.create_task(package_worker())
    
    yield
    
    print("\nUygulama kapatılıyor...")
    await handle_graceful_shutdown()
    
app = FastAPI(title="RVM Sunucusu", lifespan=lifespan)

# --- Pydantic Modelleri ve Oturum Yönetimi ---
class SessionStartRequest(BaseModel): guid: str; sessionId: str; userId: str
class AcceptPackageRequest(BaseModel): guid: str; uuid: str; sessionId: str; barcode: str
class SessionEndRequest(BaseModel): guid: str; sessionId: str; slipData: str
class StopOperationRequest(BaseModel): guid: str; barcode: str
class UpdateProductsRequest(BaseModel): guid: str; rvm: str; timestamp: str
class ResetRvmRequest(BaseModel): guid: str; rvm: str; timestamp: str

dogrulama_servisi = DogrulamaServisi()
aktif_oturum = {"aktif": False, "sessionId": None, "userId": None, "kabul_edilen_urunler": []}

# --- Arka Plan Fonksiyonları ---
async def process_package_and_send_result(data: AcceptPackageRequest):
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
    global aktif_oturum
    if not aktif_oturum["aktif"]: return

    print("Oturum sonlandırılıyor, işlem özeti hazırlanıyor...")
    #sensor.led_kapat()
    
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
    durum_makinesi.durum_degistir("oturum_yok")
    print("Yerel oturum temizlendi.")

# --- API Uç Noktaları (Endpoints) ---

@app.post("/sessionStart")
async def session_start(data: SessionStartRequest):
    global aktif_oturum
    print(f"Gelen /sessionStart isteği: {data.model_dump_json()}")
    if aktif_oturum["aktif"]:
        return {"errorCode": 2, "errorMessage": "Aktif oturum var."}
    
    aktif_oturum = {"aktif": True, "sessionId": data.sessionId, "userId": data.userId, "kabul_edilen_urunler": []}
    # DÜZELTME: Doğru nesne ve metot adını kullan
    durum_makinesi.durum_degistir("oturum_var")
    #sensor.led_ac()
    
    print(f"✅ /sessionStart isteği kabul edildi. Yeni oturum: {aktif_oturum['sessionId']}")
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/acceptPackage")
async def accept_package(data: AcceptPackageRequest):
    if durum_makinesi.durum != "oturum_var":
        print(f"UYARI: Makine '{durum_makinesi.durum}' durumundayken paket kabul edilemez.")
        return {"errorCode": 3, "errorMessage": "Makine paket kabul etmeye hazır değil."}

    print(f"Gelen /acceptPackage isteği, kuyruğa ekleniyor: {data.barcode}")
    await package_queue.put(data)
    return {"errorCode": 0, "errorMessage": "Package queued for processing"}

@app.post("/sessionEnd")
async def session_end(data: SessionEndRequest, background_tasks: BackgroundTasks):
    print(f"Gelen /sessionEnd isteği: {data.model_dump_json()}")
    if not aktif_oturum["aktif"] or aktif_oturum["sessionId"] != data.sessionId:
        return {"errorCode": 2, "errorMessage": "Aktif veya geçerli bir oturum bulunamadı."}
    
    background_tasks.add_task(handle_graceful_shutdown)
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/maintenanceMode")
async def maintenanceMode():
    print("Bakım Modu Aktif")
    # DÜZELTME: Doğru nesne ve metot adını kullan
    durum_makinesi.durum_degistir("bakim")
    return {"errorCode": 0, "errorMessage": "Bakım moduna geçildi"}

@app.post("/stopOperation")
async def stop_operation(data: StopOperationRequest):
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/updateProducts")
async def update_products(data: UpdateProductsRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(istemci.get_all_products_and_save)
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/resetRvm")
async def reset_rvm(data: ResetRvmRequest):
    return {"errorCode": 0, "errorMessage": ""}

