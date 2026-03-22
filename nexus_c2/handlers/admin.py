from aiogram import Router, types, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.repository import InMemoryRepository
from config import AppConfig, SystemSettings, UserRole

router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_ban_id = State()

# --- GŁÓWNE MENU C2 ---
def get_main_admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⚙️ USTAWIENIA SYSTEMU", callback_data="adm_nav_settings")
    kb.button(text="👥 ZASOBY LUDZKIE (HR)", callback_data="adm_nav_hr")
    kb.button(text="💰 SKARBIEC (FINANSE)", callback_data="adm_nav_vault")
    kb.button(text="📡 LIVE OPS (AKTYWNE TX)", callback_data="adm_nav_live")
    kb.button(text="📢 ROZEŚLIJ KOMUNIKAT", callback_data="adm_broadcast")
    kb.button(text="☠️ PROTOKÓŁ GHOST ☠️", callback_data="adm_ghost_confirm")
    kb.adjust(1)
    return kb.as_markup()

@router.message(F.text == "⚙️ SYSTEM")
async def system_panel_main(message: types.Message, config: AppConfig):
    if message.from_user.id != config.ADMIN_ID: return
    
    await message.answer(
        "🛡 **NEXUS-C2 COMMAND CENTER**\nWybierz moduł operacyjny:", 
        reply_markup=get_main_admin_kb(),
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data == "adm_nav_main")
async def nav_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🛡 **NEXUS-C2 COMMAND CENTER**\nWybierz moduł operacyjny:",
        reply_markup=get_main_admin_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

# --- MODUŁ 1: USTAWIENIA SYSTEMU ---
@router.callback_query(lambda c: c.data == "adm_nav_settings")
async def nav_settings(callback: types.CallbackQuery, settings: SystemSettings):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔴 LOCKDOWN: ON" if settings.maintenance_mode else "🟢 LOCKDOWN: OFF", callback_data="adm_toggle_maint")
    kb.button(text="🟢 REKRUTACJA: ON" if settings.recruitment_open else "🔴 REKRUTACJA: OFF", callback_data="adm_toggle_recr")
    kb.button(text="🟢 ANTI-OCR: ON" if getattr(settings, 'anti_ocr_active', False) else "🔴 ANTI-OCR: OFF", callback_data="adm_toggle_ocr")
    kb.button(text="🟢 AUTO-DELETE: ON" if getattr(settings, 'auto_delete_tx', False) else "🔴 AUTO-DELETE: OFF", callback_data="adm_toggle_del")
    kb.button(text="🔙 POWRÓT", callback_data="adm_nav_main")
    kb.adjust(1)
    
    await callback.message.edit_text("⚙️ **USTAWIENIA SYSTEMU**\nZarządzaj globalnymi flagami bezpieczeństwa:", reply_markup=kb.as_markup(), parse_mode="Markdown")

@router.callback_query(lambda c: c.data.startswith("adm_toggle_"))
async def toggle_settings(callback: types.CallbackQuery, settings: SystemSettings):
    action = callback.data.split("_")[2]
    if action == "maint": settings.maintenance_mode = not settings.maintenance_mode
    elif action == "recr": settings.recruitment_open = not settings.recruitment_open
    elif action == "ocr": settings.anti_ocr_active = not getattr(settings, 'anti_ocr_active', False)
    elif action == "del": settings.auto_delete_tx = not getattr(settings, 'auto_delete_tx', False)
    
    await nav_settings(callback, settings) # Odśwież widok

# --- MODUŁ 2: HR I ZASOBY LUDZKIE ---
@router.callback_query(lambda c: c.data == "adm_nav_hr")
async def nav_hr(callback: types.CallbackQuery, repo: InMemoryRepository):
    runners = 0
    operators = 0
    burned = 0
    
    for u in repo._users.values():
        if u.role == UserRole.RUNNER: runners += 1
        elif u.role == UserRole.OPERATOR: operators += 1
        if getattr(u, 'status', '') == "BURNED": burned += 1

    kb = InlineKeyboardBuilder()
    kb.button(text="🔥 SPAL NODE'A (BAN)", callback_data="adm_ban_user")
    kb.button(text="🔙 POWRÓT", callback_data="adm_nav_main")
    kb.adjust(1)
    
    text = (
        "👥 **ZASOBY LUDZKIE (HR)**\n\n"
        f"🏃 Aktywni Runnerzy: `{runners}`\n"
        f"💻 Operatorzy (Wydawki): `{operators}`\n"
        f"☠️ Spalone Node'y (Bany): `{burned}`\n"
    )
    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "adm_ban_user")
async def ask_ban_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Wpisz Telegram ID użytkownika, którego chcesz SPALIĆ (zbanować):")
    await state.set_state(AdminStates.waiting_for_ban_id)
    await callback.answer()

@router.message(AdminStates.waiting_for_ban_id)
async def process_ban(message: types.Message, state: FSMContext, repo: InMemoryRepository):
    try:
        target_id = int(message.text)
        user = repo.get_user(target_id)
        if user:
            user.status = "BURNED"
            user.shadowbanned = True
            repo.save_user(user)
            await message.answer(f"✅ Node `{target_id}` został pomyślnie SPALONY. Odcięto mu dostęp.", parse_mode="Markdown")
        else:
            await message.answer("❌ Nie znaleziono użytkownika w bazie.")
    except ValueError:
        await message.answer("❌ Błędne ID. Anulowano.")
    await state.clear()

