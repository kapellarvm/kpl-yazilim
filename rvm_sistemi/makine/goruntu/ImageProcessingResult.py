from dataclasses import dataclass
from typing import Optional
from app.shared.enums import PackageType
@dataclass
class ImageProcessingResult:
    type: Optional[PackageType] = None
    confidence: Optional[float] = None
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    message: Optional[str] = None
