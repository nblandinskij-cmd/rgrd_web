from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes
from datetime import datetime
import io
import csv

from ..data_manager import (
    data, save_data, is_admin, get_master_by_user, get_master_branch,
    get_balance, get_masters_by_branch, get_branch_stats,
    get_all_branches_stats, filter_incomes_by_period
)
from ..keyboards import (
    branch_management_kb, reports_kb, tools_kb, pending_kb,
    cancel_kb, yes_no_kb, period_kb, pending_action_kb,
    get_main_keyboard, master_action_kb, account_action_kb,
    history_action_kb
)
from ..utils import extract_numbers
from ..prices import PRICES

# --------------------------------------------
# Состояния для ConversationHandler (вынесены, чтобы импортировать в main)
# --------------------------------------------
(
    ADD_BRANCH_NAME, DEL_BRANCH_SELECT, DEL_BRANCH_CONFIRM, BRANCH_STATS_SELECT,
    ADD_MASTER_BRANCH, ADD_MASTER_NAME, MASTER_LIST_NAV, MASTER_ACTION_CHOOSE,
    EDIT_MASTER_NAME, DELETE_MASTER_CONFIRM,
    STATS_BRANCH_SELECT, RATING_PERIOD, RATING_NAV, DETAILED_STATS_PERIOD,
    PENDING_SELECT, PENDING_ACTION, CHANGE_AMOUNT,
    HISTORY_SELECT, HISTORY_ACTION, HISTORY_CHANGE_AMOUNT,
    ACCOUNT_SELECT, ACCOUNT_ACTION, ACCOUNT_PAYMENT_AMOUNT, ACCOUNT_PAYMENT_COMMENT,
    CALC_INPUT, PERCENT_INPUT
) = range(1, 27)  # Уникальные номера для всех состояний

# --------------------------------------------
# ФИЛИАЛЫ
# --------------------------------------------
async def branches_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return
    await update.message.reply_text("🏢 Управление филиалами:", reply_markup=branch_management_kb())

