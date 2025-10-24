# THREAD LIFECYCLE VE RECONNECTION SORUNLARI - Detaylı Analiz

**Tarih:** 23 Ekim 2025  
**Problem:** Program çalışırken USB kopma/bağlanma sonrası thread'ler başlamıyor, motor komutları gitmiyor  
**Kullanıcı Gözlemi:** "ctrl+c ile kesip python ana.py ile açınca düzgün çalışıyor ama çalışma sırasında kopma olduğunda birçok şey karışıyor"

---

## 🔴 LOG ANALİZİ - KRİTİK SORUNLAR

### Problem 1: İLK BAĞLANTI KOPMASINDA RECONNECTION BAŞLAMIYOR (6.1s timeout)

```log
13:28:14 - Motor I/O Error oluşuyor
❌ motor port erişim hatası: [Errno 5] Input/output error
INFO: Reconnection başlatıldı [motor]: I/O Error
INFO: motor bağlantı hatası yönetimi
INFO: motor write thread'i bekleniyor...
INFO: motor write thread çıkıyor
INFO: USB reset deneniyor: /dev/ttyUSB2
WARNING: USB reset başarısız
INFO: Thread kaydedildi: motor_reconnect
INFO: motor yeniden bağlanma 1/10

# BURADA PORT ARAMA BAŞLIYOR
INFO: Port arama lock alındı
INFO: Kart arama başlatıldı (Deneme 1/3)
[USB autosuspend kapatma işlemleri - 23 saniye]
INFO: Tüm açık portlar kapatılıyor...
INFO: /dev/ttyUSB3 portu kapatıldı
INFO: Kart arama başlatıldı - Hedef: motor
INFO: 1 uyumlu port bulundu
INFO: /dev/ttyUSB3 taranıyor...

# PORT SAĞLIK SERVİSİ PARALEL ÇALIŞIYOR
📡 [PORT-SAĞLIK] MOTOR → PING gönderiliyor...
⚠️ [MOTOR-PING] Reconnect devam ediyor - ping atlanıyor  # ✅ DOĞRU - reconnect devam ediyor
❌ [PORT-SAĞLIK] MOTOR → PONG alınamadı! (Başarısız: 1/3)

# YENİ PING DENEMELER
📡 [PORT-SAĞLIK] MOTOR → PING gönderiliyor...
⚠️ [MOTOR-PING] Reconnect devam ediyor - ping atlanıyor
❌ [PORT-SAĞLIK] MOTOR → PONG alınamadı! (Başarısız: 2/3)
⚠️ [PORT-SAĞLIK] MOTOR → UYARI! Son pong: 6.1s önce  # ❌ SORUN: Son pong 6s önce!

# PORT SAĞLIK SERVİSİ KART YENİDEN BAŞLATMA TETİKLEDİ
🔧 [PORT-SAĞLIK] MOTOR kartı ping başarısız - yeniden başlatılıyor
🔄 [PORT-SAĞLIK] Kartlar yeniden başlatılıyor...
📋 [PORT-SAĞLIK] Sıralama: SENSOR ÖNCE, MOTOR SONRA
  ⏳ Motor kartı boot süreci için ek bekleme...
  🔧 Motor kartı: /dev/ttyUSB2

# PORT AÇMA HATASI
❌ motor port hatası: [Errno 2] No such file or directory: '/dev/ttyUSB2'
  ❌ Motor portu açılamadı!

# PORT_YONETICI TARAMADA HATA
⏳ [PORT-SAĞLIK] Kartların stabilizasyonu için 5 saniye bekleniyor...
WARNING: /dev/ttyUSB3 - Tanımlanamayan cihaz
INFO: /dev/ttyUSB3 portu kapatıldı
❌ Tanımlı hiçbir kart bulunamadı!
WARNING: İlk denemede başarısız (basarili=False, kritik_eksik=False)
WARNING: USB reset ile tekrar deneniyor (2 deneme kaldı)
```

