import asyncio
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.repository import InMemoryRepository
from config import AppConfig, UserRole, SystemSettings

router = Router()

class BlikOpStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_code = State()

# --- MODUŁ PANIKI (EMERGENCY WIPE) ---
@router.message(F.text == "🔥 PANIKA")
async def emergency_panic(message: types.Message, repo: InMemoryRepository, bot: Bot, config: AppConfig):
    uid = message.from_user.id
    user = repo.get_user(uid)
    
    if not user or user.role != UserRole.RUNNER: return
        
    user.status = "BURNED"
    user.shadowbanned = True
    repo.save_user(user)
    
    await bot.send_message(config.ADMIN_ID, f"🚨 **CRITICAL ALERT** 🚨\nRunner `{user.username}` ({uid}) wcisnął PANIKĘ!\nDostęp odcięty.")
    
    kb = types.ReplyKeyboardRemove()
    await message.answer("🧹 Pamięć wyczyszczona.", reply_markup=kb)
    for _ in range(5): await message.answer("...")
    await message.answer("Error 502: Connection Refused.")

# --- KROK 1: INICJACJA ---
@router.message(F.text == "📥 DODAJ KOD")
async def request_blik_amount(message: types.Message, repo: InMemoryRepository, state: FSMContext):
    user = repo.get_user(message.from_user.id)
    if user and user.role in [UserRole.OPERATOR, UserRole.ADMIN]:
        await message.answer("💰 Podaj **KWOTĘ** do wypłaty (np. 1500):")
        await state.set_state(BlikOpStates.waiting_for_amount)

@router.message(BlikOpStates.waiting_for_amount)
async def process_blik_amount(message: types.Message, state: FSMContext):
    await state.update_data(amount=message.text)
    await message.answer("🔢 Teraz podaj **6-cyfrowy KOD BLIK**:")
    await state.set_state(BlikOpStates.waiting_for_code)

@router.message(BlikOpStates.waiting_for_code, F.text.regexp(r'^\d{6}$'))
async def incoming_blik_signal(message: types.Message, repo: InMemoryRepository, state: FSMContext, bot: Bot, settings: SystemSettings):
    uid = message.from_user.id
    data = await state.get_data()
    amount = data.get("amount", "0")
    code = message.text
    await state.clear()
    
    if settings.maintenance_mode: return await message.answer("⚠️ Lockdown. Odrzucono.")
    
    tx_id = f"TX{message.message_id}"
    try: await message.delete()
    except: pass
    
    repo.add_active_tx(tx_id, {"code": code, "amount": amount, "op_id": uid, "status": "NEW"})
    
    kb = InlineKeyboardBuilder()
    kb.button(text="⚡️ PRZEJMIJ ZLECENIE", callback_data=f"clm_{tx_id}")
    
    powiadomiono = 0
    for u_id, u_data in repo._users.items():
        if u_data.role in [UserRole.RUNNER, UserRole.ADMIN] and u_data.status == "ACTIVE":
            try:
                await bot.send_message(u_id, f"🚨 **NOWE ZLECENIE** 🚨\nID: `{tx_id}`\nKwota: **{amount} PLN**", reply_markup=kb.as_markup(), parse_mode="Markdown")
                powiadomiono += 1
            except: continue
                
    await message.answer(f"✅ Sieć powiadomiona.\nID: `{tx_id}` | Kwota: `{amount} PLN` | Node'y: {powiadomiono}", parse_mode="Markdown")

# --- KROK 2: PRZEJĘCIE ---
@router.callback_query(lambda c: c.data.startswith("clm_"))
async def claim_signal(callback: types.CallbackQuery, repo: InMemoryRepository, bot: Bot):
    uid = callback.from_user.id
    user = repo.get_user(uid)
    tx_id = callback.data.split("_")[1]
    
    if not user or user.role not in [UserRole.RUNNER, UserRole.ADMIN]: return await callback.answer("Brak uprawnień.")
    
    tx_data = repo.get_tx(tx_id)
    if not tx_data or tx_data.get("status") != "NEW":
        return await callback.answer("❌ Zlecenie przejęte lub wygasłe.")
    
    tx_data["status"] = "CLAIMED"
    tx_data["runner_id"] = uid
    
    status_kb = InlineKeyboardBuilder()
    status_kb.button(text="⏳ PROŚBA O AKCEPTACJĘ PIN", callback_data=f"reqpin_{tx_id}")
    status_kb.button(text="❌ BŁĄD", callback_data=f"err_{tx_id}")
    status_kb.adjust(1)
    
    await bot.send_message(uid, f"🏁 **TX: {tx_id}**\n💰 Kwota: **{tx_data['amount']} PLN**\n🔢 KOD: `{tx_data['code']}`\n\nWpisz w ATM i proś o PIN!", reply_markup=status_kb.as_markup(), parse_mode="Markdown")
    await bot.send_message(tx_data["op_id"], f"🎯 Runner {callback.from_user.first_name} dobiegł. Oczekuj na PIN...")
    await callback.message.edit_text(f"{callback.message.text}\n\n**[PRZEJĘTE]**", parse_mode="Markdown")
    await callback.answer("Biegnij do bankomatu!")