async def list_branches_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return ConversationHandler.END
    branches = data["branches"]
    if not branches:
        await update.message.reply_text("Список филиалов пуст.", reply_markup=branch_management_kb())
        return ConversationHandler.END
    text = "📋 Список филиалов:\n" + "\n".join(f"• {b}" for b in branches)
    keyboard = [[b] for b in branches]
    keyboard.append(["🔙 Назад", "🏠 Главное меню"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text + "\n\nВыберите филиал для просмотра статистики:", reply_markup=reply_markup)
    return BRANCH_STATS_SELECT

async def branch_stats_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Назад", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    if text not in data["branches"]:
        await update.message.reply_text("Неизвестный филиал. Выберите из списка.",
                                        reply_markup=ReplyKeyboardMarkup([[b] for b in data["branches"]] + [["🔙 Назад", "🏠 Главное меню"]], resize_keyboard=True))
        return BRANCH_STATS_SELECT
    stats = get_branch_stats(text)
    masters = get_masters_by_branch(text)
    out = f"📊 *Филиал: {text}*\n\n"
    if masters:
        out += "👥 *Мастера:*\n" + "\n".join(f"• {m}" for m in masters) + "\n\n"
    else:
        out += "Нет мастеров в этом филиале.\n\n"
    out += f"💰 Общая сумма доходов: {stats['total']} руб.\n"
    out += f"📦 Количество операций: {stats['count']}\n"
    out += f"📈 Средний чек: {stats['avg']} руб.\n"
    if stats['top']:
        out += "\n🏆 *Топ мастеров:*\n"
        for i, m in enumerate(stats['top'], 1):
            out += f"{i}. {m['name']} – {m['amount']} руб.\n"
    await update.message.reply_text(out, parse_mode="Markdown", reply_markup=branch_management_kb())
    return ConversationHandler.END

async def add_branch_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return ConversationHandler.END
    await update.message.reply_text("Введите название нового филиала:", reply_markup=cancel_kb())
    return ADD_BRANCH_NAME

async def add_branch_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    name = text.strip()
    if not name:
        await update.message.reply_text("Название не может быть пустым.", reply_markup=cancel_kb())
        return ADD_BRANCH_NAME
    if name in data["branches"]:
        await update.message.reply_text(f"Филиал '{name}' уже существует.", reply_markup=branch_management_kb())
        return ConversationHandler.END
    data["branches"].append(name)
    save_data(data)
    await update.message.reply_text(f"✅ Филиал '{name}' добавлен.", reply_markup=branch_management_kb())
    return ConversationHandler.END

async def remove_branch_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return ConversationHandler.END
    branches = data["branches"]
    if not branches:
        await update.message.reply_text("Нет филиалов для удаления.", reply_markup=branch_management_kb())
        return ConversationHandler.END
    keyboard = [[b] for b in branches]
    keyboard.append(["🔙 Отмена"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите филиал для удаления:", reply_markup=reply_markup)
    return DEL_BRANCH_SELECT

async def remove_branch_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 Отмена":
        await update.message.reply_text("Действие отменено.", reply_markup=branch_management_kb())
        return ConversationHandler.END
    if text not in data["branches"]:
        await update.message.reply_text("Неизвестный филиал.", reply_markup=ReplyKeyboardMarkup([[b] for b in data["branches"]] + [["🔙 Отмена"]], resize_keyboard=True))
        return DEL_BRANCH_SELECT
    if get_masters_by_branch(text):
        await update.message.reply_text(f"Невозможно удалить филиал '{text}', так как в нём есть мастера.", reply_markup=branch_management_kb())
        return ConversationHandler.END
    context.user_data["del_branch"] = text
    await update.message.reply_text(f"Вы уверены, что хотите удалить филиал '{text}'? (Да/Нет)", reply_markup=yes_no_kb())
    return DEL_BRANCH_CONFIRM

async def remove_branch_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Нет":
        await update.message.reply_text("Удаление отменено.", reply_markup=branch_management_kb())
        return ConversationHandler.END
    if text == "✅ Да":
        branch = context.user_data.get("del_branch")
        if not branch or branch not in data["branches"]:
            await update.message.reply_text("Ошибка.", reply_markup=branch_management_kb())
            return ConversationHandler.END
        data["branches"].remove(branch)
        save_data(data)
        await update.message.reply_text(f"✅ Филиал '{branch}' удалён.", reply_markup=branch_management_kb())
        context.user_data.pop("del_branch", None)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Ответьте Да или Нет.", reply_markup=yes_no_kb())
        return DEL_BRANCH_CONFIRM

# --------------------------------------------
# ИНСТРУМЕНТЫ (Управление мастерами, экспорт, процент, расчёт)
# --------------------------------------------
async def tools_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return
    await update.message.reply_text("🛠 Инструменты:", reply_markup=tools_kb())

async def add_master_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return ConversationHandler.END
    branches = data["branches"]
    if not branches:
        await update.message.reply_text("Нет филиалов. Сначала добавьте филиал.", reply_markup=tools_kb())
        return ConversationHandler.END
    keyboard = [[b] for b in branches]
    keyboard.append(["🔙 Отмена"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите филиал для нового мастера:", reply_markup=reply_markup)
    return ADD_MASTER_BRANCH

async def add_master_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 Отмена":
        await update.message.reply_text("Действие отменено.", reply_markup=tools_kb())
        return ConversationHandler.END
    if text not in data["branches"]:
        await update.message.reply_text("Неизвестный филиал.", reply_markup=ReplyKeyboardMarkup([[b] for b in data["branches"]] + [["🔙 Отмена"]], resize_keyboard=True))
        return ADD_MASTER_BRANCH
    context.user_data["new_master_branch"] = text
    await update.message.reply_text(f"Введите имя нового мастера для филиала {text}:", reply_markup=cancel_kb())
    return ADD_MASTER_NAME

async def add_master_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    name = text.strip()
    if not name:
        await update.message.reply_text("Имя не может быть пустым.", reply_markup=cancel_kb())
        return ADD_MASTER_NAME
    if name in [m["name"] for m in data["masters"]]:
        await update.message.reply_text(f"Мастер {name} уже существует.", reply_markup=tools_kb())
        return ConversationHandler.END
    branch = context.user_data.get("new_master_branch")
    if not branch:
        await update.message.reply_text("Ошибка: не выбран филиал.", reply_markup=tools_kb())
        return ConversationHandler.END
    data["masters"].append({"name": name, "branch": branch})
    save_data(data)
    await update.message.reply_text(f"✅ Мастер {name} добавлен в филиал {branch}.", reply_markup=get_main_keyboard(update.effective_user.id))
    context.user_data.pop("new_master_branch", None)
    return ConversationHandler.END

async def list_masters_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return ConversationHandler.END
    masters = data["masters"]
    if not masters:
        await update.message.reply_text("Список мастеров пуст.", reply_markup=tools_kb())
        return ConversationHandler.END
    page = context.user_data.get("masters_page", 0)
    total = len(masters)
    per_page = 5
    start = page * per_page
    end = min(start + per_page, total)
    if start >= total:
        page = 0
        start = 0
        end = min(per_page, total)
    context.user_data["masters_page"] = page
    text = "📋 *Список мастеров* (стр. {}/{})\n\n".format(page+1, (total-1)//per_page+1 if total else 1)
    for i, m in enumerate(masters[start:end], start+1):
        text += f"{i}. {m['name']} (филиал: {m['branch']})\n"
    keyboard = []
    for m in masters[start:end]:
        keyboard.append([m['name']])
    nav = []
    if page > 0:
        nav.append("◀️ Назад")
    if end < total:
        nav.append("Вперёд ▶️")
    if nav:
        keyboard.append(nav)
    keyboard.append(["🔙 Назад", "🏠 Главное меню"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    return MASTER_LIST_NAV

async def master_list_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Назад", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=tools_kb())
        return ConversationHandler.END
    if text == "◀️ Назад":
        page = context.user_data.get("masters_page", 0) - 1
        context.user_data["masters_page"] = page
        await list_masters_start(update, context)
        return MASTER_LIST_NAV
    if text == "Вперёд ▶️":
        page = context.user_data.get("masters_page", 0) + 1
        context.user_data["masters_page"] = page
        await list_masters_start(update, context)
        return MASTER_LIST_NAV
    if text in [m["name"] for m in data["masters"]]:
        context.user_data["selected_master_name"] = text
        await update.message.reply_text(f"Вы выбрали мастера *{text}*. Что хотите сделать?", parse_mode="Markdown", reply_markup=master_action_kb())
        return MASTER_ACTION_CHOOSE
    else:
        await update.message.reply_text("Неизвестная команда. Используйте кнопки.", reply_markup=tools_kb())
        return ConversationHandler.END

async def master_action_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 Отмена":
        await update.message.reply_text("Действие отменено.", reply_markup=tools_kb())
        context.user_data.pop("selected_master_name", None)
        return ConversationHandler.END
    master_name = context.user_data.get("selected_master_name")
    if not master_name:
        await update.message.reply_text("Ошибка: мастер не выбран.", reply_markup=tools_kb())
        return ConversationHandler.END
    if text == "✏️ Переименовать":
        await update.message.reply_text(f"Введите новое имя для мастера {master_name}:", reply_markup=cancel_kb())
        return EDIT_MASTER_NAME
    elif text == "❌ Удалить":
        await update.message.reply_text(f"Вы уверены, что хотите удалить мастера '{master_name}'? (Да/Нет)", reply_markup=yes_no_kb())
        return DELETE_MASTER_CONFIRM
    else:
        await update.message.reply_text("Используйте кнопки.", reply_markup=master_action_kb())
        return MASTER_ACTION_CHOOSE

async def edit_master_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=tools_kb())
        context.user_data.pop("selected_master_name", None)
        return ConversationHandler.END
    old_name = context.user_data.get("selected_master_name")
    new_name = text.strip()
    if not new_name:
        await update.message.reply_text("Имя не может быть пустым.", reply_markup=cancel_kb())
        return EDIT_MASTER_NAME
    if new_name in [m["name"] for m in data["masters"]] and new_name != old_name:
        await update.message.reply_text(f"Мастер {new_name} уже существует.", reply_markup=cancel_kb())
        return EDIT_MASTER_NAME
    for m in data["masters"]:
        if m["name"] == old_name:
            m["name"] = new_name
            break
    for inc in data["incomes"]:
        if inc.get("master") == old_name:
            inc["master"] = new_name
    for uid, name in data["users"].items():
        if name == old_name:
            data["users"][uid] = new_name
    for p in data["pending"]:
        if p.get("master") == old_name:
            p["master"] = new_name
    for pay in data["payments"]:
        if pay.get("master") == old_name:
            pay["master"] = new_name
    save_data(data)
    context.user_data.pop("selected_master_name", None)
    await update.message.reply_text(f"✅ Мастер переименован: {old_name} → {new_name}", reply_markup=tools_kb())
    return ConversationHandler.END

async def delete_master_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Нет":
        await update.message.reply_text("Удаление отменено.", reply_markup=tools_kb())
        context.user_data.pop("selected_master_name", None)
        return ConversationHandler.END
    if text == "✅ Да":
        name = context.user_data.get("selected_master_name")
        if not name:
            await update.message.reply_text("Ошибка.", reply_markup=tools_kb())
            return ConversationHandler.END
        data["masters"] = [m for m in data["masters"] if m["name"] != name]
        for uid, mname in list(data["users"].items()):
            if mname == name:
                del data["users"][uid]
        save_data(data)
        await update.message.reply_text(f"✅ Мастер {name} удалён.", reply_markup=tools_kb())
        context.user_data.pop("selected_master_name", None)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Ответьте Да или Нет.", reply_markup=yes_no_kb())
        return DELETE_MASTER_CONFIRM

# --------------------------------------------
# ОТЧЁТЫ
# --------------------------------------------
async def reports_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return
    await update.message.reply_text("📊 Отчёты:", reply_markup=reports_kb())

async def overall_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return
    all_stats = get_all_branches_stats()
    text = "📊 *Общая статистика по всем филиалам*\n\n"
    total_all = 0
    for branch, stats in all_stats.items():
        text += f"🏢 *{branch}*: {stats['total']} руб. (операций: {stats['count']})\n"
        total_all += stats['total']
    text += f"\n💰 *Общий доход: {total_all} руб.*"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard(update.effective_user.id))

async def branch_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return
    branches = data["branches"]
    if not branches:
        await update.message.reply_text("Нет филиалов.", reply_markup=get_main_keyboard(update.effective_user.id))
        return
    keyboard = [[b] for b in branches]
    keyboard.append(["🔙 Назад", "🏠 Главное меню"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите филиал для детальной статистики:", reply_markup=reply_markup)
    return STATS_BRANCH_SELECT

async def stats_branch_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Назад", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    if text not in data["branches"]:
        await update.message.reply_text("Неизвестный филиал.", reply_markup=ReplyKeyboardMarkup([[b] for b in data["branches"]] + [["🔙 Назад", "🏠 Главное меню"]], resize_keyboard=True))
        return STATS_BRANCH_SELECT
    stats = get_branch_stats(text)
    out = f"📊 *Детальная статистика филиала {text}*\n"
    out += f"💰 Общая сумма: {stats['total']} руб.\n"
    out += f"📦 Количество операций: {stats['count']}\n"
    out += f"📈 Средний чек: {stats['avg']} руб.\n"
    if stats['top']:
        out += "\n🏆 *Топ мастеров:*\n"
        for i, m in enumerate(stats['top'], 1):
            out += f"{i}. {m['name']} – {m['amount']} руб.\n"
    await update.message.reply_text(out, parse_mode="Markdown", reply_markup=get_main_keyboard(update.effective_user.id))
    return ConversationHandler.END

async def detailed_stats_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return ConversationHandler.END
    await update.message.reply_text("Выберите период для детальной статистики по мастерам:", reply_markup=period_kb())
    return DETAILED_STATS_PERIOD

async def detailed_stats_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Назад", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
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
        return DETAILED_STATS_PERIOD

    filtered = filter_incomes_by_period(data["incomes"], period_key)
    if not filtered:
        await update.message.reply_text(f"Нет данных за выбранный период.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END

    total_sum = sum(inc["amount"] for inc in filtered)
    count = len(filtered)
    avg = total_sum / count if count else 0
    masters_sum = {}
    for inc in filtered:
        m = inc.get("master", "Неизвестно")
        masters_sum[m] = masters_sum.get(m, 0) + inc["amount"]
    sorted_masters = sorted(masters_sum.items(), key=lambda x: x[1], reverse=True)

    out = f"📊 *Детальная статистика за период: {text}*\n\n"
    out += f"💰 Общая сумма: {total_sum:.2f} руб.\n"
    out += f"📦 Количество операций: {count}\n"
    out += f"📈 Средний чек: {avg:.2f} руб.\n\n"
    out += "👥 *Доходы по мастерам:*\n"
    if sorted_masters:
        for i, (m, amount) in enumerate(sorted_masters, 1):
            out += f"{i}. {m} – {amount:.2f} руб.\n"
    else:
        out += "Нет данных."

    await update.message.reply_text(out, parse_mode="Markdown", reply_markup=get_main_keyboard(update.effective_user.id))
    return ConversationHandler.END

# Рейтинг
async def rating_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return
    await update.message.reply_text("Выберите период для рейтинга:", reply_markup=period_kb())
    return RATING_PERIOD

async def rating_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Назад", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    period_map = {
        "📅 Сегодня": "сегодня",
        "📅 Неделя": "неделя",
        "📅 Месяц": "месяц",
        "📅 Год": "год",
        "📅 Вся история": "все"
    }
    period_key = period_map.get(text, "все")
    filtered = filter_incomes_by_period(data["incomes"], period_key)
    masters_sum = {}
    for inc in filtered:
        m = inc.get("master", "Неизвестно")
        masters_sum[m] = masters_sum.get(m, 0) + inc["amount"]
    sorted_rating = sorted(masters_sum.items(), key=lambda x: x[1], reverse=True)
    page = context.user_data.get("rating_page", 0)
    total = len(sorted_rating)
    per_page = 10
    start = page * per_page
    end = min(start + per_page, total)
    if start >= total:
        page = 0
        start = 0
        end = min(per_page, total)
    context.user_data["rating_page"] = page
    context.user_data["rating_data"] = sorted_rating
    context.user_data["rating_period"] = text

    out = f"🏆 *Рейтинг мастеров ({text})* (стр. {page+1}/{ (total-1)//per_page +1 if total else 1})\n"
    for i, (m, amount) in enumerate(sorted_rating[start:end], start+1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        out += f"{medal} {m} – {amount:.2f} руб.\n"
    if not sorted_rating:
        out = "Нет данных."
    keyboard = []
    nav = []
    if page > 0:
        nav.append("◀️ Назад")
    if end < total:
        nav.append("Вперёд ▶️")
    if nav:
        keyboard.append(nav)
    keyboard.append(["🔙 Назад", "🏠 Главное меню"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(out, parse_mode="Markdown", reply_markup=reply_markup)
    return RATING_NAV

async def rating_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Назад", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    if text == "◀️ Назад":
        page = context.user_data.get("rating_page", 0) - 1
        context.user_data["rating_page"] = page
        await rating_period(update, context)
        return RATING_NAV
    if text == "Вперёд ▶️":
        page = context.user_data.get("rating_page", 0) + 1
        context.user_data["rating_page"] = page
        await rating_period(update, context)
        return RATING_NAV
    await update.message.reply_text("Используйте кнопки навигации.", reply_markup=ReplyKeyboardMarkup([["◀️ Назад", "Вперёд ▶️"], ["🔙 Назад", "🏠 Главное меню"]], resize_keyboard=True))
    return RATING_NAV

# --------------------------------------------
# ЗАЯВКИ
# --------------------------------------------
async def pending_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return
    await update.message.reply_text("📋 Заявки:", reply_markup=pending_kb())

async def pending_list_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return ConversationHandler.END
    pending = [p for p in data["pending"] if p.get("status") == "pending"]
    if not pending:
        await update.message.reply_text("Нет активных заявок.", reply_markup=pending_kb())
        return ConversationHandler.END
    page = context.user_data.get("pending_page", 0)
    total = len(pending)
    per_page = 5
    start = page * per_page
    end = min(start + per_page, total)
    if start >= total:
        page = 0
        start = 0
        end = min(per_page, total)
    context.user_data["pending_page"] = page
    context.user_data["pending_list"] = pending
    text = f"📋 *Активные заявки* (стр. {page+1}/{ (total-1)//per_page +1 if total else 1})\n"
    for i, p in enumerate(pending[start:end], start+1):
        text += f"\n{i}. {p['master']} – {p['amount']:.2f} руб. (ориг. {p.get('original_amount', 0):.2f})\n"
        text += f"   {p['text'][:50]}...\n"
    keyboard = []
    for i in range(start+1, end+1):
        keyboard.append([f"📌 Заявка #{i}"])
    nav = []
    if page > 0:
        nav.append("◀️ Назад")
    if end < total:
        nav.append("Вперёд ▶️")
    if nav:
        keyboard.append(nav)
    keyboard.append(["🔙 Назад", "🏠 Главное меню"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    return PENDING_SELECT

async def pending_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Назад", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=pending_kb())
        return ConversationHandler.END
    if text == "◀️ Назад":
        page = context.user_data.get("pending_page", 0) - 1
        context.user_data["pending_page"] = page
        await pending_list_start(update, context)
        return PENDING_SELECT
    if text == "Вперёд ▶️":
        page = context.user_data.get("pending_page", 0) + 1
        context.user_data["pending_page"] = page
        await pending_list_start(update, context)
        return PENDING_SELECT
    if text.startswith("📌 Заявка #"):
        try:
            num = int(text.split("#")[1].strip())
        except:
            await update.message.reply_text("Неверный номер.", reply_markup=pending_kb())
            return PENDING_SELECT
        pending_list = context.user_data.get("pending_list", [])
        if num < 1 or num > len(pending_list):
            await update.message.reply_text("Заявка не найдена.", reply_markup=pending_kb())
            return PENDING_SELECT
        pending_item = pending_list[num-1]
        if pending_item.get("status") != "pending":
            await update.message.reply_text("Заявка уже обработана.", reply_markup=pending_kb())
            return PENDING_SELECT
        context.user_data["selected_pending_idx"] = num-1
        await update.message.reply_text(
            f"Вы выбрали заявку #{num} от {pending_item['master']} на сумму {pending_item['amount']:.2f} руб.\nЧто хотите сделать?",
            reply_markup=pending_action_kb()
        )
        return PENDING_ACTION
    else:
        await update.message.reply_text("Используйте кнопки.", reply_markup=ReplyKeyboardMarkup([[f"📌 Заявка #{i+1}" for i in range(5)]], resize_keyboard=True))
        return PENDING_SELECT

async def pending_action_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 Отмена":
        await update.message.reply_text("Действие отменено.", reply_markup=pending_kb())
        context.user_data.pop("selected_pending_idx", None)
        return ConversationHandler.END
    idx = context.user_data.get("selected_pending_idx")
    if idx is None:
        await update.message.reply_text("Ошибка.", reply_markup=pending_kb())
        return ConversationHandler.END
    pending_list = context.user_data.get("pending_list", [])
    if idx >= len(pending_list):
        await update.message.reply_text("Заявка не найдена.", reply_markup=pending_kb())
        return ConversationHandler.END
    pending_item = pending_list[idx]
    real_idx = None
    for i, p in enumerate(data["pending"]):
        if p is pending_item:
            real_idx = i
            break
    if real_idx is None:
        await update.message.reply_text("Заявка не найдена в базе.", reply_markup=pending_kb())
        return ConversationHandler.END
    if pending_item.get("status") != "pending":
        await update.message.reply_text("Заявка уже обработана.", reply_markup=pending_kb())
        return ConversationHandler.END

    if text == "✅ Подтвердить":
        branch = get_master_branch(pending_item["master"])
        pending_item["status"] = "approved"
        data["incomes"].append({
            "master": pending_item["master"],
            "branch": branch,
            "amount": pending_item["amount"],
            "date": datetime.now().isoformat(),
            "text": pending_item["text"]
        })
        save_data(data)
        await update.message.reply_text(f"✅ Заявка подтверждена.", reply_markup=pending_kb())
        for uid, name in data["users"].items():
            if name == pending_item["master"]:
                try:
                    await context.bot.send_message(int(uid), f"✅ Ваш доход {pending_item['amount']:.2f} руб. подтверждён.")
                except:
                    pass
                break
        context.user_data.pop("selected_pending_idx", None)
        return ConversationHandler.END
    elif text == "✏️ Изменить сумму":
        await update.message.reply_text("Введите новую сумму для заявки:", reply_markup=cancel_kb())
        return CHANGE_AMOUNT
    elif text == "❌ Отклонить":
        pending_item["status"] = "rejected"
        save_data(data)
        await update.message.reply_text(f"❌ Заявка отклонена.", reply_markup=pending_kb())
        for uid, name in data["users"].items():
            if name == pending_item["master"]:
                try:
                    await context.bot.send_message(int(uid), f"❌ Ваш доход отклонён.")
                except:
                    pass
                break
        context.user_data.pop("selected_pending_idx", None)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Используйте кнопки.", reply_markup=pending_action_kb())
        return PENDING_ACTION

async def change_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=pending_kb())
        context.user_data.pop("selected_pending_idx", None)
        return ConversationHandler.END
    try:
        new_amount = float(text.strip())
        if new_amount < 0:
            await update.message.reply_text("Сумма не может быть отрицательной.", reply_markup=cancel_kb())
            return CHANGE_AMOUNT
        idx = context.user_data.get("selected_pending_idx")
        if idx is None:
            await update.message.reply_text("Ошибка.", reply_markup=pending_kb())
            return ConversationHandler.END
        pending_list = context.user_data.get("pending_list", [])
        if idx >= len(pending_list):
            await update.message.reply_text("Заявка не найдена.", reply_markup=pending_kb())
            return ConversationHandler.END
        pending_item = pending_list[idx]
        if pending_item.get("status") != "pending":
            await update.message.reply_text("Заявка уже обработана.", reply_markup=pending_kb())
            return ConversationHandler.END
        pending_item["amount"] = new_amount
        save_data(data)
        await update.message.reply_text(f"✅ Сумма заявки изменена на {new_amount:.2f} руб.", reply_markup=pending_kb())
        context.user_data.pop("selected_pending_idx", None)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Введите число.", reply_markup=cancel_kb())
        return CHANGE_AMOUNT

# --------------------------------------------
# ИСТОРИЯ ЗАЯВОК (с возможностью пересмотра)
# --------------------------------------------
async def pending_history_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return ConversationHandler.END
    history = [p for p in data["pending"] if p.get("status") != "pending"]
    if not history:
        await update.message.reply_text("История заявок пуста.", reply_markup=pending_kb())
        return ConversationHandler.END
    page = context.user_data.get("history_page", 0)
    total = len(history)
    per_page = 5
    start = page * per_page
    end = min(start + per_page, total)
    if start >= total:
        page = 0
        start = 0
        end = min(per_page, total)
    context.user_data["history_page"] = page
    context.user_data["history_list"] = history
    text = f"📜 *История заявок* (стр. {page+1}/{ (total-1)//per_page +1 if total else 1})\n"
    for i, p in enumerate(history[start:end], start+1):
        status = "✅ Подтверждена" if p.get("status") == "approved" else "❌ Отклонена"
        text += f"\n{i}. {p['master']} – {p['amount']:.2f} руб. ({status})\n"
        text += f"   {p['date'][:10]} {p['text'][:30]}...\n"
    keyboard = []
    for i in range(start+1, end+1):
        keyboard.append([f"📌 История #{i}"])
    nav = []
    if page > 0:
        nav.append("◀️ Назад")
    if end < total:
        nav.append("Вперёд ▶️")
    if nav:
        keyboard.append(nav)
    keyboard.append(["🔙 Назад", "🏠 Главное меню"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    return HISTORY_SELECT

async def history_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Назад", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=pending_kb())
        return ConversationHandler.END
    if text == "◀️ Назад":
        page = context.user_data.get("history_page", 0) - 1
        context.user_data["history_page"] = page
        await pending_history_start(update, context)
        return HISTORY_SELECT
    if text == "Вперёд ▶️":
        page = context.user_data.get("history_page", 0) + 1
        context.user_data["history_page"] = page
        await pending_history_start(update, context)
        return HISTORY_SELECT
    if text.startswith("📌 История #"):
        try:
            num = int(text.split("#")[1].strip())
        except:
            await update.message.reply_text("Неверный номер.", reply_markup=pending_kb())
            return HISTORY_SELECT
        history_list = context.user_data.get("history_list", [])
        if num < 1 or num > len(history_list):
            await update.message.reply_text("Заявка не найдена.", reply_markup=pending_kb())
            return HISTORY_SELECT
        context.user_data["selected_history_idx"] = num-1
        item = history_list[num-1]
        status_text = "подтверждена ✅" if item.get("status") == "approved" else "отклонена ❌"
        await update.message.reply_text(
            f"Вы выбрали заявку #{num} от {item['master']} на сумму {item['amount']:.2f} руб.\n"
            f"Статус: {status_text}\n"
            f"Текст: {item['text'][:100]}\n\n"
            "Что хотите сделать?",
            reply_markup=history_action_kb()
        )
        return HISTORY_ACTION
    else:
        await update.message.reply_text("Используйте кнопки.", reply_markup=ReplyKeyboardMarkup([[f"📌 История #{i+1}" for i in range(5)]], resize_keyboard=True))
        return HISTORY_SELECT

async def history_action_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 Назад":
        await update.message.reply_text("Возврат к списку истории.", reply_markup=pending_kb())
        context.user_data.pop("selected_history_idx", None)
        await pending_history_start(update, context)
        return HISTORY_SELECT
    idx = context.user_data.get("selected_history_idx")
    if idx is None:
        await update.message.reply_text("Ошибка.", reply_markup=pending_kb())
        return ConversationHandler.END
    history_list = context.user_data.get("history_list", [])
    if idx >= len(history_list):
        await update.message.reply_text("Заявка не найдена.", reply_markup=pending_kb())
        return ConversationHandler.END
    item = history_list[idx]
    real_idx = None
    for i, p in enumerate(data["pending"]):
        if p is item:
            real_idx = i
            break
    if real_idx is None:
        await update.message.reply_text("Заявка не найдена в базе.", reply_markup=pending_kb())
        return ConversationHandler.END

    if text == "✅ Подтвердить":
        if item.get("status") == "approved":
            await update.message.reply_text("Заявка уже подтверждена.", reply_markup=pending_kb())
            return ConversationHandler.END
        branch = get_master_branch(item["master"])
        item["status"] = "approved"
        data["incomes"].append({
            "master": item["master"],
            "branch": branch,
            "amount": item["amount"],
            "date": datetime.now().isoformat(),
            "text": item["text"]
        })
        save_data(data)
        await update.message.reply_text(f"✅ Заявка подтверждена и доход добавлен.", reply_markup=pending_kb())
        for uid, name in data["users"].items():
            if name == item["master"]:
                try:
                    await context.bot.send_message(int(uid), f"✅ Ваш доход {item['amount']:.2f} руб. подтверждён.")
                except:
                    pass
                break
        context.user_data.pop("selected_history_idx", None)
        return ConversationHandler.END
    elif text == "❌ Отклонить":
        if item.get("status") == "rejected":
            await update.message.reply_text("Заявка уже отклонена.", reply_markup=pending_kb())
            return ConversationHandler.END
        item["status"] = "rejected"
        save_data(data)
        await update.message.reply_text(f"❌ Заявка отклонена (доход, если был, остаётся в истории).", reply_markup=pending_kb())
        for uid, name in data["users"].items():
            if name == item["master"]:
                try:
                    await context.bot.send_message(int(uid), f"❌ Ваш доход отклонён (администратор изменил решение).")
                except:
                    pass
                break
        context.user_data.pop("selected_history_idx", None)
        return ConversationHandler.END
    elif text == "✏️ Изменить сумму":
        await update.message.reply_text("Введите новую сумму для этой заявки:", reply_markup=cancel_kb())
        return HISTORY_CHANGE_AMOUNT
    else:
        await update.message.reply_text("Используйте кнопки.", reply_markup=history_action_kb())
        return HISTORY_ACTION

async def history_change_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=pending_kb())
        context.user_data.pop("selected_history_idx", None)
        return ConversationHandler.END
    try:
        new_amount = float(text.strip())
        if new_amount < 0:
            await update.message.reply_text("Сумма не может быть отрицательной.", reply_markup=cancel_kb())
            return HISTORY_CHANGE_AMOUNT
        idx = context.user_data.get("selected_history_idx")
        if idx is None:
            await update.message.reply_text("Ошибка.", reply_markup=pending_kb())
            return ConversationHandler.END
        history_list = context.user_data.get("history_list", [])
        if idx >= len(history_list):
            await update.message.reply_text("Заявка не найдена.", reply_markup=pending_kb())
            return ConversationHandler.END
        item = history_list[idx]
        old_amount = item["amount"]
        item["amount"] = new_amount
        if item.get("status") == "approved":
            for inc in data["incomes"]:
                if inc.get("text") == item["text"] and inc.get("master") == item["master"]:
                    inc["amount"] = new_amount
                    break
        save_data(data)
        await update.message.reply_text(f"✅ Сумма заявки изменена с {old_amount:.2f} на {new_amount:.2f} руб.", reply_markup=pending_kb())
        context.user_data.pop("selected_history_idx", None)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Введите число.", reply_markup=cancel_kb())
        return HISTORY_CHANGE_AMOUNT

# --------------------------------------------
# СЧЕТА (балансы и выплаты)
# --------------------------------------------
async def accounts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return
    masters = data["masters"]
    if not masters:
        await update.message.reply_text("Нет мастеров.", reply_markup=get_main_keyboard(update.effective_user.id))
        return
    keyboard = [[m["name"]] for m in masters]
    keyboard.append(["🔙 Назад", "🏠 Главное меню"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите мастера для управления счётом:", reply_markup=reply_markup)
    return ACCOUNT_SELECT

async def account_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Назад", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    if text not in [m["name"] for m in data["masters"]]:
        await update.message.reply_text("Неизвестный мастер.", reply_markup=ReplyKeyboardMarkup([[m["name"]] for m in data["masters"]] + [["🔙 Назад", "🏠 Главное меню"]], resize_keyboard=True))
        return ACCOUNT_SELECT
    context.user_data["selected_account_master"] = text
    bal = get_balance(text)
    await update.message.reply_text(f"Мастер: {text}\n💰 Баланс: {bal:.2f} руб.\nВыберите действие:", reply_markup=account_action_kb())
    return ACCOUNT_ACTION

async def account_action_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    master = context.user_data.get("selected_account_master")
    if not master:
        await update.message.reply_text("Ошибка.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    if text == "🔙 Назад":
        await update.message.reply_text("Возврат к выбору мастера.", reply_markup=ReplyKeyboardMarkup([[m["name"]] for m in data["masters"]] + [["🔙 Назад", "🏠 Главное меню"]], resize_keyboard=True))
        return ACCOUNT_SELECT
    if text == "💸 Выплатить":
        bal = get_balance(master)
        await update.message.reply_text(f"Введите сумму для выплаты мастеру {master} (доступно {bal:.2f} руб.):", reply_markup=cancel_kb())
        return ACCOUNT_PAYMENT_AMOUNT
    if text == "📜 История выплат":
        pays = [p for p in data["payments"] if p.get("master") == master]
        if not pays:
            await update.message.reply_text(f"Нет выплат по мастеру {master}.", reply_markup=get_main_keyboard(update.effective_user.id))
        else:
            out = f"📜 История выплат для мастера {master}:\n"
            for p in pays[-10:]:
                out += f"{p['date'][:10]} – {p['amount']:.2f} руб. ({p.get('comment', 'без комментария')})\n"
            await update.message.reply_text(out, reply_markup=get_main_keyboard(update.effective_user.id))
        context.user_data.pop("selected_account_master", None)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Используйте кнопки.", reply_markup=account_action_kb())
        return ACCOUNT_ACTION

async def payment_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        context.user_data.pop("selected_account_master", None)
        return ConversationHandler.END
    try:
        amount = float(text.strip())
        if amount <= 0:
            await update.message.reply_text("Сумма должна быть положительной.", reply_markup=cancel_kb())
            return ACCOUNT_PAYMENT_AMOUNT
        master = context.user_data.get("selected_account_master")
        if not master:
            await update.message.reply_text("Ошибка.", reply_markup=get_main_keyboard(update.effective_user.id))
            return ConversationHandler.END
        bal = get_balance(master)
        if amount > bal:
            await update.message.reply_text(f"❌ Недостаточно средств. Баланс: {bal:.2f} руб.", reply_markup=cancel_kb())
            return ACCOUNT_PAYMENT_AMOUNT
        context.user_data["payment_amount"] = amount
        await update.message.reply_text("Введите комментарий (или отправьте /skip):", reply_markup=cancel_kb())
        return ACCOUNT_PAYMENT_COMMENT
    except ValueError:
        await update.message.reply_text("❌ Введите число.", reply_markup=cancel_kb())
        return ACCOUNT_PAYMENT_AMOUNT

async def payment_comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        context.user_data.pop("selected_account_master", None)
        context.user_data.pop("payment_amount", None)
        return ConversationHandler.END
    comment = text.strip()
    if comment.lower() == "/skip":
        comment = ""
    master = context.user_data.get("selected_account_master")
    amount = context.user_data.get("payment_amount")
    if not master or not amount:
        await update.message.reply_text("Ошибка.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    data["payments"].append({
        "master": master,
        "amount": amount,
        "date": datetime.now().isoformat(),
        "comment": comment
    })
    save_data(data)
    await update.message.reply_text(f"✅ Выплата {amount:.2f} руб. мастеру {master} выполнена.", reply_markup=get_main_keyboard(update.effective_user.id))
    for uid, name in data["users"].items():
        if name == master:
            try:
                await context.bot.send_message(int(uid), f"💰 Вам выплачено {amount:.2f} руб. (остаток: {get_balance(master):.2f} руб.)")
            except:
                pass
            break
    context.user_data.pop("selected_account_master", None)
    context.user_data.pop("payment_amount", None)
    return ConversationHandler.END

# --------------------------------------------
# ПРОСТОЙ РАСЧЁТ, ЭКСПОРТ CSV, ИЗМЕНЕНИЕ ПРОЦЕНТА
# --------------------------------------------
async def calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите текст с числами для расчёта (числа времени вида 12:30 игнорируются):", reply_markup=cancel_kb())
    return CALC_INPUT

async def calc_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    numbers = extract_numbers(text)
    if not numbers:
        await update.message.reply_text("Не найдено чисел (временные форматы игнорируются).", reply_markup=cancel_kb())
        return CALC_INPUT
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

async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return
    if not data["incomes"]:
        await update.message.reply_text("Нет данных для экспорта.", reply_markup=tools_kb())
        return
    try:
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(["Мастер", "Филиал", "Сумма", "Дата", "Текст"])
        for inc in data["incomes"]:
            writer.writerow([inc.get("master", ""), inc.get("branch", ""), inc["amount"], inc["date"], inc.get("text", "")])
        output.seek(0)
        await update.message.reply_document(
            document=output.getvalue().encode('utf-8-sig'),
            filename="incomes.csv",
            caption="📊 Экспорт доходов"
        )
    except Exception as e:
        await update.message.reply_text("❌ Не удалось создать файл экспорта.", reply_markup=tools_kb())

async def percent_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return ConversationHandler.END
    await update.message.reply_text("Введите новый процент удержания (число от 0 до 100):", reply_markup=cancel_kb())
    return PERCENT_INPUT

async def percent_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    try:
        val = float(text.strip())
        if 0 <= val <= 100:
            data["settings"]["deduction_percent"] = val
            save_data(data)
            await update.message.reply_text(f"✅ Процент удержания установлен на {val}%", reply_markup=get_main_keyboard(update.effective_user.id))
        else:
            await update.message.reply_text("❌ Введите число от 0 до 100.", reply_markup=cancel_kb())
            return PERCENT_INPUT
    except ValueError:
        await update.message.reply_text("❌ Введите число.", reply_markup=cancel_kb())
        return PERCENT_INPUT
    return ConversationHandler.END