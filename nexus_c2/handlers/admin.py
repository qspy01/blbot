from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.repository import InMemoryRepository
from config import AppConfig, SystemSettings, UserRole

router = Router()

class AdminStates(StatesGroup):
    broadcast_text = State()
    search_user_id = State()

# ==========================================
# WIDOKI (KEYBOARDS)
# ==========================================

def kb_main():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔌 MODUŁY", callback_data="adm_modules")
    kb.button(text="👥 UŻYTKOWNICY", callback_data="adm_users")
    kb.button(text="📢 BROADCAST", callback_data="adm_broadcast")
    kb.button(text="📊 STATYSTYKI", callback_data="adm_stats")
    kb.button(text="🚨 LOCKDOWN", callback_data="adm_lockdown")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

def kb_modules(settings: SystemSettings):
    kb = InlineKeyboardBuilder()
    kb.button(text=f"{'🟢' if settings.recruitment_open else '🔴'} Rekrutacja", callback_data="mod_recruitment_open")
    kb.button(text=f"{'🟢' if settings.gps_required else '🔴'} Wymóg GPS", callback_data="mod_gps_required")
    kb.button(text=f"{'🟢' if settings.anti_ocr_active else '🔴'} Anti-OCR", callback_data="mod_anti_ocr_active")
    kb.button(text=f"{'🟢' if settings.auto_delete_tx else '🔴'} Auto-Delete", callback_data="mod_auto_delete_tx")
    kb.button(text=f"{'🟢' if settings.maintenance_mode else '⚪'} Przerwa Techniczna", callback_data="mod_maintenance_mode")
    kb.button(text="⬅️ POWRÓT", callback_data="adm_main")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()

def kb_users():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Szukaj po ID", callback_data="usr_search")
    kb.button(text="🏃 Lista Runnerów", callback_data="usr_list_RUNNER")
    kb.button(text="📡 Lista Operatorów", callback_data="usr_list_OPERATOR")
    kb.button(text="⬅️ POWRÓT", callback_data="adm_main")
    kb.adjust(1, 2, 1)
    return kb.as_markup()

def kb_user_manage(uid: int, is_banned: bool):
    kb = InlineKeyboardBuilder()
    ban_txt = "🟢 ODBANUJ" if is_banned else "🔴 SHADOWBAN"
    kb.button(text=ban_txt, callback_data=f"usr_ban_{uid}")
    kb.button(text="🔄 Zmień Rolę", callback_data=f"usr_role_{uid}")
    kb.button(text="⬅️ POWRÓT", callback_data="adm_users")
    kb.adjust(2, 1)
    return kb.as_markup()

def kb_roles(uid: int):
    kb = InlineKeyboardBuilder()
    for role in UserRole:
        kb.button(text=f"Mianuj: {role.value}", callback_data=f"usr_setrole_{uid}_{role.value}")
    kb.button(text="⬅️ ANULUJ", callback_data=f"usr_manage_{uid}")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

# ==========================================
# HANDLERY GŁÓWNE
# ==========================================

@router.message(F.text == "⚙️ SYSTEM")
async def cmd_panel(message: types.Message, config: AppConfig):
    if message.from_user.id != config.ADMIN_ID: return
    await message.answer("🏦 **NEXUS-C2 COMMAND CENTER**\nWybierz sektor zarządzania:", reply_markup=kb_main())

