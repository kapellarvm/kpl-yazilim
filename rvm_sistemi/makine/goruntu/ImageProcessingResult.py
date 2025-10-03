from dataclasses import dataclass
from typing import Optional
from enum import Enum, IntEnum


class PackageType(IntEnum):
    """Package type enumeration"""
    UNKNOWN = 0
    PET = 1
    GLASS = 2
    ALUMINUM = 3
    EMPTY = 4

    @classmethod
    def get_message(cls, code: int) -> str:
        messages = {
            cls.PET: "PET",
            cls.GLASS: "Cam",
            cls.ALUMINUM: "Alüminyum"
        }
        return messages.get(cls(code), "Bilinmeyen malzeme")

class BinType(str, Enum):
    """Bin türleri"""
    PET = "1"     # PET
    GLASS = "2"         # Cam
    ALUMINUM = "3"         # Alüminyum

@dataclass

class ImageProcessingResult:
    type: Optional[PackageType] = None
    confidence: Optional[float] = None
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    message: Optional[str] = None