# --- MODUŁ 3: SKARBIEC ---
@router.callback_query(lambda c: c.data == "adm_nav_vault")
async def nav_vault(callback: types.CallbackQuery, repo: InMemoryRepository):
    total_group_profit = 0.0
    total_runner_payouts = 0.0
    
    for u in repo._users.values():
        if u.role == UserRole.RUNNER:
            earned = getattr(u, 'total_earned', 0.0)
            total_runner_payouts += earned
            total_cashed_out = earned / 0.40 if earned > 0 else 0 # Zakładając 40% prowizji
            total_group_profit += (total_cashed_out - earned)

    kb = InlineKeyboardBuilder()
    kb.button(text="🧼 WYPIERZ BRUDNE PIENIĄDZE (Reset)", callback_data="adm_wash_money")
    kb.button(text="🔙 POWRÓT", callback_data="adm_nav_main")
    kb.adjust(1)
    
    text = (
        "💰 **SKARBIEC CENTRALNY**\n\n"
        f"💎 Czysty zysk Grupy: `{total_group_profit:.2f} PLN`\n"
        f"💸 Wypłacono słupom: `{total_runner_payouts:.2f} PLN`\n\n"
        f"📊 Całkowity obrót: `{total_group_profit + total_runner_payouts:.2f} PLN`"
    )
    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "adm_wash_money")
async def wash_money(callback: types.CallbackQuery, repo: InMemoryRepository):
    # Resetowanie statystyk wszystkich runnerów
    for u in repo._users.values():
        if u.role == UserRole.RUNNER:
            u.total_earned = 0.0
            u.total_tx = 0
            repo.save_user(u)
    
    await callback.message.edit_text("🧼 **PRALNIA ZAKOŃCZONA**\nŚrodki wytransferowane na zimne portfele krypto.\nStatystyki wyzerowane.", parse_mode="Markdown")
    
    # Przycisk powrotu
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 POWRÓT", callback_data="adm_nav_main")
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())

# --- MODUŁ 4: LIVE OPS ---
@router.callback_query(lambda c: c.data == "adm_nav_live")
async def nav_live(callback: types.CallbackQuery, repo: InMemoryRepository):
    active_txs = repo._active_txs # Dostęp do słownika trwających transakcji
    
    text = "📡 **LIVE OPS (TRWAJĄCE ZLECENIA)**\n\n"
    if not active_txs:
        text += "Brak aktywnych operacji w tej chwili."
    else:
        for tx_id, data in active_txs.items():
            status = data.get('status', 'NEW')
            kwota = data.get('amount', '?')
            runner = data.get('runner_id', 'Brak')
            
            if status == "NEW":
                text += f"🟡 `{tx_id}` | {kwota} PLN | Oczekuje na przejęcie...\n"
            elif status == "CLAIMED":
                text += f"🏃‍♂️ `{tx_id}` | {kwota} PLN | Runner ID: {runner} biegnie do ATM!\n"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 ODŚWIEŻ", callback_data="adm_nav_live")
    kb.button(text="🔙 POWRÓT", callback_data="adm_nav_main")
    kb.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- MODUŁ 5: BROADCAST ---
@router.callback_query(lambda c: c.data == "adm_broadcast")
async def start_broadcast(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📢 Wpisz treść komunikatu (trafi do wszystkich aktywnych):")
    await state.set_state(AdminStates.waiting_for_broadcast)
    await call.answer()

@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext, repo: InMemoryRepository, bot: Bot):
    count = 0
    for uid, user in repo._users.items():
        if not getattr(user, 'shadowbanned', False): # Nie wysyłamy do spalonych
            try:
                await bot.send_message(uid, f"📢 **OGŁOSZENIE CENTRALNE**\n\n{message.text}", parse_mode="Markdown")
                count += 1
            except Exception:
                continue
    await message.answer(f"✅ Dostarczono do {count} aktywnych node'ów.")
    await state.clear()

# --- MODUŁ 6: PROTOKÓŁ GHOST (PANIKA GLOBALNA) ---
@router.callback_query(lambda c: c.data == "adm_ghost_confirm")
async def ghost_confirm(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="⚠️ POTWIERDZAM - ZNISZCZ WSZYSTKO", callback_data="adm_ghost_execute")
    kb.button(text="❌ ANULUJ", callback_data="adm_nav_main")
    kb.adjust(1)
    
    await callback.message.edit_text(
        "☠️ **PROTOKÓŁ GHOST** ☠️\n\n"
        "UWAGA! Użycie tej funkcji:\n"
        "1. Banuje WSZYSTKICH Runnerów i Operatorów.\n"
        "2. Usuwa wszystkie aktywne transakcje.\n"
        "3. Zamyka rekrutację.\n\n"
        "Czy na pewno masz na ogonie organy ścigania?",
        reply_markup=kb.as_markup()
    )

@router.callback_query(lambda c: c.data == "adm_ghost_execute")
async def ghost_execute(callback: types.CallbackQuery, repo: InMemoryRepository, settings: SystemSettings, config: AppConfig):
    # 1. Zamykamy dostęp z zewnątrz
    settings.recruitment_open = False
    settings.maintenance_mode = True
    
    # 2. Czyścimy operacje
    repo._active_txs.clear()
    
    # 3. Palimy wszystkich oprócz szefa
    for uid, user in repo._users.items():
        if uid != config.ADMIN_ID:
            user.status = "BURNED"
            user.shadowbanned = True
            repo.save_user(user)
            
    await callback.message.edit_text(
        "☠️ **PROTOKÓŁ GHOST WYKONANY** ☠️\n\n"
        "Sieć zniszczona. Zacieranie śladów zakończone. Ratuj się ucieczką.",
        parse_mode="Markdown"
    )


