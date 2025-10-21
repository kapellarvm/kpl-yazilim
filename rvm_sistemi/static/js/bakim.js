// RVM Bakım Paneli v2 - JavaScript

// Translate özelliğini kapat
document.documentElement.setAttribute('translate', 'no');
document.documentElement.setAttribute('class', 'notranslate');

// Global değişkenler
let bakimModuAktif = false;
let isTesting = false;
let stopLoop = true;
let cardConnectionTimeouts = {};
let websocket = null;
let isCalibrating = false;

// ⏰ ZAMAN AYARLARI SABİTLERİ
const TIMING_CONFIG = {
    // Kuyruk işleme gecikmeleri (ms)
    QUEUE_DELAYS: {
        SENSOR: 800,      // Sensör kuyruğu gecikmesi
        MOTOR: 600,       // Motor kuyruğu gecikmesi
        SYSTEM: 400       // Sistem kuyruğu gecikmesi
    },
    
    // Gömülü sisteme komut gönderme aralıkları (ms)
    EMBEDDED_COMMANDS: {
        SDS_SENSOR_INTERVAL: 3200,        // SDS sensör sorgulama (3 saniye)
        DOLULUK_INTERVAL: 3000,           // Doluluk oranı sorgulama (5 saniye)
        PING_INTERVAL: 3000,              // Ping işlemi (3 saniye)
        WEIGHT_MEASUREMENT_INTERVAL: 500, // Ağırlık ölçümü (500ms)
        SENSOR_UPDATE_INTERVAL: 1000,     // Sensör değer güncelleme (1 saniye)
        GENERAL_STATUS_INTERVAL: 5000     // Genel durum güncelleme (5 saniye)
    },
    
    // API timeout süreleri (ms)
    API_TIMEOUTS: {
        PING_TIMEOUT: 3000,               // Ping timeout (3 saniye)
        DEFAULT_TIMEOUT: 10000,           // Varsayılan API timeout (10 saniye)
        QUICK_TIMEOUT: 5000               // Hızlı işlemler için timeout (5 saniye)
    },
    
    // UI güncelleme aralıkları (ms)
    UI_UPDATES: {
        FILL_LEVEL_TRANSITION: 300,       // Doluluk bar geçiş süresi (300ms)
        COLOR_TRANSITION: 200,            // Renk geçiş süresi (200ms)
        ANIMATION_DURATION: 2000,         // Genel animasyon süresi (2 saniye)
        MESSAGE_DISPLAY_TIME: 3000        // Mesaj gösterim süresi (3 saniye)
    },
    
    // Retry ve güvenlik ayarları
    SAFETY: {
        MAX_RETRIES: 3,                   // Maksimum deneme sayısı
        RETRY_DELAY: 1000,                // Retry gecikmesi (1 saniye)
        TARE_WAIT_TIME: 3000,             // Tare bekleme süresi (3 saniye)
        CALIBRATION_TIMEOUT: 10000        // Kalibrasyon timeout (10 saniye)
    }
};

// Yeni temiz kuyruk sistemi
let sensorQueue = [];
let motorQueue = [];
let systemQueue = [];
let isPingInProgress = false;

// Temiz kuyruk yöneticisi sınıfı
class CardQueueManager {
    constructor(cardType) {
        this.cardType = cardType;
        this.queue = [];
        this.isProcessing = false;
        this.delay = cardType === 'sensor' ? TIMING_CONFIG.QUEUE_DELAYS.SENSOR : 
                    cardType === 'motor' ? TIMING_CONFIG.QUEUE_DELAYS.MOTOR : 
                    TIMING_CONFIG.QUEUE_DELAYS.SYSTEM;
        this.maxRetries = TIMING_CONFIG.SAFETY.MAX_RETRIES;
    }
    
    async addOperation(operation, priority = false) {
        const operationData = {
            id: Date.now() + Math.random(),
            operation: operation,
            priority: priority,
            retries: 0,
            timestamp: Date.now()
        };
        
        if (priority) {
            this.queue.unshift(operationData);
        } else {
            this.queue.push(operationData);
        }
        
        this.processQueue();
    }
    
    async processQueue() {
        if (this.isProcessing || this.queue.length === 0) return;
        
        this.isProcessing = true;
        console.log(`🔄 ${this.cardType.toUpperCase()} kuyruğu işleniyor (${this.queue.length} işlem)`);
        
        while (this.queue.length > 0) {
            const operationData = this.queue.shift();
            
            try {
                await operationData.operation();
                console.log(`✅ ${this.cardType.toUpperCase()} işlemi tamamlandı`);
                
                // İşlemler arası güvenlik beklemesi
                await this.sleep(this.delay);
                
            } catch (error) {
                console.error(`❌ ${this.cardType.toUpperCase()} kuyruk hatası:`, error);
                
                // Retry mekanizması
                if (operationData.retries < this.maxRetries) {
                    operationData.retries++;
                    console.log(`🔄 ${this.cardType.toUpperCase()} işlemi tekrar deneniyor (${operationData.retries}/${this.maxRetries})`);
                    this.queue.unshift(operationData);
                    await this.sleep(TIMING_CONFIG.SAFETY.RETRY_DELAY); // Retry için bekle
                } else {
                    console.error(`💥 ${this.cardType.toUpperCase()} işlemi başarısız, atlanıyor`);
                }
            }
        }
        
        this.isProcessing = false;
        console.log(`🏁 ${this.cardType.toUpperCase()} kuyruğu tamamlandı`);
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    getQueueStatus() {
        return {
            cardType: this.cardType,
            queueLength: this.queue.length,
            isProcessing: this.isProcessing,
            delay: this.delay
        };
    }
}

// Kuyruk yöneticilerini oluştur
const sensorQueueManager = new CardQueueManager('sensor');
const motorQueueManager = new CardQueueManager('motor');
const systemQueueManager = new CardQueueManager('system');

// Durum yöneticisi
const durumYoneticisi = {
    durum: 'oturum_yok',
    sensorKartBagli: false,
    motorKartBagli: false
};

// API Base URL
const API_BASE = '/api/v1';

// Icon'lar
const successIcon = `<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`;
const errorIcon = `<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`;
const loadingIcon = `<div class="w-5 h-5 border-t-2 border-blue-500 border-solid rounded-full animate-spin"></div>`;

// Utility fonksiyonları
function showMessage(text, isError = false) {
    // Mevcut mesaj sistemini kullan
    console.log(isError ? 'ERROR:' : 'SUCCESS:', text);
}

// Uyarı ekranı gösterme fonksiyonu
async function uyariEkraniGoster() {
    try {
        console.log('⚠️ Modbus Ready uyarı ekranı gösteriliyor...');
        
        const uyariMesaji = "⚠️ ACİL DURUM BUTONU AKTİF<br>Güvenlik nedeniyle tüm motorlar durduruldu.";
        
        const response = await fetch(`${API_BASE}/uyari/goster`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                mesaj: uyariMesaji,
                sure: 0,  // 10 saniye göster
                suresiz: false
            })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            console.log('✅ Uyarı ekranı başarıyla gösterildi');
        } else {
            console.warn('⚠️ Uyarı ekranı gösterilemedi:', data.message);
        }
    } catch (error) {
        console.error('❌ Uyarı ekranı hatası:', error);
    }
}

function ozellikAktifDegil() {
    showMessage('Bu özellik henüz aktif değil', true);
}

// Bakım modu kontrolü
async function bakimModuToggle() {
    const yeniDurum = !bakimModuAktif;
    
    try {
        const response = await fetch(`${API_BASE}/bakim/modu-ayarla`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                aktif: yeniDurum
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Sadece başarılı olduğunda durumu güncelle
            bakimModuAktif = yeniDurum;
            
            const btn = document.getElementById('bakimModBtn');
            if (bakimModuAktif) {
                btn.textContent = '⚙ Bakım Modu: Aktif';
                btn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                showMessage('✓ ' + data.message);
                // Bakım modu aktifken motorları iptal et (güvenlik için)
                motorlariIptalEt();
                // Bakım modu aktifken periyodik güncellemeleri başlat
                 startPeriodicUpdates();
                 // Emniyet sensörü durumlarını sorgula - 1.5 saniye sonra
                 setTimeout(() => queryEmniySensorDurum(), 1000);
            } else {
                btn.textContent = '⚙ Bakım Modu: Pasif';
                btn.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
                showMessage('✓ ' + data.message);
                // Bakım modu pasifken periyodik güncellemeleri durdur
                stopPeriodicUpdates();
                // Tüm işlemleri durdur (güvenlik için)
                stopAllOperations();
            }
            
            // Butonları güncelle
            butonlariGuncelle();
            
            // Durum güncellemesini tetikle
            setTimeout(sistemDurumunuGuncelle, 500);
        } else {
            showMessage('✗ ' + data.message, true);
        }
    } catch (error) {
        showMessage('Bağlantı hatası: ' + error.message, true);
    }
}

// Sistem durumu güncelleme
async function sistemDurumunuGuncelle() {
    try {
        const response = await fetch(`${API_BASE}/sistem/durum`);
        const data = await response.json();
        
        const motorStatus = document.getElementById('motor-card-status');
        const sensorStatus = document.getElementById('sensor-card-status');
        
        if (motorStatus) {
            if (data.motor_baglanti) {
                motorStatus.innerHTML = `${successIcon}<span class="text-green-400 font-semibold">Bağlı</span>`;
            } else {
                motorStatus.innerHTML = `${errorIcon}<span class="text-red-400 font-semibold">Bağlantı Yok</span>`;
            }
        }
        
        if (sensorStatus) {
            if (data.sensor_baglanti) {
                sensorStatus.innerHTML = `${successIcon}<span class="text-green-400 font-semibold">Bağlı</span>`;
            } else {
                sensorStatus.innerHTML = `${errorIcon}<span class="text-red-400 font-semibold">Bağlantı Yok</span>`;
            }
        }
        
        // Sekme başlıklarını güncelle
        updateTabTitles(data);
        
        // Bağlantı durumlarını güncelle
        updateConnectionStatus(data);
        
        // Bakım modu durumunu güncelle
        if (data.durum === 'bakim' && !bakimModuAktif) {
            bakimModuAktif = true;
            const btn = document.getElementById('bakimModBtn');
            if (btn) {
                btn.textContent = '⚙ Bakım Modu: Aktif';
                btn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                butonlariGuncelle();
            }
            // Bakım modu aktifken tüm güncellemeleri başlat
            startStatusUpdates();
            startPeriodicUpdates();
            startSdsUpdates();
            startDolulukUpdates();
        } else if (data.durum !== 'bakim' && bakimModuAktif) {
            bakimModuAktif = false;
            const btn = document.getElementById('bakimModBtn');
            if (btn) {
                btn.textContent = '⚙ Bakım Modu: Pasif';
                btn.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
                butonlariGuncelle();
            }
            // Bakım modu pasifken tüm güncellemeleri durdur
            stopStatusUpdates();
            stopPeriodicUpdates();
            // WebSocket bağlantısını kapat
            disconnectWebSocket();
            // Durum göstergelerini gri yap
            setStatusIndicatorsGray();
        }
        
        // Durum yöneticisini güncelle
        durumYoneticisi.durum = data.durum;
        durumYoneticisi.sensorKartBagli = data.sensor_baglanti;
        durumYoneticisi.motorKartBagli = data.motor_baglanti;
        
    } catch (error) {
        console.error('Durum güncellemesi başarısız:', error);
    }
}

// Sekme başlıklarını güncelle
function updateTabTitles(data) {
    const sensorTab = document.getElementById('tab-btn-sensors');
    const motorTab = document.getElementById('tab-btn-motors');
    
    if (sensorTab) {
        if (data.sensor_baglanti) {
            sensorTab.innerHTML = `Sensör Kartı <span class="text-green-400">●</span>`;
        } else {
            sensorTab.innerHTML = `Sensör Kartı <span class="text-red-400">●</span>`;
        }
    }
    
    if (motorTab) {
        if (data.motor_baglanti) {
            motorTab.innerHTML = `Motor Kartı <span class="text-green-400">●</span>`;
        } else {
            motorTab.innerHTML = `Motor Kartı <span class="text-red-400">●</span>`;
        }
    }
}

// Bağlantı durumlarını güncelle
function updateConnectionStatus(data) {
    const sensorConnectionStatus = document.getElementById('sensor-connection-status');
    const motorConnectionStatus = document.getElementById('motor-connection-status');
    
    if (sensorConnectionStatus) {
        const dot = sensorConnectionStatus.querySelector('div');
        const text = sensorConnectionStatus.querySelector('span');
        
        if (data.sensor_baglanti) {
            dot.className = 'w-2 h-2 rounded-full bg-green-500';
            text.textContent = 'Bağlı';
            text.className = 'text-xs text-green-400';
        } else {
            dot.className = 'w-2 h-2 rounded-full bg-red-500';
            text.textContent = 'Bağlantı Yok';
            text.className = 'text-xs text-red-400';
        }
    }
    
    if (motorConnectionStatus) {
        const dot = motorConnectionStatus.querySelector('div');
        const text = motorConnectionStatus.querySelector('span');
        
        if (data.motor_baglanti) {
            dot.className = 'w-2 h-2 rounded-full bg-green-500';
            text.textContent = 'Bağlı';
            text.className = 'text-xs text-green-400';
        } else {
            dot.className = 'w-2 h-2 rounded-full bg-red-500';
            text.textContent = 'Bağlantı Yok';
            text.className = 'text-xs text-red-400';
        }
    }
}

// Butonları güncelle
function butonlariGuncelle() {
    const butonlar = document.querySelectorAll('button:not(#bakimModBtn):not(.reset-button):not(.tab)');
    const sliders = document.querySelectorAll('input[type="range"]');
    
    butonlar.forEach(btn => {
        if (bakimModuAktif) {
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
        } else {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
        }
    });
    
    sliders.forEach(slider => {
        if (bakimModuAktif) {
            slider.disabled = false;
            slider.style.opacity = '1';
        } else {
            slider.disabled = true;
            slider.style.opacity = '0.5';
        }
    });
}

// Sensör değerlerini güncelle
async function sensorDegerleriniGuncelle() {
    try {
        const response = await fetch(`${API_BASE}/sensor/son-deger`);
        const data = await response.json();
        
        if (data.status === 'success' && data.data) {
            const agirlikDeger = document.getElementById('loadcell-output');
            const sensorMesaj = document.getElementById('loadcell-message');
            
            if (agirlikDeger) {
                agirlikDeger.innerHTML = `${data.data.agirlik || 0} <span class="text-2xl">gr</span>`;
            }
            if (sensorMesaj) {
                sensorMesaj.textContent = data.data.mesaj || 'Henüz ölçüm yapılmadı';
            }
        }
    } catch (error) {
        console.error('Sensör değer güncellemesi başarısız:', error);
    }
}

// API çağrı fonksiyonları
async function motorKontrol(komut) {
    // Motor işlemini motor kuyruğuna ekle
    motorQueueManager.addOperation(async () => {
    try {
        const response = await fetch(`${API_BASE}/motor/${komut}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showMessage(data.message);
        } else {
            showMessage(data.message, true);
        }
    } catch (error) {
        showMessage('Bağlantı hatası: ' + error.message, true);
    }
    });
}

async function sensorKontrol(komut) {
    // Sensör işlemini sensör kuyruğuna ekle
    sensorQueueManager.addOperation(async () => {
    try {
        const response = await fetch(`${API_BASE}/sensor/${komut}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showMessage(data.message);
        } else {
            showMessage(data.message, true);
        }
    } catch (error) {
        showMessage('Bağlantı hatası: ' + error.message, true);
    }
    });
}

// Sistem reset
async function sistemReset() {
    if (!confirm('Sistemi resetlemek istediğinizden emin misiniz? Tüm bağlantılar kesilecek ve yeniden kurulacak.')) {
        return;
    }
    
    // Sistem işlemini sistem kuyruğuna ekle (yüksek öncelik)
    systemQueueManager.addOperation(async () => {
    try {
        showMessage('↻ Sistem resetleniyor...', false);
        const response = await fetch(`${API_BASE}/sistem/reset`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
                // Motor toggle'larını kapat
                turnOffMotorToggles();
            showMessage('✓ ' + data.message);
            setTimeout(sistemDurumunuGuncelle, 2000);
        } else {
            showMessage('✗ ' + data.message, true);
        }
    } catch (error) {
        showMessage('Bağlantı hatası: ' + error.message, true);
    }
    }, true); // Yüksek öncelik
}

