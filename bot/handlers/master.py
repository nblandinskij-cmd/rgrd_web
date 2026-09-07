from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes
from datetime import datetime

from ..data_manager import (
    data, save_data, get_master_by_user, get_balance,
    filter_incomes_by_period, is_admin
)
from ..keyboards import get_main_keyboard, cancel_kb, period_kb
from ..utils import extract_numbers

INCOME_REQUEST = 70
MASTER_STATS_PERIOD = 80

async def request_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        await update.message.reply_text("Администраторы используют прямое добавление доходов.")
        return
    master_name = get_master_by_user(user_id)
    if not master_name:
        await update.message.reply_text("❌ Вы не зарегистрированы.")
        return
    await update.message.reply_text("Введите список работ (числа времени вида 12:30 игнорируются):", reply_markup=cancel_kb())
    return INCOME_REQUEST

async def income_request_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    master_name = get_master_by_user(user_id)
    if not master_name:
        await update.message.reply_text("Вы не зарегистрированы.", reply_markup=get_main_keyboard(user_id))
        return ConversationHandler.END
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Отменено.", reply_markup=get_main_keyboard(user_id))
        return ConversationHandler.END
    numbers = extract_numbers(text)
    if not numbers:
        await update.message.reply_text("Не найдено чисел (временные форматы игнорируются).", reply_markup=cancel_kb())
        return INCOME_REQUEST
    total = sum(numbers)
    percent = data["settings"].get("deduction_percent", 70)
    net = total * (100 - percent) / 100
    pending = {
        "master": master_name,
        "original_amount": total,
        "amount": net,
        "text": text,
        "date": datetime.now().isoformat(),
        "status": "pending"
    }
    data["pending"].append(pending)
    save_data(data)
    await update.message.reply_text(
        f"✅ Заявка отправлена.\nНачислено: {total:.2f} руб.\nУдержание: {total - net:.2f} руб.\nК выдаче: {net:.2f} руб.",
        reply_markup=get_main_keyboard(user_id)
    )
    # Уведомляем администраторов
    for admin_id in data.get("admins", []):
        try:
            await context.bot.send_message(
                admin_id,
                f"📨 Новая заявка от {master_name}\nСумма к выдаче: {net:.2f} руб.\nТекст: {text[:100]}..."
            )
        except:
            pass
    return ConversationHandler.END

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    master_name = get_master_by_user(user_id)
    if not master_name:
        await update.message.reply_text("Вы не зарегистрированы.", reply_markup=get_main_keyboard(user_id))
        return
    incomes = [inc for inc in data["incomes"] if inc.get("master") == master_name]
    if not incomes:
        await update.message.reply_text("У вас пока нет подтверждённых доходов.", reply_markup=get_main_keyboard(user_id))
        return
    total = sum(inc["amount"] for inc in incomes)
    count = len(incomes)
    avg = total / count if count else 0
    await update.message.reply_text(
        f"📊 *Ваша статистика (мастер {master_name})*\n"
        f"💰 Общая сумма: {total:.2f} руб.\n"
        f"📦 Количество операций: {count}\n"
        f"📈 Средний чек: {avg:.2f} руб.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(user_id)
    )

async def my_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    master_name = get_master_by_user(user_id)
    if not master_name:
        await update.message.reply_text("Вы не зарегистрированы.", reply_markup=get_main_keyboard(user_id))
        return
    bal = get_balance(master_name)
    await update.message.reply_text(f"💰 Ваш баланс: {bal:.2f} руб.", reply_markup=get_main_keyboard(user_id))

async def master_stats_period_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    master_name = get_master_by_user(user_id)
    if not master_name:
        await update.message.reply_text("Вы не зарегистрированы.", reply_markup=get_main_keyboard(user_id))
        return ConversationHandler.END
    await update.message.reply_text("Выберите период для просмотра вашей статистики:", reply_markup=period_kb())
    return MASTER_STATS_PERIOD

async def master_stats_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    master_name = get_master_by_user(user_id)
    if not master_name:
        await update.message.reply_text("Вы не зарегистрированы.", reply_markup=get_main_keyboard(user_id))
        return ConversationHandler.END
    text = update.message.text
    if text in ("🔙 Назад", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(user_id))
        return ConversationHandler.END
    period_map = {
        "📅 Сегодня": "сегодня",
        "📅 Неделя": "неделя",
        "📅 Месяц": "месяц",
        "📅 Год": "год",
        "📅 Вся история": "все"
    }
    period_key = period_map.get(text)
    if not period_key:
        await update.message.reply_text("Неизвестный период. Выберите из кнопок.", reply_markup=period_kb())
        return MASTER_STATS_PERIOD

    filtered = filter_incomes_by_period(data["incomes"], period_key)
    filtered = [inc for inc in filtered if inc.get("master") == master_name]
    if not filtered:
        await update.message.reply_text(f"Нет данных за выбранный период.", reply_markup=get_main_keyboard(user_id))
        return ConversationHandler.END
    total = sum(inc["amount"] for inc in filtered)
    count = len(filtered)
    avg = total / count if count else 0
    await update.message.reply_text(
        f"📊 *Ваша статистика за период: {text}*\n"
        f"💰 Общая сумма: {total:.2f} руб.\n"
        f"📦 Количество операций: {count}\n"
        f"📈 Средний чек: {avg:.2f} руб.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(user_id)
    )
    return ConversationHandler.END

async def calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите текст с числами для расчёта (числа времени вида 12:30 игнорируются):", reply_markup=cancel_kb())
    return 60  # CALC_INPUT

async def calc_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    numbers = extract_numbers(text)
    if not numbers:
        await update.message.reply_text("Не найдено чисел (временные форматы игнорируются).", reply_markup=cancel_kb())
        return 60
    total = sum(numbers)
    percent = data["settings"].get("deduction_percent", 70)
    deduction = total * (percent / 100)
    net = total - deduction
    await update.message.reply_text(
        f"📊 *Результат расчёта*\n"
        f"Начислено: {total:.2f} руб.\n"
        f"Удержание ({percent}%): {deduction:.2f} руб.\n"
        f"К выдаче: {net:.2f} руб.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    return ConversationHandler.END