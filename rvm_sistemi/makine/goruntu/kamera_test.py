#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
from ctypes import *
from MvCameraControl_class import *

def test_kamera():
    print("🔍 Hikrobot Kamera Test Başlatılıyor...")
    
    # SDK başlat
    ret = MvCamera.MV_CC_Initialize()
    print(f"📋 SDK Initialize: 0x{ret:x}")
    
    # Transport layer kontrol
    tl_support = MvCamera.MV_CC_EnumerateTls()
    print(f"📋 Desteklenen TL: 0x{tl_support:x}")
    
    # Cihaz listesi
    device_list = MV_CC_DEVICE_INFO_LIST()
    
    # Sadece USB cihazları arat
    print("🔍 USB cihazları aranıyor...")
    ret = MvCamera.MV_CC_EnumDevices(MV_USB_DEVICE, device_list)
    print(f"📋 USB Enum sonucu: 0x{ret:x}, Bulunan: {device_list.nDeviceNum}")
    
    # GigE cihazları arat
    print("🔍 GigE cihazları aranıyor...")
    ret = MvCamera.MV_CC_EnumDevices(MV_GIGE_DEVICE, device_list)
    print(f"📋 GigE Enum sonucu: 0x{ret:x}, Bulunan: {device_list.nDeviceNum}")
    
    # Tüm cihazları arat
    print("🔍 Tüm cihazlar aranıyor...")
    tlayerType = (MV_GIGE_DEVICE | MV_USB_DEVICE)
    ret = MvCamera.MV_CC_EnumDevices(tlayerType, device_list)
    print(f"📋 Tüm Enum sonucu: 0x{ret:x}, Bulunan: {device_list.nDeviceNum}")
    
    if device_list.nDeviceNum > 0:
        print(f"✅ {device_list.nDeviceNum} adet kamera bulundu!")
        
        for i in range(device_list.nDeviceNum):
            device_info = cast(device_list.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
            print(f"📷 Kamera {i+1}:")
            print(f"   Transport Layer: 0x{device_info.nTLayerType:x}")
            
            if device_info.nTLayerType == MV_USB_DEVICE:
                usb_info = device_info.SpecialInfo.stUsb3VInfo
                print(f"   USB Vendor ID: 0x{usb_info.nVendorID:x}")
                print(f"   USB Product ID: 0x{usb_info.nProductID:x}")
                
                # String çevir
                serial = usb_info.chSerialNumber.decode('ascii', errors='ignore')
                model = usb_info.chModelName.decode('ascii', errors='ignore')
                print(f"   Model: {model}")
                print(f"   Serial: {serial}")
                
    else:
        print("❌ Hiçbir kamera bulunamadı!")
        print("💡 Kontrol listesi:")
        print("   - Kamera USB'ye takılı mı?")
        print("   - Kamera açık mı?") 
        print("   - USB kablosu çalışıyor mu?")
        print("   - Başka program kamerayı kullanıyor mu?")
    
    # SDK sonlandır
    MvCamera.MV_CC_Finalize()
    print("🏁 Test tamamlandı.")

if __name__ == "__main__":
    test_kamera()