// Sekme kontrolü
function setupTabControl() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            tabButtons.forEach(btn => {
                btn.classList.remove('active-tab');
                btn.classList.add('inactive-tab');
            });
            tabContents.forEach(content => {
                content.classList.add('hidden');
            });

            button.classList.add('active-tab');
            button.classList.remove('inactive-tab');
            const targetContentId = button.id.replace('btn', 'content');
            const targetContent = document.getElementById(targetContentId);
            if(targetContent) {
                targetContent.classList.remove('hidden');
            }
            
        });
    });
}

// Kart gizle/göster fonksiyonu
function setupToggle() {
    const chevronUpIcon = `<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" /></svg>`;
    const chevronDownIcon = `<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" /></svg>`;
    
    function setupToggle(toggleBtnId, gridId) {
        const toggleBtn = document.getElementById(toggleBtnId);
        const grid = document.getElementById(gridId);
        if (!toggleBtn || !grid) return;
        
        toggleBtn.innerHTML = chevronUpIcon;
        toggleBtn.addEventListener('click', () => {
            const isExpanded = grid.classList.contains('expanded');
            if (isExpanded) {
                grid.style.maxHeight = '0px';
                grid.style.marginTop = '0';
                grid.style.opacity = '0';
                toggleBtn.innerHTML = chevronDownIcon;
                grid.classList.remove('expanded');
            } else {
                grid.style.maxHeight = grid.scrollHeight + 'px';
                grid.style.marginTop = '1.5rem';
                grid.style.opacity = '1';
                toggleBtn.innerHTML = chevronUpIcon;
                grid.classList.add('expanded');
            }
        });
        
        grid.classList.add('expanded');
        grid.style.maxHeight = grid.scrollHeight + 'px';
        
        new ResizeObserver(() => {
            if (grid.classList.contains('expanded')) {
                grid.style.maxHeight = grid.scrollHeight + 'px';
            }
        }).observe(grid);
    }
    
    setupToggle('toggle-sensors-btn', 'sensor-details-grid');
    setupToggle('toggle-motors-btn', 'motor-details-grid');
}

// Sensör kontrolleri
function setupSensorControls() {
    // OPT Sensör Kontrolü
    function setupOptSensor(prefix) {
        const teachBtn = document.getElementById(`${prefix}-teach-btn`);
        const testBtn = document.getElementById(`${prefix}-test-btn`);
        const output = document.getElementById(`${prefix}-output`);
        const rays = document.getElementById(`${prefix}-rays`);
        const blocker = document.getElementById(`${prefix}-blocker`);

        if (teachBtn) {
            teachBtn.addEventListener('click', async () => {
                if (teachBtn.disabled) return;
                
                // Önce sensör durumunu kontrol et
                try {
                    const durumResponse = await fetch(`${API_BASE}/sensor/durum`);
                    const durumData = await durumResponse.json();
                    
                    if (!durumData.bagli) {
                        showMessage('✗ Sensör kartı bağlı değil. Sistem çalıştırılmamış olabilir.', false);
                        return;
                    }
                    
                    if (!durumData.saglikli) {
                        showMessage('✗ Sensör kartı sağlıksız. Bağlantı kontrol ediliyor...', false);
                        return;
                    }
                } catch (error) {
                    showMessage('✗ Sensör durum kontrolü başarısız: ' + error.message, false);
                    return;
                }
                
                teachBtn.disabled = true;
                if (testBtn) testBtn.disabled = true;
                
                if (rays) rays.classList.add('teaching-rays');
                teachBtn.innerText = "Öğreniyor...";
                
                try {
                    const response = await fetch(`${API_BASE}/sensor/teach`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        showMessage('✓ Giriş sensör teach tamamlandı', true);
                    } else {
                        showMessage('✗ Teach hatası: ' + data.message, false);
                    }
                } catch (error) {
                    showMessage('✗ Teach hatası: ' + error.message, false);
                    console.error('Teach API hatası:', error);
                } finally {
                    if (rays) rays.classList.remove('teaching-rays');
                    teachBtn.innerText = "Teach";
                    teachBtn.disabled = false;
                    if (testBtn) testBtn.disabled = false;
                }
            });
        }

        if (testBtn) {
            testBtn.addEventListener('click', () => {
                const result = Math.round(Math.random());
                if (output) output.innerText = result;
                if (blocker) {
                    if (result === 1) {
                        blocker.classList.remove('hidden');
                    } else {
                        blocker.classList.add('hidden');
                    }
                }
            });
        }
    }
    
    setupOptSensor('opt1009');
    setupOptSensor('diverter-opt');
    
    // Loadcell Kontrolü
    const measureBtn = document.getElementById('loadcell-measure-btn');
    const tareBtn = document.getElementById('loadcell-tare-btn');
    const loadcellVisual = document.getElementById('loadcell-visual');
    const loadcellOutput = document.getElementById('loadcell-output');
    const loadcellMessage = document.getElementById('loadcell-message');
    
    // Ağırlık ölçüm timer'ı
    let agirlikOlcTimer = null;
    let agirlikOlcAktif = false;

    if (measureBtn) {
        measureBtn.addEventListener('click', async () => {
            if (measureBtn.disabled) return;
            
            // Önce sensör durumunu kontrol et
            try {
                const durumResponse = await fetch(`${API_BASE}/sensor/durum`);
                const durumData = await durumResponse.json();
                
                if (!durumData.bagli) {
                    showMessage('✗ Sensör kartı bağlı değil. Sistem çalıştırılmamış olabilir.', false);
                    return;
                }
                
                if (!durumData.saglikli) {
                    showMessage('✗ Sensör kartı sağlıksız. Bağlantı kontrol ediliyor...', false);
                    return;
                }
            } catch (error) {
                showMessage('✗ Sensör durum kontrolü başarısız: ' + error.message, false);
                return;
            }
            
            if (agirlikOlcAktif) {
                // Eğer zaten çalışıyorsa durdur
                agirlikOlcDurdur();
                measureBtn.textContent = 'Ağırlık Ölç';
                measureBtn.classList.remove('bg-red-600', 'hover:bg-red-700');
                measureBtn.classList.add('bg-blue-600', 'hover:bg-blue-700');
                return;
            }
            
            if (tareBtn) tareBtn.disabled = true;
            measureBtn.disabled = true;
            if (loadcellMessage) loadcellMessage.innerText = 'Ağırlık ölçümü başlatılıyor...';
            if (loadcellVisual) loadcellVisual.classList.add('measuring');
            
            try {
                // İlk komutu gönder
                const response = await fetch(`${API_BASE}/sensor/agirlik-olc`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Sürekli ölçümü başlat
                    agirlikOlcBaslat();
                    measureBtn.textContent = 'Durdur';
                    measureBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
                    measureBtn.classList.add('bg-red-600', 'hover:bg-red-700');
                    if (loadcellMessage) loadcellMessage.innerText = `Sürekli ölçüm aktif (${TIMING_CONFIG.EMBEDDED_COMMANDS.WEIGHT_MEASUREMENT_INTERVAL}ms)`;
                    showMessage('✓ Sürekli ağırlık ölçümü başlatıldı', true);
                } else {
                    if (loadcellMessage) loadcellMessage.innerText = 'Ölçüm hatası';
                    showMessage('✗ Ölçüm hatası: ' + data.message, false);
                }
            } catch (error) {
                if (loadcellMessage) loadcellMessage.innerText = 'Ölçüm hatası';
                showMessage('✗ Ölçüm hatası: ' + error.message, false);
                console.error('Ağırlık ölçüm API hatası:', error);
            } finally {
                if (tareBtn) tareBtn.disabled = false;
                measureBtn.disabled = false;
            }
        });
    }

    // Sürekli ağırlık ölçümü başlat
    function agirlikOlcBaslat() {
        agirlikOlcAktif = true;
        agirlikOlcTimer = setInterval(async () => {
            try {
                await fetch(`${API_BASE}/sensor/agirlik-olc`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                console.log(`Ağırlık ölçüm komutu gönderildi (${TIMING_CONFIG.EMBEDDED_COMMANDS.WEIGHT_MEASUREMENT_INTERVAL}ms)`);
            } catch (error) {
                console.error('Ağırlık ölçüm hatası:', error);
            }
        }, TIMING_CONFIG.EMBEDDED_COMMANDS.WEIGHT_MEASUREMENT_INTERVAL); // Ağırlık ölçümü aralığı
    }

    // Sürekli ağırlık ölçümü durdur
    function agirlikOlcDurdur() {
        console.log('🛑 Ağırlık ölçümü durduruluyor...');
        
        // Bayrağı sıfırla
        agirlikOlcAktif = false;
        
        // Timer'ı temizle
        if (agirlikOlcTimer) {
            clearInterval(agirlikOlcTimer);
            agirlikOlcTimer = null;
        }
        
        // UI'yi güncelle
        if (loadcellVisual) loadcellVisual.classList.remove('measuring');
        if (loadcellMessage) loadcellMessage.innerText = 'Ölçüm durduruldu';
        
        // Buton durumunu sıfırla
        const measureBtn = document.getElementById('loadcell-measure-btn');
        if (measureBtn) {
            measureBtn.textContent = 'Ağırlık Ölç';
            measureBtn.classList.remove('bg-red-600', 'hover:bg-red-700');
            measureBtn.classList.add('bg-blue-600', 'hover:bg-blue-700');
            measureBtn.disabled = false;
        }
        
        showMessage('✓ Ağırlık ölçümü durduruldu', true);
        console.log('✅ Ağırlık ölçümü durduruldu');
    }
    
    if (tareBtn) {
        tareBtn.addEventListener('click', async () => {
            if(tareBtn.disabled) return;
            
            // Önce sensör durumunu kontrol et
            try {
                const durumResponse = await fetch(`${API_BASE}/sensor/durum`);
                const durumData = await durumResponse.json();
                
                if (!durumData.bagli) {
                    showMessage('✗ Sensör kartı bağlı değil. Sistem çalıştırılmamış olabilir.', false);
                    return;
                }
                
                if (!durumData.saglikli) {
                    showMessage('✗ Sensör kartı sağlıksız. Bağlantı kontrol ediliyor...', false);
                    return;
                }
            } catch (error) {
                showMessage('✗ Sensör durum kontrolü başarısız: ' + error.message, false);
                return;
            }
            
            tareBtn.disabled = true;
            if (measureBtn) measureBtn.disabled = true;
            if (loadcellMessage) loadcellMessage.innerText = 'Konveyörü boşaltın...';
            
            try {
                // Tare bekleme süresi
                await new Promise(resolve => setTimeout(resolve, TIMING_CONFIG.SAFETY.TARE_WAIT_TIME));
                
                if (loadcellMessage) loadcellMessage.innerText = 'Tare alınıyor...';
                if (loadcellVisual) loadcellVisual.classList.add('measuring');
                
                const response = await fetch(`${API_BASE}/sensor/tare`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                
                if (data.message && data.message.includes('tamamlandı')) {
                    if (loadcellOutput) {
                        loadcellOutput.innerHTML = `0.0 <span class="text-2xl">gr</span>`;
                    }
                    if (loadcellMessage) loadcellMessage.innerText = 'Tare tamamlandı';
                    showMessage('✓ Loadcell tare tamamlandı', true);
                } else {
                    if (loadcellMessage) loadcellMessage.innerText = 'Tare hatası';
                    showMessage('✗ Tare hatası: ' + (data.message || 'Bilinmeyen hata'), false);
                }
            } catch (error) {
                if (loadcellMessage) loadcellMessage.innerText = 'Tare hatası';
                showMessage('✗ Tare hatası: ' + error.message, false);
                console.error('Tare API hatası:', error);
            } finally {
                if (loadcellVisual) loadcellVisual.classList.remove('measuring');
                if (tareBtn) tareBtn.disabled = false;
                if (measureBtn) measureBtn.disabled = false;
            }
        });
    }
    
    // LED Kontrolü
    const ledVisual = document.getElementById('conveyor-led-visual');
    const ledSvg = ledVisual ? ledVisual.querySelector('svg') : null;
    const brightnessSlider = document.getElementById('led-brightness-slider');
    const brightnessInput = document.getElementById('led-brightness-input');
    
    function updateLedState(brightness) {
        const value = Math.max(0, Math.min(100, brightness));
        if (brightnessSlider) brightnessSlider.value = value;
        if (brightnessInput) brightnessInput.value = value;
        
        if (ledVisual) {
            if (value > 0) {
                ledVisual.classList.add('led-on');
                if (ledSvg) {
                    ledSvg.classList.remove('text-gray-500');
                    ledSvg.classList.add('text-yellow-300');
                }
            } else {
                ledVisual.classList.remove('led-on');
                if (ledSvg) {
                    ledSvg.classList.add('text-gray-500');
                    ledSvg.classList.remove('text-yellow-300');
                }
            }
        }
    }
    
    const ledOnBtn = document.getElementById('led-on-btn');
    const ledOffBtn = document.getElementById('led-off-btn');
    
    if (ledOnBtn) {
        ledOnBtn.addEventListener('click', async () => {
            // Önce sensör durumunu kontrol et
            try {
                const durumResponse = await fetch(`${API_BASE}/sensor/durum`);
                const durumData = await durumResponse.json();
                
                if (!durumData.bagli) {
                    showMessage('✗ Sensör kartı bağlı değil. Sistem çalıştırılmamış olabilir.', false);
                    return;
                }
                
                if (!durumData.saglikli) {
                    showMessage('✗ Sensör kartı sağlıksız. Bağlantı kontrol ediliyor...', false);
                    return;
                }
            } catch (error) {
                showMessage('✗ Sensör durum kontrolü başarısız: ' + error.message, false);
                return;
            }
            
            updateLedState(100);
            sensorKontrol('led-ac');
            await sendLedPwm(100);
        });
    }
    
    if (ledOffBtn) {
        ledOffBtn.addEventListener('click', async () => {
            // Önce sensör durumunu kontrol et
            try {
                const durumResponse = await fetch(`${API_BASE}/sensor/durum`);
                const durumData = await durumResponse.json();
                
                if (!durumData.bagli) {
                    showMessage('✗ Sensör kartı bağlı değil. Sistem çalıştırılmamış olabilir.', false);
                    return;
                }
                
                if (!durumData.saglikli) {
                    showMessage('✗ Sensör kartı sağlıksız. Bağlantı kontrol ediliyor...', false);
                    return;
                }
            } catch (error) {
                showMessage('✗ Sensör durum kontrolü başarısız: ' + error.message, false);
                return;
            }
            
            updateLedState(0);
            sensorKontrol('led-kapat');
            await sendLedPwm(0);
        });
    }
    
    if (brightnessSlider) {
        brightnessSlider.addEventListener('input', async () => {
            const value = parseInt(brightnessSlider.value, 10);
            updateLedState(value);
            await sendLedPwm(value);
        });
    }
    
    if (brightnessInput) {
        brightnessInput.addEventListener('input', async () => {
            const val = parseInt(brightnessInput.value, 10);
            if (!isNaN(val)) {
                updateLedState(val);
                await sendLedPwm(val);
            }
        });
    }
}

// LED PWM değerini sensör kartına gönder
async function sendLedPwm(value) {
    // LED PWM işlemini sensör kuyruğuna ekle
    sensorQueueManager.addOperation(async () => {
        try {
            // Önce sensör durumunu kontrol et
            const durumResponse = await fetch(`${API_BASE}/sensor/durum`);
            const durumData = await durumResponse.json();
            
            if (!durumData.bagli) {
                console.warn('Sensör kartı bağlı değil, LED PWM gönderilemedi');
                return;
            }
            
            if (!durumData.saglikli) {
                console.warn('Sensör kartı sağlıksız, LED PWM gönderilemedi');
                return;
            }
            
            // PWM değerini gönder
            const response = await fetch(`${API_BASE}/sensor/led-pwm`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ deger: value })
            });
            
            const data = await response.json();
            
            if (data.errorCode === 0) {
                console.log(`LED PWM değeri ${value} olarak ayarlandı`);
            } else {
                console.error('LED PWM ayarlama hatası:', data.message);
            }
        } catch (error) {
            console.error('LED PWM gönderme hatası:', error);
        }
    });
}

