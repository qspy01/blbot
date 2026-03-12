from typing import Dict, Optional, List
from .models import UserProfile
from config import UserRole

class InMemoryRepository:
    def __init__(self):
        self._users: Dict[int, UserProfile] = {}
        self._active_tx: Dict[str, dict] = {}

    def get_user(self, uid: int) -> Optional[UserProfile]:
        return self._users.get(uid)

    def save_user(self, user: UserProfile):
        self._users[user.uid] = user

    def add_active_tx(self, tx_id: str, data: dict):
        self._active_tx[tx_id] = data

    def get_tx(self, tx_id: str) -> Optional[dict]:
        return self._active_tx.get(tx_id)

    def remove_tx(self, tx_id: str):
        if tx_id in self._active_tx:
            del self._active_tx[tx_id]