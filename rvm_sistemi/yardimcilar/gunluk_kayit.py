import logging
from ..ayarlar import genel_ayarlar

def logger_kur():
    """Proje genelinde kullanılacak logger'ı yapılandırır."""
    logging.basicConfig(
        level=genel_ayarlar.LOG_SEVIYESI,
        format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
        handlers=[
            logging.FileHandler(genel_ayarlar.LOG_DOSYASI),
            logging.StreamHandler() # Konsola da yazması için
        ]
    )
    return logging.getLogger()

# Logger'ı bir kerelik kurup diğer dosyalardan import edebilmek için
logger = logger_kur()