// Motor toggle'larını senkronize et
function setupMotorToggles() {
    const conveyorToggle = document.getElementById('conveyor-power');
    const diverterToggle = document.getElementById('diverter-power');
    const flapToggle = document.getElementById('flap-power');
    
    if (!conveyorToggle || !diverterToggle || !flapToggle) {
        return;
    }
    
    // Toggle'ları senkronize et - birini kapatınca hepsi kapansın
    const toggles = [conveyorToggle, diverterToggle, flapToggle];
    
    // Programatik değişiklik flag'i
    let isProgrammaticChange = false;
    
    // Toggle'ı güvenli şekilde değiştir
    function setToggleChecked(toggle, checked) {
        if (isProgrammaticChange) {
            return;
        }
        
        isProgrammaticChange = true;
        toggle.checked = checked;
        
        // CSS animasyonunu tetiklemek için class ekle/çıkar
        toggle.classList.add('force-update');
        setTimeout(() => {
            toggle.classList.remove('force-update');
        }, 10);
        
        isProgrammaticChange = false;
    }
    
    toggles.forEach(toggle => {
        toggle.addEventListener('change', async () => {
            // Programatik değişiklik ise event'i yok say
            if (isProgrammaticChange) {
                return;
            }
            
            if (toggle.checked) {
                // Toggle açıldığında - diğer toggle'ları da aç
                toggles.forEach(otherToggle => {
                    if (otherToggle !== toggle && !otherToggle.checked) {
                        setToggleChecked(otherToggle, true);
                    }
                });
                
                // Motorları aktif et
                try {
                    const response = await fetch(`${API_BASE}/motor/motorlari-aktif`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const data = await response.json();
                    
                    if (data.errorCode === 0) {
                        showMessage('Motorlar aktif edildi');
                    } else {
                        showMessage(data.message || data.errorMessage, true);
                        // Hata durumunda toggle'ları kapat
                        toggles.forEach(t => setToggleChecked(t, false));
                    }
                } catch (error) {
                    // Network hatası ise toggle'ları açık bırak
                    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                        showMessage('API sunucusu çalışmıyor. Motorlar aktif edilemedi ama toggle açık bırakıldı.', false);
                    } else {
                        showMessage(`Motor aktif etme hatası: ${error.message}`, true);
                        // Hata durumunda toggle'ları kapat
                        toggles.forEach(t => setToggleChecked(t, false));
                    }
                }
            } else {
                // Toggle kapandığında - diğer toggle'ları da kapat
                toggles.forEach(otherToggle => {
                    if (otherToggle !== toggle && otherToggle.checked) {
                        setToggleChecked(otherToggle, false);
                    }
                });
                
                // Motorları iptal et
                try {
                    const response = await fetch(`${API_BASE}/motor/motorlari-iptal`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const data = await response.json();
                    if (data.errorCode === 0) {
                        showMessage('Motorlar iptal edildi');
                    } else {
                        showMessage(data.message || data.errorMessage, true);
                    }
                } catch (error) {
                    showMessage(`Motor iptal etme hatası: ${error.message}`, true);
                }
            }
        });
    });
}

// Motor toggle'larını kapat (reset sonrası kullanım için)
function turnOffMotorToggles() {
    const conveyorToggle = document.getElementById('conveyor-power');
    const diverterToggle = document.getElementById('diverter-power');
    const flapToggle = document.getElementById('flap-power');
    
    const toggles = [conveyorToggle, diverterToggle, flapToggle];
    toggles.forEach(toggle => {
        if (toggle) {
            // Toggle'ı kapat
            toggle.checked = false;
            // CSS animasyonunu tetiklemek için class ekle/çıkar
            toggle.classList.add('force-update');
            setTimeout(() => {
                toggle.classList.remove('force-update');
            }, 10);
        }
    });
}

// Motor kontrolleri
function setupMotorControls() {
    // Motor toggle'larını senkronize et
    setupMotorToggles();
    
    // Konveyör Motor Kontrolü
    const conveyorFwdBtn = document.getElementById('conveyor-fwd');
    const conveyorStopBtn = document.getElementById('conveyor-stop');
    const conveyorRevBtn = document.getElementById('conveyor-rev');
    const conveyorAnimation = document.getElementById('conveyor-animation');
    
    if (conveyorFwdBtn) {
        conveyorFwdBtn.addEventListener('click', () => {
            if (conveyorFwdBtn.disabled) return;
            if (conveyorAnimation) {
                conveyorAnimation.classList.add('conveyor-running-forward');
                conveyorAnimation.classList.remove('conveyor-running-backward');
            }
            motorKontrol('konveyor-ileri');
        });
    }
    
    if (conveyorRevBtn) {
        conveyorRevBtn.addEventListener('click', () => {
            if (conveyorRevBtn.disabled) return;
            if (conveyorAnimation) {
                conveyorAnimation.classList.add('conveyor-running-backward');
                conveyorAnimation.classList.remove('conveyor-running-forward');
            }
            motorKontrol('konveyor-geri');
        });
    }
    
    if (conveyorStopBtn) {
        conveyorStopBtn.addEventListener('click', () => {
            if (conveyorStopBtn.disabled) return;
            if (conveyorAnimation) {
                conveyorAnimation.classList.remove('conveyor-running-forward', 'conveyor-running-backward');
            }
            motorKontrol('konveyor-dur');
        });
    }
    
    // Yönlendirici Motor Kontrolü
    const diverterPlasticBtn = document.getElementById('diverter-plastic');
    const diverterGlassBtn = document.getElementById('diverter-glass');
    
    if (diverterPlasticBtn) {
        diverterPlasticBtn.addEventListener('click', () => {
            if (diverterPlasticBtn.disabled) return;
            diverterAnimasyonu('plastik');
            motorKontrol('yonlendirici-plastik');
        });
    }
    
    if (diverterGlassBtn) {
        diverterGlassBtn.addEventListener('click', () => {
            if (diverterGlassBtn.disabled) return;
            diverterAnimasyonu('cam');
            motorKontrol('yonlendirici-cam');
        });
    }
    
    // Klape Motor Kontrolü
    const flapPlasticBtn = document.getElementById('flap-plastic');
    const flapMetalBtn = document.getElementById('flap-metal');
    
    if (flapPlasticBtn) {
        flapPlasticBtn.addEventListener('click', () => {
            if (flapPlasticBtn.disabled) return;
            flapAnimasyonu('plastik');
            motorKontrol('klape-plastik');
        });
    }
    
    if (flapMetalBtn) {
        flapMetalBtn.addEventListener('click', () => {
            if (flapMetalBtn.disabled) return;
            flapAnimasyonu('metal');
            motorKontrol('klape-metal');
        });
    }
    
    // Motorları aktif et/iptal et
    const motorlariAktifBtn = document.getElementById('motorlari-aktif-btn');
    const motorlariIptalBtn = document.getElementById('motorlari-iptal-btn');
    
    if (motorlariAktifBtn) {
        motorlariAktifBtn.addEventListener('click', () => {
            motorKontrol('motorlari-aktif');
        });
    }
    
    if (motorlariIptalBtn) {
        motorlariIptalBtn.addEventListener('click', () => {
            motorKontrol('motorlari-iptal');
        });
    }
}

// Henüz aktif olmayan özellikler için placeholder fonksiyonlar
function setupPlaceholderFunctions() {
    // AC Motor kontrolleri
    const acMotorButtons = [
        'crusher-fwd-btn', 'crusher-stop-btn', 'crusher-rev-btn',
        'breaker-fwd-btn', 'breaker-stop-btn', 'breaker-rev-btn'
    ];
    
    acMotorButtons.forEach(btnId => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', ozellikAktifDegil);
        }
    });
    
    // Kalibrasyon butonları
    const calibrationButtons = [
        'calibrate-diverter-btn', 'calibrate-flap-btn', 
        'calibrate-diverter-sensor-btn', 'calibrate-all-btn'
    ];
    
    calibrationButtons.forEach(btnId => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', ozellikAktifDegil);
        }
    });
    
    // Test butonları
    const testButtons = [
        'test-plastic-btn', 'test-metal-btn', 'test-glass-btn',
        'start-stop-scenarios-btn'
    ];
    
    testButtons.forEach(btnId => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', ozellikAktifDegil);
        }
    });
    
    // Hız kontrolleri
    const speedControls = [
        { id: 'conveyor', motor: 'konveyor' },
        { id: 'diverter', motor: 'yonlendirici' },
        { id: 'flap', motor: 'klape' }
    ];
    
    speedControls.forEach(({ id, motor }) => {
        const slider = document.getElementById(`${id}-speed-slider`);
        const input = document.getElementById(`${id}-speed-input`);
        const saveBtn = document.getElementById(`${id}-speed-save`);
        
        // Slider değiştiğinde input'u güncelle
        if (slider && input) {
            slider.addEventListener('input', () => {
                input.value = slider.value;
            });
        }
        
        // Input değiştiğinde slider'ı güncelle
        if (input && slider) {
            input.addEventListener('input', () => {
                const value = Math.max(0, Math.min(100, parseInt(input.value) || 0));
                slider.value = value;
                input.value = value;
            });
        }
        
        // Kaydet butonu
        if (saveBtn) {
            saveBtn.addEventListener('click', async () => {
                if (!slider || !input) return;
                
                const speed = parseInt(slider.value);
                saveBtn.disabled = true;
                saveBtn.innerText = 'Kaydediliyor...';
                
                try {
                    const response = await fetch(`${API_BASE}/motor/hiz-ayarla`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ motor: motor, hiz: speed })
                    });
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        showMessage(`✓ ${motor} motor hızı ${speed}% olarak ayarlandı`, true);
                    } else {
                        showMessage('✗ Hız ayarlama hatası: ' + data.message, false);
                    }
                } catch (error) {
                    showMessage('✗ Hız ayarlama hatası: ' + error.message, false);
                } finally {
                    saveBtn.disabled = false;
                    saveBtn.innerText = 'Kaydet';
                }
            });
        }
    });

    // Hızlı kontroller
    const quickControlButtons = [
        'diagnostic-btn', 'empty-tank-btn', 'restart-system-btn'
    ];
    
    quickControlButtons.forEach(btnId => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', ozellikAktifDegil);
        }
    });
}

// Yönlendirici Animasyonu
function diverterAnimasyonu(tip) {
    const diverterVisual = document.getElementById('diverter-visual');
    if (!diverterVisual) return;
    
    // Önceki animasyonu temizle
    diverterVisual.classList.remove('spinning', 'spinning-rev');
    
    // Yeni animasyonu başlat
    if (tip === 'plastik') {
        diverterVisual.classList.add('spinning');
        // 2 saniye sonra durdur
        setTimeout(() => {
            diverterVisual.classList.remove('spinning');
        }, 2000);
    } else if (tip === 'cam') {
        diverterVisual.classList.add('spinning-rev');
        // 2 saniye sonra durdur
        setTimeout(() => {
            diverterVisual.classList.remove('spinning-rev');
        }, 2000);
    }
}

// Klape Animasyonu
function flapAnimasyonu(tip) {
    const flapVisual = document.getElementById('flap-visual');
    if (!flapVisual) return;
    
    // Önceki animasyonu temizle
    flapVisual.style.transform = '';
    
    // Yeni animasyonu başlat
    if (tip === 'plastik') {
        // Plastik için düz konum (0 derece)
        flapVisual.style.transform = 'rotate(0deg)';
    } else if (tip === 'metal') {
        // Metal için yatay konum (90 derece)
        flapVisual.style.transform = 'rotate(90deg)';
    }
}

// Bakım URL'ini değiştir
function bakimUrlDegistir() {
    const yeniUrl = prompt('Yeni bakım URL\'ini girin:', 'http://192.168.53.2:4321/bakim');
    if (yeniUrl) {
        fetch(`${API_BASE}/bakim/url-ayarla`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: yeniUrl })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Bakım URL\'i güncellendi! Yeni bakım modu aktif edildiğinde bu URL kullanılacak.');
                console.log(data.message);
            } else {
                console.error('URL güncelleme hatası:', data.message);
            }
        })
        .catch(error => {
            console.error('URL güncelleme hatası:', error);
        });
    }
}

