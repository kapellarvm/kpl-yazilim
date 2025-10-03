// RVM Bakım Paneli v2 - JavaScript

// Global değişkenler
let bakimModuAktif = false;
let isTesting = false;
let stopLoop = true;
let cardConnectionTimeouts = {};

// API Base URL
const API_BASE = '';

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
    bakimModuAktif = !bakimModuAktif;
    
    try {
        const response = await fetch(`${API_BASE}/api/bakim-modu-ayarla`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                aktif: bakimModuAktif
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            const btn = document.getElementById('bakimModBtn');
            if (bakimModuAktif) {
                btn.textContent = '⚙ Bakım Modu: Aktif';
                btn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                showMessage('✓ ' + data.message);
            } else {
                btn.textContent = '⚙ Bakım Modu: Pasif';
                btn.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
                showMessage('✓ ' + data.message);
            }
            
            // Butonları güncelle
            butonlariGuncelle();
            
            // Durum güncellemesini tetikle
            setTimeout(sistemDurumunuGuncelle, 500);
        } else {
            showMessage('✗ ' + data.message, true);
            bakimModuAktif = !bakimModuAktif; // Geri al
        }
    } catch (error) {
        showMessage('Bağlantı hatası: ' + error.message, true);
        bakimModuAktif = !bakimModuAktif; // Geri al
    }
}

