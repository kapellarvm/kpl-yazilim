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
                // Bakım modu aktifken periyodik güncellemeleri başlat
                startPeriodicUpdates();
            } else {
                btn.textContent = '⚙ Bakım Modu: Pasif';
                btn.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
                showMessage('✓ ' + data.message);
                // Bakım modu pasifken periyodik güncellemeleri durdur
                stopPeriodicUpdates();
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
        
        // Bakım modu durumunu güncelle
        if (data.durum === 'bakim' && !bakimModuAktif) {
            bakimModuAktif = true;
            const btn = document.getElementById('bakimModBtn');
            if (btn) {
                btn.textContent = '⚙ Bakım Modu: Aktif';
                btn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                butonlariGuncelle();
            }
            // Bakım modu aktifken periyodik güncellemeleri başlat
            startPeriodicUpdates();
        } else if (data.durum !== 'bakim' && bakimModuAktif) {
            bakimModuAktif = false;
            const btn = document.getElementById('bakimModBtn');
            if (btn) {
                btn.textContent = '⚙ Bakım Modu: Pasif';
                btn.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
                butonlariGuncelle();
            }
            // Bakım modu pasifken periyodik güncellemeleri durdur
            stopPeriodicUpdates();
            // WebSocket bağlantısını kapat
            disconnectWebSocket();
        }
        
        // Durum yöneticisini güncelle
        durumYoneticisi.durum = data.durum;
        durumYoneticisi.sensorKartBagli = data.sensor_baglanti;
        durumYoneticisi.motorKartBagli = data.motor_baglanti;
        
    } catch (error) {
        console.error('Durum güncellemesi başarısız:', error);
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
}

async function sensorKontrol(komut) {
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
}

