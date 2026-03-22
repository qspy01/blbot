import asyncio
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.repository import InMemoryRepository
from config import AppConfig, UserRole, SystemSettings

router = Router()

# Maszyna stanów dla dodawania kodu
class BlikOpStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_code = State()

# --- MODUŁ PANIKI (EMERGENCY WIPE) ---
@router.message(F.text == "🔥 PANIKA")
async def emergency_panic(message: types.Message, repo: InMemoryRepository, bot: Bot, config: AppConfig):
    uid = message.from_user.id
    user = repo.get_user(uid)
    
    if not user or user.role != UserRole.RUNNER:
        return
        
    user.status = "BURNED"
    repo.save_user(user)
    
    await bot.send_message(
        config.ADMIN_ID, 
        f"🚨🚨 **CRITICAL ALERT** 🚨🚨\nRunner `{user.username}` ({uid}) wcisnął przycisk PANIKI!\nOdcięto mu dostęp do sieci."
    )
    
    kb = types.ReplyKeyboardRemove()
    await message.answer("🧹 Pamięć wyczyszczona. Sesja usunięta.", reply_markup=kb)
    
    # Symulacja czyszczenia historii dla wywiadowców
    for _ in range(5):
        await message.answer("...")
    await message.answer("Błąd 502: Bad Gateway. Connection Refused.")


# --- KROK 1: OPERATOR INICJUJE DODANIE KODU ---
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
    amount = data.get("amount", "Nieznana")
    code = message.text
    
    await state.clear()
    
    if settings.maintenance_mode:
        return await message.answer("⚠️ System jest w trybie Lockdown. Operacja odrzucona.")
    
    tx_id = f"TX{message.message_id}"
    
    try:
        await message.delete() # Ukrycie kodu z historii operatora
    except Exception:
        pass
    
    repo.add_active_tx(tx_id, {"code": code, "amount": amount, "op_id": uid})
    
    kb = InlineKeyboardBuilder()
    kb.button(text="⚡️ PRZEJMIJ ZLECENIE", callback_data=f"clm_{tx_id}")
    
    # Rozsyłamy powiadomienie do aktywnych Runnerów
    powiadomiono = 0
    for u_id, u_data in repo._users.items():
        if u_data.role in [UserRole.RUNNER, UserRole.ADMIN] and u_data.status == "ACTIVE":
            try:
                await bot.send_message(
                    u_id,
                    f"🚨 **NOWE ZLECENIE** 🚨\nID: `{tx_id}`\nKwota: **{amount} PLN**\n\nKto pierwszy, ten lepszy!",
                    reply_markup=kb.as_markup(),
                    parse_mode="Markdown"
                )
                powiadomiono += 1
            except Exception:
                continue
                
    await message.answer(f"✅ Kod wprowadzony do sieci.\nID: `{tx_id}`\nKwota: `{amount} PLN`\nPowiadomiono node'y: {powiadomiono}", parse_mode="Markdown")

# Zabezpieczenie na wypadek, gdyby ktoś podał kod o innej długości niż 6 cyfr
@router.message(BlikOpStates.waiting_for_code)
async def invalid_blik_code(message: types.Message):
    await message.answer("❌ Kod BLIK musi składać się z dokładnie 6 cyfr. Spróbuj ponownie:")


# --- KROK 2: RUNNER PRZEJMUJE KOD ---
@router.callback_query(lambda c: c.data.startswith("clm_"))
async def claim_signal(callback: types.CallbackQuery, repo: InMemoryRepository, bot: Bot):
    uid = callback.from_user.id
    user = repo.get_user(uid)
    tx_id = callback.data.split("_")[1]
    
    if not user or user.role not in [UserRole.RUNNER, UserRole.ADMIN]:
        return await callback.answer("Brak uprawnień.", show_alert=True)
    
    tx_data = repo.get_tx(tx_id)
    if not tx_data:
        return await callback.answer("❌ Ktoś był szybszy lub zlecenie wygasło.")
    
    # Zabezpieczamy zlecenie usuwając je z puli dostępnych
    code = tx_data["code"]
    amount = tx_data["amount"]
    op_id = tx_data["op_id"]
    repo.remove_tx(tx_id) 
    
    # Przebudowujemy klawiaturę - teraz Runner musi prosić o PIN
    status_kb = InlineKeyboardBuilder()
    status_kb.button(text="⏳ PROŚBA O AKCEPTACJĘ PIN", callback_data=f"reqpin_{tx_id}_{op_id}")
    status_kb.button(text="❌ BŁĄD (Zły kod)", callback_data=f"err_{tx_id}_{op_id}")
    status_kb.adjust(1)
    
    await bot.send_message(
        uid, 
        f"🏁 **TX: {tx_id}**\n💰 Kwota: **{amount} PLN**\n🔢 KOD: `{code}`\n\nWpisz kod w bankomacie, a następnie poproś o PIN!", 
        reply_markup=status_kb.as_markup(),
        parse_mode="Markdown"
    )
    
    await bot.send_message(op_id, f"🎯 Runner {callback.from_user.first_name} dobiegł do bankomatu i przejął kod ({amount} PLN). Oczekuj na prośbę o PIN...")
    
    await callback.message.edit_text(f"{callback.message.text}\n\n**[PRZEJĘTE PRZEZ INNEGO RUNNERA]**", parse_mode="Markdown")
    await callback.answer("Zlecenie przejęte! Bignij do bankomatu.")


