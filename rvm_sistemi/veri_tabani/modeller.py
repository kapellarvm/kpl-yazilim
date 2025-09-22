# tabloların nasıl görüneceğini belirler burası

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base

# Tüm modellerimizin miras alacağı temel sınıf
Base = declarative_base()

class IslemKaydi(Base):
    __tablename__ = 'islemler'  # Tablonun veritabanındaki adı

    id = Column(Integer, primary_key=True, index=True)
    sessionId = Column(String, unique=True, nullable=False)
    userId = Column(String, nullable=False)
    baslangic_zamani = Column(DateTime, default=func.now())
    bitis_zamani = Column(DateTime)
    toplam_ambalaj = Column(Integer, default=0)
    durum = Column(String, default="basladi") # basladi, tamamlandi, hata

    def __repr__(self):
        return f"<IslemKaydi(sessionId='{self.sessionId}', user='{self.userId}')>"