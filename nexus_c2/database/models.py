from dataclasses import dataclass, field
from datetime import datetime
from config import UserRole

@dataclass
class UserProfile:
    uid: int
    username: str
    role: UserRole = UserRole.GUEST
    status: str = "PENDING"
    balance: float = 0.0
    rating_sum: float = 5.0
    rating_count: int = 1
    city: str = "Unknown"
    is_geo_verified: bool = False
    shadowbanned: bool = False
    joined_at: datetime = field(default_factory=datetime.now)

    @property
    def avg_rating(self) -> float:
        return round(self.rating_sum / self.rating_count, 2)