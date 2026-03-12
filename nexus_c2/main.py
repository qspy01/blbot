import asyncio
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import AppConfig, SystemSettings
from database.repository import InMemoryRepository
from core.security import SecurityEngine
from handlers import common, recruitment, admin, blik_ops

async def main():
    config = AppConfig()
    settings = SystemSettings()
    
    if not config.TOKEN:
        print("CRITICAL: Brak TOKENU w pliku config.py")
        return

    bot = Bot(token=config.TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    repo = InMemoryRepository()
    security = SecurityEngine()
    
    # Rejestracja middleware lub danych globalnych
    # To pozwala handlerom na dostęp do repo, config itp. przez argumenty funkcji
    dp["config"] = config
    dp["settings"] = settings
    dp["repo"] = repo
    dp["security"] = security
    dp["bot"] = bot

    # REJESTRACJA ROUTERÓW - Kolejność ma znaczenie!
    dp.include_router(admin.router)       # Admin najpierw
    dp.include_router(recruitment.router) # Rekrutacja
    dp.include_router(blik_ops.router)
    dp.include_router(common.router)

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print("--- NEXUS-C2 SYSTEM OPERACYJNY URUCHOMIONY ---")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

