#!/usr/bin/env python3
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from .config import TOKEN, WEBHOOK_URL, PORT
from .handlers import common, admin, master, webapp
from .handlers.common import REG_NAME, activate_start, activate_name, cancel, start, help_command, become_admin
from .handlers.admin import (
    # Филиалы
    branches_menu, list_branches_start, branch_stats_select,
    add_branch_start, add_branch_name,
    remove_branch_start, remove_branch_select, remove_branch_confirm,
    # Инструменты
    tools_menu, add_master_start, add_master_branch, add_master_name,
    list_masters_start, master_list_nav, master_action_choose,
    edit_master_name, delete_master_confirm,
    # Отчёты
    reports_menu, overall_stats, branch_stats_menu, stats_branch_select,
    detailed_stats_start, detailed_stats_period,
    rating_menu, rating_period, rating_nav,
    # Заявки
    pending_menu, pending_list_start, pending_select, pending_action_handle, change_amount_input,
    pending_history_start, history_select, history_action_handle, history_change_amount,
    # Счета
    accounts_menu, account_select, account_action_handle,
    payment_amount_input, payment_comment_input,
    # Инструменты общие
    calc_start, calc_input, export_csv, percent_start, percent_input
)
from .handlers.master import (
    request_income, income_request_input, my_stats, my_balance,
    master_stats_period_start, master_stats_period
)
from .handlers.webapp import webapp_button
from .keyboards import get_main_keyboard
from .data_manager import is_admin, get_master_by_user
from .prices import PRICES
from telegram import ReplyKeyboardMarkup

# Состояния из admin.py (импортируем их для регистрации)
# Они уже определены в admin.py как переменные, можно импортировать
from .handlers.admin import (
    ADD_BRANCH_NAME, DEL_BRANCH_SELECT, DEL_BRANCH_CONFIRM, BRANCH_STATS_SELECT,
    ADD_MASTER_BRANCH, ADD_MASTER_NAME, MASTER_LIST_NAV, MASTER_ACTION_CHOOSE,
    EDIT_MASTER_NAME, DELETE_MASTER_CONFIRM,
    STATS_BRANCH_SELECT, RATING_PERIOD, RATING_NAV, DETAILED_STATS_PERIOD,
    PENDING_SELECT, PENDING_ACTION, CHANGE_AMOUNT,
    HISTORY_SELECT, HISTORY_ACTION, HISTORY_CHANGE_AMOUNT,
    ACCOUNT_SELECT, ACCOUNT_ACTION, ACCOUNT_PAYMENT_AMOUNT, ACCOUNT_PAYMENT_COMMENT,
    CALC_INPUT, PERCENT_INPUT
)