# --- KROK 3: PROŚBA O PIN ---
@router.callback_query(lambda c: c.data.startswith("reqpin_"))
async def request_pin_approval(callback: types.CallbackQuery, repo: InMemoryRepository, bot: Bot):
    tx_id = callback.data.split("_")[1]
    tx_data = repo.get_tx(tx_id)
    if not tx_data: return await callback.answer("TX nie istnieje.")

    await callback.message.edit_text(f"{callback.message.text}\n\n**⏳ OCZEKIWANIE NA OPERATORA...**", reply_markup=None, parse_mode="Markdown")
    
    op_kb = InlineKeyboardBuilder()
    op_kb.button(text="✅ ZATWIERDZIŁEM", callback_data=f"ackpin_{tx_id}")
    op_kb.button(text="❌ ODRZUCONE", callback_data=f"rejpin_{tx_id}")
    op_kb.adjust(1)
    
    await bot.send_message(tx_data["op_id"], f"🚨 **AKCEPTACJA PIN WYMAGANA!** 🚨\nTX: `{tx_id}`\nRunner pod ATM. Potwierdź w banku!", reply_markup=op_kb.as_markup(), parse_mode="Markdown")

# --- KROK 4: DECYZJA OPERATORA ---
@router.callback_query(lambda c: c.data.startswith("ackpin_") or c.data.startswith("rejpin_"))
async def operator_pin_decision(callback: types.CallbackQuery, repo: InMemoryRepository, bot: Bot):
    action, tx_id = callback.data.split("_")
    tx_data = repo.get_tx(tx_id)
    if not tx_data: return await callback.answer("TX wygasła.")
    
    await callback.message.edit_reply_markup(reply_markup=None)
    
    if action == "ackpin":
        await callback.message.reply("✅ Przekazano do Runnera.")
        final_kb = InlineKeyboardBuilder()
        final_kb.button(text="💸 GOTÓWKA WYBRANA (SUKCES)", callback_data=f"done_{tx_id}")
        final_kb.button(text="❌ BŁĄD BANKOMATU", callback_data=f"err_{tx_id}")
        final_kb.adjust(1)
        await bot.send_message(tx_data["runner_id"], f"✅ **PIN ZAAKCEPTOWANY!**\nWyciągaj gotówkę!", reply_markup=final_kb.as_markup(), parse_mode="Markdown")
    else:
        await callback.message.reply("❌ Odwołano.")
        await bot.send_message(tx_data["runner_id"], "❌ **ODRZUCONO!**\nOperator anulował. Uciekaj stamtąd.", parse_mode="Markdown")
        repo.remove_tx(tx_id)

# --- KROK 5: SUKCES/ROZLICZENIE ---
@router.callback_query(lambda c: c.data.startswith("done_") or c.data.startswith("err_"))
async def finalize_tx(callback: types.CallbackQuery, repo: InMemoryRepository, bot: Bot):
    action, tx_id = callback.data.split("_")
    tx_data = repo.get_tx(tx_id)
    if not tx_data: return await callback.answer("Transakcja zamknięta.")
    
    await callback.message.edit_reply_markup(reply_markup=None)
    
    if action == "done":
        kwota = float(tx_data["amount"])
        runner = repo.get_user(tx_data["runner_id"])
        
        # PROWIZJA 40%
        if runner:
            runner.total_earned += (kwota * 0.40)
            runner.total_tx += 1
            repo.save_user(runner)
            
        await bot.send_message(tx_data["op_id"], f"🔥 **SUKCES TX {tx_id}** 🔥\nRunner wybrał {kwota} PLN!", parse_mode="Markdown")
        await callback.message.reply("✅ Zaksięgowano pomyślną wypłatę w statystykach.")
    else:
        await bot.send_message(tx_data["op_id"], f"❌ **AWARIA TX {tx_id}**\nRunner zgłosił błąd sprzętu.", parse_mode="Markdown")
        await callback.message.reply("Zgłoszono problem do centrali.")
        
    repo.remove_tx(tx_id)
    await callback.answer()


