import asyncio
import time
from collections import deque
from ...veri_tabani import veritabani_yoneticisi
from ..goruntu.image_processing_service import ImageProcessingService
from ..uyari_yoneticisi import uyari_yoneticisi
import uuid as uuid_lib

# =========================
# Servisler ve Global Durum
# =========================

image_processing_service = ImageProcessingService()

# Referanslar
motor_ref = None
sensor_ref = None

# Ürün verileri
agirlik = None
# İade durumu
giris_iade_lojik = False
mesaj = None

# Kabul edilen ürünler kuyruğu
kabul_edilen_urunler = deque()
veri_senkronizasyonu_kuyrugu = deque()

barkod_lojik = False

# DİM-DB Oturum bilgileri
aktif_oturum = {
    "aktif": False,
    "sessionId": None,
    "userId": None,
    "paket_uuid_map": {}  # Her paket için UUID haritalama
}

# =========================
# Yardımcı: Bloklayan çağrıları thread'e at
# =========================

async def _motor_call(fn_name: str, *args, **kwargs):
    """motor_ref üzerindeki bloklayan fonksiyonları thread'de çalıştır."""
    if motor_ref is None:
        return
    fn = getattr(motor_ref, fn_name, None)
    if fn is None:
        print(f"⚠️ [MOTOR] Fonksiyon bulunamadı: {fn_name}")
        return
    return await asyncio.to_thread(fn, *args, **kwargs)

async def _sensor_call(fn_name: str, *args, **kwargs):
    """sensor_ref üzerindeki bloklayan fonksiyonları thread'de çalıştır."""
    if sensor_ref is None:
        return
    fn = getattr(sensor_ref, fn_name, None)
    if fn is None:
        print(f"⚠️ [SENSÖR] Fonksiyon bulunamadı: {fn_name}")
        return
    return await asyncio.to_thread(fn, *args, **kwargs)

# =========================
# Başlat / Referans Bağlama
# =========================

async def motor_referansini_ayarla(motor):
    """Motor referansını ayarla ve güvenli başlangıç; bloklayanlar thread'de."""
    global motor_ref
    motor_ref = motor
    await _motor_call("motorlari_aktif_et")
    await _motor_call("konveyor_dur")
    await _motor_call("yonlendirici_sensor_teach")
    print("✅ Motor hazır - Sistem başlatıldı")

async def sensor_referansini_ayarla(sensor):
    """Sensör referansını ayarla; teach bloklayıcı olabilir."""
    global sensor_ref
    sensor_ref = sensor
    await _sensor_call("teach")

def oturum_baslat(session_id, user_id):
    """DİM-DB'den gelen oturum başlatma (senkron state güncellemesi)"""
    global aktif_oturum, kabul_edilen_urunler

    aktif_oturum = {
        "aktif": True,
        "sessionId": session_id,
        "userId": user_id,
        "paket_uuid_map": {}
    }

    # Eski ürünleri temizle
    kabul_edilen_urunler.clear()
    print(f"✅ [OTURUM] DİM-DB oturumu başlatıldı: {session_id}, Kullanıcı: {user_id}")

