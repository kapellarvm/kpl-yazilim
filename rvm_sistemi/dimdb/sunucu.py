from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import logging
from pydantic import BaseModel
import uuid
import time
import asyncio
from contextlib import asynccontextmanager
from rvm_sistemi.makine.senaryolar import oturum_yok, oturum_var

# Projenin diğer modüllerini doğru paket yolundan import et
from ..makine.dogrulama import DogrulamaServisi
from ..makine.durum_degistirici import durum_makinesi # Merkezi durum makinesini import et
from ..makine import kart_referanslari  # Merkezi kart referansları
from . import istemci

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
        
    asyncio.create_task(package_worker())
    
    yield
    
    print("\nUygulama kapatılıyor...")
    await handle_graceful_shutdown()
    
app = FastAPI(title="RVM Sunucusu", lifespan=lifespan)

# Log filtreleme middleware'i
@app.middleware("http")
async def log_filter(request: Request, call_next):
    # Sistem durumu isteklerini loglamayı atla
    if request.url.path == "/api/sistem-durumu":
        # Sessizce işle
        response = await call_next(request)
        return response
    else:
        # Diğer istekleri normal logla
        response = await call_next(request)
        return response

# Static dosyalar\u0131 serve et (iste\u011fe ba\u011fl\u0131)
try:
    import os
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    print(f"Static dosya yolu: {static_path}")
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")
        print("Static dosyalar ba\u015far\u0131yla y\u00fcklendi.")
    else:
        print(f"Static klas\u00f6r bulunamad\u0131: {static_path}")
except Exception as e:
    print(f"Static dosyalar y\u00fcklenemedi: {e}")

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
    oturum_var.barkod_verisi_al(data.barcode)

    #dogrulama_sonucu = dogrulama_servisi.paketi_dogrula(data.barcode)
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

# --- BAKIM EKRANI API ENDPOINT'LERİ ---

@app.get("/")
async def ana_sayfa():
    """Test endpoint'i"""
    return {"message": "RVM Sunucusu çalışıyor!", "bakim_ekrani": "/bakim"}

@app.get("/bakim")
async def bakim_ekrani():
    """Bakım ekranı HTML sayfasını döndürür"""
    import os
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "bakim.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Bakım ekranı dosyası bulunamadı</h1>", status_code=404)