// Sistem durumu güncelleme
async function sistemDurumunuGuncelle() {
    try {
        const response = await fetch(`${API_BASE}/api/sistem-durumu`);
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
        if (data.mevcut_durum === 'bakim' && !bakimModuAktif) {
            bakimModuAktif = true;
            const btn = document.getElementById('bakimModBtn');
            if (btn) {
                btn.textContent = '⚙ Bakım Modu: Aktif';
                btn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                butonlariGuncelle();
            }
        } else if (data.mevcut_durum !== 'bakim' && bakimModuAktif) {
            bakimModuAktif = false;
            const btn = document.getElementById('bakimModBtn');
            if (btn) {
                btn.textContent = '⚙ Bakım Modu: Pasif';
                btn.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
                butonlariGuncelle();
            }
        }
        
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
        const response = await fetch(`${API_BASE}/api/sensor/son-deger`);
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
        const response = await fetch(`${API_BASE}/api/motor/${komut}`, {
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
        const response = await fetch(`${API_BASE}/api/sensor/${komut}`, {
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
        const response = await fetch(`${API_BASE}/api/sistem-reset`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
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
                teachBtn.disabled = true;
                if (testBtn) testBtn.disabled = true;
                
                if (rays) rays.classList.add('teaching-rays');
                teachBtn.innerText = "Öğreniyor...";
                
                try {
                    const response = await fetch(`${API_BASE}/api/sensor/teach`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        showMessage('✓ Gyro sensör teach tamamlandı', true);
                    } else {
                        showMessage('✗ Teach hatası: ' + data.message, false);
                    }
                } catch (error) {
                    showMessage('✗ Teach hatası: ' + error.message, false);
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
    
    if (measureBtn) {
        measureBtn.addEventListener('click', async () => {
            if (measureBtn.disabled) return;
            if (tareBtn) tareBtn.disabled = true;
            measureBtn.disabled = true;
            if (loadcellMessage) loadcellMessage.innerText = 'Ölçüm yapılıyor...';
            if (loadcellVisual) loadcellVisual.classList.add('measuring');
            
            try {
                const response = await fetch(`${API_BASE}/api/sensor/agirlik-olc`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                
                if (data.status === 'success' && data.mesajlar) {
                    // Gelen mesajları parse et - "a:123.32" formatını ara
                    let agirlik = 0.0;
                    let bulundu = false;
                    
                    for (let mesaj of data.mesajlar) {
                        console.log('Ağırlık mesajı:', mesaj);
                        // "a:123.32" formatını kontrol et
                        if (mesaj.startsWith('a:')) {
                            try {
                                const agirlikStr = mesaj.substring(2); // "a:" kısmını atla
                                agirlik = parseFloat(agirlikStr);
                                if (!isNaN(agirlik)) {
                                    bulundu = true;
                                    break;
                                }
                            } catch (e) {
                                console.error('Ağırlık parse hatası:', e);
                            }
                        }
                    }
                    
                    if (bulundu) {
                        if (loadcellOutput) {
                            loadcellOutput.innerHTML = `${agirlik.toFixed(2)} <span class="text-2xl">gr</span>`;
                        }
                        if (loadcellMessage) loadcellMessage.innerText = 'Ölçüm tamamlandı';
                        showMessage(`✓ Ağırlık: ${agirlik.toFixed(2)} gr`, true);
                    } else {
                        if (loadcellMessage) loadcellMessage.innerText = 'Ağırlık verisi bulunamadı';
                        showMessage('✗ Ağırlık verisi bulunamadı (a: formatı bekleniyor)', false);
                        console.log('Gelen mesajlar:', data.mesajlar);
                    }
                } else {
                    if (loadcellMessage) loadcellMessage.innerText = 'Ölçüm hatası';
                    showMessage('✗ Ölçüm hatası: ' + data.message, false);
                }
            } catch (error) {
                if (loadcellMessage) loadcellMessage.innerText = 'Ölçüm hatası';
                showMessage('✗ Ölçüm hatası: ' + error.message, false);
            } finally {
                if (loadcellVisual) loadcellVisual.classList.remove('measuring');
                if (tareBtn) tareBtn.disabled = false;
                measureBtn.disabled = false;
            }
        });
    }
    
    if (tareBtn) {
        tareBtn.addEventListener('click', async () => {
            if(tareBtn.disabled) return;
            tareBtn.disabled = true;
            if (measureBtn) measureBtn.disabled = true;
            if (loadcellMessage) loadcellMessage.innerText = 'Konveyörü boşaltın...';
            
            try {
                // 3 saniye bekle
                await new Promise(resolve => setTimeout(resolve, 3000));
                
                if (loadcellMessage) loadcellMessage.innerText = 'Tare alınıyor...';
                if (loadcellVisual) loadcellVisual.classList.add('measuring');
                
                const response = await fetch(`${API_BASE}/api/sensor/tare`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    if (loadcellOutput) {
                        loadcellOutput.innerHTML = `0.0 <span class="text-2xl">gr</span>`;
                    }
                    if (loadcellMessage) loadcellMessage.innerText = 'Tare tamamlandı';
                    showMessage('✓ Loadcell tare tamamlandı', true);
                } else {
                    if (loadcellMessage) loadcellMessage.innerText = 'Tare hatası';
                    showMessage('✗ Tare hatası: ' + data.message, false);
                }
            } catch (error) {
                if (loadcellMessage) loadcellMessage.innerText = 'Tare hatası';
                showMessage('✗ Tare hatası: ' + error.message, false);
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
        ledOnBtn.addEventListener('click', () => {
            updateLedState(100);
            sensorKontrol('led-ac');
        });
    }
    
    if (ledOffBtn) {
        ledOffBtn.addEventListener('click', () => {
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

// Motor kontrolleri
function setupMotorControls() {
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
                    const response = await fetch(`${API_BASE}/api/motor/hiz-ayarla`, {
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
        fetch('/api/bakim-url-ayarla', {
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
        fetch(`${API_BASE}/api/sistem-durumu`)
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

// Ana başlatma fonksiyonu
function initializeBakim() {
    setupTabControl();
    setupToggle();
    setupSensorControls();
    setupMotorControls();
    setupPlaceholderFunctions();
    
    // İlk durum güncellemesi
    sistemDurumunuGuncelle();
    sensorDegerleriniGuncelle();
    butonlariGuncelle();
    updateGeneralStatus();
    
    // Periyodik güncellemeler
    setInterval(sistemDurumunuGuncelle, 5000);
    setInterval(sensorDegerleriniGuncelle, 1000);
    setInterval(updateGeneralStatus, 10000); // Her 10 saniyede bir genel durumu güncelle
}

// DOM yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', initializeBakim);