async def oturum_sonlandir():
    """Oturumu sonlandır ve DİM-DB'ye transaction result gönder (ASYNC)."""
    global aktif_oturum, kabul_edilen_urunler

    if not aktif_oturum["aktif"]:
        print("⚠️ [OTURUM] Aktif oturum yok, sonlandırma yapılmadı")
        return

    print(f"🔚 [OTURUM] Oturum sonlandırılıyor: {aktif_oturum['sessionId']}")

    try:
        from ...dimdb import istemci

        # Kabul edilen ürünleri konteyner formatına dönüştür
        containers = {}
        for urun in kabul_edilen_urunler:
            barcode = urun["barkod"]
            if barcode not in containers:
                containers[barcode] = {
                    "barcode": barcode,
                    "material": urun["materyal_turu"],
                    "count": 0,
                    "weight": 0
                }
            containers[barcode]["count"] += 1
            containers[barcode]["weight"] += urun["agirlik"]

        now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        transaction_payload = {
            "guid": str(uuid_lib.uuid4()),
            "timestamp": now_iso,
            "rvm": istemci.RVM_ID,
            "id": aktif_oturum["sessionId"] + "-tx",
            "firstBottleTime": now_iso,
            "endTime": now_iso,
            "sessionId": aktif_oturum["sessionId"],
            "userId": aktif_oturum["userId"],
            "created": now_iso,
            "containerCount": len(kabul_edilen_urunler),
            "containers": list(containers.values())
        }

        await istemci.send_transaction_result(transaction_payload)
        print("✅ [OTURUM] Transaction result DİM-DB'ye gönderildi")

    except Exception as e:
        print(f"❌ [OTURUM] Transaction result gönderme hatası: {e}")

    # Oturumu temizle
    aktif_oturum = {
        "aktif": False,
        "sessionId": None,
        "userId": None,
        "paket_uuid_map": {}
    }
    kabul_edilen_urunler.clear()
    print("🧹 [OTURUM] Yerel oturum temizlendi")

# =========================
# Barkod & DİM-DB Bildirimleri
# =========================

def barkod_verisi_al(barcode):
    """Bu fonksiyon senkron çağrılabilir; async iş kuyruk güncellediği için hızlıdır."""
    global giris_iade_lojik, barkod_lojik, aktif_oturum

    if giris_iade_lojik:
        print(f"🚫 [İADE AKTİF] Barkod görmezden gelindi: {barcode}")
        return

    # Her barkod için benzersiz UUID oluştur
    paket_uuid = str(uuid_lib.uuid4())
    aktif_oturum["paket_uuid_map"][barcode] = paket_uuid

    barkod_lojik = True
    # veri_senkronizasyonu async olduğundan, senkron bağlamdan tetikliyoruz:
    asyncio.create_task(veri_senkronizasyonu(barkod=barcode))

    print(f"\n📋 [YENİ ÜRÜN] Barkod okundu: {barcode}, UUID: {paket_uuid}")

async def dimdb_bildirimi_gonder(
    barkod, agirlik, materyal_turu, uzunluk, genislik,
    kabul_edildi, sebep_kodu, sebep_mesaji
):
    """DİM-DB'ye paket kabul/red sonucunu bildirir (ASYNC)."""
    global aktif_oturum

    if not aktif_oturum["aktif"]:
        print("⚠️ [DİM-DB] Aktif oturum yok, bildirim gönderilmedi")
        return

    try:
        from ...dimdb import istemci

        # UUID'yi al (yoksa üret)
        paket_uuid = aktif_oturum["paket_uuid_map"].get(barkod, str(uuid_lib.uuid4()))

        # Kabul edilen ürün sayılarını hesapla
        pet_sayisi = sum(1 for u in kabul_edilen_urunler if u.get('materyal_turu') == 1)
        cam_sayisi = sum(1 for u in kabul_edilen_urunler if u.get('materyal_turu') == 2)
        alu_sayisi = sum(1 for u in kabul_edilen_urunler if u.get('materyal_turu') == 3)

        result_payload = {
            "guid": str(uuid_lib.uuid4()),
            "uuid": paket_uuid,
            "sessionId": aktif_oturum["sessionId"],
            "barcode": barkod,
            "measuredPackWeight": float(agirlik),
            "measuredPackHeight": float(uzunluk),
            "measuredPackWidth": float(genislik),
            "binId": materyal_turu if kabul_edildi else -1,
            "result": sebep_kodu,
            "resultMessage": sebep_mesaji,
            "acceptedPetCount": pet_sayisi,
            "acceptedGlassCount": cam_sayisi,
            "acceptedAluCount": alu_sayisi
        }

        await istemci.send_accept_package_result(result_payload)
        print(f"✅ [DİM-DB] Accept package result gönderildi: {barkod} -> {'KABUL' if kabul_edildi else 'RED'}")

    except Exception as e:
        print(f"❌ [DİM-DB] Accept package result gönderme hatası: {e}")
        import traceback
        traceback.print_exc()

# =========================
# Doğrulama & Yönlendirme
# =========================

