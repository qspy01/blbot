from dataclasses import dataclass
from config import UserRole

@dataclass
class UserProfile:
    uid: int
    username: str
    role: UserRole = UserRole.GUEST
    status: str = "PENDING"
    city: str = ""
    is_geo_verified: bool = False
    shadowbanned: bool = False
    # Nowe pola do rozliczeń i urobku
    total_earned: float = 0.0
    total_tx: int = 0

