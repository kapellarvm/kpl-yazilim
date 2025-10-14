<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RVM Bakım Paneli</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
        }
        .status-dot {
            height: 12px;
            width: 12px;
            border-radius: 50%;
            display: inline-block;
        }
        .status-online { background-color: #22c55e; } /* green-500 */
        .status-offline { background-color: #ef4444; } /* red-500 */
        .status-warning { background-color: #f59e0b; } /* amber-500 */

        /* Performans için will-change sınıfları */
        .will-change-transform { will-change: transform; }
        .will-change-opacity { will-change: opacity; }
        .will-change-all { will-change: transform, opacity; }

        /* OPT Sensör Animasyonları (Mevcut haliyle genellikle performanslıdır) */
        @keyframes ray-animation {
            to { stroke-dashoffset: -20; }
        }
        .teaching-rays .ray {
            stroke-dasharray: 5 5;
            animation: ray-animation 0.4s linear infinite;
        }

        /* Loadcell Animasyonu (Performanslıdır) */
        @keyframes measure-animation {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }
        .measuring {
            animation: measure-animation 0.5s ease-in-out infinite;
        }
        
        /* OPTİMİZE EDİLMİŞ LED Animasyonu (Basit Opacity Pulse) */
        @keyframes led-pulse-animation {
            0%, 100% { opacity: 0.8; }
            50% { opacity: 1; }
        }
        #conveyor-led-visual.led-on svg {
            animation: led-pulse-animation 1.5s ease-in-out infinite;
        }

        .speed-slider::-webkit-slider-thumb,
        #led-brightness-slider::-webkit-slider-thumb {
          -webkit-appearance: none; appearance: none; width: 20px; height: 20px; background: #3b82f6; cursor: pointer; border-radius: 50%;
        }

        .details-grid {
            transition: max-height 0.5s ease-in-out, margin-top 0.5s ease-in-out, opacity 0.3s ease-in-out;
            overflow: hidden;
        }
        
        /* Motor Animasyonları (Performanslıdır) */
        @keyframes gear-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .spinning {
            animation: gear-spin 2s linear infinite;
        }
        @keyframes gear-spin-rev {
            from { transform: rotate(0deg); }
            to { transform: rotate(-360deg); }
        }
        .spinning-rev {
            animation: gear-spin-rev 2s linear infinite;
        }

        /* Konveyör Animasyonu (Mevcut haliyle genellikle performanslıdır) */
        #conveyor-animation-bg {
            background-image: repeating-linear-gradient(
                -45deg,
                #374151,
                #374151 15px,
                #4b5563 15px,
                #4b5563 30px
            );
            background-size: 84px 100%;
        }

        @keyframes scroll-forward {
            from { background-position: 0 0; }
            to { background-position: -42.42px 0; }
        }

        @keyframes scroll-backward {
            from { background-position: 0 0; }
            to { background-position: 42.42px 0; }
        }

        .conveyor-running-forward #conveyor-animation-bg {
            animation: scroll-forward var(--conveyor-duration, 1s) linear infinite;
        }
        .conveyor-running-backward #conveyor-animation-bg {
            animation: scroll-backward var(--conveyor-duration, 1s) linear infinite;
        }
        
        /* OPTİMİZE EDİLMİŞ Şişe Animasyonu (transform: translateX kullanarak) */
        @keyframes bottle-move-forward {
            from { transform: translateX(-50px); }
            to { transform: translateX(calc(100% + 50px)); } 
        }
        @keyframes bottle-move-backward {
            from { transform: translateX(calc(100% + 50px)); }
            to { transform: translateX(-50px); }
        }
        .conveyor-running-forward #conveyor-bottle {
            animation: bottle-move-forward var(--conveyor-bottle-duration, 3s) linear infinite;
        }
        .conveyor-running-backward #conveyor-bottle {
            animation: bottle-move-backward var(--conveyor-bottle-duration, 3s) linear infinite;
        }
        #conveyor-bottle {
            position: absolute;
            top: 50%;
            left: 0; 
            transform: translateY(-50%);
        }

        /* LED Blink Animasyonu (Performanslıdır) */
        @keyframes led-blink {
            50% { opacity: 0.2; }
        }
        .led-blink-red {
            background-color: #ef4444; /* red-500 */
            animation: led-blink 0.8s step-end infinite;
        }
        .led-blink-green {
            background-color: #22c55e; /* green-500 */
            animation: led-blink 0.5s step-end infinite;
        }
        .led-blink-orange {
            background-color: #f97316; /* orange-500 */
            animation: led-blink 0.8s step-end infinite;
        }
        .led-on-orange {
             background-color: #f97316; /* orange-500 */
        }

        /* Diğer Motor Animasyonları (Performanslıdır) */
        @keyframes diverter-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes diverter-spin-rev { 0% { transform: rotate(0deg); } 100% { transform: rotate(-360deg); } }
        
        .snowflake { position: relative; width: 10px; height: 10px; }
        .snowflake-arm { position: absolute; top: 50%; left: 50%; width: 56px; height: 4px; background-color: #2dd4bf; border-radius: 2px; transform-origin: center; margin-top: -2px; margin-left: -28px; }
        .snowflake-arm:nth-child(1) { transform: rotate(0deg); }
        .snowflake-arm:nth-child(2) { transform: rotate(60deg); }
        .snowflake-arm:nth-child(3) { transform: rotate(120deg); }

        #flap-visual {
            transition: transform var(--flap-duration, 0.5s);
        }

        /* Power Toggle Switch */
        .power-switch input { display: none; }
        .power-switch-label { display: block; overflow: hidden; cursor: pointer; border: 0 solid #bbb; border-radius: 20px; }
        .power-switch-inner { display: block; width: 200%; margin-left: -100%; transition: margin 0.3s ease-in 0s; }
        .power-switch-inner:before, .power-switch-inner:after { display: block; float: left; width: 50%; height: 24px; padding: 0; line-height: 24px; font-size: 12px; color: white; font-weight: bold; box-sizing: border-box; }
        .power-switch-inner:before { content: "AÇIK"; padding-left: 10px; background-color: #22c55e; color: #FFFFFF; }
        .power-switch-inner:after { content: "KAPALI"; padding-right: 10px; background-color: #ef4444; color: #FFFFFF; text-align: right; }
        .power-switch-switch { display: block; width: 18px; margin: 3px; background: #FFFFFF; position: absolute; top: 0; bottom: 0; right: 26px; border: 0 solid #bbb; border-radius: 20px; transition: all 0.3s ease-in 0s; }
        .power-switch input:checked + .power-switch-label .power-switch-inner { margin-left: 0; }
        .power-switch input:checked + .power-switch-label .power-switch-switch { right: 0px; }

        /* Tab Styles */
        .tab-btn.active-tab {
            border-color: #3b82f6; /* blue-500 */
            color: #60a5fa; /* blue-400 */
        }
        .tab-btn.inactive-tab {
            border-color: transparent;
            color: #9ca3af; /* gray-400 */
        }
        .tab-btn.inactive-tab:hover {
            border-color: #4b5563; /* gray-600 */
            color: #d1d5db; /* gray-300 */
        }

        /* Güvenlik Kartı Animasyonları */
        .lock-head {
            transition: transform 0.3s ease-in-out;
        }
        .lock-visual.unlocked .lock-head {
            transform: translateY(-15px);
        }

        #fan-blades {
            transform-origin: center;
        }

        #fan-svg.fan-active #fan-blades {
            animation: gear-spin var(--fan-duration, 2s) linear infinite;
        }

        .sensor-part-movable {
            transition: transform 0.3s ease-in-out;
        }
        .sensor-visual.inactive .sensor-part-movable {
            transform: translateX(25px);
        }

        /* Acil Durdurma Butonu */
        #emergency-stop-button {
            box-shadow: 0px 8px 0px #991b1b; /* red-800 for 3D effect */
            transition: transform 0.1s ease-out, box-shadow 0.1s ease-out;
        }
        #emergency-stop-button-container.pressed #emergency-stop-button {
            transform: translateY(6px);
            box-shadow: 0px 2px 0px #991b1b;
        }
        @keyframes emergency-glow {
            0%, 100% { box-shadow: 0 0 15px 5px rgba(239, 68, 68, 0); }
            50% { box-shadow: 0 0 25px 10px rgba(239, 68, 68, 0.7); }
        }
        .emergency-active {
            animation: emergency-glow 1.5s infinite;
        }


    </style>
