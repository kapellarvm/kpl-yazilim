"""
RVM Sistemi Logger Konfigürasyonu
Türkçe karakter desteği ile log kayıt sistemi
"""

import logging
import sys
from datetime import datetime
import os
from typing import Optional
import traceback
import threading


class RvmLogger:
    """RVM Sistemi için özel logger sınıfı"""
    
    def __init__(self, name: str = "rvm_sistemi"):
        self.name = name
        self.logger = None
        self._setup_logger()
    
    def _setup_logger(self):
        """Logger'ı konfigüre eder"""
        # Logger oluştur
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)
        
        # Eğer zaten handler'lar varsa temizle (duplicate'leri önlemek için)
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Log klasörünü oluştur
        log_dir = "/home/sshuser/projects/kpl-yazilim/logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Dosya handler'ı (tüm loglar)
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"rvm_sistemi_{datetime.now().strftime('%Y%m%d')}.log"),
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler'ı (terminal çıktısı)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Formatter'lar
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Handler'lara formatter'ları ata
        file_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(simple_formatter)
        
        # Handler'ları logger'a ekle
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str):
        """Debug seviyesinde log"""
        self.logger.debug(message)
        print(f"🔍 [DEBUG] {message}")
    
    def info(self, message: str):
        """Info seviyesinde log"""
        self.logger.info(message)
        print(f"ℹ️  [INFO] {message}")
    
    def warning(self, message: str):
        """Warning seviyesinde log"""
        self.logger.warning(message)
        print(f"⚠️  [WARNING] {message}")
    
    def error(self, message: str):
        """Error seviyesinde log"""
        self.logger.error(message)
        print(f"❌ [ERROR] {message}")
    
    def critical(self, message: str):
        """Critical seviyesinde log"""
        self.logger.critical(message)
        print(f"🚨 [CRITICAL] {message}")
    
    def success(self, message: str):
        """Başarı mesajları için özel log"""
        self.logger.info(f"SUCCESS: {message}")
        print(f"✅ [SUCCESS] {message}")
    
    def system(self, message: str):
        """Sistem mesajları için özel log"""
        self.logger.info(f"SYSTEM: {message}")
        print(f"🔄 [SYSTEM] {message}")
    
    def dimdb(self, message: str):
        """DİM-DB mesajları için özel log"""
        self.logger.info(f"DIMDB: {message}")
        print(f"📡 [DİM-DB] {message}")
    
    def motor(self, message: str):
        """Motor mesajları için özel log"""
        self.logger.info(f"MOTOR: {message}")
        print(f"🔧 [MOTOR] {message}")
    
    def sensor(self, message: str):
        """Sensör mesajları için özel log"""
        self.logger.info(f"SENSOR: {message}")
        print(f"📊 [SENSOR] {message}")
    
    def oturum(self, message: str):
        """Oturum mesajları için özel log"""
        self.logger.info(f"OTURUM: {message}")
        print(f"👤 [OTURUM] {message}")
    
    def exception(self, message: str, exc_info=None):
        """Exception logları için özel log"""
        if exc_info is None:
            exc_info = sys.exc_info()
        self.logger.error(f"EXCEPTION: {message}", exc_info=exc_info)
        print(f"💥 [EXCEPTION] {message}")
        if exc_info[0] is not None:
            print(f"💥 [EXCEPTION] Traceback: {traceback.format_exc()}")
    
    def thread_error(self, message: str, thread_name: str = None):
        """Thread hataları için özel log"""
        thread_info = f" (Thread: {thread_name or threading.current_thread().name})"
        self.logger.error(f"THREAD_ERROR: {message}{thread_info}")
        print(f"🧵 [THREAD_ERROR] {message}{thread_info}")
    
    def unhandled_exception(self, exc_type, exc_value, exc_traceback):
        """Unhandled exception'ları yakalar"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        self.logger.critical(f"UNHANDLED_EXCEPTION: {exc_type.__name__}: {exc_value}", 
                           exc_info=(exc_type, exc_value, exc_traceback))
        print(f"🚨 [UNHANDLED_EXCEPTION] {exc_type.__name__}: {exc_value}")
        print(f"🚨 [UNHANDLED_EXCEPTION] Traceback: {traceback.format_exc()}")


# Global logger instance
rvm_logger = RvmLogger("rvm_sistemi")

# Kolay erişim için fonksiyonlar
def log_debug(message: str):
    rvm_logger.debug(message)

def log_info(message: str):
    rvm_logger.info(message)

def log_warning(message: str):
    rvm_logger.warning(message)

def log_error(message: str):
    rvm_logger.error(message)

def log_critical(message: str):
    rvm_logger.critical(message)

def log_success(message: str):
    rvm_logger.success(message)

def log_system(message: str):
    rvm_logger.system(message)

def log_dimdb(message: str):
    rvm_logger.dimdb(message)

def log_motor(message: str):
    rvm_logger.motor(message)

def log_sensor(message: str):
    rvm_logger.sensor(message)

def log_oturum(message: str):
    rvm_logger.oturum(message)

def log_exception(message: str, exc_info=None):
    rvm_logger.exception(message, exc_info)

def log_thread_error(message: str, thread_name: str = None):
    rvm_logger.thread_error(message, thread_name)

def setup_exception_handler():
    """Unhandled exception'ları yakalamak için handler kurar"""
    sys.excepthook = rvm_logger.unhandled_exception