async def dogrulama(barkod, agirlik, materyal_turu, uzunluk, genislik):
    global kabul_edilen_urunler

    print(f"\n📊 [DOĞRULAMA] Mevcut durum: barkod={barkod}, ağırlık={agirlik}")

    # Veritabanı erişimi bloklayıcıysa to_thread kullan (emin değilsen güvenli olan budur)
    urun = await asyncio.to_thread(veritabani_yoneticisi.barkodu_dogrula, barkod)

    if not urun:
        print(f"❌ [DOĞRULAMA] Ürün veritabanında bulunamadı: {barkod}")
        await dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 1, "Ürün veritabanında yok")
        await giris_iade_et("Ürün veritabanında yok")
        return

    min_agirlik = urun.get('packMinWeight')
    max_agirlik = urun.get('packMaxWeight')
    min_genislik = urun.get('packMinWidth')
    max_genislik = urun.get('packMaxWidth')
    min_uzunluk = urun.get('packMinHeight')
    max_uzunluk = urun.get('packMaxHeight')
    materyal_id = urun.get('material')

    print(f"📊 [DOĞRULAMA] Min Agirlik: {min_agirlik}, Max Agirlik: {max_agirlik}, "
          f"Min Genişlik: {min_genislik}, Max Genişlik: {max_genislik}, "
          f"Min Uzunluk: {min_uzunluk}, Max Uzunluk: {max_uzunluk}, Materyal_id: {materyal_id}")

    print(f"📊 [DOĞRULAMA] Ölçülen ağırlık: {agirlik} gr")

    agirlik_kabul = False
    if min_agirlik is None and max_agirlik is None:
        agirlik_kabul = True
    elif min_agirlik is not None and max_agirlik is not None:
        agirlik_kabul = (min_agirlik - 20 <= agirlik <= max_agirlik + 20)
    elif min_agirlik is not None:
        agirlik_kabul = (agirlik >= min_agirlik - 20)
    elif max_agirlik is not None:
        agirlik_kabul = (agirlik <= max_agirlik + 20)

    print(f"📊 [DOĞRULAMA] Ağırlık kontrol sonucu: {agirlik_kabul}")

    if not agirlik_kabul:
        await dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 2, "Ağırlık sınırları dışında")
        await giris_iade_et("Ağırlık sınırları dışında")
        return

    if not (min_genislik <= genislik <= max_genislik):
        print(f"❌ [DOĞRULAMA] Genişlik sınırları dışında: {genislik} mm")
        await dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 3, "Genişlik sınırları dışında")
        await giris_iade_et("Genişlik sınırları dışında")
        return
    else:
        print(f"✅ [DOĞRULAMA] Genişlik kontrolü geçti: {genislik} mm")

    if not (min_uzunluk <= uzunluk <= max_uzunluk):
        print(f"❌ [DOĞRULAMA] Uzunluk sınırları dışında: {uzunluk} mm")
        await dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 4, "Uzunluk sınırları dışında")
        await giris_iade_et("Uzunluk sınırları dışında")
        return
    else:
        print(f"✅ [DOĞRULAMA] Uzunluk kontrolü geçti: {uzunluk} mm")

    if materyal_id != materyal_turu:
        print(f"❌ [DOĞRULAMA] Materyal türü uyuşmuyor: beklenen {materyal_id}, gelen {materyal_turu}")
        await dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 5, "Materyal türü uyuşmuyor")
        await giris_iade_et("Materyal türü uyuşmuyor")
        return

    print(f"✅ [DOĞRULAMA] Materyal türü kontrolü geçti: {materyal_turu}")

    # Tüm kontroller geçti, ürünü kabul et
    kabul_edilen_urunler.append({
        'barkod': barkod,
        'agirlik': agirlik,
        'materyal_turu': materyal_turu,
        'uzunluk': uzunluk,
        'genislik': genislik,
    })

    print(f"✅ [DOĞRULAMA] Ürün kabul edildi ve kuyruğa eklendi: {barkod}")
    print(f"📦 [KUYRUK] Toplam kabul edilen ürün sayısı: {len(kabul_edilen_urunler)}")

    # DİM-DB'ye kabul bildirimi gönder (await veya background task—burada await ediyoruz)
    await dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, True, 0, "Ambalaj Kabul Edildi")