// Sistem reset
async function sistemReset() {
    if (!confirm('Sistemi resetlemek istediğinizden emin misiniz? Tüm bağlantılar kesilecek ve yeniden kurulacak.')) {
        return;
    }
    
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
                    if (loadcellMessage) loadcellMessage.innerText = 'Sürekli ölçüm aktif (500ms)';
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
                console.log('Ağırlık ölçüm komutu gönderildi (500ms)');
            } catch (error) {
                console.error('Ağırlık ölçüm hatası:', error);
            }
        }, 500); // 500ms aralıklarla
    }

    // Sürekli ağırlık ölçümü durdur
    function agirlikOlcDurdur() {
        agirlikOlcAktif = false;
        if (agirlikOlcTimer) {
            clearInterval(agirlikOlcTimer);
            agirlikOlcTimer = null;
        }
        if (loadcellVisual) loadcellVisual.classList.remove('measuring');
        if (loadcellMessage) loadcellMessage.innerText = 'Ölçüm durduruldu';
        showMessage('✓ Ağırlık ölçümü durduruldu', true);
        console.log('Ağırlık ölçümü durduruldu');
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
                // 3 saniye bekle
                await new Promise(resolve => setTimeout(resolve, 3000));
                
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
        });
    }
    
    if (brightnessSlider) {
        brightnessSlider.addEventListener('input', () => updateLedState(parseInt(brightnessSlider.value, 10)));
    }
    
    if (brightnessInput) {
        brightnessInput.addEventListener('input', () => {
            const val = parseInt(brightnessInput.value, 10);
            if (!isNaN(val)) updateLedState(val);
        });
    }
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
    
    // Ağırlık ölçüm timer'ını durdur
    if (agirlikOlcAktif) {
        agirlikOlcDurdur();
    }
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
        case 'alarm_update':
            console.log('Alarm güncelleme alındı:', data.data);
            updateAlarmDisplayFromWebSocket(data.data);
            break;
        default:
            console.log('Bilinmeyen WebSocket mesaj tipi:', data.type);
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
        readyEl.textContent = data.ready || 'HAYIR';
        if (data.ready === 'EVET') {
            readyEl.classList.add('text-green-400');
            readyEl.classList.remove('text-red-400');
        } else {
            readyEl.classList.remove('text-green-400');
            readyEl.classList.add('text-red-400');
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

// Periyodik güncellemeleri başlat
function startPeriodicUpdates() {
    // Eğer zaten çalışıyorsa durdur
    stopPeriodicUpdates();
    
    // Periyodik güncellemeleri başlat
    sistemDurumInterval = setInterval(sistemDurumunuGuncelle, 5000);
    sensorDegerInterval = setInterval(sensorDegerleriniGuncelle, 1000);
    genelDurumInterval = setInterval(updateGeneralStatus, 10000);
    
    // Hazne doluluk güncelleme
    setInterval(async () => {
        await loadHazneDoluluk();
    }, 10000);
}

// Periyodik güncellemeleri durdur
function stopPeriodicUpdates() {
    if (sistemDurumInterval) {
        clearInterval(sistemDurumInterval);
        sistemDurumInterval = null;
    }
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
    
    // İlk durum güncellemesi
    sistemDurumunuGuncelle();
    sensorDegerleriniGuncelle();
    butonlariGuncelle();
    updateGeneralStatus();
    
    // WebSocket bağlantısını her zaman başlat
    connectWebSocket();
    
    // Periyodik güncellemeleri başlat (sadece bakım modu aktifken)
    if (bakimModuAktif) {
        startPeriodicUpdates();
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

// Hazne doluluk güncelleme
async function updateFillLevel(material, percentage) {
    const fillElement = document.getElementById(`${material}-fill`);
    const textElement = document.getElementById(`${material}-text`);
    
    if (fillElement) {
        fillElement.style.height = `${percentage}%`;
    }
    if (textElement) {
        textElement.innerText = `${percentage}% Dolu`;
    }
}

// Hazne doluluk verilerini API'den al
async function loadHazneDoluluk() {
    try {
        const response = await fetch(`${API_BASE}/hazne/doluluk`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            updateFillLevel('plastic', data.data.plastik);
            updateFillLevel('metal', data.data.metal);
            updateFillLevel('glass', data.data.cam);
        } else {
            console.error('Hazne doluluk verisi alınamadı:', data.message);
        }
    } catch (error) {
        console.error('Hazne doluluk hatası:', error);
    }
}

// Kalibrasyon fonksiyonları
function showCalibrationStatus(message) {
    const statusElement = document.getElementById('calibration-status');
    if (statusElement) {
        statusElement.textContent = message;
        setTimeout(() => {
            statusElement.textContent = '';
        }, 3000);
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
    const testBtn = document.getElementById(`${prefix}-test-btn`);
    
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
    
    // Test butonu event listener'ı
    if (testBtn) {
        testBtn.addEventListener('click', async () => {
            try {
                const sensorTipi = prefix === 'top-sensor' ? 'ust' : 'alt';
                const response = await fetch(`${API_BASE}/guvenlik/sensor-test?sensor_tipi=${sensorTipi}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Sensör durumunu geçici olarak değiştir (test için)
                    if (statusText.textContent.includes('Aktif')) {
                        setPassive();
                    } else {
                        setActive();
                    }
                    showMessage(data.message);
                } else {
                    showMessage(data.message, true);
                }
            } catch (error) {
                showMessage(`Sensör test hatası: ${error.message}`, true);
            }
        });
    }
    
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
    const bypassBtn = document.getElementById('safety-relay-bypass-btn');
    
    const relayLed = document.getElementById('safety-relay-led');
    const relayText = document.getElementById('safety-relay-text');
    const bypassLed = document.getElementById('bypass-led');
    const bypassText = document.getElementById('bypass-text');

    if (!resetBtn || !bypassBtn || !relayLed || !relayText || !bypassLed || !bypassText) return;

    let isBypassActive = false;

    resetBtn.addEventListener('click', async () => {
        // Butonları devre dışı bırak
        resetBtn.disabled = true;
        bypassBtn.disabled = true;

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
            bypassBtn.disabled = false;
        }
    });

    bypassBtn.addEventListener('click', async () => {
        try {
            const response = await fetch(`${API_BASE}/guvenlik/role-bypass`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                isBypassActive = !isBypassActive;
                if (isBypassActive) {
                    bypassLed.classList.remove('bg-green-500');
                    bypassLed.classList.add('bg-red-500');
                    bypassText.textContent = 'Kilitler Pasif';
                    bypassText.classList.remove('text-green-400');
                    bypassText.classList.add('text-red-400');
                } else {
                    bypassLed.classList.remove('bg-red-500');
                    bypassLed.classList.add('bg-green-500');
                    bypassText.textContent = 'Kilitler Aktif';
                    bypassText.classList.remove('text-red-400');
                    bypassText.classList.add('text-green-400');
                }
                showMessage(data.message);
            } else {
                showMessage(data.message, true);
            }
        } catch (error) {
            showMessage(`Röle bypass hatası: ${error.message}`, true);
        }
    });
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
