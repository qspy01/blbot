from aiogram import Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.repository import InMemoryRepository
from config import AppConfig, UserRole, SystemSettings
from handlers.common import get_main_kb

router = Router()

class RecruitmentStates(StatesGroup):
    role = State()
    city = State()
    exp = State()

@router.message(lambda m: m.text == "📝 APLIKUJ")
async def start_recruitment(message: types.Message, state: FSMContext, settings: SystemSettings):
    if not settings.recruitment_open:
        return await message.answer("❌ Rekrutacja jest obecnie zamknięta.")
        
    kb = InlineKeyboardBuilder()
    kb.button(text="🏃 RUNNER (ATM)", callback_data="apply_RUNNER")
    kb.button(text="📡 OPERATOR (KODY)", callback_data="apply_OPERATOR")
    
    await message.answer("Wybierz ścieżkę kariery:", reply_markup=kb.as_markup())
    await state.set_state(RecruitmentStates.role)

@router.callback_query(RecruitmentStates.role)
async def process_role(call: types.CallbackQuery, state: FSMContext):
    role = call.data.split("_")[1]
    await state.update_data(applied_role=role)
    await call.message.edit_text(f"Wybrano: `{role}`. W jakim mieście operujesz?")
    await state.set_state(RecruitmentStates.city)

@router.message(RecruitmentStates.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Podaj krótkie BIO/Doświadczenie:")
    await state.set_state(RecruitmentStates.exp)

@router.message(RecruitmentStates.exp)
async def process_exp(message: types.Message, state: FSMContext, repo: InMemoryRepository, config: AppConfig, bot: Bot):
    data = await state.get_data()
    uid = message.from_user.id
    
    user = repo.get_user(uid)
    if user:
        user.city = data['city']
        repo.save_user(user)

    adm_kb = InlineKeyboardBuilder()
    adm_kb.button(text="✅ ZAAKCEPTUJ", callback_data=f"hr_acc_{uid}_{data['applied_role']}")
    adm_kb.button(text="❌ ODRZUĆ", callback_data=f"hr_rej_{uid}")
    
    try:
        await bot.send_message(
            config.ADMIN_ID, 
            f"📩 **NOWE PODANIE**\nID: `{uid}`\nRola: `{data['applied_role']}`\nMiasto: `{data['city']}`\nEXP: `{message.text}`",
            reply_markup=adm_kb.as_markup(),
            parse_mode="Markdown"
        )
    except Exception:
        pass
    
    await message.answer("✅ Twoja aplikacja została przekazana do weryfikacji.")
    await state.clear()

@router.callback_query(lambda c: c.data.startswith("hr_acc_"))
async def accept_user(callback: types.CallbackQuery, repo: InMemoryRepository, bot: Bot):
    parts = callback.data.split("_")
    target_uid = int(parts[2])
    role = parts[3]
    
    user = repo.get_user(target_uid)
    if user:
        user.role = UserRole(role)
        user.status = "ACTIVE"
        repo.save_user(user)
        try:
            await bot.send_message(
                target_uid, 
                f"✅ Twoja aplikacja została zaakceptowana! Jesteś teraz: {role}", 
                reply_markup=get_main_kb(user)
            )
        except Exception:
            pass
        await callback.message.edit_text(f"{callback.message.text}\n\n**[ZAAKCEPTOWANO]**", parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("hr_rej_"))
async def reject_user(callback: types.CallbackQuery, repo: InMemoryRepository, bot: Bot):
    target_uid = int(callback.data.split("_")[2])
    user = repo.get_user(target_uid)
    if user:
        user.status = "REJECTED"
        repo.save_user(user)
        try:
            await bot.send_message(target_uid, "❌ Twoja aplikacja została odrzucona.")
        except Exception:
            pass
        await callback.message.edit_text(f"{callback.message.text}\n\n**[ODRZUCONO]**", parse_mode="Markdown")
    await callback.answer()

