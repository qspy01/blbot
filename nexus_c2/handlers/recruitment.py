from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Założenie: Posiadasz te moduły w swoim projekcie
# Jeśli ścieżki są inne, dostosuj importy poniżej
from database.repository import InMemoryRepository
from config import AppConfig, SystemSettings, UserRole
from database.models import UserProfile

router = Router()

class RecruitmentState(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_experience = State()

@router.message(F.text == "📝 APLIKUJ")
async def start_recruitment(message: types.Message, state: FSMContext, settings: SystemSettings):
    # Sprawdzenie czy rekrutacja jest otwarta w ustawieniach systemu
    if not settings.recruitment_open:
        return await message.answer("❌ Rekrutacja do NEXUS-C2 jest obecnie zamknięta.")
    
    await message.answer("🛡 **PROCES REKRUTACJI**\n\nPodaj swoje imię lub pseudonim operacyjny:")
    await state.set_state(RecruitmentState.waiting_for_name)

@router.message(RecruitmentState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Ile masz lat?")
    await state.set_state(RecruitmentState.waiting_for_age)

@router.message(RecruitmentState.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("Opisz krótko swoje doświadczenie (miasto, dostępność, sprzęt):")
    await state.set_state(RecruitmentState.waiting_for_experience)

@router.message(RecruitmentState.waiting_for_experience)
async def finalize_application(message: types.Message, state: FSMContext, config: AppConfig, bot: Bot):
    data = await state.get_data()
    uid = message.from_user.id
    
    # Przygotowanie raportu dla administracji
    app_report = (
        f"📩 **NOWE ZGŁOSZENIE DO SYSTEMU**\n\n"
        f"👤 Użytkownik: {message.from_user.full_name}\n"
        f"🆔 Telegram ID: `{uid}`\n"
        f"📛 Nick: {data['name']}\n"
        f"🎂 Wiek: {data['age']}\n"
        f"📝 Doświadczenie:\n{message.text}"
    )

    # Przyciski decyzyjne dla admina
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ AKCEPTUJ", callback_data=f"hr_acc_{uid}")
    kb.button(text="❌ ODRZUĆ", callback_data=f"hr_rej_{uid}")
    kb.adjust(1)

    # Wysyłka do admina (pobranego z configu)
    await bot.send_message(
        config.ADMIN_ID, 
        app_report, 
        reply_markup=kb.as_markup(), 
        parse_mode="Markdown"
    )
    
    await message.answer("✅ Twoje zgłoszenie zostało wysłane. Oczekuj na weryfikację przez Centralę.")
    await state.clear()

# --- OBSŁUGA DECYZJI ---

@router.callback_query(F.data.startswith("hr_acc_"))
async def accept_user(callback: types.CallbackQuery, repo: InMemoryRepository, bot: Bot):
    # Wyciąganie ID użytkownika z callback_data
    target_uid = int(callback.data.split("_")[2])
    
    # Logika nadania uprawnień w bazie danych
    user = repo.get_user(target_uid) or UserProfile(uid=target_uid, username=f"User_{target_uid}")
    user.role = UserRole.RUNNER
    user.status = "ACTIVE"
    repo.save_user(user)
    
    try:
        await bot.send_message(
            target_uid, 
            "🎉 **SYSTEM: AKTYWACJA**\n\nTwoja aplikacja została zaakceptowana. Otrzymałeś status: `RUNNER`.\nWpisz /start aby odświeżyć menu."
        )
    except Exception:
        pass # Użytkownik mógł zablokować bota

    await callback.message.edit_text(f"{callback.message.text}\n\n✅ **STATUS: ZAAKCEPTOWANY**")
    await callback.answer("Użytkownik został dodany do bazy.")

@router.callback_query(F.data.startswith("hr_rej_"))
async def reject_user(callback: types.CallbackQuery, bot: Bot):
    target_uid = int(callback.data.split("_")[2])
    
    try:
        await bot.send_message(target_uid, "❌ Twoje zgłoszenie do systemu zostało odrzucone.")
    except Exception:
        pass

    await callback.message.edit_text(f"{callback.message.text}\n\n❌ **STATUS: ODRZUCONY**")
    await callback.answer("Zgłoszenie odrzucone.")

