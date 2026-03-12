from dataclasses import dataclass
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    RUNNER = "RUNNER"
    GUEST = "GUEST"

@dataclass
class SystemSettings:
    """Dynamiczne flagi modułów zarządzane z poziomu panelu Admina"""
    maintenance_mode: bool = False
    recruitment_open: bool = True
    gps_required: bool = True
    anti_ocr_active: bool = True
    auto_delete_tx: bool = True

@dataclass
class AppConfig:
    TOKEN: str = "8297296320:AAE0XaY2YLBa-Ghf-6eOYmE-N_xUY6FU75w"  # ENTER TOKEN
    ADMIN_ID: int = 8107223648  # ENTER ADMIN ID
    GROUP_ID: int = -5166034765  # ENTER WORKGROUP ID
    MIN_RATING_LOCK: float = 3.5
    TX_TIMEOUT: int = 90
    WIPE_MEMORY_ON_SHUTDOWN: bool = True
