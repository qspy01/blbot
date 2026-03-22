from aiogram import Router, types, F
from database.repository import InMemoryRepository
from config import AppConfig, UserRole

router = Router()

RUNNER_COMMISSION = 0.40  # 40% dla Wybieraka

@router.message(F.text == "📊 MÓJ UROBEK")
async def check_stats(message: types.Message, repo: InMemoryRepository):
    user = repo.get_user(message.from_user.id)
    if not user or user.role != UserRole.RUNNER:
        return

    earned = getattr(user, 'total_earned', 0.0)
    tx_count = getattr(user, 'total_tx', 0)
    
    await message.answer(
        f"💰 **TWÓJ STATUS FINANSOWY**\n\n"
        f"🔄 Zrealizowanych wypłat: `{tx_count}`\n"
        f"💸 Zarobiono na czysto: `{earned:.2f} PLN`\n\n"
        f"_(Prowizja wynosi {int(RUNNER_COMMISSION * 100)}% od każdej udanej transakcji)_",
        parse_mode="Markdown"
    )

@router.message(F.text == "📊 TABLICA LIDERÓW")
async def top_runners(message: types.Message, repo: InMemoryRepository, config: AppConfig):
    if message.from_user.id != config.ADMIN_ID:
        return
        
    runners_data = []
    total_group_profit = 0.0

    for u_id, u_data in repo._users.items():
        if u_data.role == UserRole.RUNNER:
            earned = getattr(u_data, 'total_earned', 0.0)
            txs = getattr(u_data, 'total_tx', 0)
            
            # Wliczanie do zysku "Centrali" (pozostałe 60%)
            total_cashed_out = earned / RUNNER_COMMISSION if earned > 0 else 0
            total_group_profit += (total_cashed_out - earned)
            
            runners_data.append({"name": u_data.username, "earned": earned, "txs": txs})
            
    # Sortowanie od najlepszego
    runners_data.sort(key=lambda x: x["earned"], reverse=True)
    
    msg_text = "🏆 **TABLICA LIDERÓW (RUNNERZY)**\n\n"
    if not runners_data:
        msg_text += "Brak aktywnych runnerów.\n"
    
    for idx, r in enumerate(runners_data, 1):
        msg_text += f"*{idx}.* {r['name']} | Wypłaty: `{r['txs']}` | Urobek: `{r['earned']:.2f} PLN`\n"
        
    msg_text += f"\n💎 **ZYSK GRUPY (DLA GÓRY):** `{total_group_profit:.2f} PLN`"
    
    await message.answer(msg_text, parse_mode="Markdown")


