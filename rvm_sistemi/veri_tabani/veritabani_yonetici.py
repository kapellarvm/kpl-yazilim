

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Bir önceki adımdaki gibi 'relative import' kullanıyoruz
from ..ayarlar import genel_ayarlar
from .modeller import Base 

# SQLite veritabanı motorunu oluşturuyoruz
engine = create_engine(
    f"sqlite:///{genel_ayarlar.VERITABANI_YOLU}",
    connect_args={"check_same_thread": False} 
)

# Veritabanı ile konuşmak için oturum (session) yapılandırması
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Hatanın çözümü olan fonksiyon:
def init_db():
    """
    Modeller dosyasında tanımlanan tüm tabloları veritabanında oluşturur.
    Eğer tablolar zaten varsa, tekrar oluşturmaz.
    """
    Base.metadata.create_all(bind=engine)