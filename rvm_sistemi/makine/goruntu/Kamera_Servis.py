# -- coding: utf-8 --

import sys
from ctypes import *
import numpy as np
import cv2
sys.path.append("../MvImport")
from MvCameraControl_class import *

class KameraServis:
    def __init__(self):
        self.cam = None
        self.device_list = None

    def baslat(self):
        MvCamera.MV_CC_Initialize()

        self.device_list = MV_CC_DEVICE_INFO_LIST()
        tlayerType = (MV_GIGE_DEVICE | MV_USB_DEVICE | MV_GENTL_CAMERALINK_DEVICE
                      | MV_GENTL_CXP_DEVICE | MV_GENTL_XOF_DEVICE | MV_USB_DEVICE)

        ret = MvCamera.MV_CC_EnumDevices(tlayerType, self.device_list)
        if ret != 0 or self.device_list.nDeviceNum == 0:
            raise Exception(f"No devices found! ret[0x%x]" % ret)

        stDeviceList = cast(self.device_list.pDeviceInfo[0], POINTER(MV_CC_DEVICE_INFO)).contents

        self.cam = MvCamera()
        ret = self.cam.MV_CC_CreateHandle(stDeviceList)
        if ret != 0:
            raise Exception(f"Create handle failed! ret[0x%x]" % ret)

        ret = self.cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
        if ret != 0:
            raise Exception(f"Open device failed! ret[0x%x]" % ret)

        # GigE ise paket boyutu
        if stDeviceList.nTLayerType == MV_GIGE_DEVICE or stDeviceList.nTLayerType == MV_GENTL_GIGE_DEVICE:
            nPacketSize = self.cam.MV_CC_GetOptimalPacketSize()
            if int(nPacketSize) > 0:
                ret = self.cam.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)
                if ret != 0:
                    app_logger.warning(f"Warning: Set Packet Size fail! ret[0x%x]" % ret)
            else:
                app_logger.warning(f"Warning: Get Packet Size fail! ret[0x%x]" % nPacketSize)

        # Parametreler
        self.cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
        self.cam.MV_CC_SetFloatValue("ExposureTime", 1500.0)
        self.cam.MV_CC_SetFloatValue("Gain", 0.0)
        self.cam.MV_CC_SetEnumValue("PixelFormat", PixelType_Gvsp_BayerRG8)

        app_logger.info("Kamera başlatıldı ve parametreler ayarlandı.")

    def fotograf_cek(self):
        if not self.cam:
            raise Exception("Kamera başlatılmadı. Önce baslat() çağırın.")

        ret = self.cam.MV_CC_StartGrabbing()
        if ret != 0:
            raise Exception(f"Start grabbing failed! ret[0x%x]" % ret)

        stOutFrame = MV_FRAME_OUT()
        memset(byref(stOutFrame), 0, sizeof(stOutFrame))

        ret = self.cam.MV_CC_GetImageBuffer(stOutFrame, 20000)
        if stOutFrame.pBufAddr and ret == 0:
            width = stOutFrame.stFrameInfo.nWidth
            height = stOutFrame.stFrameInfo.nHeight
            frame_len = stOutFrame.stFrameInfo.nFrameLen

            buf = (c_ubyte * frame_len).from_address(addressof(stOutFrame.pBufAddr.contents))
            buf_np = np.frombuffer(buf, dtype=np.uint8)

            # BGR dönüşümü - senin şemanla
            img_bgr = self._convert_to_bgr(buf_np, stOutFrame.stFrameInfo)

            self.cam.MV_CC_FreeImageBuffer(stOutFrame)
            self.cam.MV_CC_StopGrabbing()

            return img_bgr
        else:
            self.cam.MV_CC_StopGrabbing()
            raise Exception(f"No data! ret[0x%x]" % ret)

    def _convert_to_bgr(self, buf, info):
        pixel_format = info.enPixelType

        if pixel_format == 0x01080001:  # Mono8
            img = np.frombuffer(buf, dtype=np.uint8).reshape((info.nHeight, info.nWidth))
            return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        elif pixel_format == 0x02180014:  # RGB8
            img = np.frombuffer(buf, dtype=np.uint8).reshape((info.nHeight, info.nWidth, 3))
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        elif pixel_format == 0x02180021:  # BGR8
            return np.frombuffer(buf, dtype=np.uint8).reshape((info.nHeight, info.nWidth, 3))

        elif pixel_format == 0x01080009:  # BayerRG8
            img = np.frombuffer(buf, dtype=np.uint8).reshape((info.nHeight, info.nWidth))
            return cv2.cvtColor(img, cv2.COLOR_BAYER_BG2BGR)

        elif pixel_format == 0x0108000B:  # BayerBG8
            img = np.frombuffer(buf, dtype=np.uint8).reshape((info.nHeight, info.nWidth))
            return cv2.cvtColor(img, cv2.COLOR_BAYER_BG2BGR)

        else:
            return None

    def durdur(self):
        if self.cam:
            self.cam.MV_CC_CloseDevice()
            self.cam.MV_CC_DestroyHandle()
            MvCamera.MV_CC_Finalize()
            app_logger.info("Kamera kapatıldı ve handle yok edildi.")