async def yonlendirici_hareket():
    """Kabul edilen ilk ürünü al ve motorları çalıştır (bloklayanlar thread’de)."""
    if not kabul_edilen_urunler:
        print("ℹ️ [YÖNLENDİRME] Kuyruk boş")
        return

    # En eski ürünü al
    urun = kabul_edilen_urunler.popleft()
    materyal_turu = urun.get('materyal_turu')

    materyal_isimleri = {1: "PET", 2: "CAM", 3: "ALÜMİNYUM"}
    materyal_adi = materyal_isimleri.get(materyal_turu, "BİLİNMEYEN")

    print(f"\n🔄 [YÖNLENDİRME] {materyal_adi} ürün işleniyor: {urun['barkod']}")
    print(f"📦 [KUYRUK] Kalan ürün sayısı: {len(kabul_edilen_urunler)}")

    if motor_ref:
        if materyal_turu == 2:  # Cam
            await _motor_call("yonlendirici_cam")
            print("🟦 [CAM] Cam yönlendiricisine gönderildi")
        else:  # Plastik/Metal
            await _motor_call("yonlendirici_plastik")
            print("🟩 [PLASTİK] Plastik yönlendiricisine gönderildi")

    print("✅ [YÖNLENDİRME] İşlem tamamlandı\n")

# =========================
# İade & Mantık
# =========================

async def giris_iade_et(sebep):
    """Giriş iadesi—motor geri sarma bloklayıcı olabilir; thread’de çağır."""
    global giris_iade_lojik
    print(f"\n❌ [GİRİŞ İADESİ] Sebep: {sebep}")
    giris_iade_lojik = True
    await _motor_call("konveyor_geri")

def lojik_sifirla():
    global giris_iade_lojik, barkod_lojik
    giris_iade_lojik = False
    barkod_lojik = False

# =========================
# Görüntü İşleme Tetikleme
# =========================

async def goruntu_isleme_tetikle():
    """Görüntü yakalama/işleme bloklayıcıdır; thread’de çalıştır."""
    await asyncio.sleep(0.3)  # non-blocking bekleme
    goruntu_sonuc = await asyncio.to_thread(image_processing_service.capture_and_process)
    print(f"\n📷 [GÖRÜNTÜ İŞLEME] Sonuç: {goruntu_sonuc}")
    await veri_senkronizasyonu(
        materyal_turu=goruntu_sonuc.type.value,
        uzunluk=float(goruntu_sonuc.height_mm),
        genislik=float(goruntu_sonuc.width_mm)
    )

# =========================
# Veri Senkronizasyonu
# =========================

async def veri_senkronizasyonu(barkod=None, agirlik=None, materyal_turu=None, uzunluk=None, genislik=None):
    """FIFO ürün kayıtlarını parçalı gelen verilerle tamamlayıp doğrulamaya gönderir."""
    # Eğer kuyruk boşsa, yeni ürün başlat
    if not veri_senkronizasyonu_kuyrugu:
        veri_senkronizasyonu_kuyrugu.append({
            'barkod': None,
            'agirlik': None,
            'materyal_turu': None,
            'uzunluk': None,
            'genislik': None
        })

    # Her zaman FIFO mantığında en öndeki ürünü güncelle
    urun = veri_senkronizasyonu_kuyrugu[0]

    if barkod is not None:
        urun['barkod'] = barkod
    if agirlik is not None:
        urun['agirlik'] = agirlik
    if materyal_turu is not None:
        urun['materyal_turu'] = materyal_turu
    if uzunluk is not None:
        urun['uzunluk'] = uzunluk
    if genislik is not None:
        urun['genislik'] = genislik

    # Güncel durum
    print(f"🔍 [VERİ SENKRONİZASYONU] Güncel ürün durumu: {urun}")

    # Barkod yokken diğer veriler geldiyse—ürünü iptal et
    if urun['barkod'] is None and any(urun[k] is not None for k in ['agirlik', 'materyal_turu', 'uzunluk', 'genislik']):
        print(f"❌ [VERİ SENKRONİZASYONU] Karşılaştırma hatası - barkod olmadan veri geldi: {urun}")
        veri_senkronizasyonu_kuyrugu.popleft()  # hatalı ürünü sil
        print(f"🔄 [VERİ SENKRONİZASYONU] Güncel kuyruk durumu: {list(veri_senkronizasyonu_kuyrugu)}")
        return

    # Tüm alanlar dolduysa işleme al
    if all(urun[k] is not None for k in urun):
        print(f"✅ [VERİ SENKRONİZASYONU] Tüm veriler alındı: {urun}")
        await dogrulama(urun['barkod'], urun['agirlik'], urun['materyal_turu'], urun['uzunluk'], urun['genislik'])
        veri_senkronizasyonu_kuyrugu.popleft()  # işlenen ürünü kuyruktan çıkar

    print(f"🔄 [VERİ SENKRONİZASYONU] Güncel kuyruk durumu: {list(veri_senkronizasyonu_kuyrugu)}")

