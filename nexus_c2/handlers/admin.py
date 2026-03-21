from aiogram import Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.repository import InMemoryRepository
from config import AppConfig, SystemSettings

router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()

@router.message(lambda m: m.text == "⚙️ SYSTEM")
async def system_panel(message: types.Message, config: AppConfig, settings: SystemSettings):
    if message.from_user.id != config.ADMIN_ID: return
    
    kb = InlineKeyboardBuilder()
    status_maint = "🔴 LOCKDOWN: ON" if settings.maintenance_mode else "🟢 LOCKDOWN: OFF"
    status_recr = "🟢 REKRUTACJA: ON" if settings.recruitment_open else "🔴 REKRUTACJA: OFF"
    status_gps = "🟢 GPS WYMAGANY" if settings.gps_required else "🔴 GPS IGNOROWANY"
    status_ocr = "🟢 ANTI-OCR: ON" if settings.anti_ocr_active else "🔴 ANTI-OCR: OFF"
    status_del = "🟢 AUTO-DELETE: ON" if settings.auto_delete_tx else "🔴 AUTO-DELETE: OFF"

    kb.button(text=status_maint, callback_data="toggle_maint")
    kb.button(text=status_recr, callback_data="toggle_recr")
    kb.button(text=status_gps, callback_data="toggle_gps")
    kb.button(text=status_ocr, callback_data="toggle_ocr")
    kb.button(text=status_del, callback_data="toggle_del")
    kb.button(text="📢 NOWE OGŁOSZENIE", callback_data="adm_broadcast")
    
    kb.adjust(1)
    await message.answer("🛠 **PANEL ADMINISTRATORA**\nZarządzaj ustawieniami:", reply_markup=kb.as_markup())

@router.callback_query(lambda c: c.data.startswith("toggle_"))
async def toggle_settings(callback: types.CallbackQuery, settings: SystemSettings, config: AppConfig):
    if callback.from_user.id != config.ADMIN_ID: return
    
    action = callback.data.split("_")[1]
    if action == "maint": settings.maintenance_mode = not settings.maintenance_mode
    elif action == "recr": settings.recruitment_open = not settings.recruitment_open
    elif action == "gps": settings.gps_required = not settings.gps_required
    elif action == "ocr": settings.anti_ocr_active = not settings.anti_ocr_active
    elif action == "del": settings.auto_delete_tx = not settings.auto_delete_tx

    kb = InlineKeyboardBuilder()
    status_maint = "🔴 LOCKDOWN: ON" if settings.maintenance_mode else "🟢 LOCKDOWN: OFF"
    status_recr = "🟢 REKRUTACJA: ON" if settings.recruitment_open else "🔴 REKRUTACJA: OFF"
    status_gps = "🟢 GPS WYMAGANY" if settings.gps_required else "🔴 GPS IGNOROWANY"
    status_ocr = "🟢 ANTI-OCR: ON" if settings.anti_ocr_active else "🔴 ANTI-OCR: OFF"
    status_del = "🟢 AUTO-DELETE: ON" if settings.auto_delete_tx else "🔴 AUTO-DELETE: OFF"

    kb.button(text=status_maint, callback_data="toggle_maint")
    kb.button(text=status_recr, callback_data="toggle_recr")
    kb.button(text=status_gps, callback_data="toggle_gps")
    kb.button(text=status_ocr, callback_data="toggle_ocr")
    kb.button(text=status_del, callback_data="toggle_del")
    kb.button(text="📢 NOWE OGŁOSZENIE", callback_data="adm_broadcast")
    kb.adjust(1)
    
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
    await callback.answer("Zaktualizowano ustawienia.")

@router.callback_query(lambda c: c.data == "adm_broadcast")
async def start_broadcast(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Wpisz treść wiadomości do wszystkich użytkowników:")
    await state.set_state(AdminStates.waiting_for_broadcast)
    await call.answer()

@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext, repo: InMemoryRepository, bot: Bot):
    users = list(repo._users.keys())
    count = 0
    for uid in users:
        try:
            await bot.send_message(uid, f"📢 **OGŁOSZENIE CENTRALNE**\n\n{message.text}")
            count += 1
        except Exception:
            continue
    await message.answer(f"✅ Wysłano do {count} node-ów.")
    await state.clear()

