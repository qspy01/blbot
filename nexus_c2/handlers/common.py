from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from database.repository import InMemoryRepository
from database.models import UserProfile
from config import AppConfig, UserRole
from config import SystemSettings

router = Router()

def get_main_kb(user: UserProfile):
    builder = ReplyKeyboardBuilder()
    if user.role == UserRole.ADMIN:
        builder.button(text="⚙️ SYSTEM")
    elif user.role == UserRole.RUNNER:
        builder.button(text="📍 LOKALIZACJA", request_location=True)
    elif user.role == UserRole.OPERATOR:
        builder.button(text="📥 DODAJ KOD")
    else:
        builder.button(text="📝 APLIKUJ")
    return builder.as_markup(resize_keyboard=True)

@router.message(Command("start"))
async def cmd_start(message: types.Message, repo: InMemoryRepository, config: AppConfig):
    uid = message.from_user.id
    user = repo.get_user(uid)
    if not user:
        user = UserProfile(uid=uid, username=message.from_user.full_name)
        if uid == config.ADMIN_ID:
            user.role, user.status = UserRole.ADMIN, "ACTIVE"
        repo.save_user(user)
    await message.answer(f"🛡 **NEXUS-C2**\nRola: `{user.role.value}`", reply_markup=get_main_kb(user), parse_mode="Markdown")