# --- KROK 3: RUNNER PROSI O PIN ---
@router.callback_query(lambda c: c.data.startswith("reqpin_"))
async def request_pin_approval(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    tx_id = parts[1]
    op_id = int(parts[2])
    runner_id = callback.from_user.id
    
    # Runner widzi, że prośba poszła
    await callback.message.edit_text(
        f"{callback.message.text}\n\n**⏳ OCZEKIWANIE NA OPERATORA... NIE DOTYKAJ BANKOMATU!**", 
        reply_markup=None, 
        parse_mode="Markdown"
    )
    
    # Operator dostaje guzik do akceptacji
    op_kb = InlineKeyboardBuilder()
    op_kb.button(text="✅ ZATWIERDZIŁEM W APLIKACJI", callback_data=f"ackpin_{tx_id}_{runner_id}")
    op_kb.button(text="❌ ODRZUCONE PRZEZ BANK", callback_data=f"rejpin_{tx_id}_{runner_id}")
    op_kb.adjust(1)
    
    await bot.send_message(
        op_id, 
        f"🚨🚨 **AKCEPTACJA PIN WYMAGANA!** 🚨🚨\nTX: `{tx_id}`\nRunner stoi przy bankomacie!\nSzybko wejdź w aplikację bankową ofiary i potwierdź wypłatę!", 
        reply_markup=op_kb.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer("Wysłano prośbę o PIN. Czekaj!")


# --- KROK 4: OPERATOR AKCEPTUJE/ODRZUCA PIN ---
@router.callback_query(lambda c: c.data.startswith("ackpin_") or c.data.startswith("rejpin_"))
async def operator_pin_decision(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    action = parts[0]
    tx_id = parts[1]
    runner_id = int(parts[2])
    op_id = callback.from_user.id
    
    await callback.message.edit_reply_markup(reply_markup=None)
    
    if action == "ackpin":
        await callback.message.reply(f"✅ Przekazano do Runnera. Czekamy na potwierdzenie wypłaty gotówki.")
        
        # Runner dostaje zielone światło
        final_kb = InlineKeyboardBuilder()
        final_kb.button(text="💸 GOTÓWKA WYBRANA (SUKCES)", callback_data=f"done_{tx_id}_{op_id}")
        final_kb.button(text="❌ BŁĄD BANKOMATU", callback_data=f"err_{tx_id}_{op_id}")
        final_kb.adjust(1)
        
        await bot.send_message(
            runner_id,
            f"✅ **PIN ZAAKCEPTOWANY DLA {tx_id}!**\nOperator potwierdził wypłatę. Wyciągaj gotówkę!",
            reply_markup=final_kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await callback.message.reply(f"❌ Odwołano operację.")
        await bot.send_message(
            runner_id,
            f"❌ **ODRZUCONO {tx_id}!**\nOperator odrzucił transakcję (np. limit na koncie ofiary). Uciekaj stamtąd.",
            parse_mode="Markdown"
        )
    await callback.answer()


# --- KROK 5: RUNNER ZGŁASZA FINALNY STATUS ---
@router.callback_query(lambda c: c.data.startswith("done_") or c.data.startswith("err_"))
async def finalize_tx(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    action = parts[0]
    tx_id = parts[1]
    op_id = int(parts[2])
    
    await callback.message.edit_reply_markup(reply_markup=None)
    
    if action == "done":
        await bot.send_message(op_id, f"🔥 **SUKCES TX {tx_id}** 🔥\nRunner potwierdził wybranie gotówki z maszyny!", parse_mode="Markdown")
        await callback.message.reply("✅ Zaksięgowano pomyślną wypłatę w systemie.")
    else:
        await bot.send_message(op_id, f"❌ **AWARIA TX {tx_id}**\nRunner zgłosił błąd (zacięcie maszyny / awaria bankomatu).", parse_mode="Markdown")
        await callback.message.reply("Zgłoszono problem do operatora.")
        
    await callback.answer()


