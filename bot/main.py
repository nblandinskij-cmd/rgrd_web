#!/usr/bin/env python3
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from .config import TOKEN, WEBHOOK_URL, PORT
from .handlers import common, admin, master, webapp
from .handlers.common import REG_NAME, activate_start, activate_name, cancel, start, help_command, become_admin

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("become_admin", become_admin))
    app.add_handler(CommandHandler("app", webapp.webapp_button))

    # Активация
    activate_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔑 Активировать$"), activate_start)],
        states={REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, activate_name)]},
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    )
    app.add_handler(activate_conv)

    # Здесь нужно зарегистрировать все ConversationHandler из admin.py и master.py
    # Например:
    # app.add_handler(ConversationHandler(...)) для филиалов, мастеров, заявок, счетов и т.д.
    # Я приведу пример для филиалов и заявок, остальные по аналогии.

    # --- Пример: филиалы (список, добавление, удаление) ---
    from .handlers.admin import (list_branches_start, branch_stats_select,
                                 add_branch_start, add_branch_name,
                                 remove_branch_start, remove_branch_select, remove_branch_confirm)
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Список филиалов$"), list_branches_start)],
        states={10: [MessageHandler(filters.TEXT & ~filters.COMMAND, branch_stats_select)]},  # state = 10
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Добавить филиал$"), add_branch_start)],
        states={11: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_branch_name)]},
        fallbacks=[MessageHandler(filters.Regex("^(🔙 Отмена|🏠 Главное меню)$"), cancel)],
        allow_reentry=True
    ))
    # ... и т.д.

    # Основной обработчик меню
    async def handle_menu(update, context):
        from .handlers.common import start, help_command
        from .handlers.admin import branches_menu, reports_menu, tools_menu, pending_menu, add_master_start, list_masters_start, calc_start, export_csv, percent_start
        from .handlers.master import request_income, my_stats, my_balance, master_stats_period_start
        from .handlers.webapp import webapp_button
        from ..keyboards import get_main_keyboard
        from ..data_manager import is_admin, get_master_by_user
        from ..prices import PRICES

        user_id = update.effective_user.id
        text = update.message.text

        # Прайс-лист (обработка категорий)
        if context.user_data.get('viewing_price'):
            if text in PRICES:
                from ..prices import PRICES
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

        if text == "📋 Прайс-лист":
            context.user_data['viewing_price'] = True
            await update.message.reply_text("Выберите категорию:", reply_markup=ReplyKeyboardMarkup([[cat] for cat in PRICES.keys()] + [["🔙 Назад"]], resize_keyboard=True))
            return

        if text == "🌐 Открыть приложение":
            await webapp_button(update, context)
            return

        # Админ-функции
        if is_admin_user:
            if text == "🏢 Филиалы":
                await branches_menu(update, context)
            elif text == "📊 Отчёты":
                await reports_menu(update, context)
            elif text == "📋 Заявки":
                await pending_menu(update, context)
            elif text == "💰 Счета":
                await accounts_menu(update, context)  # нужно импортировать
            elif text == "🛠 Инструменты":
                await tools_menu(update, context)
            elif text == "❓ Помощь":
                await help_command(update, context)
            elif text == "➕ Добавить мастера":
                await add_master_start(update, context)
            elif text == "📋 Список мастеров":
                await list_masters_start(update, context)
            elif text == "🧮 Простой расчёт":
                await calc_start(update, context)
            elif text == "📤 Экспорт CSV":
                await export_csv(update, context)
            elif text == "⚙️ Изменить процент":
                await percent_start(update, context)
            else:
                await update.message.reply_text("Неизвестная команда.", reply_markup=get_main_keyboard(user_id))
            return

        # Мастер-функции
        if is_registered:
            if text == "📝 Запросить подтверждение":
                await request_income(update, context)
            elif text == "📊 Моя статистика":
                await my_stats(update, context)
            elif text == "📊 Моя статистика за период":
                await master_stats_period_start(update, context)
            elif text == "💰 Мой баланс":
                await my_balance(update, context)
            elif text == "🧮 Простой расчёт":
                await calc_start(update, context)
            elif text == "❓ Помощь":
                await help_command(update, context)
            else:
                await update.message.reply_text("Неизвестная команда.", reply_markup=get_main_keyboard(user_id))
            return

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    # Запуск
    if WEBHOOK_URL:
        app.run_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=f"{WEBHOOK_URL}/{TOKEN}")
    else:
        app.run_polling()

if __name__ == "__main__":
    main()