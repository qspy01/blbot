import asyncio
import secrets
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.repository import InMemoryRepository
from core.security import SecurityEngine
from config import AppConfig, UserRole, SystemSettings

router = Router()

@router.message(F.location)
async def handle_gps_verification(message: types.Message, repo: InMemoryRepository, settings: SystemSettings):
    # Weryfikacja flagi z panelu admina
    if not settings.gps_required:
        return await message.answer("ℹ️ Moduł GPS jest obecnie wyłączony przez administrację. Weryfikacja pominięta.")
        
    uid = message.from_user.id
    user = repo.get_user(uid)
    if user:
        user.is_geo_verified = True
        repo.save_user(user)
        await message.answer("📍 **POZYCJA ZWERYFIKOWANA**\nTwój status: `W GOTOWOŚCI`. Możesz odbierać sygnały.")

@router.message(F.text.regexp(r'^\d{6}$'))
async def incoming_blik_signal(message: types.Message, repo: InMemoryRepository, config: AppConfig, settings: SystemSettings):
    # Weryfikacja flagi Lockdown
    if settings.maintenance_mode:
        return await message.answer("⚠️ System jest w trybie Lockdown. Operacja zablokowana.")

    uid = message.from_user.id
    user = repo.get_user(uid)
    
    if not user or user.role not in [UserRole.OPERATOR, UserRole.ADMIN]:
        return

    tx_id = secrets.token_hex(3).upper()
    repo.add_active_tx(tx_id, {"code": message.text, "op_id": uid})
    
    # Weryfikacja flagi Auto-Delete dla głównego czatu
    if settings.auto_delete_tx:
        await message.delete()

    kb = InlineKeyboardBuilder()
    gps_req_text = " (GPS REQ)" if settings.gps_required else ""
    kb.button(text=f"⚡️ PRZEJMIJ{gps_req_text}", callback_data=f"claim_{tx_id}")
    
    await message.bot.send_message(
        config.GROUP_ID, 
        f"🚨 **NOWY SYGNAŁ: {tx_id}**\nStatus: Oczekiwanie na runnera...",
        reply_markup=kb.as_markup()
    )

@router.callback_query(F.data.startswith("claim_"))
async def claim_signal(call: types.CallbackQuery, repo: InMemoryRepository, security: SecurityEngine, config: AppConfig, settings: SystemSettings):
    if settings.maintenance_mode:
        return await call.answer("⚠️ System w trybie Lockdown!", show_alert=True)

    tx_id = call.data.split("_")[1]
    uid = call.from_user.id
    user = repo.get_user(uid)

    if not user or user.shadowbanned:
        return await call.answer("Błąd: Brak uprawnień do tego sygnału!", show_alert=True)
        
    if settings.gps_required and not user.is_geo_verified:
        return await call.answer("Błąd: Wymagana aktywna weryfikacja GPS!", show_alert=True)

    tx = repo.get_tx(tx_id)
    if not tx:
        return await call.answer("Ten sygnał został już przejęty lub wygasł.")

    code = tx["code"]
    repo.remove_tx(tx_id)
    
    caption = f"🏁 **TX-ID: {tx_id}**\nMasz {config.TX_TIMEOUT}s na realizację wypłaty."
    
    # Weryfikacja flagi Anti-OCR
    if settings.anti_ocr_active:
        img_buf = security.generate_stealth_image(code)
        msg = await call.bot.send_photo(
            uid, 
            types.BufferedInputFile(img_buf.read(), filename="signal.png"),
            caption=caption
        )
    else:
        msg = await call.bot.send_message(uid, f"{caption}\n\n**KOD:** `{code}`")
    
    await call.answer("Sygnał odebrany. Sprawdź czat prywatny.")

    # Weryfikacja flagi Auto-Delete z czatu prywatnego runnera
    if settings.auto_delete_tx:
        await asyncio.sleep(config.TX_TIMEOUT)
        try:
            await call.bot.delete_message(uid, msg.message_id)
        except:
            pass