**SORUN TESPİTİ:**
1. ❌ **Motor reconnection başlıyor AMA port arama uzun sürüyor (23s USB autosuspend işlemleri)**
2. ❌ **Bu sırada port_saglik_servisi PARALEL çalışıyor ve ping atıyor**
3. ❌ **6 saniye sonra port_saglik_servisi "ping başarısız" diyor ve KART YENİDEN BAŞLATMA tetikliyor**
4. ❌ **Bu esnada zaten çalışan reconnection worker ile çakışma oluyor**
5. ❌ **Port_saglik_servisi `/dev/ttyUSB2` portu açmaya çalışıyor ama o port ARTIKyok** (USB3'e geçmiş)
6. ❌ **Birden fazla thread aynı anda port arıyor ve birbirini engelliyor**

---

### Problem 2: USB RESET SONRASI THREAD BAŞLAMIYOR

```log
13:29:03 - USB Reset tamamlandı, portlar bulundu
INFO: Agresif USB reset başarılı, portlar yeniden taranacak...
INFO: UYKU MODU AKTİF
INFO: Reset operasyonu bitti: reset_1761215303 (başarılı)
INFO: Reset cooldown deaktif edildi
INFO: Port arama lock bırakıldı
✅ [PORT-SAĞLIK] Kartlar hazır - ping/pong testi başlayacak!

# SENSOR PING BAŞARIYOR
📡 [PORT-SAĞLIK] SENSOR → PING gönderiliyor...
INFO: sensor write thread - komut gönderiliyor: ping
✅ sensor write thread - komut gönderildi: ping
❌ [SENSOR-PING] Timeout! PONG gelmedi (0.602s)  # ❌ TIMEOUT!

# SENSOR I/O ERROR
❌ sensor port erişim hatası: [Errno 5] Input/output error
WARNING: sensor reconnection zaten devam ediyor veya sistem meşgul
INFO: sensor USB reset devam ediyor, reconnection atlanıyor

# USB RESET SONRASI PORTLAR YENİDEN BULUNDU
✅ SENSOR kartı /dev/ttyUSB1 portunda bulundu
✅ MOTOR kartı /dev/ttyUSB0 portunda bulundu
INFO: sensor port açıldı: /dev/ttyUSB1
INFO: sensor porta bağlandı: /dev/ttyUSB1
INFO: sensor write thread başlatıldı
INFO: sensor thread'leri çalışıyor - Listen: True, Write: True
✅ sensor yeniden bağlandı
✅ sensor reconnection tamamlandı - thread'ler çalışıyor

# SENSOR ÇALIŞIYOR AMA MOTOR HAKKINDA HİÇBİR LOG YOK!
# Motor thread'leri başladı mı? HAYIR!
```

**SORUN TESPİTİ:**
1. ❌ **USB reset sonrası portlar bulundu: SENSOR→/dev/ttyUSB1, MOTOR→/dev/ttyUSB0**
2. ❌ **Sensor kartı başarıyla bağlandı ve thread'ler çalışıyor**
3. ❌ **MOTOR KARTI HAKKINDA HİÇBİR LOG YOK!**
4. ❌ **Motor thread'leri hiç başlatılmamış**
5. ❌ **Port_yonetici.baglan() sadece port buldu ama reconnection worker çağrılmadı**

---

### Problem 3: BAKIM MODUNA GİRİNCE MOTOR KOMUTU GÖNDERİLEMİYOR

```log
13:30:37 - Bakım moduna girildi
[WebSocket] Client bağlantıyı kapattı
Durum değiştiriliyor: oturum_yok -> bakim
[Bakım Modu] Bakım moduna giriliyor...

# SENSOR KOMUTU GÖNDERİLİYOR
INFO: SENSOR: Komut gönderiliyor: msud
✅ Üst kapak durum sorgusu gönderildi
INFO: sensor write thread - komut gönderiliyor: ust_kilit_durum_sorgula
❌ sensor yazma hatası: write failed: [Errno 5] Input/output error  # ❌ I/O ERROR!

# SENSOR RECONNECTION BAŞLADI
INFO: Reconnection başlatıldı [sensor]: I/O Error
INFO: sensor bağlantı hatası yönetimi
INFO: sensor write thread bitti

# SENSOR BAŞARIYLA YENİDEN BAĞLANDI
✅ SENSOR kartı /dev/ttyUSB1 portunda bulundu
✅ MOTOR kartı /dev/ttyUSB0 portunda bulundu  # ❌ MOTOR BULUNDU AMA BAĞLANMADI!
INFO: sensor port açıldı: /dev/ttyUSB1
INFO: sensor thread'leri çalışıyor - Listen: True, Write: True
✅ sensor yeniden bağlandı

# SENSOR ÇALIŞIYOR VE MESAJLAR GELİYOR
🔔 [SENSOR] MESAJ: do#c:5#p:4#m:39
🔔 [SENSOR] MESAJ: g/msap

# MOTOR HAKKINDA HİÇBİR LOG YOK!
# Motor thread'leri başlamadı mı? EVET, BAŞLAMADI!
```

**SORUN TESPİTİ:**
1. ❌ **Sensor kartı I/O Error verdi ve başarıyla yeniden bağlandı**
2. ❌ **Port arama sırasında MOTOR kartı da bulundu (/dev/ttyUSB0)**
3. ❌ **Ama motor kartı reconnection worker'ı çağrılmadı**
4. ❌ **Motor thread'leri başlatılmadı**
5. ❌ **Motor komutları write thread olmadığı için gönderilemiyor**

---

## 🔍 KÖK NEDEN ANALİZİ

### Neden 1: PORT_SAGLIK_SERVISI ve RECONNECTION WORKER ÇATIŞMASI

**Akış:**
```
1. Motor I/O Error oluşur
   └─> _handle_connection_error() çağrılır
       └─> running = False (thread'leri durdur)
       └─> Port kapat
       └─> _reconnect_worker() başlat
           └─> _auto_find_port() çağrılır
               └─> port_yoneticisi.baglan() (LOCK ALIR)
                   └─> USB autosuspend kapatma (23 saniye!)
                   └─> Port temizleme
                   └─> Port tarama
                   
2. PARALEL OLARAK port_saglik_servisi çalışıyor
   └─> _kart_ping_kontrol() her 3 saniyede
       └─> Motor ping atıyor
       └─> 6 saniye sonra "ping başarısız"
       └─> _kartlari_yeniden_baslat() tetikleniyor
           └─> motor.dinlemeyi_durdur() (running = False)
           └─> motor.port_adi = "/dev/ttyUSB2" (ESKİ PORT!)
           └─> motor.portu_ac() (PORT BULUNAMIYOR!)

3. SONUÇ: İki thread çakışıyor
   ❌ reconnection_worker zaten port arıyor
   ❌ port_saglik_servisi AYNI ANDA kart yeniden başlatıyor
   ❌ Birbirlerini engelliyor ve hiçbiri başarılı olmuyor
```

**ÇÖZÜM:**
- ✅ **port_saglik_servisi reconnection devam ederken BEKLEMELI**
- ✅ **Reconnection timeout kontrolü daha uzun olmalı (minimum 30s)**
- ✅ **Port arama sırasında port_saglik_servisi DURMALI**

### Neden 2: PORT_YONETICI.BAGLAN() SADECE PORT BULUYOR, RECONNECTION BAŞLATMIYOR

**Sorun:**
```python
# port_yonetici.baglan() çağrıldığında
basarili, mesaj, portlar = self.port_yonetici.baglan()

# Bu fonksiyon sadece portları BULUYOR:
# {"motor": "/dev/ttyUSB0", "sensor": "/dev/ttyUSB1"}

# AMA:
# - motor_karti._auto_find_port() ÇAĞRILMIYOR
# - motor.dinlemeyi_baslat() ÇAĞRILMIYOR
# - motor thread'leri BAŞLATILMIYOR

# SONUÇ:
# - Portlar bulundu ama kartlar bağlanmadı
# - Thread'ler başlatılmadı
# - Komutlar gönderilemiyor
```

**KÖK NEDEN:**
```python
# _reconnect_worker() içinde:
if self._auto_find_port():  # Bu fonksiyon başarılı
    # Port bulundu ve bağlandı
    # Thread'ler başlatıldı
    system_state.finish_reconnection(self.cihaz_adi, True)
    return

# AMA port_yonetici.baglan() doğrudan çağrıldığında:
basarili, mesaj, portlar = port_yonetici.baglan()
# Bu sadece port listesi döndürüyor
# _auto_find_port() ÇAĞRILMIYOR!
# dinlemeyi_baslat() ÇAĞRILMIYOR!
```

**ÇÖZÜM:**
- ❌ **port_yonetici.baglan() fonksiyonu YANLIŞ kullanılıyor**
- ✅ **Her kart için _auto_find_port() veya _try_connect_to_port() çağrılmalı**
- ✅ **Port bulunduktan sonra thread'ler başlatılmalı**

### Neden 3: THREAD LIFECYCLE KONTROLÜ EKSİK

**Sorun:**
```python
# dinlemeyi_baslat() çağrıldığında:
def dinlemeyi_baslat(self):
    # Port kontrolü
    with self._port_lock:
        if not self.seri_nesnesi or not self.seri_nesnesi.is_open:
            return  # Port açık değil
        
        # Thread'ler zaten çalışıyorsa
        if self.running and self.listen_thread and ... and self.write_thread ...:
            return  # Zaten çalışıyor
        
        # Eski thread'leri temizle
        if self.running:
            self.running = False
            # Lock bırak
    
    # Thread başlat
    ...

# SORUN:
# 1. Eğer önceki thread'ler crash olduysa?
#    - self.running = True ama thread'ler ölü
#    - Yeniden başlatma yapılmıyor
#
# 2. Eğer port değiştiyse?
#    - Thread'ler eski portu dinliyor
#    - Yeni port için thread başlatılmıyor
#
# 3. Eğer reconnection sırasında çağrıldıysa?
#    - Zaten reconnection devam ediyor
#    - Thread'ler çakışıyor
```

**ÇÖZÜM:**
- ✅ **Thread durumu kontrol edilmeli (is_alive() check)**
- ✅ **Port değişikliği kontrol edilmeli**
- ✅ **Reconnection durumu kontrol edilmeli**
- ✅ **Zombie thread'ler temizlenmeli**

---

## 🛠️ ÇÖZÜM ÖNERİLERİ

### Çözüm 1: PORT_SAGLIK_SERVISI - RECONNECTION BEKLEME MEKANİZMASI

**Değişiklik:** `port_saglik_servisi.py::_kart_ping_kontrol()`

```python
def _kart_ping_kontrol(self, kart, kart_adi: str):
    """Kart ping kontrolü - RECONNECTION BYPASS"""
    durum = self.kart_durumlari[kart_adi]
    
    # ✅ RECONNECTION DEVAM EDİYORSA PING ATMA
    if system_state.is_card_reconnecting(kart_adi):
        # Reconnection ne kadar süredir devam ediyor?
        reconnect_duration = system_state.get_reconnection_duration(kart_adi)
        
        if reconnect_duration < 30:  # 30 saniyeden azsa bekle
            print(f"⏳ [PORT-SAĞLIK] {kart_adi.upper()} → Reconnection devam ediyor ({reconnect_duration:.1f}s)")
            return  # Ping atma, bekle
        else:
            # 30 saniyeden fazla sürüyorsa uyarı ver ama müdahale etme
            print(f"⚠️ [PORT-SAĞLIK] {kart_adi.upper()} → Reconnection uzun sürüyor ({reconnect_duration:.1f}s)")
            # Yine de ping atma, reconnection worker devam etsin
            return
    
    # Normal ping kontrolü devam eder...
```

### Çözüm 2: PORT_YONETICI.BAGLAN() SONRASI KART BAĞLAMA

**Değişiklik:** `port_saglik_servisi.py::_kartlari_yeniden_baslat()`

```python
def _kartlari_yeniden_baslat(self, portlar: dict):
    """Kartları yeniden başlat - DÜZELTİLMİŞ"""
    try:
        print("🔄 [PORT-SAĞLIK] Kartlar yeniden başlatılıyor...")
        
        # ÖNEMLİ: Bu fonksiyon SADECE port_yonetici.baglan() çağrıldıktan SONRA kullanılmamalı
        # Bunun yerine her kart için reconnection tetiklemeliyiz
        
        # SENSOR KARTI
        if "sensor" in portlar:
            print(f"  🔧 Sensor kartı reconnection tetikleniyor...")
            # Önce mevcut thread'leri temizle
            self.sensor_karti.dinlemeyi_durdur()
            time.sleep(0.5)
            
            # Port ata
            self.sensor_karti.port_adi = portlar["sensor"]
            
            # ✅ _auto_find_port() yerine direkt portu aç ve bağlan
            if self.sensor_karti._try_connect_to_port():
                print(f"  ✅ Sensor kartı bağlandı: {portlar['sensor']}")
            else:
                print(f"  ❌ Sensor kartı bağlanamadı!")
        
        # MOTOR KARTI
        if "motor" in portlar:
            print(f"  🔧 Motor kartı reconnection tetikleniyor...")
            # Önce mevcut thread'leri temizle
            self.motor_karti.dinlemeyi_durdur()
            time.sleep(0.5)
            
            # Port ata
            self.motor_karti.port_adi = portlar["motor"]
            
            # ✅ _auto_find_port() yerine direkt portu aç ve bağlan
            if self.motor_karti._try_connect_to_port():
                print(f"  ✅ Motor kartı bağlandı: {portlar['motor']}")
                
                # Motor komutları gönder
                time.sleep(1)
                self.motor_karti.parametre_gonder()
                time.sleep(0.5)
                self.motor_karti.reset()
                time.sleep(2)
                
                print(f"  ✅ Motor kartı hazır")
            else:
                print(f"  ❌ Motor kartı bağlanamadı!")
        
        # Durumları sıfırla
        self._durumlari_sifirla()
        print(f"✅ [PORT-SAĞLIK] Kartlar hazır!")
        
    except Exception as e:
        print(f"❌ [PORT-SAĞLIK] Hata: {e}")
        log_error(f"Kart yeniden başlatma hatası: {e}")
```

### Çözüm 3: THREAD LIFECYCLE - ZOMBIE THREAD TEMİZLİĞİ

**Değişiklik:** `motor_karti.py::dinlemeyi_baslat()`

```python
def dinlemeyi_baslat(self):
    """Thread başlatma - ZOMBIE THREAD TEMİZLİĞİ"""
    # Port kontrolü
    with self._port_lock:
        if not self.seri_nesnesi or not self.seri_nesnesi.is_open:
            log_warning(f"{self.cihaz_adi} port açık değil - thread başlatılamıyor")
            return
        
        # ✅ ZOMBIE THREAD KONTROLÜ
        # Thread'ler "çalışıyor" görünüyorsa ama gerçekte is_alive() False ise temizle
        threads_alive = (
            (self.listen_thread and self.listen_thread.is_alive()) and
            (self.write_thread and self.write_thread.is_alive())
        )
        
        if self.running and not threads_alive:
            # Zombie thread durumu - temizle
            log_warning(f"{self.cihaz_adi} zombie thread tespit edildi - temizleniyor")
            self.running = False
            self._cleanup_threads()
            time.sleep(0.5)
        
        # Thread'ler zaten çalışıyorsa (gerçekten alive)
        if self.running and threads_alive:
            log_warning(f"{self.cihaz_adi} thread'ler zaten çalışıyor")
            return
        
        # Eski thread'leri temizle
        if self.running:
            log_system(f"{self.cihaz_adi} eski thread'leri temizleniyor...")
            self.running = False
    
    # Lock dışında temizlik ve başlatma...
    # (Mevcut kod devam eder)
```

### Çözüm 4: SYSTEM_STATE_MANAGER - RECONNECTION DURATION TRACKING

**Ekleme:** `system_state_manager.py`

```python
class SystemStateManager:
    def __init__(self):
        # ... mevcut kod ...
        
        # Reconnection timing
        self._reconnection_start_times: Dict[str, float] = {}
    
    def start_reconnection(self, card_name: str, reason: str = "") -> bool:
        """Kart reconnection başlat"""
        if not self.can_start_reconnection(card_name):
            return False
        
        with self._reconnect_lock:
            self._reconnecting_cards.add(card_name)
            self._reconnection_start_times[card_name] = time.time()  # ✅ BAŞLANGIÇ ZAMANI
            self.set_card_state(card_name, CardState.RECONNECTING, reason)
            
            log_system(f"Reconnection başlatıldı [{card_name}]: {reason}")
            return True
    
    def finish_reconnection(self, card_name: str, success: bool) -> bool:
        """Kart reconnection bitir"""
        with self._reconnect_lock:
            if card_name not in self._reconnecting_cards:
                return False
            
            self._reconnecting_cards.remove(card_name)
            
            # ✅ BAŞLANGIÇ ZAMANINI TEMİZLE
            if card_name in self._reconnection_start_times:
                del self._reconnection_start_times[card_name]
            
            # ... mevcut kod ...
    
    def get_reconnection_duration(self, card_name: str) -> float:
        """Reconnection ne kadar süredir devam ediyor?"""
        with self._reconnect_lock:
            if card_name not in self._reconnecting_cards:
                return 0.0
            
            start_time = self._reconnection_start_times.get(card_name, time.time())
            return time.time() - start_time
```

---

## 📋 UYGULAMA PLANI

### Adım 1: system_state_manager.py - Reconnection Duration
- ✅ `_reconnection_start_times` dictionary ekle
- ✅ `get_reconnection_duration()` metodu ekle
- ✅ `start_reconnection()` başlangıç zamanını kaydet
- ✅ `finish_reconnection()` zamanı temizle

### Adım 2: motor_karti.py ve sensor_karti.py - Zombie Thread Temizliği
- ✅ `dinlemeyi_baslat()` içinde `is_alive()` kontrolü ekle
- ✅ Zombie thread tespit edilirse temizle ve yeniden başlat
- ✅ Port değişikliği kontrolü ekle

### Adım 3: port_saglik_servisi.py - Reconnection Bypass
- ✅ `_kart_ping_kontrol()` içinde reconnection duration kontrolü
- ✅ 30 saniyeden az sürüyorsa ping atma
- ✅ `_kartlari_yeniden_baslat()` içinde `_try_connect_to_port()` kullan

### Adım 4: port_yonetici.py - Port Bulma İyileştirme
- ⚠️ **Dikkat:** Bu dosyada büyük değişiklik yapmayın
- ✅ Port bulma başarılı olsa bile kart bağlantısı ayrı yapılmalı

---

## 🎯 BEKLENEN SONUÇ

### Senaryo 1: USB Kopma Sırasında
```
1. Motor I/O Error oluşur
2. _handle_connection_error() çağrılır
3. running = False, thread'ler durdurulur
4. Port kapatılır
5. _reconnect_worker() başlatılır
6. Port arama başlar (lock alır)
7. ✅ Port_saglik_servisi reconnection devam ettiğini görür
8. ✅ 30 saniye bekler, ping atmaz
9. Port bulunur ve bağlanır
10. Thread'ler başlatılır
11. ✅ Motor komutları gönderilir
12. ✅ Sistem normale döner
```

### Senaryo 2: USB Reset Sonrası
```
1. USB reset tamamlanır
2. Portlar yeniden oluşur: /dev/ttyUSB0, /dev/ttyUSB1
3. Port_yonetici.baglan() portları bulur
4. ✅ Her kart için _try_connect_to_port() çağrılır
5. ✅ Portlar açılır
6. ✅ Thread'ler başlatılır
7. ✅ Motor ve sensor komutları gönderilir
8. ✅ Sistem normale döner
```

### Senaryo 3: Zombie Thread Durumu
```
1. Thread'ler crash olur ama running = True kalır
2. dinlemeyi_baslat() çağrılır
3. ✅ is_alive() kontrolü False döner
4. ✅ Zombie thread tespit edilir
5. ✅ Thread'ler temizlenir
6. ✅ Yeni thread'ler başlatılır
7. ✅ Sistem normale döner
```

---

## ⚠️ DİKKAT EDİLMESİ GEREKENLER

### 1. Port Arama Lock'u
- ❌ **Port arama sırasında port_saglik_servisi PING ATMAMALI**
- ✅ **Lock alındığında reconnection devam ediyor demektir**
- ✅ **30 saniye minimum bekleme süresi**

### 2. Thread Lifecycle
- ❌ **dinlemeyi_baslat() içinde LOCK İÇİNDE thread başlatma**
- ✅ **Lock dışında thread başlat (deadlock önleme)**
- ✅ **is_alive() kontrolü yap (zombie thread önleme)**

### 3. Port Değişikliği
- ❌ **Eski port adıyla portu açmaya çalışma**
- ✅ **Port bulunduktan sonra port_adi güncelle**
- ✅ **_try_connect_to_port() ile direkt bağlan**

### 4. Reconnection Coordination
- ❌ **Birden fazla thread aynı anda reconnection yapmasın**
- ✅ **system_state_manager ile koordine et**
- ✅ **Reconnection devam ederken yeni reconnection başlatma**

---

**NOT:** Bu çözümler uygulandığında sistem stabil şekilde çalışmalı. Kullanıcı "ctrl+c ile kesip açınca düzgün çalışıyor" dediği için donanımsal bir sorun yok. Sorun tamamen thread lifecycle ve reconnection koordinasyonundan kaynaklanıyor.
