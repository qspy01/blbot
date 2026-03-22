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
        builder.button(text="📊 STATYSTYKI")
    elif user.role == UserRole.RUNNER:
        builder.button(text="🟢 STATUS: W PRACY")
        builder.button(text="🔥 PANIKA") # Nowy przycisk awaryjny
    elif user.role == UserRole.OPERATOR:
        builder.button(text="📥 DODAJ KOD")
    else:
        # Klawiatura dla przykrywki (Decoy Mode)
        builder.button(text="📈 Kurs Bitcoin (BTC)")
        builder.button(text="📉 Kurs Ethereum (ETH)")
    return builder.as_markup(resize_keyboard=True)

@router.message(Command("start"))
async def cmd_start(message: types.Message, repo: InMemoryRepository, config: AppConfig):
    uid = message.from_user.id
    user = repo.get_user(uid)
    
    # Automatyczne dodanie Admina
    if uid == config.ADMIN_ID and not user:
        user = UserProfile(uid=uid, username=message.from_user.full_name, role=UserRole.ADMIN, status="ACTIVE")
        repo.save_user(user)
    
    if not user:
        user = UserProfile(uid=uid, username=message.from_user.full_name)
        repo.save_user(user)

    if user.role in [UserRole.ADMIN, UserRole.OPERATOR, UserRole.RUNNER]:
        await message.answer(f"🛡 **NEXUS-C2**\nZalogowano pomyślnie.\nRola: `{user.role.value}`", reply_markup=get_main_kb(user), parse_mode="Markdown")
    else:
        # TRYB PRZYKRYWKI - Bot udaje narzędzie do kryptowalut
        await message.answer("👋 Witaj w CryptoTracker Bot!\nWybierz kryptowalutę z menu poniżej, aby sprawdzić aktualny kurs.", reply_markup=get_main_kb(user))

# Obsługa przykrywki
@router.message(lambda m: m.text in ["📈 Kurs Bitcoin (BTC)", "📉 Kurs Ethereum (ETH)"])
async def decoy_crypto_response(message: types.Message, repo: InMemoryRepository):
    user = repo.get_user(message.from_user.id)
    if user and user.role != UserRole.GUEST:
        return # Ignoruj, jeśli to ktoś z grupy
        
    import random
    if "BTC" in message.text:
        price = f"${random.randint(62000, 64000)}.00"
        await message.answer(f"🪙 **Bitcoin (BTC)**\nAktualny kurs: {price}\nZmiana 24h: +1.2%")
    else:
        price = f"${random.randint(3400, 3600)}.00"
        await message.answer(f"💠 **Ethereum (ETH)**\nAktualny kurs: {price}\nZmiana 24h: -0.4%")

# Tajna komenda do włączenia rekrutacji z poziomu Przykrywki
@router.message(Command("apply_job_777"))
async def secret_apply(message: types.Message, repo: InMemoryRepository):
    user = repo.get_user(message.from_user.id)
    if user and user.role == UserRole.GUEST:
        await message.answer("Uruchamiam bezpieczny kanał rekrutacyjny...\nWpisz komendę /start_rekrutacja (To musisz zaprogramować w module rekrutacji).")