# =========================
# Mesaj İşleme (ASYNC)
# =========================

async def mesaj_isle(metin: str):
    """Durum makinesinden gelen metin mesajlarını asenkron yönetir."""
    global giris_iade_lojik, agirlik, barkod_lojik

    msg = metin.strip().lower()

    if msg == "oturum_var":
        print("🟢 [OTURUM] Aktif oturum başlatıldı")
        if sensor_ref:
            await _sensor_call("led_ac")
            lojik_sifirla()

    elif msg.startswith("a:"):
        if not giris_iade_lojik:
            try:
                agirlik_val = float(msg.split(":")[1].replace(",", "."))
            except Exception:
                print(f"⚠️ [A] Ağırlık format hatası: {msg}")
                return

            await veri_senkronizasyonu(agirlik=agirlik_val)
        else:
            print(f"🚫 [İADE AKTİF] Ağırlık görmezden gelindi: {msg}")

    elif msg == "gsi":
        if not giris_iade_lojik:
            print("🟢 [GSI] Şişe geldi.")
            await _motor_call("konveyor_ileri")
        else:
            # Gömülüden: 10cm geri adımı vb. (burada sadece kısa bekleme ve uyarı)
            await asyncio.sleep(0.2)
            print("▶️ [GSI] LÜTFEN ŞİŞEYİ ALINIZ.")
            uyari_yoneticisi.uyari_goster("Lütfen Şişeyi Alınız", 1)
            await _motor_call("konveyor_dur")

    elif msg == "gso":
        if not giris_iade_lojik:
            print("🟠 [GSO] Şişe içeride kontrole hazır.")

            if barkod_lojik:
                # Görüntü işleme bloklayıcı → async tetikleme
                await goruntu_isleme_tetikle()
            else:
                print("❌ [KONTROL] Barkod verisi yok")
                await giris_iade_et("Barkod yok")
        else:
            print("🟠 [GSO] İade şişe alındı.")
            await asyncio.sleep(2)
            lojik_sifirla()

    elif msg == "yso":
        print("🔵 [YSO] Yönlendirici sensör tetiklendi.")
        await yonlendirici_hareket()

# =========================
# Notlar / Örnek Kullanım
# =========================
# - Bu modül async olarak kullanılmalı.
# - Senkron bir yerden çağıracaksanız: asyncio.run(mesaj_isle("..."))
# - Seri port okuması gibi olaylar geldiğinde uygun yere await mesaj_isle(...) koyun.

# Örnek:
# if __name__ == "__main__":
#     async def demo():
#         # Burada motor/sensör mock’larını verip sistemi ayağa kaldırabilirsiniz.
#         oturum_baslat("sess-123", "user-42")
#         await mesaj_isle("oturum_var")
#         barkod_verisi_al("1923026353360")
#         await mesaj_isle("gsi")
#         await mesaj_isle("gso")
#         # ... vb.
#     asyncio.run(demo())