def main():
    app = Application.builder().token(TOKEN).build()

    # --- Базовые команды ---
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("become_admin", become_admin))
    app.add_handler(CommandHandler("app", webapp_button))

    # --- Активация (регистрация мастера) ---
    activate_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔑 Активировать$"), activate_start)],
        states={REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, activate_name)]},
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    )
    app.add_handler(activate_conv)

    # --- Филиалы ---
    # Список филиалов (просмотр статистики)
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Список филиалов$"), list_branches_start)],
        states={BRANCH_STATS_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, branch_stats_select)]},
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))
    # Добавить филиал
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Добавить филиал$"), add_branch_start)],
        states={ADD_BRANCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_branch_name)]},
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))
    # Удалить филиал
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❌ Удалить филиал$"), remove_branch_start)],
        states={
            DEL_BRANCH_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_branch_select)],
            DEL_BRANCH_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_branch_confirm)]
        },
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))

    # --- Инструменты (администратор) ---
    # Добавить мастера
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Добавить мастера$"), add_master_start)],
        states={
            ADD_MASTER_BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_master_branch)],
            ADD_MASTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_master_name)]
        },
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))
    # Список мастеров (с действиями: переименовать, удалить)
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Список мастеров$"), list_masters_start)],
        states={
            MASTER_LIST_NAV: [MessageHandler(filters.TEXT & ~filters.COMMAND, master_list_nav)],
            MASTER_ACTION_CHOOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, master_action_choose)],
            EDIT_MASTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_master_name)],
            DELETE_MASTER_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_master_confirm)]
        },
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))
    # Простой расчёт (используется и мастерами, и админами)
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🧮 Простой расчёт$"), calc_start)],
        states={CALC_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_input)]},
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))
    # Экспорт CSV – отдельная команда без состояния
    app.add_handler(MessageHandler(filters.Regex("^📤 Экспорт CSV$"), export_csv))
    # Изменить процент
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⚙️ Изменить процент$"), percent_start)],
        states={PERCENT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, percent_input)]},
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))

    # --- Отчёты ---
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📊 Статистика по филиалу$"), branch_stats_menu)],
        states={STATS_BRANCH_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, stats_branch_select)]},
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📊 Детальная статистика по мастерам$"), detailed_stats_start)],
        states={DETAILED_STATS_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, detailed_stats_period)]},
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("rating", rating_menu)],
        states={
            RATING_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, rating_period)],
            RATING_NAV: [MessageHandler(filters.TEXT & ~filters.COMMAND, rating_nav)]
        },
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))

    # --- Заявки (активные) ---
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Активные заявки$"), pending_list_start)],
        states={
            PENDING_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pending_select)],
            PENDING_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, pending_action_handle)],
            CHANGE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_amount_input)]
        },
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))

    # --- История заявок (с возможностью пересмотра) ---
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📜 История заявок$"), pending_history_start)],
        states={
            HISTORY_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, history_select)],
            HISTORY_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, history_action_handle)],
            HISTORY_CHANGE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, history_change_amount)]
        },
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))

    # --- Счета (балансы и выплаты) ---
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💰 Счета$"), accounts_menu)],
        states={
            ACCOUNT_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_select)],
            ACCOUNT_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_action_handle)],
            ACCOUNT_PAYMENT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_amount_input)],
            ACCOUNT_PAYMENT_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_comment_input)]
        },
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))

    # --- Мастер: запрос дохода ---
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Запросить подтверждение$"), request_income)],
        states={70: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_request_input)]},  # INCOME_REQUEST = 70
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))

    # --- Мастер: статистика за период ---
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📊 Моя статистика за период$"), master_stats_period_start)],
        states={80: [MessageHandler(filters.TEXT & ~filters.COMMAND, master_stats_period)]},  # MASTER_STATS_PERIOD = 80
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))

    # --- Основной обработчик текстовых сообщений (меню) ---
    async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text

        # Обработка просмотра прайс-листа (категории)
        if context.user_data.get('viewing_price'):
            if text in PRICES:
                cat = text
                services = PRICES[cat]
                lines = [f"📋 *{cat}*"]
                for s, p in services.items():
                    if isinstance(p, list):
                        p_str = f"{p[0]} / {p[1]} / {p[2]}"
                    elif isinstance(p, dict):
                        p_str = f"{p['base']} (ед., +{p['extra_row']} за доп. ряд)"
                    else:
                        p_str = str(p)
                    lines.append(f"▪ {s} — {p_str}")
                await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))
                context.user_data['viewing_price'] = False
                return
            elif text == "🔙 Назад":
                context.user_data['viewing_price'] = False
                await update.message.reply_text("Возврат.", reply_markup=get_main_keyboard(user_id))
                return
            else:
                await update.message.reply_text("Выберите категорию.", reply_markup=ReplyKeyboardMarkup([[cat] for cat in PRICES.keys()] + [["🔙 Назад"]], resize_keyboard=True))
                return

        if text == "🏠 Главное меню":
            await start(update, context)
            return

        is_admin_user = is_admin(user_id)
        is_registered = bool(get_master_by_user(user_id))

        if not is_admin_user and not is_registered:
            if text == "🔑 Активировать":
                await activate_start(update, context)
                return
            if text == "❓ Помощь":
                await help_command(update, context)
                return
            await update.message.reply_text("Неизвестная команда.", reply_markup=get_main_keyboard(user_id))
            return

        # Прайс-лист
        if text == "📋 Прайс-лист":
            context.user_data['viewing_price'] = True
            await update.message.reply_text("Выберите категорию:", reply_markup=ReplyKeyboardMarkup([[cat] for cat in PRICES.keys()] + [["🔙 Назад"]], resize_keyboard=True))
            return

        # WebApp
        if text == "🌐 Открыть приложение":
            await webapp_button(update, context)
            return

        # Администратор
        if is_admin_user:
            if text == "🏢 Филиалы":
                await branches_menu(update, context)
            elif text == "📊 Отчёты":
                await reports_menu(update, context)
            elif text == "📋 Заявки":
                await pending_menu(update, context)
            elif text == "💰 Счета":
                await accounts_menu(update, context)
            elif text == "🛠 Инструменты":
                await tools_menu(update, context)
            elif text == "❓ Помощь":
                await help_command(update, context)
            elif text == "📊 Общая статистика":
                await overall_stats(update, context)
            # Другие админ-функции уже обрабатываются через ConversationHandler
            else:
                await update.message.reply_text("Неизвестная команда.", reply_markup=get_main_keyboard(user_id))
            return

        # Мастер
        if is_registered:
            if text == "📝 Запросить подтверждение":
                await request_income(update, context)
            elif text == "📊 Моя статистика":
                await my_stats(update, context)
            elif text == "💰 Мой баланс":
                await my_balance(update, context)
            elif text == "🧮 Простой расчёт":
                await calc_start(update, context)
            elif text == "❓ Помощь":
                await help_command(update, context)
            else:
                await update.message.reply_text("Неизвестная команда.", reply_markup=get_main_keyboard(user_id))
            return

        await update.message.reply_text("Неизвестная команда.", reply_markup=get_main_keyboard(user_id))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    # Запуск
    if WEBHOOK_URL:
        app.run_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=f"{WEBHOOK_URL}/{TOKEN}")
    else:
        app.run_polling()

if __name__ == "__main__":
    main()