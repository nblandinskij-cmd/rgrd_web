from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from .data_manager import is_admin, get_master_by_user

def get_main_keyboard(user_id):
    if is_admin(user_id):
        return ReplyKeyboardMarkup([
            ["🏢 Филиалы", "📊 Отчёты"],
            ["📋 Заявки", "💰 Счета"],
            ["🛠 Инструменты", "❓ Помощь"],
            ["🌐 Открыть приложение"]
        ], resize_keyboard=True)
    elif get_master_by_user(user_id):
        return ReplyKeyboardMarkup([
            ["📝 Запросить подтверждение"],
            ["📊 Моя статистика", "📊 Моя статистика за период"],
            ["💰 Мой баланс"],
            ["🧮 Простой расчёт"],
            ["📋 Прайс-лист"],
            ["🌐 Открыть приложение"],
            ["❓ Помощь"]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ["🔑 Активировать"],
            ["❓ Помощь"]
        ], resize_keyboard=True)

def cancel_kb():
    return ReplyKeyboardMarkup([["🔙 Отмена", "🏠 Главное меню"]], resize_keyboard=True)

def branch_management_kb():
    return ReplyKeyboardMarkup([
        ["📋 Список филиалов"],
        ["➕ Добавить филиал"],
        ["❌ Удалить филиал"],
        ["🔙 Назад", "🏠 Главное меню"]
    ], resize_keyboard=True)

def reports_kb():
    return ReplyKeyboardMarkup([
        ["📊 Общая статистика"],
        ["📊 Статистика по филиалу"],
        ["📊 Детальная статистика по мастерам"],
        ["🔙 Назад", "🏠 Главное меню"]
    ], resize_keyboard=True)

def tools_kb():
    return ReplyKeyboardMarkup([
        ["➕ Добавить мастера"],
        ["📋 Список мастеров"],
        ["🧮 Простой расчёт"],
        ["📋 Прайс-лист"],
        ["📤 Экспорт CSV"],
        ["⚙️ Изменить процент"],
        ["🔙 Назад", "🏠 Главное меню"]
    ], resize_keyboard=True)

def pending_kb():
    return ReplyKeyboardMarkup([
        ["📋 Активные заявки"],
        ["📜 История заявок"],
        ["🔙 Назад", "🏠 Главное меню"]
    ], resize_keyboard=True)

def yes_no_kb():
    return ReplyKeyboardMarkup([["✅ Да"], ["❌ Нет"]], resize_keyboard=True)

def account_action_kb():
    return ReplyKeyboardMarkup([
        ["💸 Выплатить"],
        ["📜 История выплат"],
        ["🔙 Назад"]
    ], resize_keyboard=True)

def pending_action_kb():
    return ReplyKeyboardMarkup([
        ["✅ Подтвердить"],
        ["✏️ Изменить сумму"],
        ["❌ Отклонить"],
        ["🔙 Отмена"]
    ], resize_keyboard=True)

def master_action_kb():
    return ReplyKeyboardMarkup([
        ["✏️ Переименовать"],
        ["❌ Удалить"],
        ["🔙 Отмена"]
    ], resize_keyboard=True)

def period_kb():
    return ReplyKeyboardMarkup([
        ["📅 Сегодня"],
        ["📅 Неделя"],
        ["📅 Месяц"],
        ["📅 Год"],
        ["📅 Вся история"],
        ["🔙 Назад", "🏠 Главное меню"]
    ], resize_keyboard=True)

def history_action_kb():
    return ReplyKeyboardMarkup([
        ["✅ Подтвердить"],
        ["❌ Отклонить"],
        ["✏️ Изменить сумму"],
        ["🔙 Назад"]
    ], resize_keyboard=True)

def webapp_inline_kb(webapp_url):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🌐 Открыть приложение", web_app=WebAppInfo(url=webapp_url))
    ]])