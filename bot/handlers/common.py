from telegram import Update, ContextTypes
from telegram.ext import ConversationHandler
from ..data_manager import data, save_data, is_admin, get_master_by_user
from ..keyboards import get_main_keyboard, cancel_kb
from ..config import ADMIN_PASSWORD

REG_NAME = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.clear()
    text = "🌟 Добро пожаловать в ArtRegardFinance!\n\n"
    if is_admin(user_id):
        text += "Вы вошли как администратор."
    elif get_master_by_user(user_id):
        text += f"Вы вошли как мастер {get_master_by_user(user_id)}."
    else:
        text += "Вы не зарегистрированы. Нажмите «Активировать» для начала работы."
    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        text = ("📖 Справка (администратор)\n\n"
                "🏢 Филиалы – управление филиалами\n"
                "📊 Отчёты – статистика\n"
                "📋 Заявки – активные заявки и история\n"
                "💰 Счета – балансы и выплаты\n"
                "🛠 Инструменты – управление мастерами, расчёт, экспорт, настройки\n"
                "🌐 Открыть приложение – веб-интерфейс")
    else:
        text = ("📖 Справка (мастер)\n\n"
                "📝 Запросить подтверждение – отправить доход на проверку\n"
                "📊 Моя статистика – посмотреть свои доходы\n"
                "📊 Моя статистика за период – выбор периода\n"
                "💰 Мой баланс – посмотреть текущий баланс\n"
                "🧮 Простой расчёт – быстрый расчёт без сохранения\n"
                "📋 Прайс-лист – актуальные цены\n"
                "🌐 Открыть приложение – веб-интерфейс")
    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id))

async def become_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_PASSWORD:
        await update.message.reply_text("❌ Функция отключена.")
        return
    code = " ".join(context.args).strip()
    if code == ADMIN_PASSWORD:
        user_id = update.effective_user.id
        if user_id not in data.get("admins", []):
            data.setdefault("admins", []).append(user_id)
            save_data(data)
            await update.message.reply_text("✅ Вы стали администратором! Нажмите /start.")
        else:
            await update.message.reply_text("Вы уже администратор.")
    else:
        await update.message.reply_text("❌ Неверный код.")

async def activate_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id) or get_master_by_user(user_id):
        await update.message.reply_text("Вы уже зарегистрированы.", reply_markup=get_main_keyboard(user_id))
        return ConversationHandler.END
    await update.message.reply_text("Введите имя мастера:", reply_markup=cancel_kb())
    return REG_NAME

async def activate_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ("🔙 Отмена", "🏠 Главное меню"):
        await update.message.reply_text("Отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END
    name = text.strip()
    if not name:
        await update.message.reply_text("Имя не может быть пустым.", reply_markup=cancel_kb())
        return REG_NAME
    if name not in [m["name"] for m in data["masters"]]:
        await update.message.reply_text(f"Мастер '{name}' не найден.", reply_markup=cancel_kb())
        return REG_NAME
    user_id = update.effective_user.id
    if any(m == name and int(u) != user_id for u, m in data["users"].items()):
        await update.message.reply_text(f"Имя '{name}' уже занято.", reply_markup=cancel_kb())
        return REG_NAME
    data["users"][str(user_id)] = name
    save_data(data)
    await update.message.reply_text(f"✅ Вы зарегистрированы как мастер '{name}'.", reply_markup=get_main_keyboard(user_id))
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(update.effective_user.id))
    return ConversationHandler.END