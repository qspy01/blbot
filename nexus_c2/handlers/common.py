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
        builder.button(text="📊 TABLICA LIDERÓW")
    elif user.role == UserRole.RUNNER:
        builder.button(text="🟢 STATUS: W PRACY")
        builder.button(text="📊 MÓJ UROBEK")
        builder.button(text="🔥 PANIKA")
    elif user.role == UserRole.OPERATOR:
        builder.button(text="📥 DODAJ KOD")
    else:
        # TRYB PRZYKRYWKI - Klawiatura dla GUEST
        builder.button(text="📈 Kurs Bitcoin (BTC)")
        builder.button(text="📉 Kurs Ethereum (ETH)")
    return builder.as_markup(resize_keyboard=True)

@router.message(Command("start"))
async def cmd_start(message: types.Message, repo: InMemoryRepository, config: AppConfig):
    uid = message.from_user.id
    user = repo.get_user(uid)
    
    # Automatyczne utworzenie profilu
    if not user:
        user = UserProfile(uid=uid, username=message.from_user.full_name)
        
    # Nadanie uprawnień Admina pierwszemu użytkownikowi
    if uid == config.ADMIN_ID:
        user.role = UserRole.ADMIN
        user.status = "ACTIVE"
        
    repo.save_user(user)

    if user.role in [UserRole.ADMIN, UserRole.OPERATOR, UserRole.RUNNER]:
        if getattr(user, 'shadowbanned', False):
            return # Zbanowany użytkownik nie dostaje odpowiedzi
        await message.answer(f"🛡 **NEXUS-C2**\nZalogowano pomyślnie.\nRola: `{user.role.value}`", reply_markup=get_main_kb(user), parse_mode="Markdown")
    else:
        # TRYB PRZYKRYWKI - Odpowiedź dla niezaufanych
        await message.answer("👋 Witaj w CryptoTracker Bot!\nWybierz kryptowalutę z menu poniżej, aby sprawdzić aktualny kurs.", reply_markup=get_main_kb(user))

@router.message(lambda m: m.text in ["📈 Kurs Bitcoin (BTC)", "📉 Kurs Ethereum (ETH)"])
async def decoy_crypto_response(message: types.Message, repo: InMemoryRepository):
    user = repo.get_user(message.from_user.id)
    if user and user.role != UserRole.GUEST:
        return
        
    import random
    if "BTC" in message.text:
        price = f"${random.randint(62000, 64000)}.00"
        await message.answer(f"🪙 **Bitcoin (BTC)**\nAktualny kurs: {price}\nZmiana 24h: +1.2%")
    else:
        price = f"${random.randint(3400, 3600)}.00"
        await message.answer(f"💠 **Ethereum (ETH)**\nAktualny kurs: {price}\nZmiana 24h: -0.4%")

# Tajna komenda wyzwalająca rekrutację ukrytą pod przykrywką
@router.message(Command("apply_job_777"))
async def secret_apply(message: types.Message, repo: InMemoryRepository):
    user = repo.get_user(message.from_user.id)
    if user and user.role == UserRole.GUEST:
        await message.answer("Uruchamiam bezpieczny kanał rekrutacyjny...\nWpisz '📝 APLIKUJ', aby rozpocząć proces.")