@router.callback_query(F.data == "adm_main")
async def nav_main(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🏦 **NEXUS-C2 COMMAND CENTER**\nWybierz sektor zarządzania:", reply_markup=kb_main())

# ==========================================
# ZARZĄDZANIE MODUŁAMI
# ==========================================

@router.callback_query(F.data == "adm_modules")
async def nav_modules(call: types.CallbackQuery, settings: SystemSettings):
    await call.message.edit_text("⚙️ **ZARZĄDZANIE MODUŁAMI**\nKliknij, aby przełączyć stan:", reply_markup=kb_modules(settings))

@router.callback_query(F.data.startswith("mod_"))
async def toggle_module(call: types.CallbackQuery, settings: SystemSettings):
    attr = call.data.replace("mod_", "")
    if hasattr(settings, attr):
        current = getattr(settings, attr)
        setattr(settings, attr, not current)
        await call.message.edit_reply_markup(reply_markup=kb_modules(settings))
        await call.answer(f"Zmieniono stan modułu: {attr}")

@router.callback_query(F.data == "adm_lockdown")
async def trigger_lockdown(call: types.CallbackQuery, settings: SystemSettings):
    settings.maintenance_mode = True
    settings.recruitment_open = False
    await call.message.edit_text("🚨 **LOCKDOWN AKTYWNY** 🚨\nSystem zablokowany. Włączono przerwę techniczną i zamknięto rekrutację.", reply_markup=kb_main())
    await call.answer("LOCKDOWN!")

# ==========================================
# STATYSTYKI
# ==========================================

@router.callback_query(F.data == "adm_stats")
async def show_stats(call: types.CallbackQuery, repo: InMemoryRepository, settings: SystemSettings):
    tot = len(repo._users)
    run = len(repo.get_all_by_role(UserRole.RUNNER))
    opr = len(repo.get_all_by_role(UserRole.OPERATOR))
    pend = len([u for u in repo._users.values() if u.status == "PENDING"])
    
    txt = (
        "📊 **RAPORT SYSTEMOWY**\n\n"
        f"👥 Wszystkich w bazie: `{tot}`\n"
        f"🏃 Runnerów: `{run}`\n"
        f"📡 Operatorów: `{opr}`\n"
        f"⏳ Oczekujących (Aplikacje): `{pend}`\n\n"
        f"💰 Aktywne sygnały (TX): `{len(repo._active_tx)}`\n"
        f"🛡 Lockdown: `{'TAK' if settings.maintenance_mode else 'NIE'}`"
    )
    await call.message.edit_text(txt, reply_markup=kb_main())

# ==========================================
# BROADCAST
# ==========================================

@router.callback_query(F.data == "adm_broadcast")
async def nav_broadcast(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("📢 **SYSTEM BROADCAST**\nWprowadź treść komunikatu, który ma zostać wysłany do WSZYSTKICH w sieci:")
    await state.set_state(AdminStates.broadcast_text)

@router.message(AdminStates.broadcast_text)
async def process_broadcast(message: types.Message, state: FSMContext, repo: InMemoryRepository):
    users = list(repo._users.keys())
    sent = 0
    msg_id = await message.answer("Trwa wysyłanie...")
    
    for uid in users:
        try:
            await message.bot.send_message(uid, f"📢 **KOMUNIKAT CENTRALNY**\n\n{message.text}")
            sent += 1
        except: pass
        
    await msg_id.edit_text(f"✅ Transmisja zakończona.\nDostarczono do: `{sent}/{len(users)}` nodów.", reply_markup=kb_main())
    await state.clear()

# ==========================================
# ZARZĄDZANIE UŻYTKOWNIKAMI
# ==========================================

@router.callback_query(F.data == "adm_users")
async def nav_users(call: types.CallbackQuery):
    await call.message.edit_text("👥 **ZARZĄDZANIE PERSONELEM**\nWybierz akcję:", reply_markup=kb_users())

@router.callback_query(F.data.startswith("usr_list_"))
async def list_users_role(call: types.CallbackQuery, repo: InMemoryRepository):
    role = UserRole(call.data.split("_")[2])
    users = repo.get_all_by_role(role)
    
    if not users:
        return await call.answer(f"Brak użytkowników o roli {role.value}", show_alert=True)
        
    txt = f"Lista: **{role.value}**\n\n"
    for u in users:
        ban_mark = "🔴" if u.shadowbanned else "🟢"
        txt += f"{ban_mark} `{u.uid}` | {u.username} | {u.city}\n"
        
    await call.message.edit_text(txt, reply_markup=kb_users())

@router.callback_query(F.data == "usr_search")
async def search_user_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("🔍 **WYSZUKIWANIE**\nWprowadź dokładne ID użytkownika Telegram:")
    await state.set_state(AdminStates.search_user_id)

@router.message(AdminStates.search_user_id)
async def process_user_search(message: types.Message, state: FSMContext, repo: InMemoryRepository):
    try:
        uid = int(message.text)
    except:
        return await message.answer("Błąd: ID musi być liczbą.", reply_markup=kb_users())
        
    user = repo.get_user(uid)
    await state.clear()
    
    if not user:
        return await message.answer(f"❌ Nie znaleziono użytkownika o ID: `{uid}`", reply_markup=kb_users())
        
    txt = (
        f"👤 **PROFIL: {user.username}**\n"
        f"ID: `{user.uid}`\n"
        f"Rola: `{user.role.value}`\n"
        f"Miasto: `{user.city}`\n"
        f"Status GPS: `{'Zweryfikowany' if user.is_geo_verified else 'Brak'}`\n"
        f"Shadowban: `{'TAK' if user.shadowbanned else 'NIE'}`\n"
    )
    await message.answer(txt, reply_markup=kb_user_manage(uid, user.shadowbanned))

@router.callback_query(F.data.startswith("usr_manage_"))
async def back_to_user(call: types.CallbackQuery, repo: InMemoryRepository):
    uid = int(call.data.split("_")[2])
    user = repo.get_user(uid)
    await call.message.edit_text(f"Zarządzanie ID: `{uid}`", reply_markup=kb_user_manage(uid, user.shadowbanned))

@router.callback_query(F.data.startswith("usr_ban_"))
async def toggle_user_ban(call: types.CallbackQuery, repo: InMemoryRepository):
    uid = int(call.data.split("_")[2])
    user = repo.get_user(uid)
    if user:
        user.shadowbanned = not user.shadowbanned
        repo.save_user(user)
        await call.message.edit_reply_markup(reply_markup=kb_user_manage(uid, user.shadowbanned))
        await call.answer(f"Zmieniono ban dla: {uid}")

@router.callback_query(F.data.startswith("usr_role_"))
async def show_roles_menu(call: types.CallbackQuery):
    uid = int(call.data.split("_")[2])
    await call.message.edit_reply_markup(reply_markup=kb_roles(uid))

@router.callback_query(F.data.startswith("usr_setrole_"))
async def set_user_role(call: types.CallbackQuery, repo: InMemoryRepository):
    parts = call.data.split("_")
    uid = int(parts[2])
    new_role = UserRole(parts[3])
    
    user = repo.get_user(uid)
    if user:
        user.role = new_role
        user.status = "ACTIVE"
        repo.save_user(user)
        await call.message.edit_text(f"✅ Rola dla `{uid}` zmieniona na `{new_role.value}`", reply_markup=kb_user_manage(uid, user.shadowbanned))
        
        try:
            await call.message.bot.send_message(uid, f"🔄 Centrala zmieniła Twoje uprawnienia.\nNowa rola: `{new_role.value}`. Wpisz /start, aby odświeżyć menu.")
        except: pass