// Genel durum güncelleme
function updateGeneralStatus() {
    // Sistem durumu - API'den al
    const systemState = document.getElementById('system-state');
    if (systemState) {
        fetch(`${API_BASE}/sistem/durum`)
            .then(response => response.json())
            .then(data => {
                if (data.durum) {
                    durumYoneticisi.durum = data.durum;
                    // Durumu Türkçe'ye çevir
                    let durumText = data.durum;
                    if (data.durum === 'oturum_yok') durumText = 'Oturum Yok';
                    else if (data.durum === 'oturum_var') durumText = 'Oturum Var';
                    else if (data.durum === 'bakim') durumText = 'Bakım';
                    systemState.textContent = durumText;
                }
            })
            .catch(error => {
                console.error('Durum alma hatası:', error);
                systemState.textContent = durumYoneticisi.durum || 'Bilinmiyor';
            });
    }
    
    // Çalışma süresi (basit implementasyon)
    const uptime = document.getElementById('uptime');
    if (uptime) {
        const now = new Date();
        const startTime = new Date(now.getTime() - (now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds()) * 1000);
        const diff = now - startTime;
        const hours = Math.floor(diff / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        uptime.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    // Son aktivite
    const lastActivity = document.getElementById('last-activity');
    if (lastActivity) {
        lastActivity.textContent = new Date().toLocaleTimeString('tr-TR');
    }
    
    // Bağlantı durumları
    updateConnectionStatus();
}

// Bağlantı durumu güncelleme
function updateConnectionStatus() {
    // Sensör kartı durumu
    const sensorStatus = document.getElementById('sensor-connection-status');
    if (sensorStatus) {
        const dot = sensorStatus.querySelector('div');
        const text = sensorStatus.querySelector('span');
        if (durumYoneticisi.sensorKartBagli) {
            dot.className = 'w-3 h-3 rounded-full bg-green-500';
            text.textContent = 'Bağlı';
        } else {
            dot.className = 'w-3 h-3 rounded-full bg-red-500';
            text.textContent = 'Bağlantı Yok';
        }
    }
    
    // Motor kartı durumu
    const motorStatus = document.getElementById('motor-connection-status');
    if (motorStatus) {
        const dot = motorStatus.querySelector('div');
        const text = motorStatus.querySelector('span');
        if (durumYoneticisi.motorKartBagli) {
            dot.className = 'w-3 h-3 rounded-full bg-green-500';
            text.textContent = 'Bağlı';
        } else {
            dot.className = 'w-3 h-3 rounded-full bg-red-500';
            text.textContent = 'Bağlantı Yok';
        }
    }
}

// Periyodik güncelleme interval'ları
let sistemDurumInterval = null;
let sensorDegerInterval = null;
let genelDurumInterval = null;

// WebSocket bağlantı fonksiyonları
function connectWebSocket() {
    console.log('WebSocket bağlantısı başlatılıyor...');
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/bakim`;
        
        console.log('WebSocket URL oluşturuldu:', wsUrl);
        websocket = new WebSocket(wsUrl);
        console.log('WebSocket nesnesi oluşturuldu');
        
        websocket.onopen = function(event) {
            console.log('WebSocket bağlantısı kuruldu');
            showMessage('Gerçek zamanlı veri bağlantısı kuruldu', false);
            console.log('WebSocket URL:', wsUrl);
        };
        
        websocket.onmessage = function(event) {
            console.log('WebSocket mesaj alındı:', event.data);
            try {
                const data = JSON.parse(event.data);
                console.log('WebSocket mesaj parse edildi:', data);
                handleWebSocketMessage(data);
            } catch (error) {
                console.error('WebSocket mesaj parse hatası:', error);
            }
        };
        
        websocket.onclose = function(event) {
            console.log('WebSocket bağlantısı kapandı');
            showMessage('Gerçek zamanlı veri bağlantısı kesildi', true);
            
            // 5 saniye sonra yeniden bağlan
            setTimeout(() => {
                if (bakimModuAktif) {
                    connectWebSocket();
                }
            }, 5000);
        };
        
        websocket.onerror = function(error) {
            console.error('WebSocket hatası:', error);
            showMessage('WebSocket bağlantı hatası', true);
        };
        
    } catch (error) {
        console.error('WebSocket bağlantı hatası:', error);
        showMessage('WebSocket bağlantısı kurulamadı', true);
    }
}

function disconnectWebSocket() {
    if (websocket) {
        websocket.close();
        websocket = null;
    }
    
    // Tüm işlemleri durdur (güvenlik için)
    stopAllOperations();
}

function handleWebSocketMessage(data) {
    console.log('WebSocket mesaj işleniyor:', data.type);
    switch (data.type) {
        case 'modbus_update':
            console.log('Modbus güncelleme alındı:', data.motor_type, data.data);
            updateMotorDisplayFromWebSocket(data.motor_type, data.data);
            break;
        case 'system_status':
            console.log('Sistem durumu güncelleme alındı:', data.data);
            updateSystemStatusFromWebSocket(data.data);
            break;
        case 'sensor_update':
            console.log('Sensör güncelleme alındı:', data.data);
            updateSensorDataFromWebSocket(data.data);
            break;
        case 'sds_update':
            console.log('SDS güncelleme alındı:', data.data);
            updateSdsDataFromWebSocket(data.data);
            break;
        case 'doluluk_update':
            console.log('Doluluk güncelleme alındı:', data.data);
            updateDolulukDataFromWebSocket(data.data);
            break;
        case 'alarm_update':
            console.log('Alarm güncelleme alındı:', data.data);
            updateAlarmDisplayFromWebSocket(data.data);
            break;
        case 'sensor_message':
            console.log('Sensör mesajı alındı:', data.message);
            handleSensorMessage(data.message);
            break;
        // measurement_status case kaldırıldı
        default:
            console.log('Bilinmeyen WebSocket mesaj tipi:', data.type);
    }
}

// Sensör mesajlarını işle
function handleSensorMessage(message) {
    console.log('Sensör mesajı işleniyor:', message);
    
    switch (message) {
        case 'g/msup':
            // Üst kapak açık
            updateLidStatus('top-sensor', false);
            console.log('🔓 Üst kapak açık');
            break;
        case 'g/msua':
            // Üst kapak kapalı
            updateLidStatus('top-sensor', true);
            console.log('🔒 Üst kapak kapalı');
            break;
        case 'g/msap':
            // Alt kapak açık
            updateLidStatus('bottom-sensor', false);
            console.log('🔓 Alt kapak açık');
            break;
        case 'g/msaa':
            // Alt kapak kapalı
            updateLidStatus('bottom-sensor', true);
            console.log('🔒 Alt kapak kapalı');
            break;
        default:
            console.log('Bilinmeyen sensör mesajı:', message);
    }
}

// Emniyet sensörü durumunu sorgula
async function queryEmniySensorDurum() {
    try {
        console.log('🔐 Emniyet sensörü durumları sorgulanıyor...');
        
        // Üst kapak durumunu sorgula
        const responseUst = await fetch(`${API_BASE}/sensor/komut-gonder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ komut: 'msud' })
        });
        
        // Alt kapak durumunu sorgula  
        const responseAlt = await fetch(`${API_BASE}/sensor/komut-gonder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ komut: 'msad' })
        });
        
        console.log('✅ Emniyet sensörü durum sorgusu gönderildi');
    } catch (error) {
        console.error('❌ Emniyet sensörü durum sorgulama hatası:', error);
    }
}

// Kapak durumunu güncelle
function updateLidStatus(sensorPrefix, isClosed) {
    const visual = document.getElementById(`${sensorPrefix}-visual`);
    const statusLed = document.getElementById(`${sensorPrefix}-status-led`);
    const statusText = document.getElementById(`${sensorPrefix}-status-text`);
    
    if (!visual || !statusLed || !statusText) return;
    
    if (isClosed) {
        // Kapak kapalı - sensör aktif
        visual.classList.remove('inactive');
        statusLed.classList.remove('bg-red-500');
        statusLed.classList.add('bg-green-500');
        statusText.textContent = 'Aktif (Kapak Kapalı)';
        statusText.classList.remove('text-red-400');
        statusText.classList.add('text-green-400');
    } else {
        // Kapak açık - sensör pasif
        visual.classList.add('inactive');
        statusLed.classList.remove('bg-green-500');
        statusLed.classList.add('bg-red-500');
        statusText.textContent = 'Pasif (Kapak Açık)';
        statusText.classList.remove('text-green-400');
        statusText.classList.add('text-red-400');
    }
}

function updateMotorDisplayFromWebSocket(motorType, data) {
    console.log('Motor display güncelleniyor:', motorType, data);
    const prefix = motorType === 'crusher' ? 'crusher' : 'breaker';
    console.log('Motor prefix:', prefix);
    
    // Motor verilerini güncelle
    const setFreqEl = document.getElementById(`${prefix}-set-freq`);
    const outFreqEl = document.getElementById(`${prefix}-out-freq`);
    const voltageEl = document.getElementById(`${prefix}-voltage`);
    const currentEl = document.getElementById(`${prefix}-current`);
    const powerEl = document.getElementById(`${prefix}-power`);
    const busVoltageEl = document.getElementById(`${prefix}-bus-voltage`);
    const tempEl = document.getElementById(`${prefix}-temp`);
    const directionEl = document.getElementById(`${prefix}-direction`);
    const statusEl = document.getElementById(`${prefix}-status`);
    const readyEl = document.getElementById(`${prefix}-ready`);
    const faultEl = document.getElementById(`${prefix}-fault`);
    
    if (setFreqEl) setFreqEl.textContent = data.set_freq || '0.0 Hz';
    if (outFreqEl) outFreqEl.textContent = data.out_freq || '0.0 Hz';
    if (voltageEl) voltageEl.textContent = data.voltage || '0.0 V';
    if (currentEl) currentEl.textContent = data.current || '0.0 A';
    if (powerEl) powerEl.textContent = data.power || '0.0 W';
    if (busVoltageEl) busVoltageEl.textContent = data.bus_voltage || '0.0 V';
    if (tempEl) tempEl.textContent = data.temperature || '0.0 °C';
    if (directionEl) directionEl.textContent = data.direction || 'DURUYOR';
    if (statusEl) statusEl.textContent = data.status || 'DURUYOR';
    
    // Ready durumu
    if (readyEl) {
        const previousReady = readyEl.textContent;
        readyEl.textContent = data.ready || 'HAYIR';
        
        if (data.ready === 'EVET') {
            readyEl.classList.add('text-green-400');
            readyEl.classList.remove('text-red-400');
        } else {
            readyEl.classList.remove('text-green-400');
            readyEl.classList.add('text-red-400');
            
            // Ready durumu "HAYIR" olduğunda motorları durdur
            if (previousReady === 'EVET' && data.ready === 'HAYIR') {
                console.warn('⚠️ Modbus ready durumu HAYIR oldu - Motorlar durduruluyor');
                tumMotorlarDur();
            }
        }
    }
    
    // Fault durumu
    if (faultEl) {
        faultEl.textContent = data.fault || 'YOK';
        if (data.fault === 'VAR') {
            faultEl.classList.add('text-red-400');
            faultEl.classList.remove('text-green-400');
        } else {
            faultEl.classList.remove('text-red-400');
            faultEl.classList.add('text-green-400');
        }
    }
    
    // Motor çalışma durumuna göre animasyon
    const gears = document.getElementById(`${prefix}-gears`);
    if (gears) {
        if (data.status === 'ÇALIŞIYOR') {
            gears.classList.remove('spinning', 'spinning-rev');
            if (data.direction === 'İLERİ') {
                gears.classList.add('spinning');
            } else if (data.direction === 'GERİ') {
                gears.classList.add('spinning-rev');
            }
        } else {
            gears.classList.remove('spinning', 'spinning-rev');
        }
    }
}

function updateSystemStatusFromWebSocket(data) {
    // Sistem durumu güncellemeleri
    console.log('Sistem durumu güncellendi:', data);
}

function updateSensorDataFromWebSocket(data) {
    // Sensör verisi güncellemeleri
    console.log('Sensör verisi güncellendi:', data);
    
    // Ağırlık verisi kontrolü
    if (data.agirlik !== undefined) {
        const loadcellOutput = document.getElementById('loadcell-output');
        const loadcellMessage = document.getElementById('loadcell-message');
        const loadcellVisual = document.getElementById('loadcell-visual');
        
        if (loadcellOutput) {
            loadcellOutput.innerHTML = `${data.agirlik.toFixed(2)} <span class="text-2xl">gr</span>`;
        }
        if (loadcellMessage) {
            loadcellMessage.innerText = 'Ölçüm başlatıldı';
        }
        if (loadcellVisual) {
            loadcellVisual.classList.remove('measuring');
            loadcellVisual.classList.add('success');
            
            // 2 saniye sonra success class'ını kaldır
            setTimeout(() => {
                loadcellVisual.classList.remove('success');
            }, 2000);
        }
        
        showMessage(`✓ Ağırlık: ${data.agirlik.toFixed(2)} gr`, true);
        console.log('Ağırlık verisi güncellendi:', data.agirlik);
    }
    
    // Motor verisi kontrolü
    if (data.uzunluk_motor_verisi !== undefined) {
        console.log('Motor verisi güncellendi:', data.uzunluk_motor_verisi);
        // Motor verisi işleme kodu buraya eklenebilir
    }
}

function updateSdsDataFromWebSocket(data) {
    // SDS sensör verilerini mevcut sensörlere entegre et
    console.log('SDS verisi güncellendi:', data);
    
    // SDS verilerini mevcut sensörlere eşleştir
    const sensorMapping = [
        { sdsKey: 'sds_giris', sensorPrefix: 'opt1009' },
        { sdsKey: 'sds_plastik', sensorPrefix: 'plastic' },
        { sdsKey: 'sds_cam', sensorPrefix: 'glass' },
        { sdsKey: 'sds_metal', sensorPrefix: 'metal' },
        { sdsKey: 'sds_led', sensorPrefix: 'led' }
    ];
    
    sensorMapping.forEach(mapping => {
        if (data[mapping.sdsKey]) {
            updateSingleSdsSensor(mapping.sensorPrefix, data[mapping.sdsKey]);
        }
    });
    
    // Doluluk kartlarının sağlık durumlarını güncelle
    updateDolulukHealthFromSDS(data);
}

function updateSingleSdsSensor(prefix, sensorData) {
    // Mevcut sensör kartındaki SDS verilerini güncelle
    const voltageEl = document.getElementById(`${prefix}-voltage`);
    const currentEl = document.getElementById(`${prefix}-current`);
    const healthEl = document.getElementById(`${prefix}-health`);
    const healthDot = healthEl?.querySelector('.w-2.h-2.rounded-full');
    
    // Gerilim güncelle
    if (voltageEl) {
        voltageEl.textContent = `${sensorData.gerilim.toFixed(2)} V`;
    }
    
    // Akım güncelle
    if (currentEl) {
        currentEl.textContent = `${sensorData.akim.toFixed(2)} A`;
    }
    
    // Sağlık durumu güncelle
    if (healthEl) {
        healthEl.innerHTML = `${sensorData.saglik} <span class="w-2 h-2 rounded-full"></span>`;
        const newHealthDot = healthEl.querySelector('.w-2.h-2.rounded-full');
        
        // Sağlık durumunu temizle ve küçük harfe çevir
        const cleanSaglik = sensorData.saglik.trim().toLowerCase();
        
        // Sağlık durumuna göre renk ayarla
        if (newHealthDot) {
            newHealthDot.classList.remove('bg-gray-500', 'bg-green-500', 'bg-red-500', 'bg-yellow-500');
            
            if (cleanSaglik === 'normal') {
                newHealthDot.classList.add('bg-green-500');
            } else if (cleanSaglik.includes('bağlantı kopuk') || cleanSaglik.includes('kopuk') || cleanSaglik.includes('baglanti kopuk')) {
                newHealthDot.classList.add('bg-red-500');
            } else {
                newHealthDot.classList.add('bg-yellow-500');
            }
        }
    }
    
    console.log(`SDS ${prefix} sensörü güncellendi:`, sensorData);
}

// SDS sensör sorgulama sistemi
let sdsInterval = null;
let dolulukInterval = null;

function startSdsUpdates() {
    // Eğer zaten çalışıyorsa durdur
    stopSdsUpdates();
    
    // 1 saniyede bir SDS komutunu gönder
    sdsInterval = setInterval(async () => {
        try {
            await fetch(`${API_BASE}/sensor/sds-sensorler`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            console.log(`SDS sensör sorgulama komutu gönderildi (${TIMING_CONFIG.EMBEDDED_COMMANDS.SDS_SENSOR_INTERVAL}ms)`);
        } catch (error) {
            console.error('SDS sensör sorgulama hatası:', error);
        }
    }, TIMING_CONFIG.EMBEDDED_COMMANDS.SDS_SENSOR_INTERVAL); // SDS sensör sorgulama aralığı
    
    console.log(`SDS sensör güncellemeleri başlatıldı (${TIMING_CONFIG.EMBEDDED_COMMANDS.SDS_SENSOR_INTERVAL}ms aralık)`);
}

function startDolulukUpdates() {
    // Eğer zaten çalışıyorsa durdur
    stopDolulukUpdates();
    
    // 5 saniyede bir doluluk komutunu gönder
    dolulukInterval = setInterval(async () => {
        try {
            await fetch(`${API_BASE}/sensor/doluluk-orani`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            console.log(`Doluluk oranı sorgulama komutu gönderildi (${TIMING_CONFIG.EMBEDDED_COMMANDS.DOLULUK_INTERVAL}ms)`);
        } catch (error) {
            console.error('Doluluk oranı sorgulama hatası:', error);
        }
    }, TIMING_CONFIG.EMBEDDED_COMMANDS.DOLULUK_INTERVAL); // Doluluk oranı sorgulama aralığı
    
    console.log(`Doluluk oranı güncellemeleri başlatıldı (${TIMING_CONFIG.EMBEDDED_COMMANDS.DOLULUK_INTERVAL}ms aralık)`);
}

function stopSdsUpdates() {
    if (sdsInterval) {
        clearInterval(sdsInterval);
        sdsInterval = null;
        console.log('SDS sensör güncellemeleri durduruldu');
    }
}

function stopDolulukUpdates() {
    if (dolulukInterval) {
        clearInterval(dolulukInterval);
        dolulukInterval = null;
        console.log('Doluluk oranı güncellemeleri durduruldu');
    }
}

function updateDolulukDataFromWebSocket(data) {
    console.log('Doluluk verisi güncellendi:', data);
    
    // Plastik hazne doluluk
    updateSingleDolulukBar('plastik-doluluk', 'plastic-fill', data.plastik, '#3b82f6');
    
    // Metal hazne doluluk  
    updateSingleDolulukBar('metal-doluluk', 'metal-fill', data.metal, '#9ca3af');
    
    // Cam hazne doluluk
    updateSingleDolulukBar('cam-doluluk', 'glass-fill', data.cam, '#10b981');
}

function updateSingleDolulukBar(textId, fillId, percentage, defaultColor) {
    const textEl = document.getElementById(textId);
    const fillEl = document.getElementById(fillId);
    
    if (textEl) {
        textEl.textContent = `${percentage}%`;
    }
    
    if (fillEl) {
        // Mevcut height değerini computed style'dan al
        const computedStyle = window.getComputedStyle(fillEl);
        const currentHeight = computedStyle.height;
        const currentHeightValue = parseFloat(currentHeight) || 0;
        
        // Container'ın yüksekliğini al
        const containerHeight = fillEl.parentElement.offsetHeight;
        const currentPercentage = (currentHeightValue / containerHeight) * 100;
        
        // Eğer değer aynıysa güncelleme yapma (tolerance: 1%)
        if (Math.abs(currentPercentage - percentage) < 1) {
            return;
        }
        
        // Transition'ı kapat
        fillEl.style.transition = 'none';
        
        // Değeri ayarla
        fillEl.style.height = `${percentage}%`;
        
        // Doluluk seviyesine göre renk değiştir
        if (percentage >= 80) {
            fillEl.style.backgroundColor = '#ef4444'; // Kırmızı - Dolu
        } else if (percentage >= 50) {
            fillEl.style.backgroundColor = '#f59e0b'; // Sarı - Orta
        } else {
            fillEl.style.backgroundColor = defaultColor; // Varsayılan renk
        }
        
        // Kısa bir gecikme sonra transition'ı tekrar aç
        requestAnimationFrame(() => {
            fillEl.style.transition = `height ${TIMING_CONFIG.UI_UPDATES.FILL_LEVEL_TRANSITION}ms ease-out, background-color ${TIMING_CONFIG.UI_UPDATES.COLOR_TRANSITION}ms ease-out`;
        });
    }
}

function updateDolulukHealthFromSDS(sdsData) {
    console.log('Doluluk sağlık durumu güncellendi:', sdsData);
    
    // Plastik hazne sağlık durumu
    if (sdsData.sds_plastik) {
        updateSingleDolulukHealth('plastic', sdsData.sds_plastik);
    }
    
    // Metal hazne sağlık durumu
    if (sdsData.sds_metal) {
        updateSingleDolulukHealth('metal', sdsData.sds_metal);
    }
    
    // Cam hazne sağlık durumu
    if (sdsData.sds_cam) {
        updateSingleDolulukHealth('glass', sdsData.sds_cam);
    }
}

function updateSingleDolulukHealth(hazneType, sensorData) {
    const healthEl = document.getElementById(`${hazneType}-health`);
    if (healthEl) {
        healthEl.innerHTML = `${sensorData.saglik} <span class="w-2 h-2 rounded-full"></span>`;
        const healthDot = healthEl.querySelector('.w-2.h-2.rounded-full');
        
        // Sağlık durumunu temizle ve küçük harfe çevir
        const cleanSaglik = sensorData.saglik.trim().toLowerCase();
        
        // Sağlık durumuna göre renk ayarla
        if (healthDot) {
            healthDot.classList.remove('bg-gray-500', 'bg-green-500', 'bg-red-500', 'bg-yellow-500');
            
            if (cleanSaglik === 'normal') {
                healthDot.classList.add('bg-green-500');
            } else if (cleanSaglik.includes('bağlantı kopuk') || cleanSaglik.includes('kopuk') || cleanSaglik.includes('baglanti kopuk')) {
                healthDot.classList.add('bg-red-500');
            } else {
                healthDot.classList.add('bg-yellow-500');
            }
        }
    }
}


// Sadece durum güncellemelerini başlat (hafif işlemler)
function startStatusUpdates() {
    // Eğer zaten çalışıyorsa durdur
    stopStatusUpdates();
    
    // Ping ile sağlık durumu kontrolü (15 saniyede bir - güvenli aralık)
    //sistemDurumInterval = setInterval(pingKartlar, 1000); // 15 saniyede bir - GÜVENLİ
}

// Durum güncellemelerini durdur
function stopStatusUpdates() {
    if (sistemDurumInterval) {
        clearInterval(sistemDurumInterval);
        sistemDurumInterval = null;
    }
    // SDS güncellemelerini de durdur
    stopSdsUpdates();
    // Doluluk oranı güncellemelerini de durdur
    stopDolulukUpdates();
}

// Eski kuyruk sistemi kaldırıldı - yeni CardQueueManager kullanılıyor

// Kartları ping ile sağlık durumunu kontrol et
async function pingKartlar() {
    // Ağırlık ölçümü aktifse ping atma
    if (typeof agirlikOlcAktif !== 'undefined' && agirlikOlcAktif) {
        console.log('📏 Ağırlık ölçümü aktif - Ping atlanıyor');
        return;
    }
    
    // Kuyruklarda bekleyen işlem varsa ping atma
    if (sensorQueueManager.queue.length > 0 || motorQueueManager.queue.length > 0 || systemQueueManager.queue.length > 0) {
        console.log('⏳ Kuyruklarda bekleyen işlem var - Ping atlanıyor');
        return;
    }
    
    // Kuyruklar işleniyorsa ping atma
    if (sensorQueueManager.isProcessing || motorQueueManager.isProcessing || systemQueueManager.isProcessing) {
        console.log('🔄 Kuyruklar işleniyor - Ping atlanıyor');
        return;
    }
    
    if (isPingInProgress) {
        return; // Zaten ping devam ediyorsa atla
    }
    
    isPingInProgress = true;
    console.log('📡 Ping işlemi başlatılıyor...');
    
    try {
        // Sadece mevcut bağlantıları ping et (port arama yapma)
        const sensorData = await pingSingleCard('sensor');
        const motorData = await pingSingleCard('motor');
        
        // Ping sonuçlarına göre durum göstergelerini güncelle
        updateConnectionStatusFromPing(sensorData, motorData);
        
    } catch (error) {
        console.log('📡 Ping genel hatası:', error.message);
        // Hata durumunda gri göster
        setStatusIndicatorsGray();
    } finally {
        isPingInProgress = false;
        console.log('📡 Ping işlemi tamamlandı');
    }
}

// Tek kart ping işlemi (güvenli)
async function pingSingleCard(cardType) {
    const controller = new AbortController();
    const timeout = setTimeout(() => {
        controller.abort();
    }, TIMING_CONFIG.API_TIMEOUTS.PING_TIMEOUT); // Ping timeout
    
    try {
        const response = await fetch(`${API_BASE}/${cardType}/ping`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`📡 ${cardType.toUpperCase()} ping başarılı:`, data.saglikli ? 'Sağlıklı' : 'Sağlıksız');
        return data;
        
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log(`📡 ${cardType.toUpperCase()} ping timeout - atlanıyor`);
        } else {
            console.log(`📡 ${cardType.toUpperCase()} ping hatası:`, error.message);
        }
        
        // Hata durumunda varsayılan değer döndür
        return {
            saglikli: false,
            message: `Ping hatası: ${error.message}`,
            error: true
        };
    } finally {
        clearTimeout(timeout);
    }
}

// Ping sonuçlarına göre durum göstergelerini güncelle
function updateConnectionStatusFromPing(sensorData, motorData) {
    // Sensör kartı durumu
    const sensorHealthy = sensorData && sensorData.saglikli === true;
    updateSingleConnectionStatus('sensor', sensorHealthy);
    
    // Motor kartı durumu
    const motorHealthy = motorData && motorData.saglikli === true;
    updateSingleConnectionStatus('motor', motorHealthy);
}

// Tek bir kartın durum göstergesini güncelle
function updateSingleConnectionStatus(cardType, isHealthy) {
    const isSensor = cardType === 'sensor';
    const tabId = isSensor ? 'tab-btn-sensors' : 'tab-btn-motors';
    const statusId = isSensor ? 'sensor-connection-status' : 'motor-connection-status';
    const cardName = isSensor ? 'Sensör Kartı' : 'Motor Kartı';
    
    // Sekme başlığını güncelle
    const tab = document.getElementById(tabId);
    if (tab) {
        if (isHealthy) {
            tab.innerHTML = `${cardName} <span class="text-green-400">●</span>`;
        } else {
            tab.innerHTML = `${cardName} <span class="text-red-400">●</span>`;
        }
    }
    
    // Bağlantı durumu göstergesini güncelle
    const statusElement = document.getElementById(statusId);
    if (statusElement) {
        const dot = statusElement.querySelector('div');
        const text = statusElement.querySelector('span');
        
        if (dot) {
            if (isHealthy) {
                dot.className = 'w-2 h-2 rounded-full bg-green-500';
            } else {
                dot.className = 'w-2 h-2 rounded-full bg-red-500';
            }
        }
        
        if (text) {
            if (isHealthy) {
                text.textContent = 'Bağlı';
                text.className = 'text-xs text-green-400';
            } else {
                text.textContent = 'Bağlantı Yok';
                text.className = 'text-xs text-red-400';
            }
        }
    }
}

// Durum göstergelerini gri yap (bakım modu pasifken)
function setStatusIndicatorsGray() {
    // Sekme başlıklarındaki durum göstergelerini gri yap
    const sensorTab = document.getElementById('tab-btn-sensors');
    const motorTab = document.getElementById('tab-btn-motors');
    
    if (sensorTab) {
        sensorTab.innerHTML = `Sensör Kartı <span class="text-gray-400">●</span>`;
    }
    
    if (motorTab) {
        motorTab.innerHTML = `Motor Kartı <span class="text-gray-400">●</span>`;
    }
    
    // Bağlantı & Kontroller bölümündeki durum göstergelerini gri yap
    const sensorConnectionStatus = document.getElementById('sensor-connection-status');
    const motorConnectionStatus = document.getElementById('motor-connection-status');
    
    if (sensorConnectionStatus) {
        const dot = sensorConnectionStatus.querySelector('div');
        const text = sensorConnectionStatus.querySelector('span');
        
        if (dot) {
            dot.className = 'w-2 h-2 rounded-full bg-gray-500';
        }
        if (text) {
            text.textContent = 'Bakım Modu Pasif';
            text.className = 'text-xs text-gray-400';
        }
    }
    
    if (motorConnectionStatus) {
        const dot = motorConnectionStatus.querySelector('div');
        const text = motorConnectionStatus.querySelector('span');
        
        if (dot) {
            dot.className = 'w-2 h-2 rounded-full bg-gray-500';
        }
        if (text) {
            text.textContent = 'Bakım Modu Pasif';
            text.className = 'text-xs text-gray-400';
        }
    }
}

// Periyodik güncellemeleri başlat (ağır işlemler - sadece bakım modu aktifken)
function startPeriodicUpdates() {
    // Eğer zaten çalışıyorsa durdur
    stopPeriodicUpdates();
    
    // Ağır periyodik güncellemeleri başlat
    sensorDegerInterval = setInterval(sensorDegerleriniGuncelle, TIMING_CONFIG.EMBEDDED_COMMANDS.SENSOR_UPDATE_INTERVAL);
    genelDurumInterval = setInterval(updateGeneralStatus, TIMING_CONFIG.EMBEDDED_COMMANDS.GENERAL_STATUS_INTERVAL);

    
    // Hazne doluluk güncelleme - KALDIRILDI: WebSocket'ten geliyor
}

// Periyodik güncellemeleri durdur (ağır işlemler)
function stopPeriodicUpdates() {
    if (sensorDegerInterval) {
        clearInterval(sensorDegerInterval);
        sensorDegerInterval = null;
    }
    if (genelDurumInterval) {
        clearInterval(genelDurumInterval);
        genelDurumInterval = null;
    }
}

// Ana başlatma fonksiyonu
function initializeBakim() {
    setupTabControl();
    setupToggle();
    setupSensorControls();
    setupMotorControls();
    setupPlaceholderFunctions();
    setupSafetyControls();
    toleransSekmesiKurulum();
    
    // İlk durum güncellemesi
    sistemDurumunuGuncelle();
    sensorDegerleriniGuncelle();
    butonlariGuncelle();
    updateGeneralStatus();
    
    // WebSocket bağlantısını her zaman başlat
    connectWebSocket();
    
    // Sadece bakım modu aktifken tüm işlemleri başlat
    if (bakimModuAktif) {
        startStatusUpdates();
        startPeriodicUpdates();
        startSdsUpdates();
        startDolulukUpdates();
    } else {
        // Bakım modu pasifken durum göstergelerini gri yap
        setStatusIndicatorsGray();
    }
}

// Yeni özellikler için fonksiyonlar

// Hızlı kontroller
async function diagnosticBaslat() {
    try {
        showMessage('Diagnostik başlatılıyor...');
        const response = await fetch(`${API_BASE}/sistem/durum`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            showMessage('Diagnostik tamamlandı - Sistem sağlıklı');
        } else {
            showMessage('Diagnostik tamamlandı - Sistem sorunları tespit edildi', true);
        }
    } catch (error) {
        showMessage('Diagnostik hatası: ' + error.message, true);
    }
}

// Tüm motorları durdur fonksiyonu
async function tumMotorlarDur() {
    try {
        console.log('🛑 Tüm motorlar durduruluyor (Modbus ready HAYIR)');
        
        // Önce uyarı ekranını göster
        await uyariEkraniGoster();
        
        const response = await fetch(`${API_BASE}/motor/motorlari-iptal`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            console.log('✅ Tüm motorlar başarıyla durduruldu');
            showMessage('🛑 Modbus ready HAYIR - Tüm motorlar durduruldu', true);
        } else {
            console.warn('⚠️ Motor durdurma başarısız:', data.message);
            showMessage('⚠️ Motor durdurma başarısız: ' + data.message, true);
        }
    } catch (error) {
        console.error('❌ Motor durdurma hatası:', error);
        showMessage('❌ Motor durdurma hatası: ' + error.message, true);
    }
}

async function depoyuBosalt() {
    try {
        showMessage('Depo boşaltılıyor...');
        // Tüm motorları durdur
        await fetch(`${API_BASE}/motor/motorlari-iptal`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        // AC motorları durdur
        await fetch(`${API_BASE}/ac-motor/tum-motorlar-dur`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        showMessage('Depo boşaltma tamamlandı');
    } catch (error) {
        showMessage('Depo boşaltma hatası: ' + error.message, true);
    }
}

async function sistemiYenidenBaslat() {
    try {
        showMessage('Sistem yeniden başlatılıyor...');
        const response = await fetch(`${API_BASE}/sistem/reset`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            showMessage('Sistem yeniden başlatıldı');
        } else {
            showMessage('Sistem yeniden başlatma hatası: ' + data.message, true);
        }
    } catch (error) {
        showMessage('Sistem yeniden başlatma hatası: ' + error.message, true);
    }
}

// AC Motor kontrolü
function setupAcMotor(prefix) {
    const fwdBtn = document.getElementById(`${prefix}-fwd-btn`);
    const revBtn = document.getElementById(`${prefix}-rev-btn`);
    const stopBtn = document.getElementById(`${prefix}-stop-btn`);
    const gears = document.getElementById(`${prefix}-gears`);
    
    if (!fwdBtn || !revBtn || !stopBtn || !gears) return;
    
    let isRunning = false;
    let currentDirection = "Duruyor";

    const updateMotorDisplay = (running, direction = "Duruyor") => {
        const setFreqEl = document.getElementById(`${prefix}-set-freq`);
        const outFreqEl = document.getElementById(`${prefix}-out-freq`);
        const voltageEl = document.getElementById(`${prefix}-voltage`);
        const currentEl = document.getElementById(`${prefix}-current`);
        const powerEl = document.getElementById(`${prefix}-power`);
        const busVoltageEl = document.getElementById(`${prefix}-bus-voltage`);
        const tempEl = document.getElementById(`${prefix}-temp`);
        const directionEl = document.getElementById(`${prefix}-direction`);
        const statusEl = document.getElementById(`${prefix}-status`);
        const readyEl = document.getElementById(`${prefix}-ready`);
        const faultEl = document.getElementById(`${prefix}-fault`);

        if (running) {
            if (outFreqEl) outFreqEl.textContent = '50.0 Hz';
            if (voltageEl) voltageEl.textContent = '220.0 V';
            if (currentEl) currentEl.textContent = '1.5 A';
            if (powerEl) powerEl.textContent = '330.0 W';
            if (busVoltageEl) busVoltageEl.textContent = '310.0 V';
            if (tempEl) tempEl.textContent = '35.0 °C';
            if (directionEl) directionEl.textContent = direction;
            if (statusEl) statusEl.textContent = 'Çalışıyor';
            if (readyEl) {
                readyEl.textContent = 'Hayır';
                readyEl.classList.remove('text-green-400');
                readyEl.classList.add('text-red-400');
            }
        } else {
            if (outFreqEl) outFreqEl.textContent = '0.0 Hz';
            if (voltageEl) voltageEl.textContent = '0.0 V';
            if (currentEl) currentEl.textContent = '0.0 A';
            if (powerEl) powerEl.textContent = '0.0 W';
            if (busVoltageEl) busVoltageEl.textContent = '310.0 V';
            if (tempEl) tempEl.textContent = '35.0 °C';
            if (directionEl) directionEl.textContent = 'Duruyor';
            if (statusEl) statusEl.textContent = 'Çalışmıyor';
            if (readyEl) {
                readyEl.textContent = 'Evet';
                readyEl.classList.add('text-green-400');
                readyEl.classList.remove('text-red-400');
            }
            if (faultEl) {
                faultEl.textContent = 'Yok';
                faultEl.classList.add('text-green-400');
                faultEl.classList.remove('text-red-400');
            }
        }
    };

    const startMotor = async (direction, motorType) => {
        try {
            const endpoint = motorType === 'crusher' ? 'ezici' : 'kirici';
            const directionEndpoint = direction === 'İleri' ? 'ileri' : 'geri';
            const response = await fetch(`${API_BASE}/ac-motor/${endpoint}-${directionEndpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                isRunning = true;
                currentDirection = direction;
                if (gears) {
                    gears.classList.remove('spinning', 'spinning-rev');
                    if (direction === 'İleri') {
                        gears.classList.add('spinning');
                    } else {
                        gears.classList.add('spinning-rev');
                    }
                }
                updateMotorDisplay(true, direction);
                showMessage(`${motorType} motor ${direction} başlatıldı`);
            } else {
                showMessage(`${motorType} motor başlatılamadı: ${data.message}`, true);
            }
        } catch (error) {
            showMessage(`${motorType} motor hatası: ${error.message}`, true);
        }
    };

    const stopMotor = async (motorType) => {
        try {
            const endpoint = motorType === 'crusher' ? 'ezici' : 'kirici';
            const response = await fetch(`${API_BASE}/ac-motor/${endpoint}-dur`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                isRunning = false;
                currentDirection = "Duruyor";
                if (gears) {
                    gears.classList.remove('spinning', 'spinning-rev');
                }
                updateMotorDisplay(false);
                showMessage(`${motorType} motor durduruldu`);
            } else {
                showMessage(`${motorType} motor durdurulamadı: ${data.message}`, true);
            }
        } catch (error) {
            showMessage(`${motorType} motor dur hatası: ${error.message}`, true);
        }
    };

    fwdBtn.addEventListener('click', () => {
        const motorType = prefix === 'crusher' ? 'crusher' : 'breaker';
        startMotor("İleri", motorType);
    });
    
    revBtn.addEventListener('click', () => {
        const motorType = prefix === 'crusher' ? 'crusher' : 'breaker';
        startMotor("Geri", motorType);
    });
    
    stopBtn.addEventListener('click', () => {
        const motorType = prefix === 'crusher' ? 'crusher' : 'breaker';
        stopMotor(motorType);
    });

    updateMotorDisplay(false);
}

