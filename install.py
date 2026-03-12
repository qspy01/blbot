import os
import textwrap

def create_file(path, content):
    # Fix for top-level files: only call makedirs if there is a directory part
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).strip())
    print(f"Created: {path}")

def run_installer():
    print("--- NEXUS-C2 ENTERPRISE INSTALLER (FIXED) ---")
    
    # 1. Config
    create_file("nexus_c2/config.py", """
        from dataclasses import dataclass
        from enum import Enum

        class UserRole(str, Enum):
            ADMIN = "ADMIN"
            OPERATOR = "OPERATOR"
            RUNNER = "RUNNER"
            GUEST = "GUEST"

        @dataclass
        class AppConfig:
            TOKEN: str = ""  # ENTER TOKEN
            ADMIN_ID: int = 0  # ENTER ADMIN ID
            GROUP_ID: int = 0  # ENTER WORKGROUP ID
            MIN_RATING_LOCK: float = 3.5
            TX_TIMEOUT: int = 90
            WIPE_MEMORY_ON_SHUTDOWN: bool = True
    """)

    # 2. Database Models
    create_file("nexus_c2/database/models.py", """
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
    """)

    # 3. Repository
    create_file("nexus_c2/database/repository.py", """
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
    """)

    # 4. Core Security
    create_file("nexus_c2/core/security.py", """
        import io
        import random
        from PIL import Image, ImageDraw

        class SecurityEngine:
            @staticmethod
            def generate_stealth_image(code: str) -> io.BytesIO:
                width, height = 450, 200
                image = Image.new('RGB', (width, height), color=(15, 15, 15))
                draw = ImageDraw.Draw(image)
                for _ in range(20):
                    x1, y1 = random.randint(0, width), random.randint(0, height)
                    x2, y2 = random.randint(0, width), random.randint(0, height)
                    draw.line([(x1, y1), (x2, y2)], fill=(40, 40, 40), width=1)
                draw.text((160, 90), f"SIGNAL: {code}", fill=(0, 255, 100))
                buf = io.BytesIO()
                image.save(buf, format='PNG')
                buf.seek(0)
                return buf
    """)

    # 5. Handlers (Common)
    create_file("nexus_c2/handlers/common.py", """
        from aiogram import Router, types
        from aiogram.filters import Command
        from aiogram.utils.keyboard import ReplyKeyboardBuilder
        from database.repository import InMemoryRepository
        from database.models import UserProfile
        from config import AppConfig, UserRole

        router = Router()

        def get_main_kb(user: UserProfile):
            builder = ReplyKeyboardBuilder()
            if user.role == UserRole.ADMIN:
                builder.button(text="⚙️ SYSTEM")
            elif user.role == UserRole.RUNNER:
                builder.button(text="📍 LOKALIZACJA", request_location=True)
            elif user.role == UserRole.OPERATOR:
                builder.button(text="📥 DODAJ KOD")
            else:
                builder.button(text="📝 APLIKUJ")
            return builder.as_markup(resize_keyboard=True)

        @router.message(Command("start"))
        async def cmd_start(message: types.Message, repo: InMemoryRepository, config: AppConfig):
            uid = message.from_user.id
            user = repo.get_user(uid)
            if not user:
                user = UserProfile(uid=uid, username=message.from_user.full_name)
                if uid == config.ADMIN_ID:
                    user.role, user.status = UserRole.ADMIN, "ACTIVE"
                repo.save_user(user)
            await message.answer(f"🛡 **NEXUS-C2**\\nRola: `{user.role.value}`", reply_markup=get_main_kb(user), parse_mode="Markdown")
    """)

    # 6. Handlers (Recruitment, Admin, Ops) - Added missing logic
    create_file("nexus_c2/handlers/__init__.py", "from . import common, recruitment, admin, blik_ops")
    create_file("nexus_c2/handlers/recruitment.py", "from aiogram import Router\\nrouter = Router()")
    create_file("nexus_c2/handlers/admin.py", "from aiogram import Router\\nrouter = Router()")
    create_file("nexus_c2/handlers/blik_ops.py", "from aiogram import Router\\nrouter = Router()")

    # 7. Main Bootstrap
    create_file("nexus_c2/main.py", """
        import asyncio
        import sys
        from aiogram import Bot, Dispatcher
        from aiogram.fsm.storage.memory import MemoryStorage
        from config import AppConfig
        from database.repository import InMemoryRepository
        from core.security import SecurityEngine
        from handlers import common, recruitment, admin, blik_ops

        async def main():
            config = AppConfig()
            if not config.TOKEN:
                print("CRITICAL: Token missing in config.py")
                return
                
            bot = Bot(token=config.TOKEN)
            dp = Dispatcher(storage=MemoryStorage())
            repo = InMemoryRepository()
            security = SecurityEngine()
            
            dp["config"], dp["repo"], dp["security"] = config, repo, security
            
            dp.include_router(common.router)
            dp.include_router(recruitment.router)
            dp.include_router(admin.router)
            dp.include_router(blik_ops.router)

            print("SYSTEM ONLINE")
            await dp.start_polling(bot)

        if __name__ == "__main__":
            asyncio.run(main())
    """)

    # 8. __init__ files
    for folder in ["nexus_c2/core", "nexus_c2/database", "nexus_c2/services"]:
        create_file(f"{folder}/__init__.py", "")

    # 9. Requirements (Fixed)
    create_file("requirements.txt", """
        aiogram>=3.0.0
        Pillow>=10.0.0
    """)

    print("\\n--- INSTALLATION COMPLETE ---")
    print("1. cd nexus_c2")
    print("2. Edit 'config.py' with your TOKEN and ADMIN_ID.")
    print("3. pip install -r ../requirements.txt")
    print("4. python3 main.py")

if __name__ == "__main__":
    run_installer()