</head>
<body class="bg-gray-900 text-white">

    <div class="min-h-screen flex flex-col p-4 sm:p-6 lg:p-8">
        <!-- Başlık Bölümü -->
        <header class="mb-8">
            <div class="flex flex-wrap justify-between items-center gap-4">
                <div>
                    <h1 class="text-2xl sm:text-3xl font-bold text-gray-100">RVM Bakım Paneli</h1>
                    <p class="text-gray-400">IP Adresi: 192.168.53.2</p>
                </div>
                <div class="flex items-center space-x-3">
                    <span id="system-status-dot" class="status-dot status-online"></span>
                    <span id="system-status-text" class="font-semibold text-lg">Çevrimiçi</span>
                </div>
            </div>
        </header>

        <!-- Ana İçerik Grid'i -->
        <main class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Genel Durum & Hızlı Kontroller (Sol Sütun) -->
             <div class="space-y-6 lg:col-span-1">
                <!-- Acil Durdurma Butonu -->
                <div class="bg-gray-800 p-6 rounded-2xl shadow-lg">
                    <h2 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Acil Durdurma</h2>
                    <div id="emergency-stop-container" class="flex flex-col items-center justify-center gap-4">
                        <div id="emergency-stop-button-container" class="w-32 h-32 bg-yellow-400 rounded-lg shadow-lg flex items-center justify-center cursor-pointer p-2">
                             <div class="w-28 h-28 bg-black rounded-full flex items-center justify-center shadow-inner">
                                <div id="emergency-stop-button" class="w-24 h-24 bg-red-600 rounded-full flex items-center justify-center text-center text-white font-bold">
                                    ACİL DURDURMA
                                </div>
                            </div>
                        </div>
                        <span id="emergency-stop-status" class="font-semibold text-green-400 text-lg">Sistem Aktif</span>
                    </div>
                </div>
                <div class="bg-gray-800 p-6 rounded-2xl shadow-lg">
                   <h2 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Genel Durum</h2>
                   <div class="space-y-6">
                        <!-- Sensör Değerleri -->
                        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-6">
                            <!-- KPL04-PN-0001 -->
                            <div>
                                <h3 class="text-lg font-semibold text-blue-400">KPL04-PN-0001</h3>
                                <div class="mt-2 space-y-2 text-sm">
                                    <div class="flex justify-between items-center bg-gray-700/50 p-2 rounded-md"><span>Sıcaklık:</span><span class="font-mono text-lg font-bold">28°C</span></div>
                                    <div class="flex justify-between items-center bg-gray-700/50 p-2 rounded-md"><span>Basınç:</span><span class="font-mono text-lg font-bold">1012 hPa</span></div>
                                    <div class="flex justify-between items-center bg-gray-700/50 p-2 rounded-md"><span>Nem:</span><span class="font-mono text-lg font-bold">55%</span></div>
                                </div>
                            </div>
                            <!-- KPL04-PN-0002 -->
                            <div>
                                <h3 class="text-lg font-semibold text-blue-400">KPL04-PN-0002</h3>
                                <div class="mt-2 space-y-2 text-sm">
                                    <div class="flex justify-between items-center bg-gray-700/50 p-2 rounded-md"><span>Sıcaklık:</span><span class="font-mono text-lg font-bold">35°C</span></div>
                                    <div class="flex justify-between items-center bg-gray-700/50 p-2 rounded-md"><span>Basınç:</span><span class="font-mono text-lg font-bold">1010 hPa</span></div>
                                    <div class="flex justify-between items-center bg-gray-700/50 p-2 rounded-md"><span>Nem:</span><span class="font-mono text-lg font-bold">52%</span></div>
                                </div>
                            </div>
                        </div>
                
                        <!-- Etiket Bilgileri -->
                        <div class="pt-4 border-t border-gray-700">
                            <h3 class="text-lg font-semibold text-blue-400 mb-3">Etiket Bilgileri</h3>
                            <div class="text-sm space-y-2 text-gray-300">
                                <div class="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">
                                    <span class="font-semibold">Üretici Ünvanı:</span><span class="break-words">KAPELLA ELEKTROMEKANİK A.Ş.</span>
                                    <span class="font-semibold">Üretici Adresi:</span><span class="break-words">29 Ekim Mah. 10002 Sk. B No:16/1 Menemen/İzmir</span>
                                    <span class="font-semibold">Marka:</span><span>KapellaRVM</span>
                                    <span class="font-semibold">Model:</span><span>KPL04</span>
                                    <span class="font-semibold">Seri No:</span><span>2025-KPL04-0001</span>
                                    <span class="font-semibold">Beyan Gerilimi:</span><span>220-230 V</span>
                                    <span class="font-semibold">Beyan Akımı:</span><span>15A</span>
                                    <span class="font-semibold">Beyan Gücü:</span><span>3.3 kW</span>
                                    <span class="font-semibold">Beyan Frekansı:</span><span>50-60 Hz</span>
                                    <span class="font-semibold">Numunenin Tanımı:</span><span>Depozito İade Makinesi</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="bg-gray-800 p-6 rounded-2xl shadow-lg">
                    <h2 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Hızlı Kontroller</h2>
                    <div class="flex flex-col space-y-3">
                        <button class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition duration-300">Diagnostik Başlat</button>
                        <button class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded-lg transition duration-300">Depoyu Boşalt</button>
                        <button class="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-4 rounded-lg transition duration-300">Sistemi Yeniden Başlat</button>
                    </div>
                </div>
            </div>

            <!-- Sekme Kontrol Bölümü (Sağ Sütun) -->
            <div class="lg:col-span-2">
                <!-- Sekme Butonları -->
                <div class="border-b border-gray-700">
                    <nav class="-mb-px flex space-x-2 sm:space-x-8" aria-label="Tabs">
                        <button id="tab-btn-sensors" class="tab-btn active-tab whitespace-nowrap py-3 px-2 sm:py-4 sm:px-1 border-b-2 font-medium text-base sm:text-lg">
                            Sensör Kartı
                        </button>
                        <button id="tab-btn-motors" class="tab-btn inactive-tab whitespace-nowrap py-3 px-2 sm:py-4 sm:px-1 border-b-2 font-medium text-base sm:text-lg">
                            Motor Kartı
                        </button>
                        <button id="tab-btn-safety" class="tab-btn inactive-tab whitespace-nowrap py-3 px-2 sm:py-4 sm:px-1 border-b-2 font-medium text-base sm:text-lg">
                            Güvenlik Kartı
                        </button>
                    </nav>
                </div>
        
                <!-- Sekme İçerikleri -->
                <div class="mt-0">
                    <!-- Sensör Kartı İçeriği -->
                    <div id="tab-content-sensors" class="tab-content">
                        <div class="bg-gray-800 p-4 sm:p-6 rounded-b-2xl shadow-lg">
                            <div class="flex flex-wrap justify-between items-center gap-4 mb-4 border-b border-gray-700 pb-2"><div class="flex items-center space-x-4"><h2 class="text-xl font-semibold">Sensör Kartı Detayları</h2><div id="sensor-card-status" class="flex items-center space-x-2"></div></div><div class="flex items-center space-x-2"><button id="toggle-sensors-btn" class="p-2 rounded-full hover:bg-gray-700 transition-colors" title="Paneli Daralt/Genişlet"></button><button id="reset-sensor-card-btn" class="bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded-lg transition duration-300">Kartı Resetle</button></div></div>
                            <div id="sensor-details-grid" class="details-grid mt-6 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6 lg:gap-8">
                                <!-- OPT 1009 -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-1 text-center">Giriş Sensörü</h3>
                                    <div id="opt1009-visual" class="relative w-full h-12 mx-auto my-1">
                                        <svg class="w-full h-full" viewBox="0 0 100 40">
                                            <rect x="5" y="10" width="20" height="20" rx="4" fill="#4b5563"/>
                                            <circle cx="15" cy="20" r="3" fill="#60a5fa" />
                                            <rect x="75" y="10" width="20" height="20" rx="4" fill="#9ca3af"/>
                                            <rect x="80" y="15" width="4" height="10" fill="#fbbf24"/>
                                            <g id="opt1009-rays">
                                                <line class="ray" x1="25" y1="20" x2="75" y2="20" stroke="#facc15" stroke-width="2"/>
                                            </g>
                                            <g id="opt1009-blocker" class="hidden" opacity="0.6">
                                                <path d="M 50 5 L 55 10 L 55 30 L 50 35 L 45 30 L 45 10 Z" fill="#60a5fa" stroke="#e0f2fe" stroke-width="1.5"/>
                                            </g>
                                        </svg>
                                    </div>
                                    <div class="text-center mb-2"><span class="text-2xl font-mono" id="opt1009-output">--</span></div>
                                    <div class="flex space-x-2"><button id="opt1009-teach-btn" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Teach</button><button id="opt1009-test-btn" class="w-full bg-gray-600 hover:bg-gray-500 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Test Et</button></div>
                                    <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">24.1 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">30.2 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">15 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">0.36 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>
                                <!-- Loadcell -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col"><h3 class="font-semibold text-md mb-1 text-center">Loadcell Ağırlık Sensörleri</h3><div class="flex-grow flex flex-col items-center justify-center"><div id="loadcell-visual" class="mb-1"><svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" /></svg></div><div id="loadcell-output" class="text-3xl font-mono text-center mb-1">0.0 <span class="text-lg">gr</span></div><div id="loadcell-message" class="text-center text-amber-400 h-4 mb-1 text-xs"></div></div><div class="flex space-x-2 mt-auto"><button id="loadcell-measure-btn" class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Ağırlık Ölç</button><button id="loadcell-tare-btn" class="w-full bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Tare Al</button></div></div>
                                <!-- Konveyör LED -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col"><h3 class="font-semibold text-md mb-1 text-center">Konveyör LED Kontrolü</h3><div class="flex-grow flex items-center justify-center my-1"><div id="conveyor-led-visual" class="relative w-16 h-16 flex items-center justify-center"><svg xmlns="http://www.w3.org/2000/svg" class="w-12 h-12 text-gray-500 transition-colors duration-300 will-change-opacity" fill="currentColor" viewBox="0 0 24 24"><path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z"/></svg></div></div><div class="space-y-2 mt-auto"><div class="flex items-center space-x-2"><input type="range" id="led-brightness-slider" min="0" max="100" value="0" class="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer"><input type="number" id="led-brightness-input" min="0" max="100" value="0" class="w-16 bg-gray-900 text-center font-mono rounded-md border border-gray-600 p-1 text-sm"></div><div class="flex space-x-2"><button id="led-on-btn" class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Aç</button><button id="led-off-btn" class="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Kapat</button></div></div>
                                    <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">12.0 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">12.5 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">500 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">6.0 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>
                                <!-- Plastik Hazne -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-1 text-center">Plastik Hazne Doluluk</h3>
                                    <div class="w-20 h-28 bg-gray-800 rounded-t-lg mx-auto relative overflow-hidden border-2 border-gray-600 mt-2">
                                        <div id="plastic-fill" class="absolute bottom-0 w-full bg-blue-500 transition-all duration-500"></div>
                                    </div>
                                    <p id="plastic-text" class="mt-1 text-lg font-mono text-center"></p>
                                    <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">24.0 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">22.1 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">10 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">0.24 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>
                                <!-- Metal Hazne -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-1 text-center">Metal Hazne Doluluk</h3>
                                    <div class="w-20 h-28 bg-gray-800 rounded-t-lg mx-auto relative overflow-hidden border-2 border-gray-600 mt-2">
                                        <div id="metal-fill" class="absolute bottom-0 w-full bg-gray-400 transition-all duration-500"></div>
                                    </div>
                                    <p id="metal-text" class="mt-1 text-lg font-mono text-center"></p>
                                    <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">24.0 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">24.3 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">12 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">0.29 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>
                                <!-- Cam Hazne -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-1 text-center">Cam Hazne Doluluk</h3>
                                    <div class="w-20 h-28 bg-gray-800 rounded-t-lg mx-auto relative overflow-hidden border-2 border-gray-600 mt-2">
                                        <div id="glass-fill" class="absolute bottom-0 w-full bg-green-500 transition-all duration-500"></div>
                                    </div>
                                    <p id="glass-text" class="mt-1 text-lg font-mono text-center"></p>
                                    <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">24.0 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">23.5 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">11 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">0.26 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>
                                 <!-- AC Ezici Motor -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-1 text-center">AC Ezici Motor</h3>
                                    <div class="relative w-full h-16 mx-auto my-1 flex justify-center items-center">
                                        <svg id="crusher-gears" class="w-14 h-14 text-gray-400 will-change-transform" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-1.01L14.07 2.42c-.05-.26-.27-.47-.52-.52H10.45c-.25 0-.47.21-.52.47L9.5 4.95c-.61-.28-1.17.61-1.69 1.01l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24-.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69 1.01L9.93 21.5c-.05.26.17.52.47.52h3.1c.25 0 .47-.21.52-.47l.43-2.47c.61-.28 1.17-.61 1.69-1.01l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
                                        </svg>
                                    </div>
                                    <div class="grid grid-cols-3 gap-2 mt-auto">
                                        <button id="crusher-fwd-btn" class="bg-blue-600 hover:bg-blue-700 p-2 rounded-lg text-sm">İleri</button>
                                        <button id="crusher-stop-btn" class="bg-gray-600 hover:bg-gray-500 p-2 rounded-lg text-sm">Dur</button>
                                        <button id="crusher-rev-btn" class="bg-blue-600 hover:bg-blue-700 p-2 rounded-lg text-sm">Geri</button>
                                    </div>
                                    <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Verilen Frekans:</span><span id="crusher-set-freq" class="font-mono">50.0 Hz</span></li>
                                        <li class="flex justify-between"><span>Çıkış Frekansı:</span><span id="crusher-out-freq" class="font-mono">0.0 Hz</span></li>
                                        <li class="flex justify-between"><span>Voltaj:</span><span id="crusher-voltage" class="font-mono">0.0 V</span></li>
                                        <li class="flex justify-between"><span>Akım:</span><span id="crusher-current" class="font-mono">0.0 A</span></li>
                                        <li class="flex justify-between"><span>Güç:</span><span id="crusher-power" class="font-mono">0.0 W</span></li>
                                        <li class="flex justify-between"><span>Bus Voltajı:</span><span id="crusher-bus-voltage" class="font-mono">310 V</span></li>
                                        <li class="flex justify-between"><span>Sıcaklık:</span><span id="crusher-temp" class="font-mono">35 °C</span></li>
                                        <li class="flex justify-between"><span>Çalışma Yönü:</span><span id="crusher-direction">Duruyor</span></li>
                                        <li class="flex justify-between"><span>Çalışma Durumu:</span><span id="crusher-status">Çalışmıyor</span></li>
                                        <li class="flex justify-between"><span>Hazır Mı:</span><span id="crusher-ready" class="text-green-400">Evet</span></li>
                                        <li class="flex justify-between"><span>Arıza Var Mı:</span><span id="crusher-fault" class="text-green-400">Yok</span></li>
                                    </ul>
                                </div>
                                 <!-- AC Kırıcı Motor -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-1 text-center">AC Kırıcı Motor</h3>
                                     <div class="relative w-full h-16 mx-auto my-1 flex justify-center items-center">
                                        <svg id="breaker-gears" class="w-14 h-14 text-gray-400 will-change-transform" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-1.01L14.07 2.42c-.05-.26-.27-.47-.52-.52H10.45c-.25 0-.47.21-.52.47L9.5 4.95c-.61-.28-1.17.61-1.69 1.01l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24-.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69 1.01L9.93 21.5c-.05.26.17.52.47.52h3.1c.25 0 .47-.21.52-.47l.43-2.47c.61-.28 1.17-.61 1.69-1.01l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
                                        </svg>
                                    </div>
                                    <div class="grid grid-cols-3 gap-2 mt-auto">
                                        <button id="breaker-fwd-btn" class="bg-blue-600 hover:bg-blue-700 p-2 rounded-lg text-sm">İleri</button>
                                        <button id="breaker-stop-btn" class="bg-gray-600 hover:bg-gray-500 p-2 rounded-lg text-sm">Dur</button>
                                        <button id="breaker-rev-btn" class="bg-blue-600 hover:bg-blue-700 p-2 rounded-lg text-sm">Geri</button>
                                    </div>
                                    <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                       <li class="flex justify-between"><span>Verilen Frekans:</span><span id="breaker-set-freq" class="font-mono">50.0 Hz</span></li>
                                       <li class="flex justify-between"><span>Çıkış Frekansı:</span><span id="breaker-out-freq" class="font-mono">0.0 Hz</span></li>
                                       <li class="flex justify-between"><span>Voltaj:</span><span id="breaker-voltage" class="font-mono">0.0 V</span></li>
                                       <li class="flex justify-between"><span>Akım:</span><span id="breaker-current" class="font-mono">0.0 A</span></li>
                                       <li class="flex justify-between"><span>Güç:</span><span id="breaker-power" class="font-mono">0.0 W</span></li>
                                       <li class="flex justify-between"><span>Bus Voltajı:</span><span id="breaker-bus-voltage" class="font-mono">310 V</span></li>
                                       <li class="flex justify-between"><span>Sıcaklık:</span><span id="breaker-temp" class="font-mono">35 °C</span></li>
                                       <li class="flex justify-between"><span>Çalışma Yönü:</span><span id="breaker-direction">Duruyor</span></li>
                                       <li class="flex justify-between"><span>Çalışma Durumu:</span><span id="breaker-status">Çalışmıyor</span></li>
                                       <li class="flex justify-between"><span>Hazır Mı:</span><span id="breaker-ready" class="text-green-400">Evet</span></li>
                                       <li class="flex justify-between"><span>Arıza Var Mı:</span><span id="breaker-fault" class="text-green-400">Yok</span></li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                    <!-- Motor Kartı İçeriği -->
                    <div id="tab-content-motors" class="tab-content hidden">
                        <div class="bg-gray-800 p-4 sm:p-6 rounded-b-2xl shadow-lg">
                            <div class="flex flex-wrap justify-between items-center gap-4 mb-4 border-b border-gray-700 pb-2">
                                <div class="flex items-center space-x-4"><h2 class="text-xl font-semibold">Motor Kartı Detayları</h2><div id="motor-card-status" class="flex items-center space-x-2"></div></div>
                                <div class="flex items-center space-x-2"><button id="toggle-motors-btn" class="p-2 rounded-full hover:bg-gray-700 transition-colors" title="Paneli Daralt/Genişlet"></button><button id="reset-motor-card-btn" class="bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded-lg transition duration-300">Kartı Resetle</button></div>
                            </div>
                            <div id="motor-details-grid" class="details-grid mt-6 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6 lg:gap-8">
                                <!-- Konveyör Motor -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <div class="flex justify-between items-center mb-1"><h3 class="font-semibold text-md text-center">Konveyör Motor</h3><div class="power-switch relative w-12"><input type="checkbox" id="conveyor-power" class="motor-power-toggle" checked><label for="conveyor-power" class="power-switch-label"><span class="power-switch-inner"></span><span class="power-switch-switch"></span></label></div></div>
                                    <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm my-1 px-2 text-gray-300"><div class="flex items-center justify-between"><span class="font-semibold">Konum:</span><div id="conveyor-pos-led" class="w-4 h-4 rounded-full bg-gray-600"></div></div><div class="flex items-center justify-between"><span class="font-semibold">Alarm:</span><div id="conveyor-alarm-led" class="w-4 h-4 rounded-full bg-green-500"></div></div></div>
                                    <div id="conveyor-animation" class="w-full h-16 flex items-center justify-center mt-1 mb-2 relative bg-gray-800 border-2 border-gray-600 rounded-md overflow-hidden">
                                       <div id="conveyor-animation-bg" class="absolute inset-0"></div>
                                       <div id="conveyor-bottle" class="h-6 w-12 text-cyan-200 will-change-transform">
                                            <svg viewBox="0 0 32 16" fill="currentColor" class="w-full h-full">
                                                <path d="M29,6h-2V3c0-1.7-1.3-3-3-3H3C1.3,0,0,1.3,0,3v10c0,1.7,1.3,3,3,3h21c1.7,0,3-1.3,3-3v-3h2c1.7,0,3-1.3,3-3V9 C32,7.3,30.7,6,29,6z M26,13H3V3h21V13z"></path>
                                            </svg>
                                       </div>
                                    </div>
                                    <div class="flex items-center space-x-2 text-sm px-1 mb-2"><label for="conveyor-speed-slider" class="font-semibold">Hız:</label><input type="range" id="conveyor-speed-slider" min="0" max="100" value="50" class="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer speed-slider"><input type="number" id="conveyor-speed-input" min="0" max="100" value="50" class="w-16 bg-gray-900 text-center font-mono rounded-md border border-gray-600 p-1 text-sm"></div>
                                    <div class="grid grid-cols-3 gap-2 mt-auto"><button id="conveyor-fwd" class="bg-blue-600 hover:bg-blue-700 p-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed">İleri</button><button id="conveyor-stop" class="bg-gray-600 hover:bg-gray-500 p-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed">Dur</button><button id="conveyor-rev" class="bg-blue-600 hover:bg-blue-700 p-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed">Geri</button></div>
                                </div>
                                <!-- Yönlendirici Motor -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <div class="flex justify-between items-center mb-1"><h3 class="font-semibold text-md text-center">Yönlendirici Motor</h3><div class="power-switch relative w-12"><input type="checkbox" id="diverter-power" class="motor-power-toggle" checked><label for="diverter-power" class="power-switch-label"><span class="power-switch-inner"></span><span class="power-switch-switch"></span></label></div></div>
                                    <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm my-1 px-2 text-gray-300"><div class="flex items-center justify-between"><span class="font-semibold">Konum:</span><div id="diverter-pos-led" class="w-4 h-4 rounded-full bg-gray-600"></div></div><div class="flex items-center justify-between"><span class="font-semibold">Alarm:</span><div id="diverter-alarm-led" class="w-4 h-4 rounded-full bg-green-500"></div></div></div>
                                    <div class="flex items-center justify-center h-16 mt-1 mb-2"><div id="diverter-visual" class="w-16 h-16 relative flex items-center justify-center will-change-transform">
                                        <div class="snowflake"><div class="snowflake-arm"></div><div class="snowflake-arm"></div><div class="snowflake-arm"></div></div>
                                    </div></div>
                                    <div class="flex items-center space-x-2 text-sm px-1 mb-2"><label for="diverter-speed-slider" class="font-semibold">Hız:</label><input type="range" id="diverter-speed-slider" min="0" max="100" value="50" class="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer speed-slider"><input type="number" id="diverter-speed-input" min="0" max="100" value="50" class="w-16 bg-gray-900 text-center font-mono rounded-md border border-gray-600 p-1 text-sm"></div>
                                    <div class="grid grid-cols-2 gap-2 mt-auto"><button id="diverter-plastic" class="bg-teal-600 hover:bg-teal-700 p-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed">Plastik</button><button id="diverter-glass" class="bg-teal-600 hover:bg-teal-700 p-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed">Cam</button></div>
                                </div>
                                <!-- Klape Motor -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <div class="flex justify-between items-center mb-1"><h3 class="font-semibold text-md text-center">Klape Motor</h3><div class="power-switch relative w-12"><input type="checkbox" id="flap-power" class="motor-power-toggle" checked><label for="flap-power" class="power-switch-label"><span class="power-switch-inner"></span><span class="power-switch-switch"></span></label></div></div>
                                    <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm my-1 px-2 text-gray-300"><div class="flex items-center justify-between"><span class="font-semibold">Konum:</span><div id="flap-pos-led" class="w-4 h-4 rounded-full bg-gray-600"></div></div><div class="flex items-center justify-between"><span class="font-semibold">Alarm:</span><div id="flap-alarm-led" class="w-4 h-4 rounded-full bg-green-500"></div></div></div>
                                    <div class="flex items-center justify-center h-16 mt-1 mb-2"><div id="flap-visual" class="w-2 h-10 bg-indigo-400 rounded-full origin-bottom will-change-transform"></div></div>
                                    <div class="flex items-center space-x-2 text-sm px-1 mb-2"><label for="flap-speed-slider" class="font-semibold">Hız:</label><input type="range" id="flap-speed-slider" min="0" max="100" value="50" class="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer speed-slider"><input type="number" id="flap-speed-input" min="0" max="100" value="50" class="w-16 bg-gray-900 text-center font-mono rounded-md border border-gray-600 p-1 text-sm"></div>
                                    <div class="grid grid-cols-2 gap-2 mt-auto"><button id="flap-plastic" class="bg-indigo-600 hover:bg-indigo-700 p-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed">Plastik</button><button id="flap-metal" class="bg-indigo-600 hover:bg-indigo-700 p-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed">Metal</button></div>
                                </div>
                                <!-- Yönlendirici OPT Sensörü -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-1 text-center">Yönlendirici Sensör</h3>
                                    <div id="diverter-opt-visual" class="relative w-full h-12 mx-auto my-1">
                                         <svg class="w-full h-full" viewBox="0 0 100 40">
                                            <rect x="5" y="10" width="20" height="20" rx="4" fill="#4b5563"/>
                                            <circle cx="15" cy="20" r="3" fill="#60a5fa" />
                                            <rect x="75" y="10" width="20" height="20" rx="4" fill="#9ca3af"/>
                                            <rect x="80" y="15" width="4" height="10" fill="#fbbf24"/>
                                            <g id="diverter-opt-rays">
                                                <line class="ray" x1="25" y1="20" x2="75" y2="20" stroke="#facc15" stroke-width="2"/>
                                            </g>
                                            <g id="diverter-opt-blocker" class="hidden" opacity="0.6">
                                                <path d="M 50 5 L 55 10 L 55 30 L 50 35 L 45 30 L 45 10 Z" fill="#60a5fa" stroke="#e0f2fe" stroke-width="1.5"/>
                                            </g>
                                        </svg>
                                    </div>
                                    <div class="text-center mb-2"><span class="text-2xl font-mono" id="diverter-opt-output">--</span></div>
                                    <div class="flex space-x-2"><button id="diverter-opt-teach-btn" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Teach</button><button id="diverter-opt-test-btn" class="w-full bg-gray-600 hover:bg-gray-500 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Test Et</button></div>
                                    <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">24.2 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">36.1 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">18 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">0.44 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>
                                <!-- Yönlendirici İndüktif Sensör -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-1 text-center">Yönlendirici İndüktif</h3>
                                    <div class="relative w-full h-16 mx-auto my-1 flex justify-center items-center overflow-hidden">
                                       <svg class="w-full h-full" viewBox="0 0 100 60">
                                            <rect id="diverter-inductive-metal" x="0" y="22.5" width="15" height="15" rx="2" fill="#9ca3af" class="transition-transform duration-300" />
                                            <g transform="translate(75, 15)">
                                                <rect x="0" y="0" width="20" height="30" rx="4" fill="#4b5563"/>
                                                <circle cx="10" cy="15" r="6" stroke="#9ca3af" stroke-width="1.5" fill="none"/>
                                                <circle cx="10" cy="15" r="2" fill="#9ca3af"/>
                                            </g>
                                        </svg>
                                    </div>
                                    <div class="text-center mb-2">
                                        <span class="text-2xl font-mono" id="diverter-inductive-output">--</span>
                                    </div>
                                    <div class="flex mt-auto">
                                        <button id="diverter-inductive-test-btn" class="w-full bg-gray-600 hover:bg-gray-500 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Test Et</button>
                                    </div>
                                    <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">24.0 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">28.5 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">14 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">0.34 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>
                                <!-- Klape İndüktif Sensör -->
                                 <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-1 text-center">Klape İndüktif</h3>
                                     <div class="relative w-full h-16 mx-auto my-1 flex justify-center items-center overflow-hidden">
                                       <svg class="w-full h-full" viewBox="0 0 100 60">
                                            <rect id="flap-inductive-metal" x="0" y="22.5" width="15" height="15" rx="2" fill="#9ca3af" class="transition-transform duration-300" />
                                            <g transform="translate(75, 15)">
                                                <rect x="0" y="0" width="20" height="30" rx="4" fill="#4b5563"/>
                                                <circle cx="10" cy="15" r="6" stroke="#9ca3af" stroke-width="1.5" fill="none"/>
                                                <circle cx="10" cy="15" r="2" fill="#9ca3af"/>
                                            </g>
                                        </svg>
                                    </div>
                                    <div class="text-center mb-2">
                                        <span class="text-2xl font-mono" id="flap-inductive-output">--</span>
                                    </div>
                                    <div class="flex mt-auto">
                                        <button id="flap-inductive-test-btn" class="w-full bg-gray-600 hover:bg-gray-500 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Test Et</button>
                                    </div>
                                    <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">24.1 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">29.2 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">15 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">0.36 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                     <!-- Güvenlik Kartı İçeriği -->
                    <div id="tab-content-safety" class="tab-content hidden">
                         <div class="bg-gray-800 p-4 sm:p-6 rounded-b-2xl shadow-lg">
                             <div class="flex flex-wrap justify-between items-center gap-4 mb-4 border-b border-gray-700 pb-2">
                                <h2 class="text-xl font-semibold">Güvenlik Kartı Detayları</h2>
                             </div>
                              <div id="safety-details-grid" class="details-grid mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-6 lg:gap-8">
                                <!-- Üst Kapak Kilit -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-2 text-center">Üst Kapak Kilidi</h3>
                                    <div class="flex-grow flex items-center justify-center my-2">
                                        <div id="top-lock-visual" class="lock-visual w-16 h-16">
                                            <svg viewBox="0 -15 50 95" class="w-full h-full">
                                                <rect x="5" y="15" width="40" height="65" rx="3" fill="#111827" />
                                                <g class="lock-head">
                                                    <rect x="10" y="5" width="30" height="15" rx="2" fill="#f59e0b" />
                                                    <rect x="15" y="8" width="20" height="5" fill="#111827" />
                                                </g>
                                            </svg>
                                        </div>
                                    </div>
                                     <div class="flex items-center justify-center space-x-4 mb-3">
                                        <div class="flex items-center space-x-2">
                                            <div id="top-lock-status-led" class="w-3 h-3 rounded-full bg-red-500"></div>
                                            <span id="top-lock-status-text" class="font-semibold text-red-400">Kilit Kapalı</span>
                                        </div>
                                        <div class="flex items-center space-x-2">
                                            <div id="top-lock-tongue-led" class="w-3 h-3 rounded-full bg-green-500"></div>
                                            <span id="top-lock-tongue-text" class="font-semibold text-green-400">Dil Var</span>
                                        </div>
                                    </div>
                                    <div class="flex space-x-2 mt-auto">
                                        <button id="top-lock-open-btn" class="w-full bg-green-600 hover:bg-green-700 p-2 rounded-lg text-sm">Kilit Aç</button>
                                        <button id="top-lock-close-btn" class="w-full bg-red-600 hover:bg-red-700 p-2 rounded-lg text-sm">Kilit Kapat</button>
                                    </div>
                                    <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">12.0 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">15.1 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">75 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">0.9 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>

                                <!-- Alt Kapak Kilit -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-2 text-center">Alt Kapak Kilidi</h3>
                                    <div class="flex-grow flex items-center justify-center my-2">
                                        <div id="bottom-lock-visual" class="lock-visual w-16 h-16">
                                            <svg viewBox="0 -15 50 95" class="w-full h-full">
                                                <rect x="5" y="15" width="40" height="65" rx="3" fill="#111827" />
                                                <g class="lock-head">
                                                    <rect x="10" y="5" width="30" height="15" rx="2" fill="#f59e0b" />
                                                    <rect x="15" y="8" width="20" height="5" fill="#111827" />
                                                </g>
                                            </svg>
                                        </div>
                                    </div>
                                    <div class="flex items-center justify-center space-x-4 mb-3">
                                        <div class="flex items-center space-x-2">
                                            <div id="bottom-lock-status-led" class="w-3 h-3 rounded-full bg-red-500"></div>
                                            <span id="bottom-lock-status-text" class="font-semibold text-red-400">Kilit Kapalı</span>
                                        </div>
                                        <div class="flex items-center space-x-2">
                                            <div id="bottom-lock-tongue-led" class="w-3 h-3 rounded-full bg-green-500"></div>
                                            <span id="bottom-lock-tongue-text" class="font-semibold text-green-400">Dil Var</span>
                                        </div>
                                    </div>
                                    <div class="flex space-x-2 mt-auto">
                                        <button id="bottom-lock-open-btn" class="w-full bg-green-600 hover:bg-green-700 p-2 rounded-lg text-sm">Kilit Aç</button>
                                        <button id="bottom-lock-close-btn" class="w-full bg-red-600 hover:bg-red-700 p-2 rounded-lg text-sm">Kilit Kapat</button>
                                    </div>
                                     <ul class="mt-2 space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">12.1 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">14.8 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">74 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">0.89 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>
                                
                                <!-- Üst Kapak Manyetik Sensör -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-2 text-center">Üst Kapak Emniyet Sensörü</h3>
                                    <div class="flex-grow flex items-center justify-center my-2">
                                        <div id="top-sensor-visual" class="sensor-visual w-24 h-16">
                                            <svg viewBox="0 0 100 50" class="w-full h-full">
                                                <!-- Sabit Parça -->
                                                <g>
                                                    <rect x="5" y="10" width="30" height="30" rx="3" fill="#f59e0b"/>
                                                    <rect x="30" y="10" width="5" height="30" fill="#111827"/>
                                                    <circle cx="15" cy="20" r="4" fill="#1f2937"/>
                                                    <circle cx="15" cy="30" r="4" fill="#1f2937"/>
                                                </g>
                                                <!-- Hareketli Parça -->
                                                <g class="sensor-part-movable">
                                                    <rect x="45" y="10" width="30" height="30" rx="3" fill="#f59e0b"/>
                                                    <rect x="45" y="10" width="5" height="30" fill="#111827"/>
                                                    <circle cx="65" cy="20" r="4" fill="#1f2937"/>
                                                    <circle cx="65" cy="30" r="4" fill="#1f2937"/>
                                                </g>
                                            </svg>
                                        </div>
                                    </div>
                                     <div class="flex items-center justify-center space-x-2 mb-3">
                                        <div id="top-sensor-status-led" class="w-3 h-3 rounded-full bg-green-500"></div>
                                        <span id="top-sensor-status-text" class="font-semibold text-green-400">Aktif (Kapak Kapalı)</span>
                                    </div>
                                     <ul class="mt-auto space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">5.0 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">2.1 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">5 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">0.025 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>

                                <!-- Alt Kapak Manyetik Sensör -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-2 text-center">Alt Kapak Emniyet Sensörü</h3>
                                    <div class="flex-grow flex items-center justify-center my-2">
                                        <div id="bottom-sensor-visual" class="sensor-visual w-24 h-16">
                                             <svg viewBox="0 0 100 50" class="w-full h-full">
                                                <!-- Sabit Parça -->
                                                <g>
                                                    <rect x="5" y="10" width="30" height="30" rx="3" fill="#f59e0b"/>
                                                    <rect x="30" y="10" width="5" height="30" fill="#111827"/>
                                                    <circle cx="15" cy="20" r="4" fill="#1f2937"/>
                                                    <circle cx="15" cy="30" r="4" fill="#1f2937"/>
                                                </g>
                                                <!-- Hareketli Parça -->
                                                <g class="sensor-part-movable">
                                                    <rect x="45" y="10" width="30" height="30" rx="3" fill="#f59e0b"/>
                                                    <rect x="45" y="10" width="5" height="30" fill="#111827"/>
                                                    <circle cx="65" cy="20" r="4" fill="#1f2937"/>
                                                    <circle cx="65" cy="30" r="4" fill="#1f2937"/>
                                                </g>
                                            </svg>
                                        </div>
                                    </div>
                                    <div class="flex items-center justify-center space-x-2 mb-3">
                                        <div id="bottom-sensor-status-led" class="w-3 h-3 rounded-full bg-green-500"></div>
                                        <span id="bottom-sensor-status-text" class="font-semibold text-green-400">Aktif (Kapak Kapalı)</span>
                                    </div>
                                    <ul class="mt-auto space-y-1 text-xs text-gray-300">
                                        <li class="flex justify-between"><span>Bus Voltajı:</span> <span class="font-mono">5.0 V</span></li>
                                        <li class="flex justify-between"><span>Şönt Voltajı:</span> <span class="font-mono">2.2 mV</span></li>
                                        <li class="flex justify-between"><span>Akım:</span> <span class="font-mono">5 mA</span></li>
                                        <li class="flex justify-between"><span>Güç:</span> <span class="font-mono">0.025 W</span></li>
                                        <li class="flex justify-between items-center"><span>Sağlık Durumu:</span> <span class="flex items-center gap-1">İyi <span class="w-2 h-2 rounded-full bg-green-500"></span></span></li>
                                    </ul>
                                </div>
                                  <!-- Soğutma Fanı -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-2 text-center">Soğutma Fanı</h3>
                                    <div class="flex-grow flex items-center justify-center my-2">
                                        <div class="w-20 h-20">
                                            <svg id="fan-svg" viewBox="0 0 100 100" class="w-full h-full text-gray-500 transition-colors duration-300">
                                                <!-- Frame -->
                                                <rect width="100" height="100" rx="10" fill="#1f2937" />
                                                <path d="M50,10 A40,40 0 1,1 50,90 A40,40 0 1,1 50,10 M50,18 A32,32 0 1,0 50,82 A32,32 0 1,0 50,18" fill="#111827"/>
                                                <circle cx="15" cy="15" r="5" fill="#111827" />
                                                <circle cx="85" cy="15" r="5" fill="#111827" />
                                                <circle cx="15" cy="85" r="5" fill="#111827" />
                                                <circle cx="85" cy="85" r="5" fill="#111827" />
                                                
                                                <!-- Blades and Hub -->
                                                <g id="fan-blades">
                                                    <circle cx="50" cy="50" r="18" fill="#1f2937" />
                                                    <path d="M50 50 L 35 25 C 50 20, 50 20, 65 25 Z" fill="currentColor"/>
                                                    <path d="M50 50 L 25 65 C 20 50, 20 50, 25 35 Z" fill="currentColor"/>
                                                    <path d="M50 50 L 65 75 C 50 80, 50 80, 35 75 Z" fill="currentColor"/>
                                                    <path d="M50 50 L 75 35 C 80 50, 80 50, 75 65 Z" fill="currentColor"/>
                                                </g>
                                            </svg>
                                        </div>
                                    </div>
                                    <div class="space-y-2 mt-auto">
                                        <div class="flex items-center space-x-2">
                                            <input type="range" id="fan-speed-slider" min="0" max="100" value="0" class="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer speed-slider">
                                            <input type="number" id="fan-speed-input" min="0" max="100" value="0" class="w-16 bg-gray-900 text-center font-mono rounded-md border border-gray-600 p-1 text-sm">
                                        </div>
                                        <div class="flex space-x-2">
                                            <button id="fan-on-btn" class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Aç</button>
                                            <button id="fan-off-btn" class="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-3 rounded-lg transition text-sm">Kapat</button>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Güvenlik Rölesi -->
                                <div class="bg-gray-700/50 p-3 rounded-lg flex flex-col">
                                    <h3 class="font-semibold text-md mb-2 text-center">Güvenlik Rölesi</h3>
                                    <div class="flex-grow flex items-center justify-center my-2">
                                        <div class="w-20 h-24 p-2">
                                             <svg id="safety-relay-icon" viewBox="0 0 60 80" class="w-full h-full">
                                                <rect x="0" y="0" width="60" height="80" rx="5" fill="#f59e0b"/>
                                                <rect x="0" y="0" width="25" height="80" fill="#111827" ry="5" rx="5"/>
                                                <rect x="30" y="20" width="25" height="40" fill="#111827" opacity="0.7" rx="2"/>
                                            </svg>
                                        </div>
                                    </div>
                                     <div class="grid grid-cols-2 gap-2 text-sm text-center mb-3 px-2">
                                        <div id="safety-relay-status" class="flex items-center justify-center space-x-2 py-1 bg-gray-900/50 rounded-md">
                                            <div id="safety-relay-led" class="w-3 h-3 rounded-full bg-red-500"></div>
                                            <span id="safety-relay-text" class="font-semibold text-red-400">Röle Pasif</span>
                                        </div>
                                         <div id="bypass-status" class="flex items-center justify-center space-x-2 py-1 bg-gray-900/50 rounded-md">
                                            <div id="bypass-led" class="w-3 h-3 rounded-full bg-green-500"></div>
                                            <span id="bypass-text" class="font-semibold text-green-400">Kilitler Aktif</span>
                                        </div>
                                    </div>
                                    <div class="flex space-x-2 mt-auto">
                                        <button id="safety-relay-reset-btn" class="w-full bg-blue-600 hover:bg-blue-700 p-2 rounded-lg text-sm">Reset</button>
                                        <button id="safety-relay-bypass-btn" class="w-full bg-yellow-600 hover:bg-yellow-700 p-2 rounded-lg text-sm">Bypass</button>
                                    </div>
                                </div>


                            </div>
                         </div>
                    </div>
                </div>
            </div>

        </main>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const successIcon = `<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`;
            const errorIcon = `<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`;
            const loadingIcon = `<div class="w-5 h-5 border-t-2 border-blue-500 border-solid rounded-full animate-spin"></div>`;
            
            // --- SEKME KONTROLÜ ---
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

                    const visibleGrid = document.querySelector(`#${targetContentId} .details-grid.expanded`);
                    if (visibleGrid) {
                         visibleGrid.style.maxHeight = visibleGrid.scrollHeight + 'px';
                    }
                });
            });

            // --- KART GİZLE/GÖSTER FONKSİYONU ---
            const chevronUpIcon = `<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" /></svg>`;
            const chevronDownIcon = `<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" /></svg>`;
            function setupToggle(toggleBtnId, gridId) {
                const toggleBtn = document.getElementById(toggleBtnId), grid = document.getElementById(gridId);
                if (!toggleBtn || !grid) return;
                toggleBtn.innerHTML = chevronUpIcon;
                toggleBtn.addEventListener('click', () => { const isExpanded = grid.classList.contains('expanded'); if (isExpanded) { grid.style.maxHeight = '0px'; grid.style.marginTop = '0'; grid.style.opacity = '0'; toggleBtn.innerHTML = chevronDownIcon; grid.classList.remove('expanded'); } else { grid.style.maxHeight = grid.scrollHeight + 'px'; grid.style.marginTop = '1.5rem'; grid.style.opacity = '1'; toggleBtn.innerHTML = chevronUpIcon; grid.classList.add('expanded'); } });
                grid.classList.add('expanded'); grid.style.maxHeight = grid.scrollHeight + 'px';
                new ResizeObserver(() => { if (grid.classList.contains('expanded')) { grid.style.maxHeight = grid.scrollHeight + 'px'; } }).observe(grid);
            }
            setupToggle('toggle-sensors-btn', 'sensor-details-grid');
            setupToggle('toggle-motors-btn', 'motor-details-grid');

            // --- GENEL KART BAĞLANTI KONTROL FONKSİYONU ---
            let cardConnectionTimeouts = {};
            function setCardStatus(container, resetButton, status, message = '') {
                let icon = '', textClass = '';
                switch (status) {
                    case 'connected': icon = successIcon; textClass = 'text-green-400'; message = message || 'Bağlandı'; resetButton.disabled = false; break;
                    case 'disconnected': icon = errorIcon; textClass = 'text-red-400'; message = message || 'Bağlantı Yok'; resetButton.disabled = false; break;
                    case 'connecting': icon = loadingIcon; textClass = 'text-blue-400'; message = message || 'İşlem...'; resetButton.disabled = true; break;
                }
                container.innerHTML = `${icon}<span class="${textClass} font-semibold">${message}</span>`;
            }
            function setupCardConnection(cardName, containerId, resetBtnId) {
                const container = document.getElementById(containerId);
                const resetButton = document.getElementById(resetBtnId);
                if (!container || !resetButton) return;

                const connectCard = () => { clearTimeout(cardConnectionTimeouts[cardName]); setCardStatus(container, resetButton, 'connecting', 'Bağlantı başarılı!'); cardConnectionTimeouts[cardName] = setTimeout(() => { setCardStatus(container, resetButton, 'connected'); }, 2000); };
                const resetCard = () => { clearTimeout(cardConnectionTimeouts[cardName]); setCardStatus(container, resetButton, 'connecting', 'Bağlantı koptu...'); setTimeout(() => { setCardStatus(container, resetButton, 'disconnected'); cardConnectionTimeouts[cardName] = setTimeout(connectCard, 5000); }, 3000); };
                
                resetButton.addEventListener('click', resetCard);
                setCardStatus(container, resetButton, 'connected');
            }
            setupCardConnection('sensor', 'sensor-card-status', 'reset-sensor-card-btn');
            setupCardConnection('motor', 'motor-card-status', 'reset-motor-card-btn');

            // --- SENSÖR KARTI KONTROLLERİ ---
            // OPT Sensör Kontrolü
            function setupOptSensor(prefix) {
                const teachBtn = document.getElementById(`${prefix}-teach-btn`);
                const testBtn = document.getElementById(`${prefix}-test-btn`);
                const output = document.getElementById(`${prefix}-output`);
                const rays = document.getElementById(`${prefix}-rays`);
                const blocker = document.getElementById(`${prefix}-blocker`);

                teachBtn.addEventListener('click', () => { 
                    if (teachBtn.disabled) return;
                    teachBtn.disabled = true; testBtn.disabled = true;
                    rays.classList.add('teaching-rays');
                    teachBtn.innerText = "Öğreniyor...";
                    setTimeout(() => {
                        rays.classList.remove('teaching-rays');
                        teachBtn.innerText = "Teach";
                        teachBtn.disabled = false; testBtn.disabled = false;
                    }, 5000);
                });

                testBtn.addEventListener('click', () => {
                    const result = Math.round(Math.random());
                    output.innerText = result;
                    if (result === 1) {
                        blocker.classList.remove('hidden');
                    } else {
                        blocker.classList.add('hidden');
                    }
                });
            }
            setupOptSensor('opt1009');
            
            const measureBtn = document.getElementById('loadcell-measure-btn'), tareBtn = document.getElementById('loadcell-tare-btn'), loadcellVisual = document.getElementById('loadcell-visual'), loadcellOutput = document.getElementById('loadcell-output'), loadcellMessage = document.getElementById('loadcell-message');
            measureBtn.addEventListener('click', () => { if (measureBtn.disabled) return; tareBtn.disabled = true; measureBtn.disabled = true; loadcellMessage.innerText = 'Ölçüm yapılıyor...'; loadcellVisual.classList.add('measuring'); setTimeout(() => { loadcellOutput.innerHTML = `${(Math.random() * 50).toFixed(1)} <span class="text-2xl">gr</span>`; loadcellMessage.innerText = ''; loadcellVisual.classList.remove('measuring'); tareBtn.disabled = false; measureBtn.disabled = false; }, 2000); });
            tareBtn.addEventListener('click', () => { if(tareBtn.disabled) return; tareBtn.disabled = true; measureBtn.disabled = true; loadcellMessage.innerText = 'Konveyörü boşaltın...'; setTimeout(() => { loadcellMessage.innerText = 'Tare alınıyor...'; loadcellVisual.classList.add('measuring'); setTimeout(() => { loadcellOutput.innerHTML = `0.0 <span class="text-2xl">gr</span>`; loadcellMessage.innerText = 'Tare alma başarılı!'; loadcellVisual.classList.remove('measuring'); setTimeout(() => { loadcellMessage.innerText = ''; tareBtn.disabled = false; measureBtn.disabled = false; }, 2000); }, 2000); }, 3000); });
            function updateFillLevel(material, percentage) { document.getElementById(`${material}-fill`).style.height = `${percentage}%`; document.getElementById(`${material}-text`).innerText = `${percentage}% Dolu`; }
            updateFillLevel('plastic', 65); updateFillLevel('metal', 80); updateFillLevel('glass', 45);
            const ledVisual = document.getElementById('conveyor-led-visual'), ledSvg = ledVisual.querySelector('svg'), brightnessSlider = document.getElementById('led-brightness-slider'), brightnessInput = document.getElementById('led-brightness-input');
            function updateLedState(brightness) { 
                const value = Math.max(0, Math.min(100, brightness)); 
                brightnessSlider.value = value; 
                brightnessInput.value = value; 
                if (value > 0) { 
                    ledVisual.classList.add('led-on'); 
                    ledSvg.classList.remove('text-gray-500'); 
                    ledSvg.classList.add('text-yellow-300'); 
                } else { 
                    ledVisual.classList.remove('led-on'); 
                    ledSvg.classList.add('text-gray-500'); 
                    ledSvg.classList.remove('text-yellow-300'); 
                } 
            }
            document.getElementById('led-on-btn').addEventListener('click', () => updateLedState(100)); document.getElementById('led-off-btn').addEventListener('click', () => updateLedState(0));
            brightnessSlider.addEventListener('input', () => updateLedState(parseInt(brightnessSlider.value, 10))); brightnessInput.addEventListener('input', () => { const val = parseInt(brightnessInput.value, 10); if (!isNaN(val)) updateLedState(val); });

            // AC Motor Kontrolleri
            function setupAcMotor(prefix) {
                // Buttons and visual elements
                const fwdBtn = document.getElementById(`${prefix}-fwd-btn`);
                const revBtn = document.getElementById(`${prefix}-rev-btn`);
                const stopBtn = document.getElementById(`${prefix}-stop-btn`);
                const gears = document.getElementById(`${prefix}-gears`);
                
                // Data display elements
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

                let interval = null;
                let motorData = {
                    outFreq: 0,
                    temp: 35
                };

                const updateMotorDisplay = (isRunning, direction = "Duruyor") => {
                    if (isRunning) {
                        motorData.temp += Math.random() * 0.1;
                        motorData.outFreq = Math.min(50, motorData.outFreq + 2.5);

                        outFreqEl.textContent = `${motorData.outFreq.toFixed(1)} Hz`;
                        voltageEl.textContent = `${(220 + (Math.random() - 0.5) * 5).toFixed(1)} V`;
                        currentEl.textContent = `${(1.5 + (Math.random() - 0.5) * 0.2).toFixed(1)} A`;
                        powerEl.textContent = `${(parseFloat(voltageEl.textContent) * parseFloat(currentEl.textContent)).toFixed(1)} W`;
                        busVoltageEl.textContent = `${(310 + (Math.random() - 0.5) * 3).toFixed(1)} V`;
                        tempEl.textContent = `${motorData.temp.toFixed(1)} °C`;
                        directionEl.textContent = direction;
                        statusEl.textContent = 'Çalışıyor';
                        readyEl.textContent = 'Hayır';
                        readyEl.classList.remove('text-green-400');
                        readyEl.classList.add('text-red-400');
                    } else {
                        // Reset to default stopped state
                        motorData.outFreq = 0;
                        motorData.temp = Math.max(35, motorData.temp - 1);
                        
                        outFreqEl.textContent = '0.0 Hz';
                        voltageEl.textContent = '0.0 V';
                        currentEl.textContent = '0.0 A';
                        powerEl.textContent = '0.0 W';
                        busVoltageEl.textContent = '310.0 V';
                        tempEl.textContent = `${motorData.temp.toFixed(1)} °C`;
                        directionEl.textContent = 'Duruyor';
                        statusEl.textContent = 'Çalışmıyor';
                        readyEl.textContent = 'Evet';
                        readyEl.classList.add('text-green-400');
                        readyEl.classList.remove('text-red-400');
                        faultEl.textContent = 'Yok';
                        faultEl.classList.add('text-green-400');
                        faultEl.classList.remove('text-red-400');
                    }
                };

                const startMotor = (direction) => {
                    if (interval) clearInterval(interval);
                    motorData.outFreq = 0; // reset ramp
                    interval = setInterval(() => updateMotorDisplay(true, direction), 250);
                };

                const stopMotor = () => {
                    gears.classList.remove('spinning', 'spinning-rev');
                    if (interval) clearInterval(interval);
                    interval = null; // Clear main running interval immediately
                    
                    // A new interval for graceful shutdown simulation
                    const shutdownInterval = setInterval(() => {
                        let isCooling = motorData.temp > 35;
                        let isSlowing = motorData.outFreq > 0;

                        if(isSlowing){
                             motorData.outFreq = Math.max(0, motorData.outFreq - 5);
                             outFreqEl.textContent = `${motorData.outFreq.toFixed(1)} Hz`;
                             voltageEl.textContent = '0.0 V';
                             currentEl.textContent = '0.0 A';
                             powerEl.textContent = '0.0 W';
                        }
                         if (isCooling) {
                             motorData.temp = Math.max(35, motorData.temp - 0.5);
                             tempEl.textContent = `${motorData.temp.toFixed(1)} °C`;
                        }

                        if(!isCooling && !isSlowing) {
                             clearInterval(shutdownInterval);
                             updateMotorDisplay(false);
                        }
                    }, 50);
                };

                fwdBtn.addEventListener('click', () => {
                    gears.classList.remove('spinning-rev');
                    gears.classList.add('spinning');
                    startMotor("İleri");
                });
                revBtn.addEventListener('click', () => {
                    gears.classList.remove('spinning');
                    gears.classList.add('spinning-rev');
                    startMotor("Geri");
                });
                stopBtn.addEventListener('click', stopMotor);

                // Initial state
                updateMotorDisplay(false);
            }
            setupAcMotor('crusher');
            setupAcMotor('breaker');

            // --- MOTOR KARTI KONTROLLERİ ---
            // Generic Motor Kontrol Fonksiyonu (Yönlendirici ve Klape için)
            function controlPositionalMotor(elements, action, duration) {
                if (elements.buttons.some(b => b.disabled)) return;
                elements.buttons.forEach(b => b.disabled = true);
                
                elements.alarmLed.className = 'w-4 h-4 rounded-full bg-green-500';
                elements.posLed.className = 'w-4 h-4 rounded-full bg-gray-600';

                action();

                if (Math.random() < 0.15) { 
                    setTimeout(() => {
                        if (elements.stopAction) elements.stopAction();
                        elements.alarmLed.className = 'w-4 h-4 rounded-full led-blink-red';
                        elements.posLed.className = 'w-4 h-4 rounded-full led-blink-red';
                        elements.buttons.forEach(b => b.disabled = false);
                    }, duration / 2);
                    return;
                }

                setTimeout(() => {
                    if (elements.stopAction) elements.stopAction();
                    elements.posLed.className = 'w-4 h-4 rounded-full led-blink-green';
                    elements.buttons.forEach(b => b.disabled = false);
                    setTimeout(() => {
                        if (elements.posLed.classList.contains('led-blink-green')) {
                            elements.posLed.className = 'w-4 h-4 rounded-full bg-gray-600';
                        }
                    }, 2000);
                }, duration);
            }

            // Hız Ayarı Fonksiyonu
            function setupSpeedControl(prefix, visualElement, minDuration, maxDuration, bottleElement = null, minBottleDuration = 0, maxBottleDuration = 0) {
                const speedSlider = document.getElementById(`${prefix}-speed-slider`);
                const speedInput = document.getElementById(`${prefix}-speed-input`);
                if (!speedSlider || !speedInput) return;

                const updateSpeed = () => {
                    const speed = parseInt(speedInput.value, 10);
                    const duration = maxDuration - ((speed / 100) * (maxDuration - minDuration));
                    visualElement.style.setProperty(`--${prefix}-duration`, `${duration}s`);
                    
                    if (bottleElement) {
                         const bottleDuration = maxBottleDuration - ((speed / 100) * (maxBottleDuration - minBottleDuration));
                         bottleElement.style.setProperty(`--${prefix}-bottle-duration`, `${bottleDuration}s`);
                    }
                };

                speedSlider.addEventListener('input', () => { speedInput.value = speedSlider.value; updateSpeed(); });
                speedInput.addEventListener('input', () => { 
                    let val = parseInt(speedInput.value, 10);
                    if (isNaN(val)) val = 0;
                    if (val < 0) val = 0;
                    if (val > 100) val = 100;
                    speedSlider.value = val;
                    speedInput.value = val;
                    updateSpeed(); 
                });
                updateSpeed(); // Initial call
            }

            // Güç Anahtarı Kontrolü
            document.querySelectorAll('.motor-power-toggle').forEach(toggle => {
                toggle.addEventListener('change', event => {
                    const isChecked = event.target.checked;
                    const controlContainer = event.target.closest('.bg-gray-700\\/50');
                    const motorPrefix = toggle.id.split('-')[0];

                    controlContainer.querySelectorAll('button, input[type="range"], input[type="number"]').forEach(el => {
                         if (el.type !== 'checkbox') el.disabled = !isChecked;
                    });
                    
                    const visuals = controlContainer.querySelectorAll('.my-2, .grid.mt-auto, .flex.items-center.space-x-2');
                    visuals.forEach(v => v.style.opacity = isChecked ? 1 : 0.5);

                    if (motorPrefix === 'conveyor') {
                        document.getElementById('conveyor-animation').classList.remove('conveyor-running-forward', 'conveyor-running-backward');
                    } else if (motorPrefix === 'diverter') {
                        const diverterVisual = document.getElementById('diverter-visual');
                        diverterVisual.style.animation = '';
                        diverterVisual.style.transform = '';
                    } else if (motorPrefix === 'flap') {
                         document.getElementById('flap-visual').style.transform = 'rotate(0deg)';
                    }
                    
                    if (isChecked) {
                        const posLed = document.getElementById(`${prefix}-pos-led`);
                        const alarmLed = document.getElementById(`${prefix}-alarm-led`);
                        if (posLed) posLed.className = 'w-4 h-4 rounded-full bg-gray-600';
                        if (alarmLed) alarmLed.className = 'w-4 h-4 rounded-full bg-green-500';
                    }
                });
            });

            // Konveyör Motor Kontrolü
            const conveyorAnimation = document.getElementById('conveyor-animation');
            const conveyorFwdBtn = document.getElementById('conveyor-fwd');
            const conveyorStopBtn = document.getElementById('conveyor-stop');
            const conveyorRevBtn = document.getElementById('conveyor-rev');
            const conveyorPosLed = document.getElementById('conveyor-pos-led');
            const conveyorAlarmLed = document.getElementById('conveyor-alarm-led');
            setupSpeedControl('conveyor', conveyorAnimation, 0.5, 2, conveyorAnimation, 1.5, 4);

            const resetConveyorLeds = () => {
                conveyorAlarmLed.className = 'w-4 h-4 rounded-full bg-green-500';
                conveyorPosLed.className = 'w-4 h-4 rounded-full bg-gray-600';
            };

            conveyorFwdBtn.addEventListener('click', () => {
                if (conveyorFwdBtn.disabled) return;
                resetConveyorLeds();
                conveyorAnimation.classList.add('conveyor-running-forward');
                conveyorAnimation.classList.remove('conveyor-running-backward');
            });

            conveyorRevBtn.addEventListener('click', () => {
                if (conveyorRevBtn.disabled) return;
                resetConveyorLeds();
                conveyorAnimation.classList.add('conveyor-running-backward');
                conveyorAnimation.classList.remove('conveyor-running-forward');
            });

            conveyorStopBtn.addEventListener('click', () => {
                if (conveyorStopBtn.disabled) return;
                conveyorAnimation.classList.remove('conveyor-running-forward', 'conveyor-running-backward');
                conveyorPosLed.className = 'w-4 h-4 rounded-full led-blink-green';
                setTimeout(() => {
                    if (conveyorPosLed.classList.contains('led-blink-green')) {
                        conveyorPosLed.className = 'w-4 h-4 rounded-full bg-gray-600';
                    }
                }, 2000);
            });


            // Yönlendirici Motor
            const diverterVisual = document.getElementById('diverter-visual');
            const diverterElements = {
                buttons: [document.getElementById('diverter-plastic'), document.getElementById('diverter-glass')],
                posLed: document.getElementById('diverter-pos-led'),
                alarmLed: document.getElementById('diverter-alarm-led'),
                stopAction: () => diverterVisual.style.animation = ''
            };
            setupSpeedControl('diverter', diverterVisual, 0.5, 2);
            
            const getDiverterDuration = () => {
                const speed = parseInt(document.getElementById('diverter-speed-input').value, 10);
                return 2 - ((speed / 100) * (2 - 0.5));
            };

            diverterElements.buttons[0].addEventListener('click', () => {
                const duration = getDiverterDuration();
                controlPositionalMotor(diverterElements, () => { 
                    diverterVisual.style.animation = `diverter-spin-rev ${duration}s linear infinite`; 
                    setTimeout(() => { diverterVisual.style.transform = 'rotate(-45deg)'; }, duration * 1000);
                }, duration * 1000);
            });
            diverterElements.buttons[1].addEventListener('click', () => {
                const duration = getDiverterDuration();
                controlPositionalMotor(diverterElements, () => { 
                    diverterVisual.style.animation = `diverter-spin ${duration}s linear infinite`; 
                    setTimeout(() => { diverterVisual.style.transform = 'rotate(45deg)'; }, duration * 1000);
                }, duration * 1000);
            });

            // Klape Motor
            const flapVisual = document.getElementById('flap-visual');
            const flapElements = {
                buttons: [document.getElementById('flap-plastic'), document.getElementById('flap-metal')],
                posLed: document.getElementById('flap-pos-led'),
                alarmLed: document.getElementById('flap-alarm-led')
            };
            setupSpeedControl('flap', flapVisual, 0.2, 1);
            
            const getFlapDuration = () => {
                const speed = parseInt(document.getElementById('flap-speed-input').value, 10);
                return (1 - ((speed / 100) * (1 - 0.2))) * 1000;
            };

            flapElements.buttons[0].addEventListener('click', () => controlPositionalMotor(flapElements, () => { flapVisual.style.transform = 'rotate(0deg)'; }, getFlapDuration()));
            flapElements.buttons[1].addEventListener('click', () => controlPositionalMotor(flapElements, () => { flapVisual.style.transform = 'rotate(90deg)'; }, getFlapDuration()));

            // Yönlendirici OPT Sensörü
            setupOptSensor('diverter-opt');
            
            // İndüktif Sensörler
            const dInductiveBtn = document.getElementById('diverter-inductive-test-btn');
            const dInductiveOut = document.getElementById('diverter-inductive-output');
            const dInductiveMetal = document.getElementById('diverter-inductive-metal');
            dInductiveBtn.addEventListener('click', () => {
                const result = Math.round(Math.random());
                dInductiveOut.innerText = result;
                dInductiveMetal.style.transform = result === 1 ? 'translateX(55px)' : 'translateX(0px)';
            });

            const fInductiveBtn = document.getElementById('flap-inductive-test-btn');
            const fInductiveOut = document.getElementById('flap-inductive-output');
            const fInductiveMetal = document.getElementById('flap-inductive-metal');
            fInductiveBtn.addEventListener('click', () => {
                const result = Math.round(Math.random());
                fInductiveOut.innerText = result;
                fInductiveMetal.style.transform = result === 1 ? 'translateX(55px)' : 'translateX(0px)';
            });

            // --- GÜVENLİK KARTI KONTROLLERİ ---
            function setupFanControl() {
                const fanSvg = document.getElementById('fan-svg');
                const speedSlider = document.getElementById('fan-speed-slider');
                const speedInput = document.getElementById('fan-speed-input');
                const onBtn = document.getElementById('fan-on-btn');
                const offBtn = document.getElementById('fan-off-btn');

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

                onBtn.addEventListener('click', () => updateFanState(speedInput.value > 0 ? speedInput.value : 100));
                offBtn.addEventListener('click', () => updateFanState(0));
                speedSlider.addEventListener('input', () => updateFanState(speedSlider.value));
                speedInput.addEventListener('input', () => updateFanState(speedInput.value));
                
                updateFanState(0); // Initial state
            }
            function setupMagneticSensor(prefix) {
                const visual = document.getElementById(`${prefix}-visual`);
                const statusLed = document.getElementById(`${prefix}-status-led`);
                const statusText = document.getElementById(`${prefix}-status-text`);
                
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

                openBtn.addEventListener('click', () => {
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
                });

                closeBtn.addEventListener('click', () => {
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
                });
            }

             function setupSafetyRelay() {
                const resetBtn = document.getElementById('safety-relay-reset-btn');
                const bypassBtn = document.getElementById('safety-relay-bypass-btn');
                
                const relayLed = document.getElementById('safety-relay-led');
                const relayText = document.getElementById('safety-relay-text');
                const bypassLed = document.getElementById('bypass-led');
                const bypassText = document.getElementById('bypass-text');

                let isBypassActive = false;

                resetBtn.addEventListener('click', () => {
                    // Butonları devre dışı bırak
                    resetBtn.disabled = true;
                    bypassBtn.disabled = true;

                    // "Resetleniyor" durumuna ayarla
                    relayLed.classList.remove('bg-red-500', 'bg-green-500');
                    relayLed.classList.add('bg-yellow-500');
                    relayText.textContent = 'Resetleniyor...';
                    relayText.classList.remove('text-red-400', 'text-green-400');
                    relayText.classList.add('text-yellow-400');

                    // 2 saniye bekle
                    setTimeout(() => {
                        // "Aktif" durumuna ayarla
                        relayLed.classList.remove('bg-red-500', 'bg-yellow-500');
                        relayLed.classList.add('bg-green-500');
                        relayText.textContent = 'Röle Aktif';
                        relayText.classList.remove('text-red-400', 'text-yellow-400');
                        relayText.classList.add('text-green-400');

                        // Butonları tekrar aktif et
                        resetBtn.disabled = false;
                        bypassBtn.disabled = false;
                    }, 2000);
                });

                bypassBtn.addEventListener('click', () => {
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
                });
            }

            // --- ACİL DURDURMA KONTROLÜ ---
            function setupEmergencyStop() {
                const eStopContainer = document.getElementById('emergency-stop-button-container');
                const eStopButton = document.getElementById('emergency-stop-button');
                const eStopStatus = document.getElementById('emergency-stop-status');
                
                let isStopped = false;

                eStopContainer.addEventListener('click', () => {
                    isStopped = !isStopped;
                    
                    // Tüm motor güç anahtarları
                    const powerToggles = document.querySelectorAll('.motor-power-toggle');
                    
                    if (isStopped) {
                        // Sistemi durdur
                        eStopContainer.classList.add('pressed', 'emergency-active');
                        eStopButton.textContent = 'AKTİF ET';
                        eStopStatus.textContent = 'ACİL DURUM';
                        eStopStatus.classList.remove('text-green-400');
                        eStopStatus.classList.add('text-red-400');

                        // Tüm motorların gücünü kapat
                        powerToggles.forEach(toggle => {
                            if(toggle.checked) {
                                toggle.checked = false;
                                toggle.dispatchEvent(new Event('change'));
                            }
                        });
                        document.getElementById('crusher-stop-btn').click();
                        document.getElementById('breaker-stop-btn').click();

                        // Diğer tüm kontrolleri devre dışı bırak
                        document.querySelectorAll('button, input').forEach(el => {
                            if (!el.closest('#emergency-stop-container')) {
                                el.disabled = true;
                            }
                        });
                        
                    } else {
                        // Sistemi yeniden başlat
                        eStopContainer.classList.remove('pressed', 'emergency-active');
                        eStopButton.textContent = 'ACİL DURDURMA';
                        eStopStatus.textContent = 'Sistem Aktif';
                        eStopStatus.classList.remove('text-red-400');
                        eStopStatus.classList.add('text-green-400');

                        // Tüm motorların gücünü aç (varsayılan olarak)
                        powerToggles.forEach(toggle => {
                             if(!toggle.checked) {
                                toggle.checked = true;
                                toggle.dispatchEvent(new Event('change'));
                            }
                        });

                        // Diğer tüm kontrolleri aktif et
                         document.querySelectorAll('button, input').forEach(el => {
                            el.disabled = false;
                        });
                    }
                });
            }


            const topSensorControls = setupMagneticSensor('top-sensor');
            const bottomSensorControls = setupMagneticSensor('bottom-sensor');
            setupLockControl('top-lock', topSensorControls);
            setupLockControl('bottom-lock', bottomSensorControls);
            setupFanControl();
            setupSafetyRelay();
            setupEmergencyStop();
            
            // Kalibrasyon Kontrolleri
            const calibrateDiverterBtn = document.getElementById('calibrate-diverter-btn');
            const calibrateFlapBtn = document.getElementById('calibrate-flap-btn');
            const calibrateDiverterSensorBtn = document.getElementById('calibrate-diverter-sensor-btn');
            const calibrateAllBtn = document.getElementById('calibrate-all-btn');
            const calibrationStatus = document.getElementById('calibration-status');

            let isCalibrating = false;

            function showCalibrationStatus(message) {
                calibrationStatus.textContent = message;
                setTimeout(() => {
                    calibrationStatus.textContent = '';
                }, 3000);
            }

            function calibrateDiverter() {
                return new Promise(resolve => {
                    diverterVisual.style.animation = `diverter-spin-rev 1s linear`;
                    setTimeout(() => {
                        diverterVisual.style.animation = '';
                        diverterVisual.style.transform = ''; // Reset to default
                        resolve();
                    }, 1000);
                });
            }

            function calibrateFlap() {
                 return new Promise(resolve => {
                    const duration = (flapVisual.style.transform === 'rotate(90deg)') ? getFlapDuration() : 0;
                    flapVisual.style.transform = 'rotate(0deg)';
                    setTimeout(() => {
                        resolve();
                    }, duration);
                });
            }

            function calibrateDiverterSensor() {
                 return new Promise(resolve => {
                    const rays = document.getElementById('diverter-opt-rays');
                    rays.classList.add('teaching-rays');
                    setTimeout(() => {
                        rays.classList.remove('teaching-rays');
                        resolve();
                    }, 5000);
                });
            }

            calibrateDiverterBtn.addEventListener('click', async () => {
                if(isCalibrating) return;
                isCalibrating = true;
                calibrationStatus.textContent = "Yönlendirici Motor kalibre ediliyor...";
                await calibrateDiverter();
                showCalibrationStatus('Yönlendirici Motor kalibrasyonu başarılı!');
                isCalibrating = false;
            });

            calibrateFlapBtn.addEventListener('click', async () => {
                if(isCalibrating) return;
                isCalibrating = true;
                calibrationStatus.textContent = "Klape Motor kalibre ediliyor...";
                await calibrateFlap();
                showCalibrationStatus('Klape Motor kalibrasyonu başarılı!');
                isCalibrating = false;
            });
            
            calibrateDiverterSensorBtn.addEventListener('click', async () => {
                 if(isCalibrating) return;
                isCalibrating = true;
                calibrationStatus.textContent = "Yönlendirici Sensör kalibre ediliyor...";
                await calibrateDiverterSensor();
                showCalibrationStatus('Yönlendirici Sensör kalibrasyonu başarılı!');
                isCalibrating = false;
            });

            calibrateAllBtn.addEventListener('click', async () => {
                if(isCalibrating) return;
                isCalibrating = true;
                calibrationStatus.textContent = "Tüm sistem kalibre ediliyor...";
                await Promise.all([calibrateDiverter(), calibrateFlap(), calibrateDiverterSensor()]);
                showCalibrationStatus('Tüm kalibrasyonlar başarılı!');
                isCalibrating = false;
            });

            // Motor Test Kontrolleri
            const testPlasticBtn = document.getElementById('test-plastic-btn');
            const testMetalBtn = document.getElementById('test-metal-btn');
            const testGlassBtn = document.getElementById('test-glass-btn');
            const startStopScenariosBtn = document.getElementById('start-stop-scenarios-btn');
            const testStatus = document.getElementById('test-status');
            
            let isTesting = false;
            let stopLoop = true;

            const scenarioButtons = [testPlasticBtn, testMetalBtn, testGlassBtn];
            const allTestButtons = [...scenarioButtons, startStopScenariosBtn];
            
            function toggleAllControls(disable) {
                document.querySelectorAll('#motor-details-grid button, #motor-details-grid input, #sensor-details-grid button, #sensor-details-grid input, #calibration-section button, #test-section button, #safety-details-grid button').forEach(el => {
                    if (!el.closest('.power-switch') && el.id !== 'start-stop-scenarios-btn') {
                        el.disabled = disable;
                    }
                });
            }


            const delay = ms => new Promise(res => setTimeout(res, ms));

            async function runScenario(scenario) {
                if (isTesting && !stopLoop) return; 
                isTesting = true;
                
                const opt1009_output = document.getElementById('opt1009-output');
                const opt1009_blocker = document.getElementById('opt1009-blocker');
                const diverter_opt_output = document.getElementById('diverter-opt-output');
                const diverter_opt_blocker = document.getElementById('diverter-opt-blocker');
                
                const crusherFwdBtn = document.getElementById('crusher-fwd-btn');
                const crusherStopBtn = document.getElementById('crusher-stop-btn');
                const breakerFwdBtn = document.getElementById('breaker-fwd-btn');
                const breakerStopBtn = document.getElementById('breaker-stop-btn');

                testStatus.textContent = `${scenario.charAt(0).toUpperCase() + scenario.slice(1)} senaryosu başlatılıyor...`;
                await delay(1000);

                testStatus.textContent = "Ürün giriş sensöründe...";
                opt1009_output.innerText = 1;
                opt1009_blocker.classList.remove('hidden');
                await delay(1500);
                opt1009_output.innerText = '--';
                opt1009_blocker.classList.add('hidden');

                testStatus.textContent = "Ürün konveyörde ilerliyor...";
                conveyorAnimation.classList.add('conveyor-running-forward');
                await delay(3000);
                conveyorAnimation.classList.remove('conveyor-running-forward');

                testStatus.textContent = "Ürün yönlendirici sensöründe...";
                diverter_opt_output.innerText = 1;
                diverter_opt_blocker.classList.remove('hidden');
                await delay(1500);
                diverter_opt_output.innerText = '--';
                diverter_opt_blocker.classList.add('hidden');
                
                if(scenario === 'plastik' || scenario === 'metal') {
                    testStatus.textContent = "Yönlendirici 'Plastik/Metal' konumuna dönüyor...";
                    const duration = getDiverterDuration();
                    diverterVisual.style.animation = `diverter-spin-rev ${duration}s linear`;
                    await delay(duration * 1000);
                    diverterVisual.style.animation = '';
                    diverterVisual.style.transform = 'rotate(-45deg)';

                    if (scenario === 'plastik') {
                        testStatus.textContent = "Klape konumu 'Plastik' olarak ayarlanıyor...";
                        if (flapVisual.style.transform === 'rotate(90deg)') {
                            const flapDuration = getFlapDuration();
                            flapVisual.style.transform = 'rotate(0deg)';
                            await delay(flapDuration);
                        }
                    } else { // metal
                         testStatus.textContent = "Klape 'Metal' konumuna ayarlanıyor...";
                         if (flapVisual.style.transform !== 'rotate(90deg)') {
                            const flapDuration = getFlapDuration();
                            flapVisual.style.transform = 'rotate(90deg)';
                            await delay(flapDuration);
                        }
                    }

                    await delay(1000);
                    testStatus.textContent = "Ezici motor çalıştırılıyor...";
                    crusherFwdBtn.click();
                    await delay(3000); 
                    crusherStopBtn.click();
                    testStatus.textContent = "Ezme işlemi tamamlandı.";
                    await delay(1000);

                } else if (scenario === 'cam') {
                     testStatus.textContent = "Yönlendirici 'Cam' konumuna dönüyor...";
                    const duration = getDiverterDuration();
                    diverterVisual.style.animation = `diverter-spin ${duration}s linear`;
                    await delay(duration * 1000);
                    diverterVisual.style.animation = '';
                    diverterVisual.style.transform = 'rotate(45deg)';

                    await delay(1000);
                    testStatus.textContent = "Kırıcı motor çalıştırılıyor...";
                    breakerFwdBtn.click();
                    await delay(3000);
                    breakerStopBtn.click();
                    testStatus.textContent = "Kırma işlemi tamamlandı.";
                    await delay(1000);
                }

                await delay(1000);
                testStatus.textContent = `${scenario.charAt(0).toUpperCase() + scenario.slice(1)} senaryosu tamamlandı!`;
                
                await delay(1500);
                testStatus.textContent = '';
                diverterVisual.style.transform = '';
                isTesting = false;
            }

            async function runSingleScenario(scenario) {
                allTestButtons.forEach(btn => btn.disabled = true);
                toggleAllControls(true);
                await runScenario(scenario);
                toggleAllControls(false);
                allTestButtons.forEach(btn => btn.disabled = false);
            }

            testPlasticBtn.addEventListener('click', () => runSingleScenario('plastik'));
            testMetalBtn.addEventListener('click', () => runSingleScenario('metal'));
            testGlassBtn.addEventListener('click', () => runSingleScenario('cam'));

            async function scenarioLoop() {
                while (!stopLoop) {
                    const scenarios = ['plastik', 'metal', 'cam'];
                    const randomScenario = scenarios[Math.floor(Math.random() * scenarios.length)];
                    await runScenario(randomScenario);
                    if (stopLoop) break;
                    await delay(2000);
                }
                
                startStopScenariosBtn.textContent = 'Senaryoları Başlat';
                startStopScenariosBtn.classList.remove('bg-red-600', 'hover:bg-red-700');
                startStopScenariosBtn.classList.add('bg-orange-500', 'hover:bg-orange-600');
                allTestButtons.forEach(btn => btn.disabled = false);
                toggleAllControls(false);
                isTesting = false; // Ensure testing flag is reset
            }

            startStopScenariosBtn.addEventListener('click', () => {
                if (stopLoop) {
                    stopLoop = false;
                    isTesting = false; // Reset just in case
                    startStopScenariosBtn.textContent = 'Senaryoları Durdur';
                    startStopScenariosBtn.classList.remove('bg-orange-500', 'hover:bg-orange-600');
                    startStopScenariosBtn.classList.add('bg-red-600', 'hover:bg-red-700');
                    scenarioButtons.forEach(btn => btn.disabled = true);
                    toggleAllControls(true);
                    scenarioLoop();
                } else {
                    stopLoop = true;
                    startStopScenariosBtn.textContent = 'Durduruluyor...';
                    startStopScenariosBtn.disabled = true;
                }
            });
           
        });
    </script>

</body>
</html>