// Hazne doluluk güncelleme - KALDIRILDI: updateSingleDolulukBar kullanılıyor

// Hazne doluluk verilerini API'den al - KALDIRILDI: WebSocket kullanılıyor

// Kalibrasyon fonksiyonları
function showCalibrationStatus(message) {
    const statusElement = document.getElementById('calibration-status');
    if (statusElement) {
        statusElement.textContent = message;
        setTimeout(() => {
            statusElement.textContent = '';
        }, TIMING_CONFIG.UI_UPDATES.MESSAGE_DISPLAY_TIME);
    }
}

async function calibrateDiverter() {
    try {
        const response = await fetch(`${API_BASE}/kalibrasyon/yonlendirici`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            // Animasyon göster
            const diverterVisual = document.getElementById('diverter-visual');
            if (diverterVisual) {
                diverterVisual.style.animation = `diverter-spin-rev 1s linear`;
                setTimeout(() => {
                    diverterVisual.style.animation = '';
                    diverterVisual.style.transform = '';
                }, 1000);
            }
            return true;
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('Yönlendirici kalibrasyon hatası:', error);
        return false;
    }
}

async function calibrateFlap() {
    try {
        const response = await fetch(`${API_BASE}/kalibrasyon/klape`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            // Animasyon göster
            const flapVisual = document.getElementById('flap-visual');
            if (flapVisual) {
                flapVisual.style.transform = 'rotate(0deg)';
            }
            return true;
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('Klape kalibrasyon hatası:', error);
        return false;
    }
}

async function calibrateDiverterSensor() {
    try {
        const response = await fetch(`${API_BASE}/kalibrasyon/yonlendirici-sensor`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            // Animasyon göster
            const rays = document.getElementById('diverter-opt-rays');
            if (rays) {
                rays.classList.add('teaching-rays');
                setTimeout(() => {
                    rays.classList.remove('teaching-rays');
                }, 5000);
            }
            return true;
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('Yönlendirici sensör kalibrasyon hatası:', error);
        return false;
    }
}

// Test senaryoları
async function runScenario(scenario) {
    if (isTesting && !stopLoop) return; 
    isTesting = true;
    
    const testStatus = document.getElementById('test-status');
    const opt1009_output = document.getElementById('opt1009-output');
    const opt1009_blocker = document.getElementById('opt1009-blocker');
    const diverter_opt_output = document.getElementById('diverter-opt-output');
    const diverter_opt_blocker = document.getElementById('diverter-opt-blocker');
    const conveyorAnimation = document.getElementById('conveyor-animation');
    const diverterVisual = document.getElementById('diverter-visual');
    const flapVisual = document.getElementById('flap-visual');

    try {
        if (testStatus) testStatus.textContent = `${scenario.charAt(0).toUpperCase() + scenario.slice(1)} senaryosu başlatılıyor...`;
        
        // Senaryo endpoint'ini çağır
        const endpoint = scenario === 'plastik' ? 'plastik-senaryo' : 
                        scenario === 'metal' ? 'metal-senaryo' : 'cam-senaryo';
        
        const response = await fetch(`${API_BASE}/test/${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.status !== 'success') {
            throw new Error(data.message);
        }
        
        // Görsel animasyonları göster
        if (testStatus) testStatus.textContent = "Ürün giriş sensöründe...";
        if (opt1009_output) opt1009_output.innerText = 1;
        if (opt1009_blocker) opt1009_blocker.classList.remove('hidden');
        await new Promise(resolve => setTimeout(resolve, 1500));
        if (opt1009_output) opt1009_output.innerText = '--';
        if (opt1009_blocker) opt1009_blocker.classList.add('hidden');

        if (testStatus) testStatus.textContent = "Ürün konveyörde ilerliyor...";
        if (conveyorAnimation) conveyorAnimation.classList.add('conveyor-running-forward');
        await new Promise(resolve => setTimeout(resolve, 3000));
        if (conveyorAnimation) conveyorAnimation.classList.remove('conveyor-running-forward');

        if (testStatus) testStatus.textContent = "Ürün yönlendirici sensöründe...";
        if (diverter_opt_output) diverter_opt_output.innerText = 1;
        if (diverter_opt_blocker) diverter_opt_blocker.classList.remove('hidden');
        await new Promise(resolve => setTimeout(resolve, 1500));
        if (diverter_opt_output) diverter_opt_output.innerText = '--';
        if (diverter_opt_blocker) diverter_opt_blocker.classList.add('hidden');
        
        if(scenario === 'plastik' || scenario === 'metal') {
            if (testStatus) testStatus.textContent = "Yönlendirici 'Plastik/Metal' konumuna dönüyor...";
            if (diverterVisual) {
                diverterVisual.style.animation = `diverter-spin-rev 2s linear`;
                await new Promise(resolve => setTimeout(resolve, 2000));
                diverterVisual.style.animation = '';
                diverterVisual.style.transform = 'rotate(-45deg)';
            }

            if (scenario === 'plastik') {
                if (testStatus) testStatus.textContent = "Klape konumu 'Plastik' olarak ayarlanıyor...";
                if (flapVisual && flapVisual.style.transform === 'rotate(90deg)') {
                    flapVisual.style.transform = 'rotate(0deg)';
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
            } else { // metal
                if (testStatus) testStatus.textContent = "Klape 'Metal' konumuna ayarlanıyor...";
                if (flapVisual && flapVisual.style.transform !== 'rotate(90deg)') {
                    flapVisual.style.transform = 'rotate(90deg)';
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
            }

            await new Promise(resolve => setTimeout(resolve, 1000));
            if (testStatus) testStatus.textContent = "Ezici motor çalıştırılıyor...";
            await new Promise(resolve => setTimeout(resolve, 3000)); 
            if (testStatus) testStatus.textContent = "Ezme işlemi tamamlandı.";
            await new Promise(resolve => setTimeout(resolve, 1000));

        } else if (scenario === 'cam') {
            if (testStatus) testStatus.textContent = "Yönlendirici 'Cam' konumuna dönüyor...";
            if (diverterVisual) {
                diverterVisual.style.animation = `diverter-spin 2s linear`;
                await new Promise(resolve => setTimeout(resolve, 2000));
                diverterVisual.style.animation = '';
                diverterVisual.style.transform = 'rotate(45deg)';
            }

            await new Promise(resolve => setTimeout(resolve, 1000));
            if (testStatus) testStatus.textContent = "Kırıcı motor çalıştırılıyor...";
            await new Promise(resolve => setTimeout(resolve, 3000));
            if (testStatus) testStatus.textContent = "Kırma işlemi tamamlandı.";
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        await new Promise(resolve => setTimeout(resolve, 1000));
        if (testStatus) testStatus.textContent = `${scenario.charAt(0).toUpperCase() + scenario.slice(1)} senaryosu tamamlandı!`;
        
        await new Promise(resolve => setTimeout(resolve, 1500));
        if (testStatus) testStatus.textContent = '';
        if (diverterVisual) diverterVisual.style.transform = '';
        
    } catch (error) {
        if (testStatus) testStatus.textContent = `Senaryo hatası: ${error.message}`;
        showMessage(`Test senaryosu hatası: ${error.message}`, true);
    } finally {
        isTesting = false;
    }
}

// DOM yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', () => {
    initializeBakim();
    
    // Tolerans ayarlarını yükle
    toleransAyarlariYukle();
    
    // Sayfa kapatılırken tüm işlemleri durdur (güvenlik için)
    window.addEventListener('beforeunload', function() {
        console.log('🛑 Sayfa kapatılıyor - tüm bakım işlemleri durduruluyor...');
        stopAllOperations();
    });
    
    // Sayfa görünürlük değiştiğinde kontrol et
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            console.log('🛑 Sayfa gizlendi - tüm bakım işlemleri durduruluyor...');
            stopAllOperations();
        }
    });
    
    // Yeni özellikler için event listener'lar
    const diagnosticBtn = document.getElementById('diagnostic-btn');
    if (diagnosticBtn) {
        diagnosticBtn.addEventListener('click', diagnosticBaslat);
    }
    
    const emptyTankBtn = document.getElementById('empty-tank-btn');
    if (emptyTankBtn) {
        emptyTankBtn.addEventListener('click', depoyuBosalt);
    }
    
    const restartSystemBtn = document.getElementById('restart-system-btn');
    if (restartSystemBtn) {
        restartSystemBtn.addEventListener('click', sistemiYenidenBaslat);
    }
    
    // AC Motor kontrolleri
    setupAcMotor('crusher');
    setupAcMotor('breaker');
    
    // Hazne doluluk güncelleme
    updateFillLevel('plastic', 65);
    updateFillLevel('metal', 80);
    updateFillLevel('glass', 45);
    
    // Kalibrasyon kontrolleri
    const calibrateDiverterBtn = document.getElementById('calibrate-diverter-btn');
    if (calibrateDiverterBtn) {
        calibrateDiverterBtn.addEventListener('click', async () => {
            if(isCalibrating) return;
            isCalibrating = true;
            showCalibrationStatus("Yönlendirici Motor kalibre ediliyor...");
            await calibrateDiverter();
            showCalibrationStatus('Yönlendirici Motor kalibrasyonu başarılı!');
            isCalibrating = false;
        });
    }
    
    const calibrateFlapBtn = document.getElementById('calibrate-flap-btn');
    if (calibrateFlapBtn) {
        calibrateFlapBtn.addEventListener('click', async () => {
            if(isCalibrating) return;
            isCalibrating = true;
            showCalibrationStatus("Klape Motor kalibre ediliyor...");
            await calibrateFlap();
            showCalibrationStatus('Klape Motor kalibrasyonu başarılı!');
            isCalibrating = false;
        });
    }
    
    const calibrateDiverterSensorBtn = document.getElementById('calibrate-diverter-sensor-btn');
    if (calibrateDiverterSensorBtn) {
        calibrateDiverterSensorBtn.addEventListener('click', async () => {
            if(isCalibrating) return;
            isCalibrating = true;
            showCalibrationStatus("Yönlendirici Sensör kalibre ediliyor...");
            await calibrateDiverterSensor();
            showCalibrationStatus('Yönlendirici Sensör kalibrasyonu başarılı!');
            isCalibrating = false;
        });
    }
    
    const calibrateAllBtn = document.getElementById('calibrate-all-btn');
    if (calibrateAllBtn) {
        calibrateAllBtn.addEventListener('click', async () => {
            if(isCalibrating) return;
            isCalibrating = true;
            showCalibrationStatus("Tüm sistem kalibre ediliyor...");
            await Promise.all([calibrateDiverter(), calibrateFlap(), calibrateDiverterSensor()]);
            showCalibrationStatus('Tüm kalibrasyonlar başarılı!');
            isCalibrating = false;
        });
    }
    
    // Test senaryoları
    const testPlasticBtn = document.getElementById('test-plastic-btn');
    if (testPlasticBtn) {
        testPlasticBtn.addEventListener('click', () => runScenario('plastik'));
    }
    
    const testMetalBtn = document.getElementById('test-metal-btn');
    if (testMetalBtn) {
        testMetalBtn.addEventListener('click', () => runScenario('metal'));
    }
    
    const testGlassBtn = document.getElementById('test-glass-btn');
    if (testGlassBtn) {
        testGlassBtn.addEventListener('click', () => runScenario('cam'));
    }
    
    const startStopScenariosBtn = document.getElementById('start-stop-scenarios-btn');
    if (startStopScenariosBtn) {
        startStopScenariosBtn.addEventListener('click', () => {
            if (stopLoop) {
                stopLoop = false;
                isTesting = false;
                startStopScenariosBtn.textContent = 'Senaryoları Durdur';
                startStopScenariosBtn.classList.remove('bg-orange-500', 'hover:bg-orange-600');
                startStopScenariosBtn.classList.add('bg-red-600', 'hover:bg-red-700');
                
                // Senaryo döngüsünü başlat
                const scenarioLoop = async () => {
                    while (!stopLoop) {
                        const scenarios = ['plastik', 'metal', 'cam'];
                        const randomScenario = scenarios[Math.floor(Math.random() * scenarios.length)];
                        await runScenario(randomScenario);
                        if (stopLoop) break;
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    }
                    
                    startStopScenariosBtn.textContent = 'Senaryoları Başlat';
                    startStopScenariosBtn.classList.remove('bg-red-600', 'hover:bg-red-700');
                    startStopScenariosBtn.classList.add('bg-orange-500', 'hover:bg-orange-600');
                    isTesting = false;
                };
                
                scenarioLoop();
            } else {
                stopLoop = true;
                startStopScenariosBtn.textContent = 'Durduruluyor...';
                startStopScenariosBtn.disabled = true;
            }
        });
    }
});

// Alarm durumlarını güncelleyen fonksiyon
function updateAlarmDisplayFromWebSocket(data) {
    console.log('Alarm display güncelleniyor:', data);
    
    // Konveyor alarm
    if (data.konveyor_alarm !== undefined) {
        const conveyorAlarmLed = document.getElementById('conveyor-alarm-led');
        if (conveyorAlarmLed) {
            if (data.konveyor_alarm) {
                conveyorAlarmLed.classList.remove('bg-green-500');
                conveyorAlarmLed.classList.add('bg-red-500');
                console.log('Konveyor alarm aktif - LED kırmızı');
            } else {
                conveyorAlarmLed.classList.remove('bg-red-500');
                conveyorAlarmLed.classList.add('bg-green-500');
                console.log('Konveyor alarm pasif - LED yeşil');
            }
        }
    }
    
    // Yönlendirici alarm
    if (data.yonlendirici_alarm !== undefined) {
        const diverterAlarmLed = document.getElementById('diverter-alarm-led');
        if (diverterAlarmLed) {
            if (data.yonlendirici_alarm) {
                diverterAlarmLed.classList.remove('bg-green-500');
                diverterAlarmLed.classList.add('bg-red-500');
                console.log('Yönlendirici alarm aktif - LED kırmızı');
            } else {
                diverterAlarmLed.classList.remove('bg-red-500');
                diverterAlarmLed.classList.add('bg-green-500');
                console.log('Yönlendirici alarm pasif - LED yeşil');
            }
        }
    }
    
    // Klape alarm
    if (data.seperator_alarm !== undefined) {
        const flapAlarmLed = document.getElementById('flap-alarm-led');
        if (flapAlarmLed) {
            if (data.seperator_alarm) {
                flapAlarmLed.classList.remove('bg-green-500');
                flapAlarmLed.classList.add('bg-red-500');
                console.log('Klape alarm aktif - LED kırmızı');
            } else {
                flapAlarmLed.classList.remove('bg-red-500');
                flapAlarmLed.classList.add('bg-green-500');
                console.log('Klape alarm pasif - LED yeşil');
            }
        }
    }
}

// Reset butonları için event listener'lar
document.addEventListener('DOMContentLoaded', function() {
    // Sensör kartı reset butonu
    const resetSensorBtn = document.getElementById('reset-sensor-card-btn');
    if (resetSensorBtn) {
        resetSensorBtn.addEventListener('click', async () => {
            if (resetSensorBtn.disabled) return;
            
            // Önce sensör durumunu kontrol et
            try {
                const durumResponse = await fetch(`${API_BASE}/sensor/durum`);
                const durumData = await durumResponse.json();
                
                if (!durumData.bagli) {
                    showMessage('✗ Sensör kartı bağlı değil. Sistem çalıştırılmamış olabilir.', false);
                    return;
                }
            } catch (error) {
                showMessage('✗ Sensör durum kontrolü başarısız: ' + error.message, false);
                return;
            }
            
            resetSensorBtn.disabled = true;
            resetSensorBtn.textContent = 'Resetting...';
            
            try {
                const response = await fetch(`${API_BASE}/sensor/reset`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                
                if (data.message && data.message.includes('resetlendi')) {
                    showMessage('✓ Sensör kartı başarıyla resetlendi', true);
                } else {
                    showMessage('✗ Sensör reset hatası: ' + (data.message || 'Bilinmeyen hata'), false);
                }
            } catch (error) {
                showMessage('✗ Sensör reset hatası: ' + error.message, false);
                console.error('Sensör reset API hatası:', error);
            } finally {
                resetSensorBtn.disabled = false;
                resetSensorBtn.textContent = 'Kartı Resetle';
            }
        });
    }
    
    // Motor kartı reset butonu
    const resetMotorBtn = document.getElementById('reset-motor-card-btn');
    if (resetMotorBtn) {
        resetMotorBtn.addEventListener('click', async () => {
            if (resetMotorBtn.disabled) return;
            
            // Önce motor durumunu kontrol et
            try {
                const durumResponse = await fetch(`${API_BASE}/motor/durum`);
                const durumData = await durumResponse.json();
                
                if (!durumData.bagli) {
                    showMessage('✗ Motor kartı bağlı değil. Sistem çalıştırılmamış olabilir.', false);
                    return;
                }
            } catch (error) {
                showMessage('✗ Motor durum kontrolü başarısız: ' + error.message, false);
                return;
            }
            
            resetMotorBtn.disabled = true;
            resetMotorBtn.textContent = 'Resetting...';
            
            try {
                const response = await fetch(`${API_BASE}/motor/reset`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                
                if (data.message && data.message.includes('resetlendi')) {
                    // Motor toggle'larını kapat
                    turnOffMotorToggles();
                    showMessage('✓ Motor kartı başarıyla resetlendi. Motorlar kapatıldı.', true);
                } else {
                    showMessage('✗ Motor reset hatası: ' + (data.message || 'Bilinmeyen hata'), false);
                }
            } catch (error) {
                showMessage('✗ Motor reset hatası: ' + error.message, false);
                console.error('Motor reset API hatası:', error);
            } finally {
                resetMotorBtn.disabled = false;
                resetMotorBtn.textContent = 'Kartı Resetle';
            }
        });
    }
});

// --- GÜVENLİK KARTI KONTROLLERİ ---
function setupFanControl() {
    const fanSvg = document.getElementById('fan-svg');
    const speedSlider = document.getElementById('fan-speed-slider');
    const speedInput = document.getElementById('fan-speed-input');
    const onBtn = document.getElementById('fan-on-btn');
    const offBtn = document.getElementById('fan-off-btn');

    if (!fanSvg || !speedSlider || !speedInput || !onBtn || !offBtn) return;

    const updateFanState = (speed) => {
        const value = Math.max(0, Math.min(100, parseInt(speed, 10)));
        speedSlider.value = value;
        speedInput.value = value;

        if (value > 0) {
            fanSvg.classList.add('fan-active', 'text-blue-400');
            fanSvg.classList.remove('text-gray-500');
            // Speed affects animation duration. Faster speed = shorter duration.
            const duration = (2.5 - (value / 100) * 2.3).toFixed(2);
            fanSvg.style.setProperty('--fan-duration', `${duration}s`);
            
        } else {
            fanSvg.classList.remove('fan-active', 'text-blue-400');
            fanSvg.classList.add('text-gray-500');
            fanSvg.style.removeProperty('--fan-duration');
        }
    };

    onBtn.addEventListener('click', async () => {
        try {
            const response = await fetch(`${API_BASE}/guvenlik/fan-ac`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                updateFanState(speedInput.value > 0 ? speedInput.value : 100);
                showMessage(data.message);
            } else {
                showMessage(data.message, true);
            }
        } catch (error) {
            showMessage(`Fan açma hatası: ${error.message}`, true);
        }
    });
    
    offBtn.addEventListener('click', async () => {
        try {
            const response = await fetch(`${API_BASE}/guvenlik/fan-kapat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                updateFanState(0);
                showMessage(data.message);
            } else {
                showMessage(data.message, true);
            }
        } catch (error) {
            showMessage(`Fan kapatma hatası: ${error.message}`, true);
        }
    });
    speedSlider.addEventListener('input', async () => {
        const hiz = parseInt(speedSlider.value);
        try {
            const response = await fetch(`${API_BASE}/guvenlik/fan-hiz?hiz=${hiz}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                updateFanState(hiz);
            } else {
                showMessage(data.message, true);
            }
        } catch (error) {
            showMessage(`Fan hız ayarlama hatası: ${error.message}`, true);
        }
    });
    
    speedInput.addEventListener('input', async () => {
        const hiz = parseInt(speedInput.value);
        try {
            const response = await fetch(`${API_BASE}/guvenlik/fan-hiz?hiz=${hiz}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                updateFanState(hiz);
            } else {
                showMessage(data.message, true);
            }
        } catch (error) {
            showMessage(`Fan hız ayarlama hatası: ${error.message}`, true);
        }
    });
    
    updateFanState(0); // Initial state
}

function setupMagneticSensor(prefix) {
    const visual = document.getElementById(`${prefix}-visual`);
    const statusLed = document.getElementById(`${prefix}-status-led`);
    const statusText = document.getElementById(`${prefix}-status-text`);
    
    if (!visual || !statusLed || !statusText) return null;
    
    const setActive = () => {
        visual.classList.remove('inactive');
        statusLed.classList.remove('bg-red-500');
        statusLed.classList.add('bg-green-500');
        statusText.textContent = 'Aktif (Kapak Kapalı)';
        statusText.classList.remove('text-red-400');
        statusText.classList.add('text-green-400');
    };

    const setPassive = () => {
         visual.classList.add('inactive');
        statusLed.classList.remove('bg-green-500');
        statusLed.classList.add('bg-red-500');
        statusText.textContent = 'Pasif (Kapak Açık)';
        statusText.classList.remove('text-green-400');
        statusText.classList.add('text-red-400');
    };
    
    return { setActive, setPassive };
}

function setupLockControl(prefix, sensorControls) {
    const visual = document.getElementById(`${prefix}-visual`);
    const statusLed = document.getElementById(`${prefix}-status-led`);
    const statusText = document.getElementById(`${prefix}-status-text`);
    const tongueLed = document.getElementById(`${prefix}-tongue-led`);
    const tongueText = document.getElementById(`${prefix}-tongue-text`);
    const openBtn = document.getElementById(`${prefix}-open-btn`);
    const closeBtn = document.getElementById(`${prefix}-close-btn`);

    if (!visual || !statusLed || !statusText || !tongueLed || !tongueText || !openBtn || !closeBtn) return;

    openBtn.addEventListener('click', async () => {
        try {
            const endpoint = prefix === 'top-lock' ? 'ust-kilit-ac' : 'alt-kilit-ac';
            const response = await fetch(`${API_BASE}/guvenlik/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                visual.classList.add('unlocked');
                statusLed.classList.remove('bg-red-500');
                statusLed.classList.add('bg-green-500');
                statusText.textContent = 'Kilit Açık';
                statusText.classList.remove('text-red-400');
                statusText.classList.add('text-green-400');

                tongueLed.classList.remove('bg-green-500');
                tongueLed.classList.add('bg-red-500');
                tongueText.textContent = 'Dil Yok';
                tongueText.classList.remove('text-green-400');
                tongueText.classList.add('text-red-400');

                if (sensorControls) sensorControls.setPassive();
                showMessage(data.message);
            } else {
                showMessage(data.message, true);
            }
        } catch (error) {
            showMessage(`Kilit açma hatası: ${error.message}`, true);
        }
    });

    closeBtn.addEventListener('click', async () => {
        try {
            const endpoint = prefix === 'top-lock' ? 'ust-kilit-kapat' : 'alt-kilit-kapat';
            const response = await fetch(`${API_BASE}/guvenlik/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                visual.classList.remove('unlocked');
                statusLed.classList.remove('bg-green-500');
                statusLed.classList.add('bg-red-500');
                statusText.textContent = 'Kilit Kapalı';
                statusText.classList.remove('text-green-400');
                statusText.classList.add('text-red-400');

                tongueLed.classList.remove('bg-red-500');
                tongueLed.classList.add('bg-green-500');
                tongueText.textContent = 'Dil Var';
                tongueText.classList.remove('text-red-400');
                tongueText.classList.add('text-green-400');

                if (sensorControls) sensorControls.setActive();
                showMessage(data.message);
            } else {
                showMessage(data.message, true);
            }
        } catch (error) {
            showMessage(`Kilit kapatma hatası: ${error.message}`, true);
        }
    });
}

function setupSafetyRelay() {
    const resetBtn = document.getElementById('safety-relay-reset-btn');
    const bypassAktifBtn = document.getElementById('bypass-aktif-btn');
    const bypassPasifBtn = document.getElementById('bypass-pasif-btn');
    const guvenlikKartResetBtn = document.getElementById('guvenlik-kart-reset-btn');
    
    const relayLed = document.getElementById('safety-relay-led');
    const relayText = document.getElementById('safety-relay-text');
    const bypassLed = document.getElementById('bypass-led');
    const bypassText = document.getElementById('bypass-text');

    if (!resetBtn || !bypassAktifBtn || !bypassPasifBtn || !relayLed || !relayText || !bypassLed || !bypassText) return;

    let isBypassActive = false;

    resetBtn.addEventListener('click', async () => {
        // Butonları devre dışı bırak
        resetBtn.disabled = true;
        bypassAktifBtn.disabled = true;
        bypassPasifBtn.disabled = true;

        // "Resetleniyor" durumuna ayarla
        relayLed.classList.remove('bg-red-500', 'bg-green-500');
        relayLed.classList.add('bg-yellow-500');
        relayText.textContent = 'Resetleniyor...';
        relayText.classList.remove('text-red-400', 'text-green-400');
        relayText.classList.add('text-yellow-400');

        try {
            const response = await fetch(`${API_BASE}/guvenlik/role-reset`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                // "Aktif" durumuna ayarla
                relayLed.classList.remove('bg-red-500', 'bg-yellow-500');
                relayLed.classList.add('bg-green-500');
                relayText.textContent = 'Röle Aktif';
                relayText.classList.remove('text-red-400', 'text-yellow-400');
                relayText.classList.add('text-green-400');
                showMessage(data.message);
            } else {
                showMessage(data.message, true);
            }
        } catch (error) {
            showMessage(`Röle reset hatası: ${error.message}`, true);
        } finally {
            // Butonları tekrar aktif et
            resetBtn.disabled = false;
            bypassAktifBtn.disabled = false;
            bypassPasifBtn.disabled = false;
        }
    });

    // Bypass Aktif butonu
    bypassAktifBtn.addEventListener('click', async () => {
        if (bypassAktifBtn.disabled) return;
        
        try {
            const response = await fetch(`${API_BASE}/guvenlik/role-bypass`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                isBypassActive = true;
                updateBypassUI(true);
                showMessage('✓ Bypass aktif edildi - Kilitler devre dışı', true);
                // Bypass aktif edildiğinde motorları aktif et
                motorlariAktifEt();
            } else {
                showMessage('✗ Bypass aktif edilemedi: ' + data.message, true);
            }
        } catch (error) {
            showMessage('✗ Bypass aktif etme hatası: ' + error.message, true);
        }
    });

    // Bypass Pasif butonu
    bypassPasifBtn.addEventListener('click', async () => {
        if (bypassPasifBtn.disabled) return;
        
        try {
            const response = await fetch(`${API_BASE}/guvenlik/role-bypass`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                isBypassActive = false;
                updateBypassUI(false);
                showMessage('✓ Bypass pasif edildi - Kilitler aktif', true);
                // Bypass pasif edildiğinde motorları iptal et
                motorlariIptalEt();
            } else {
                showMessage('✗ Bypass pasif edilemedi: ' + data.message, true);
            }
        } catch (error) {
            showMessage('✗ Bypass pasif etme hatası: ' + error.message, true);
        }
    });

    // Güvenlik kartı reset butonu
    if (guvenlikKartResetBtn) {
        guvenlikKartResetBtn.addEventListener('click', async () => {
            if (guvenlikKartResetBtn.disabled) return;
            
            // Onay iste
            if (!confirm('Güvenlik kartını resetlemek istediğinizden emin misiniz? Tüm güvenlik ayarları sıfırlanacak.')) {
                return;
            }
            
            guvenlikKartResetBtn.disabled = true;
            guvenlikKartResetBtn.textContent = 'Resetting...';
            
            try {
                const response = await fetch(`${API_BASE}/guvenlik/guvenlik-kart-reset`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Tüm güvenlik durumlarını sıfırla
                    resetAllSafetyStates();
                    showMessage('✓ Güvenlik kartı başarıyla resetlendi', true);
                } else {
                    showMessage('✗ Güvenlik kartı reset hatası: ' + data.message, true);
                }
            } catch (error) {
                showMessage('✗ Güvenlik kartı reset hatası: ' + error.message, true);
            } finally {
                guvenlikKartResetBtn.disabled = false;
                guvenlikKartResetBtn.textContent = 'Kartı Resetle';
            }
        });
    }
    
    // Başlangıçta bypass durumunu ayarla (varsayılan: pasif)
    updateBypassUI(false);
}

// Bypass UI durumunu güncelle
function updateBypassUI(isActive) {
    const bypassLed = document.getElementById('bypass-led');
    const bypassText = document.getElementById('bypass-text');
    const bypassAktifBtn = document.getElementById('bypass-aktif-btn');
    const bypassPasifBtn = document.getElementById('bypass-pasif-btn');
    
    if (isActive) {
        // Bypass aktif - kilitler devre dışı
        if (bypassLed) {
            bypassLed.classList.remove('bg-green-500');
            bypassLed.classList.add('bg-red-500');
        }
        if (bypassText) {
            bypassText.textContent = 'Kilitler Pasif';
            bypassText.classList.remove('text-green-400');
            bypassText.classList.add('text-red-400');
        }
        if (bypassAktifBtn) {
            bypassAktifBtn.classList.remove('bg-red-600', 'hover:bg-red-700');
            bypassAktifBtn.classList.add('bg-gray-600', 'hover:bg-gray-700');
            bypassAktifBtn.disabled = true;
        }
        if (bypassPasifBtn) {
            bypassPasifBtn.classList.remove('bg-gray-600', 'hover:bg-gray-700');
            bypassPasifBtn.classList.add('bg-green-600', 'hover:bg-green-700');
            bypassPasifBtn.disabled = false;
        }
    } else {
        // Bypass pasif - kilitler aktif
        if (bypassLed) {
            bypassLed.classList.remove('bg-red-500');
            bypassLed.classList.add('bg-green-500');
        }
        if (bypassText) {
            bypassText.textContent = 'Kilitler Aktif';
            bypassText.classList.remove('text-red-400');
            bypassText.classList.add('text-green-400');
        }
        if (bypassAktifBtn) {
            bypassAktifBtn.classList.remove('bg-gray-600', 'hover:bg-gray-700');
            bypassAktifBtn.classList.add('bg-red-600', 'hover:bg-red-700');
            bypassAktifBtn.disabled = false;
        }
        if (bypassPasifBtn) {
            bypassPasifBtn.classList.remove('bg-green-600', 'hover:bg-green-700');
            bypassPasifBtn.classList.add('bg-gray-600', 'hover:bg-gray-700');
            bypassPasifBtn.disabled = true;
        }
    }
}

// Motorları iptal et (güvenlik için)
async function motorlariIptalEt() {
    try {
        console.log('Motorlar iptal ediliyor (bakım modu güvenliği)');
        const response = await fetch(`${API_BASE}/motor/motorlari-iptal`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            console.log('✓ Motorlar başarıyla iptal edildi');
            showMessage('🔒 Motorlar güvenlik için iptal edildi', true);
        } else {
            console.warn('⚠ Motor iptal etme başarısız:', data.message);
            showMessage('⚠ Motor iptal etme başarısız: ' + data.message, true);
        }
    } catch (error) {
        console.error('✗ Motor iptal etme hatası:', error);
        showMessage('✗ Motor iptal etme hatası: ' + error.message, true);
    }
}

// Motorları aktif et (bypass için)
async function motorlariAktifEt() {
    try {
        console.log('Motorlar aktif ediliyor (bypass)');
        const response = await fetch(`${API_BASE}/motor/motorlari-aktif`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            console.log('✓ Motorlar başarıyla aktif edildi');
            showMessage('🔓 Motorlar bypass ile aktif edildi', true);
        } else {
            console.warn('⚠ Motor aktif etme başarısız:', data.message);
            showMessage('⚠ Motor aktif etme başarısız: ' + data.message, true);
        }
    } catch (error) {
        console.error('✗ Motor aktif etme hatası:', error);
        showMessage('✗ Motor aktif etme hatası: ' + error.message, true);
    }
}

// Tüm güvenlik durumlarını sıfırla
function resetAllSafetyStates() {
    // Üst kilit durumunu sıfırla
    const topLockVisual = document.getElementById('top-lock-visual');
    const topLockStatusLed = document.getElementById('top-lock-status-led');
    const topLockStatusText = document.getElementById('top-lock-status-text');
    const topLockTongueLed = document.getElementById('top-lock-tongue-led');
    const topLockTongueText = document.getElementById('top-lock-tongue-text');
    
    if (topLockVisual) topLockVisual.classList.remove('unlocked');
    if (topLockStatusLed) {
        topLockStatusLed.classList.remove('bg-green-500');
        topLockStatusLed.classList.add('bg-red-500');
    }
    if (topLockStatusText) {
        topLockStatusText.textContent = 'Kilit Kapalı';
        topLockStatusText.classList.remove('text-green-400');
        topLockStatusText.classList.add('text-red-400');
    }
    if (topLockTongueLed) {
        topLockTongueLed.classList.remove('bg-red-500');
        topLockTongueLed.classList.add('bg-green-500');
    }
    if (topLockTongueText) {
        topLockTongueText.textContent = 'Dil Var';
        topLockTongueText.classList.remove('text-red-400');
        topLockTongueText.classList.add('text-green-400');
    }
    
    // Alt kilit durumunu sıfırla
    const bottomLockVisual = document.getElementById('bottom-lock-visual');
    const bottomLockStatusLed = document.getElementById('bottom-lock-status-led');
    const bottomLockStatusText = document.getElementById('bottom-lock-status-text');
    const bottomLockTongueLed = document.getElementById('bottom-lock-tongue-led');
    const bottomLockTongueText = document.getElementById('bottom-lock-tongue-text');
    
    if (bottomLockVisual) bottomLockVisual.classList.remove('unlocked');
    if (bottomLockStatusLed) {
        bottomLockStatusLed.classList.remove('bg-green-500');
        bottomLockStatusLed.classList.add('bg-red-500');
    }
    if (bottomLockStatusText) {
        bottomLockStatusText.textContent = 'Kilit Kapalı';
        bottomLockStatusText.classList.remove('text-green-400');
        bottomLockStatusText.classList.add('text-red-400');
    }
    if (bottomLockTongueLed) {
        bottomLockTongueLed.classList.remove('bg-red-500');
        bottomLockTongueLed.classList.add('bg-green-500');
    }
    if (bottomLockTongueText) {
        bottomLockTongueText.textContent = 'Dil Var';
        bottomLockTongueText.classList.remove('text-red-400');
        bottomLockTongueText.classList.add('text-green-400');
    }
    
    // Sensör durumlarını sıfırla
    const topSensorVisual = document.getElementById('top-sensor-visual');
    const topSensorStatusLed = document.getElementById('top-sensor-status-led');
    const topSensorStatusText = document.getElementById('top-sensor-status-text');
    
    if (topSensorVisual) topSensorVisual.classList.remove('inactive');
    if (topSensorStatusLed) {
        topSensorStatusLed.classList.remove('bg-red-500');
        topSensorStatusLed.classList.add('bg-green-500');
    }
    if (topSensorStatusText) {
        topSensorStatusText.textContent = 'Aktif (Kapak Kapalı)';
        topSensorStatusText.classList.remove('text-red-400');
        topSensorStatusText.classList.add('text-green-400');
    }
    
    const bottomSensorVisual = document.getElementById('bottom-sensor-visual');
    const bottomSensorStatusLed = document.getElementById('bottom-sensor-status-led');
    const bottomSensorStatusText = document.getElementById('bottom-sensor-status-text');
    
    if (bottomSensorVisual) bottomSensorVisual.classList.remove('inactive');
    if (bottomSensorStatusLed) {
        bottomSensorStatusLed.classList.remove('bg-red-500');
        bottomSensorStatusLed.classList.add('bg-green-500');
    }
    if (bottomSensorStatusText) {
        bottomSensorStatusText.textContent = 'Aktif (Kapak Kapalı)';
        bottomSensorStatusText.classList.remove('text-red-400');
        bottomSensorStatusText.classList.add('text-green-400');
    }
    
    // Fan durumunu sıfırla
    const fanSvg = document.getElementById('fan-svg');
    const fanSpeedSlider = document.getElementById('fan-speed-slider');
    const fanSpeedInput = document.getElementById('fan-speed-input');
    
    if (fanSvg) {
        fanSvg.classList.remove('fan-active', 'text-blue-400');
        fanSvg.classList.add('text-gray-500');
        fanSvg.style.removeProperty('--fan-duration');
    }
    if (fanSpeedSlider) fanSpeedSlider.value = 0;
    if (fanSpeedInput) fanSpeedInput.value = 0;
    
    // Güvenlik rölesi durumunu sıfırla
    const relayLed = document.getElementById('safety-relay-led');
    const relayText = document.getElementById('safety-relay-text');
    const bypassLed = document.getElementById('bypass-led');
    const bypassText = document.getElementById('bypass-text');
    
    if (relayLed) {
        relayLed.classList.remove('bg-red-500', 'bg-yellow-500');
        relayLed.classList.add('bg-green-500');
    }
    if (relayText) {
        relayText.textContent = 'Röle Aktif';
        relayText.classList.remove('text-red-400', 'text-yellow-400');
        relayText.classList.add('text-green-400');
    }
    if (bypassLed) {
        bypassLed.classList.remove('bg-red-500');
        bypassLed.classList.add('bg-green-500');
    }
    if (bypassText) {
        bypassText.textContent = 'Kilitler Aktif';
        bypassText.classList.remove('text-red-400');
        bypassText.classList.add('text-green-400');
    }
    
    // Bypass butonlarını sıfırla
    const bypassAktifBtn = document.getElementById('bypass-aktif-btn');
    const bypassPasifBtn = document.getElementById('bypass-pasif-btn');
    
    if (bypassAktifBtn) {
        bypassAktifBtn.classList.remove('bg-gray-600', 'hover:bg-gray-700');
        bypassAktifBtn.classList.add('bg-red-600', 'hover:bg-red-700');
        bypassAktifBtn.disabled = false;
    }
    if (bypassPasifBtn) {
        bypassPasifBtn.classList.remove('bg-green-600', 'hover:bg-green-700');
        bypassPasifBtn.classList.add('bg-gray-600', 'hover:bg-gray-700');
        bypassPasifBtn.disabled = true;
    }
    
    // Motorları da iptal et (güvenlik reset)
    motorlariIptalEt();
    
    console.log('Tüm güvenlik durumları sıfırlandı');
}

// Güvenlik kartı kontrollerini başlat
function setupSafetyControls() {
    const topSensorControls = setupMagneticSensor('top-sensor');
    const bottomSensorControls = setupMagneticSensor('bottom-sensor');
    setupLockControl('top-lock', topSensorControls);
    setupLockControl('bottom-lock', bottomSensorControls);
    setupFanControl();
    setupSafetyRelay();
}

// Kuyruk durumu izleme fonksiyonu
function getQueueStatus() {
    return {
        sensor: sensorQueueManager.getQueueStatus(),
        motor: motorQueueManager.getQueueStatus(),
        system: systemQueueManager.getQueueStatus(),
        ping: { isPingInProgress: isPingInProgress }
    };
}

// Kuyruk durumunu konsola yazdır (debug için)
function logQueueStatus() {
    const status = getQueueStatus();
    console.log('📊 Kuyruk Durumu:', status);
    return status;
}

// Tüm kuyrukları durdur ve temizle (güvenlik için)
function stopAllOperations() {
    console.log('🛑 Tüm bakım işlemleri durduruluyor...');
    
    // Tüm kuyrukları temizle
    sensorQueueManager.queue = [];
    motorQueueManager.queue = [];
    systemQueueManager.queue = [];
    
    // İşlem durumlarını sıfırla
    sensorQueueManager.isProcessing = false;
    motorQueueManager.isProcessing = false;
    systemQueueManager.isProcessing = false;
    
    // Ağırlık ölçümünü zorla durdur
    if (typeof agirlikOlcAktif !== 'undefined' && agirlikOlcAktif) {
        console.log('🛑 Ağırlık ölçümü zorla durduruluyor...');
        agirlikOlcDurdur();
    }
    
    // Ping işlemini durdur
    isPingInProgress = false;
    
    // Tüm timer'ları temizle
    if (typeof agirlikOlcTimer !== 'undefined' && agirlikOlcTimer) {
        clearInterval(agirlikOlcTimer);
        agirlikOlcTimer = null;
    }
    
    console.log('✅ Tüm işlemler durduruldu');
}

// ===========================================
// TOLERANS AYARLARI FONKSİYONLARI
// ===========================================

// Varsayılan tolerans sabitleri
const VARSAYILAN_TOLERANSLAR = {
    uzunluk_toleransi: 100,  // mm
    genislik_toleransi: 100, // mm
    metal_agirlik_toleransi: 300,  // gr
    plastik_agirlik_toleransi: 100, // gr
    cam_agirlik_toleransi: 150,  // gr
};

// Tolerans ayarlarını yükle
async function toleransAyarlariYukle() {
    try {
        console.log('📊 Tolerans ayarları yükleniyor...');
        
        const response = await fetch(`${API_BASE}/tolerans/ayarlar`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            // Mevcut toleransları input alanlarına yükle
            Object.keys(VARSAYILAN_TOLERANSLAR).forEach(key => {
                const input = document.getElementById(key.replace(/_/g, '-'));
                if (input) {
                    // 0 değerini kabul et
                    input.value = data.ayarlar[key] !== undefined && data.ayarlar[key] !== null ? 
                        data.ayarlar[key] : VARSAYILAN_TOLERANSLAR[key];
                }
            });
            
            // Mevcut değerleri göster
            mevcutDegerleriGuncelle(data.ayarlar);
            
            console.log('✅ Tolerans ayarları yüklendi');
        } else {
            console.warn('⚠️ Tolerans ayarları yüklenemedi:', data.message);
        }
    } catch (error) {
        console.error('❌ Tolerans ayarları yükleme hatası:', error);
    }
}

// Mevcut değerleri güncelle
function mevcutDegerleriGuncelle(ayarlar) {
    try {
        // Tüm toleransları güncelle
        Object.keys(VARSAYILAN_TOLERANSLAR).forEach(key => {
            const el = document.getElementById(`${key.replace(/_/g, '-')}-mevcut`);
            if (el) {
                const deger = ayarlar[key] !== undefined && ayarlar[key] !== null ? 
                    ayarlar[key] : VARSAYILAN_TOLERANSLAR[key];
                const birim = key.includes('agirlik') ? 'gram' : 'mm';
                el.textContent = `Şu anki değer: ${deger} ${birim}`;
            }
        });
        
        console.log('✅ Mevcut değerler güncellendi');
    } catch (error) {
        console.error('❌ Mevcut değerleri güncelleme hatası:', error);
    }
}

// Tolerans ayarlarını kaydet
async function toleransAyarlariKaydet() {
    try {
        console.log('💾 Tolerans ayarları kaydediliyor...');
        
        // Input değerlerini al
        const ayarlar = {};
        Object.keys(VARSAYILAN_TOLERANSLAR).forEach(key => {
            const input = document.getElementById(key.replace(/_/g, '-'));
            if (input) {
                const value = parseInt(input.value);
                // 0 değerini kabul et
                ayarlar[key] = !isNaN(value) ? value : VARSAYILAN_TOLERANSLAR[key];
            } else {
                ayarlar[key] = VARSAYILAN_TOLERANSLAR[key];
            }
        });
        
        // Değer kontrolü
        for (const [key, value] of Object.entries(ayarlar)) {
            if (isNaN(value) || value < 0) {
                showMessage(`❌ Geçersiz değer: ${key}`, true);
                return;
            }
        }
        
        const response = await fetch(`${API_BASE}/tolerans/ayarlar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(ayarlar)
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            console.log('✅ Tolerans ayarları kaydedildi');
            showMessage('✅ Tolerans ayarları başarıyla kaydedildi', false);
            
            // Mevcut değerleri güncelle
            mevcutDegerleriGuncelle(ayarlar);
        } else {
            console.warn('⚠️ Tolerans ayarları kaydedilemedi:', data.message);
            showMessage('⚠️ Tolerans ayarları kaydedilemedi: ' + data.message, true);
        }
    } catch (error) {
        console.error('❌ Tolerans ayarları kaydetme hatası:', error);
        showMessage('❌ Tolerans ayarları kaydetme hatası: ' + error.message, true);
    }
}

// Tolerans sekmesi için event listener'ları kur
function toleransSekmesiKurulum() {
    // Kaydet butonu
    const kaydetBtn = document.getElementById('tolerans-kaydet-btn');
    if (kaydetBtn) {
        kaydetBtn.addEventListener('click', toleransAyarlariKaydet);
    }
    
    // Input değer değişikliklerini dinle
    const inputIds = [
        'uzunluk-toleransi', 'genislik-toleransi',
        'cam-agirlik-toleransi', 'metal-agirlik-toleransi', 'plastik-agirlik-toleransi'
    ];
    
    inputIds.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('change', () => {
                console.log(`📝 ${id} değeri değiştirildi: ${input.value}`);
                
                // Mevcut değeri güncelle
                const mevcutEl = document.getElementById(`${id}-mevcut`);
                if (mevcutEl) {
                    const birim = id.includes('agirlik') ? 'gram' : 'mm';
                    mevcutEl.textContent = `Şu anki değer: ${input.value} ${birim}`;
                }
            });
        }
    });
}