@app.post("/api/motor/konveyor-ileri")
async def konveyor_ileri():
    """Konveyörü ileri hareket ettirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.konveyor_ileri()
        return {"status": "success", "message": "Konveyör ileri hareket ediyor"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/konveyor-geri")
async def konveyor_geri():
    """Konveyörü geri hareket ettirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.konveyor_geri()
        return {"status": "success", "message": "Konveyör geri hareket ediyor"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/konveyor-dur")
async def konveyor_dur():
    """Konveyörü durdurur"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.konveyor_dur()
        return {"status": "success", "message": "Konveyör durduruldu"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/motorlari-aktif")
async def motorlari_aktif():
    """Motorları aktif eder"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.motorlari_aktif_et()
        return {"status": "success", "message": "Motorlar aktif edildi"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/motorlari-iptal")
async def motorlari_iptal():
    """Motorları iptal eder"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.motorlari_iptal_et()
        return {"status": "success", "message": "Motorlar iptal edildi"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/yonlendirici-plastik")
async def yonlendirici_plastik():
    """Yönlendiriciyi plastik pozisyonuna getirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.yonlendirici_plastik()
        # Yönlendirici işleminden sonra konveyörü durdur
        import asyncio
        await asyncio.sleep(0.7)  # 200ms bekleme (gömülü sistem için)
        motor.konveyor_dur()
        return {"status": "success", "message": "Yönlendirici plastik pozisyonunda, konveyör durduruldu"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/yonlendirici-cam")
async def yonlendirici_cam():
    """Yönlendiriciyi cam pozisyonuna getirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.yonlendirici_cam()
        # Yönlendirici işleminden sonra konveyörü durdur
        import asyncio
        await asyncio.sleep(0.7)  # 200ms bekleme (gömülü sistem için)
        motor.konveyor_dur()
        return {"status": "success", "message": "Yönlendirici cam pozisyonunda, konveyör durduruldu"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/klape-metal")
async def klape_metal():
    """Klapeyi metal pozisyonuna getirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.klape_metal()
        return {"status": "success", "message": "Klape metal pozisyonunda"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/klape-plastik")
async def klape_plastik():
    """Klapeyi plastik pozisyonuna getirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.klape_plastik()
        return {"status": "success", "message": "Klape plastik pozisyonunda"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

class MotorParametreleri(BaseModel):
    konveyor_hizi: int = None
    yonlendirici_hizi: int = None
    klape_hizi: int = None

@app.post("/api/motor/parametreler")
async def motor_parametreleri(params: MotorParametreleri):
    """Motor hızlarını ayarlar"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.parametre_degistir(
            konveyor=params.konveyor_hizi, 
            yonlendirici=params.yonlendirici_hizi, 
            klape=params.klape_hizi
        )
        motor.parametre_gonder()
        return {"status": "success", "message": "Parametreler güncellendi"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.get("/api/sistem-durumu")
async def sistem_durumu():
    """Sistem durumunu döndürür"""
    motor_baglanti = False
    sensor_baglanti = False
    motor_hizlari = {"konveyor": 0, "yonlendirici": 0, "klape": 0}
    
    # Motor kontrolü
    motor = kart_referanslari.motor_al()
    if motor:
        try:
            motor_baglanti = motor.getir_saglik_durumu()
            motor_hizlari = {
                "konveyor": motor.konveyor_hizi,
                "yonlendirici": motor.yonlendirici_hizi,
                "klape": motor.klape_hizi
            }
        except:
            pass
    
    # Sensör kontrolü
    sensor = kart_referanslari.sensor_al()
    if sensor:
        try:
            sensor_baglanti = sensor.getir_saglik_durumu()
        except:
            pass
    
    return {
        "motor_baglanti": motor_baglanti,
        "sensor_baglanti": sensor_baglanti,
        "mevcut_durum": durum_makinesi.durum,
        "motor_hizlari": motor_hizlari
    }

@app.post("/api/bakim-modu")
async def bakim_modu(aktif: bool):
    """Bakım modunu aktif/pasif eder"""
    try:
        if aktif:
            durum_makinesi.durum_degistir("bakim")
            return {"status": "success", "message": "Bakım modu aktif edildi"}
        else:
            durum_makinesi.durum_degistir("oturum_yok")
            return {"status": "success", "message": "Bakım modu pasif edildi, sistem normal moda döndü"}
    except Exception as e:
        return {"status": "error", "message": f"Bakım modu hatası: {str(e)}"}

class BakimModuRequest(BaseModel):
    aktif: bool

@app.post("/api/bakim-modu-ayarla")
async def bakim_modu_ayarla(request: BakimModuRequest):
    """Bakım modunu aktif/pasif eder"""
    try:
        if request.aktif:
            # Durum makinesine bakım moduna geç - otomatik ekran değişimi yapılacak
            durum_makinesi.durum_degistir("bakim")
            return {"status": "success", "message": "Bakım modu aktif edildi, ekran açıldı", "durum": "bakim"}
        else:
            # Durum makinesine normal moda geç - otomatik ana ekrana dönülecek
            durum_makinesi.durum_degistir("oturum_yok")
            return {"status": "success", "message": "Bakım modu pasif edildi, ana ekrana dönüldü", "durum": "oturum_yok"}
    except Exception as e:
        return {"status": "error", "message": f"Bakım modu hatası: {str(e)}"}

@app.post("/api/sistem-reset")
async def sistem_reset():
    """Portları kapatıp yeniden port araması yapar"""
    try:
        motor = kart_referanslari.motor_al()
        sensor = kart_referanslari.sensor_al()
        
        # Kartları durdur
        if motor:
            motor.dinlemeyi_durdur()
        if sensor:
            sensor.dinlemeyi_durdur()
        
        # Kısa bekleme
        import time
        time.sleep(1)
        
        # Port yöneticisi ile yeniden ara
        from ..makine.seri.port_yonetici import KartHaberlesmeServis
        from ..makine.seri.sensor_karti import SensorKart
        from ..makine.seri.motor_karti import MotorKart
        
        yonetici = KartHaberlesmeServis()
        basarili, mesaj, portlar = yonetici.baglan()
        
        if basarili and "sensor" in portlar and "motor" in portlar:
            # Yeni kartları oluştur
            yeni_sensor = SensorKart(portlar["sensor"], cihaz_adi="sensor")
            yeni_sensor.dinlemeyi_baslat()
            
            yeni_motor = MotorKart(portlar["motor"], cihaz_adi="motor")
            yeni_motor.dinlemeyi_baslat()
            
            # Referansları güncelle
            kart_referanslari.motor_referansini_ayarla(yeni_motor)
            kart_referanslari.sensor_referansini_ayarla(yeni_sensor)
            
            return {"status": "success", "message": "Sistem başarıyla resetlendi ve portlar yeniden bağlandı"}
        else:
            return {"status": "error", "message": f"Port bulunamadı: {mesaj}"}
            
    except Exception as e:
        return {"status": "error", "message": f"Reset hatası: {str(e)}"}

# --- SENSÖR KARTI API ENDPOINT'LERİ ---

@app.post("/api/sensor/led-ac")
async def sensor_led_ac():
    """Sensör LED'ini açar"""
    sensor = kart_referanslari.sensor_al()
    if sensor:
        sensor.led_ac()
        return {"status": "success", "message": "LED açıldı"}
    return {"status": "error", "message": "Sensör bağlantısı yok"}

@app.post("/api/sensor/led-kapat")
async def sensor_led_kapat():
    """Sensör LED'ini kapatır"""
    sensor = kart_referanslari.sensor_al()
    if sensor:
        sensor.led_kapat()
        return {"status": "success", "message": "LED kapatıldı"}
    return {"status": "error", "message": "Sensör bağlantısı yok"}

@app.post("/api/sensor/loadcell-olc")
async def sensor_loadcell_olc():
    """Loadcell ölçümü yapar"""
    sensor = kart_referanslari.sensor_al()
    if sensor:
        sensor.loadcell_olc()
        return {"status": "success", "message": "Loadcell ölçümü başlatıldı"}
    return {"status": "error", "message": "Sensör bağlantısı yok"}

@app.post("/api/sensor/teach")
async def sensor_teach():
    """Gyro sensör teach yapar"""
    sensor = kart_referanslari.sensor_al()
    if sensor:
        sensor.teach()
        return {"status": "success", "message": "Gyro sensör teach başlatıldı"}
    return {"status": "error", "message": "Sensör bağlantısı yok"}

@app.post("/api/sensor/tare")
async def sensor_tare():
    """Loadcell tare (sıfırlama) yapar"""
    sensor = kart_referanslari.sensor_al()
    if sensor:
        sensor.tare()
        return {"status": "success", "message": "Loadcell tare yapıldı"}
    return {"status": "error", "message": "Sensör bağlantısı yok"}

# Global sensör değerleri
sensor_son_deger = {"agirlik": 0, "mesaj": "Henüz ölçüm yapılmadı"}

def sensor_callback(mesaj):
    """Sensör kartından gelen mesajları işler"""
    global sensor_son_deger
    print(f"[SENSOR CALLBACK] Gelen mesaj: {mesaj}")
    
    # Mesajı kaydet
    sensor_son_deger["mesaj"] = mesaj
    
    # Ağırlık değerini parse et - farklı formatları destekle
    import re
    
    # Format 1: "a:262.62" veya "a:-1.79" gibigit
    if mesaj.startswith("a:"):
        try:
            agirlik_str = mesaj.replace("a:", "").strip()
            sensor_son_deger["agirlik"] = float(agirlik_str)
            print(f"[SENSOR] Ağırlık parse edildi: {sensor_son_deger['agirlik']} gram")
        except ValueError:
            print(f"[SENSOR] Ağırlık parse hatası: {mesaj}")
    
    # Format 2: "loadcell" veya "gr" içeren mesajlar
    elif "loadcell" in mesaj.lower() or "gr" in mesaj.lower():
        sayilar = re.findall(r'-?\d+\.?\d*', mesaj)
        if sayilar:
            sensor_son_deger["agirlik"] = float(sayilar[0])
            print(f"[SENSOR] Ağırlık parse edildi: {sensor_son_deger['agirlik']} gram")

@app.get("/api/sensor/son-deger")
async def sensor_son_deger_getir():
    """Sensörden gelen son değeri döndürür"""
    return {"status": "success", "data": sensor_son_deger}

# Sensör referansını ayarla fonksiyonunu güncelle
def sensor_referansi_callback_ile_ayarla(sensor_instance):
    """Sensör referansını callback ile birlikte ayarlar"""
    sensor_instance.callback = sensor_callback
    kart_referanslari.sensor_referansini_ayarla(sensor_instance)

