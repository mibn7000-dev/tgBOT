import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

from database import db

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = '8538766694:AAFsOkPugOEEugvcCSEH161meRsb_PM7I44'
CHANNEL_ID = '-5081309106'  # Числовой ID канала, например: -1001234567890

# Состояния для ConversationHandler
WAITING_FOR_TEXT, WAITING_FOR_PHOTO, CONFIRMATION = range(3)


# ========== КЛАВИАТУРЫ ==========

def get_main_keyboard():
    """Главное меню бота"""
    keyboard = [
        ['📝 Создать задачу'],
        ['📋 Мои активные задачи'],
        ['✅ Закрыть задачу']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_cancel_keyboard():
    """Клавиатура для отмены"""
    return ReplyKeyboardMarkup([['❌ Отменить']], resize_keyboard=True)


def get_confirm_keyboard():
    """Клавиатура подтверждения"""
    return ReplyKeyboardMarkup([['✅ Подтвердить', '❌ Отменить']], resize_keyboard=True)


# ========== ОСНОВНЫЕ КОМАНДЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user

    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я бот для управления задачами вашей рабочей группы.\n"
        f"Используйте кнопки ниже для работы с задачами."
    )

    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню"""
    text = update.message.text

    if text == '📝 Создать задачу':
        await update.message.reply_text(
            "📝 Введите описание задачи:",
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_FOR_TEXT

    elif text == '📋 Мои активные задачи':
        await show_active_tasks(update, context)

    elif text == '✅ Закрыть задачу':
        await show_tasks_to_close(update, context)

    return ConversationHandler.END


# ========== СОЗДАНИЕ ЗАДАЧИ ==========

async def receive_task_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение текста задачи"""
    text = update.message.text

    if text == '❌ Отменить':
        await update.message.reply_text(
            "Создание задачи отменено.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

    # Сохраняем текст в context.user_data
    context.user_data['task_text'] = text

    await update.message.reply_text(
        "📸 Теперь отправьте фотографию для задачи (или нажмите '❌ Отменить' если фото не нужно):",
        reply_markup=get_cancel_keyboard()
    )
    return WAITING_FOR_PHOTO


async def receive_task_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение фото задачи"""
    if update.message.text == '❌ Отменить':
        # Пользователь решил не добавлять фото
        context.user_data['photo_id'] = None
        return await confirm_task(update, context)

    if update.message.photo:
        # Сохраняем file_id самой большой версии фото
        photo = update.message.photo[-1]
        context.user_data['photo_id'] = photo.file_id
        return await confirm_task(update, context)

    await update.message.reply_text(
        "Пожалуйста, отправьте фотографию или нажмите '❌ Отменить'",
        reply_markup=get_cancel_keyboard()
    )
    return WAITING_FOR_PHOTO


async def confirm_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение создания задачи"""
    task_text = context.user_data.get('task_text', 'Нет описания')
    has_photo = 'Да' if context.user_data.get('photo_id') else 'Нет'

    preview_text = (
        "📋 Предварительный просмотр задачи:\n\n"
        f"📝 Описание: {task_text}\n"
        f"📸 Фотография: {has_photo}\n\n"
        f"Создать задачу?"
    )

    if context.user_data.get('photo_id'):
        # Показываем фото с предпросмотром
        await update.message.reply_photo(
            photo=context.user_data['photo_id'],
            caption=preview_text,
            reply_markup=get_confirm_keyboard()
        )
    else:
        # Только текст
        await update.message.reply_text(
            preview_text,
            reply_markup=get_confirm_keyboard()
        )

    return CONFIRMATION


async def process_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения"""
    choice = update.message.text

    if choice == '❌ Отменить':
        await update.message.reply_text(
            "Создание задачи отменено.",
            reply_markup=get_main_keyboard(),
            reply_to_message_id=update.message.message_id
        )
        return ConversationHandler.END

    if choice == '✅ Подтвердить':
        # Создаем задачу в базе данных
        user = update.effective_user
        task_id = db.create_task(
            user_id=user.id,
            username=user.username or user.first_name,
            text=context.user_data.get('task_text'),
            photo_id=context.user_data.get('photo_id')
        )


        # Публикуем в канале
        channel_msg_id = await publish_to_channel(
            context=context,
            task_id=task_id,
            task_text=context.user_data.get('task_text'),
            photo_id=context.user_data.get('photo_id'),
            username=user.username or user.first_name
        )

        # Сохраняем ID сообщения в канале
        if channel_msg_id:
            db.update_channel_message_id(task_id, channel_msg_id)

        # Отправляем подтверждение пользователю
        success_text = (
            f"✅ Задача #{task_id} успешно создана!\n\n"
            f"📝 Описание: {context.user_data.get('task_text')}\n"
            f"📅 Создана: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"📊 Статус: В работе\n\n"
            f"Задача опубликована в рабочем канале."
        )

        await update.message.reply_text(
            success_text,
            reply_markup=get_main_keyboard()
        )

        # Очищаем временные данные
        context.user_data.clear()

        return ConversationHandler.END

    return CONFIRMATION


async def publish_to_channel(context: ContextTypes.DEFAULT_TYPE, task_id: int, task_text: str,
                             photo_id: str = None, username: str = "Неизвестный"):
    """Публикация задачи в канале"""
    try:
        caption = (
            f"📋 ЗАДАЧА #{task_id}\n"
            f"───────────────\n"
            f"👤 Автор: @{username}\n"
            f"📅 Создана: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"📊 Статус: 🔄 В РАБОТЕ\n"
            f"───────────────\n"
            f"📝 Описание:\n{task_text or 'Без описания'}\n"
            f"───────────────\n"
            f"#задача{task_id}"
        )

        if photo_id:
            message = await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo_id,
                caption=caption
            )
        else:
            message = await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=caption
            )

        return message.message_id

    except Exception as e:
        logger.error(f"Ошибка при публикации в канале: {e}")
        return None


# ========== ПОКАЗ АКТИВНЫХ ЗАДАЧ ==========

async def show_active_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать активные задачи пользователя"""
    user_id = update.effective_user.id
    tasks = db.get_active_tasks(user_id)

    if not tasks:
        await update.message.reply_text(
            "✅ У вас нет активных задач.",
            reply_markup=get_main_keyboard()
        )
        return

    response = "📋 Ваши активные задачи:\n\n"

    for task in tasks:
        response += f"#{task.id} - {task.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        if task.text:
            text_preview = task.text[:100] + "..." if len(task.text) > 100 else task.text
            response += f"📝 {text_preview}\n"
        response += f"Статус: {task.status}\n"
        response += "─" * 30 + "\n"

    await update.message.reply_text(
        response,
        reply_markup=get_main_keyboard()
    )


# ========== ЗАКРЫТИЕ ЗАДАЧ ==========

async def show_tasks_to_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать задачи для закрытия"""
    user_id = update.effective_user.id
    tasks = db.get_active_tasks(user_id)

    if not tasks:
        await update.message.reply_text(
            "У вас нет активных задач для закрытия.",
            reply_markup=get_main_keyboard()
        )
        return

    # Создаем инлайн-клавиатуру со списком задач
    keyboard = []
    for task in tasks:
        task_preview = task.text[:30] + "..." if task.text and len(
            task.text) > 30 else task.text or f"Задача #{task.id}"
        button_text = f"#{task.id}: {task_preview}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"close_{task.id}")])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])

    await update.message.reply_text(
        "Выберите задачу для закрытия:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на инлайн-кнопки"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "back_to_main":
        await query.edit_message_text(
            "Главное меню:",
            reply_markup=get_main_keyboard()
        )

    elif data.startswith("close_"):
        task_id = int(data.split("_")[1])
        task = db.get_task(task_id)

        if task:
            # Создаем клавиатуру подтверждения
            keyboard = [
                [
                    InlineKeyboardButton("✅ Да, закрыть", callback_data=f"confirm_close_{task_id}"),
                    InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_close")
                ]
            ]

            await query.edit_message_text(
                f"Вы уверены, что хотите закрыть задачу #{task_id}?\n\n"
                f"Описание: {task.text[:200] if task.text else 'Без описания'}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif data.startswith("confirm_close_"):
        task_id = int(data.split("_")[2])

        if db.close_task(task_id):
            # Обновляем сообщение в канале
            task = db.get_task(task_id)
            if task.channel_message_id:
                try:
                    # Редактируем подпись в канале
                    new_caption = (
                        f"📋 ЗАДАЧА #{task_id}\n"
                        f"───────────────\n"
                        f"👤 Автор: @{task.username}\n"
                        f"📅 Создана: {task.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                        f"📊 Статус: ✅ ЗАКРЫТА\n"
                        f"───────────────\n"
                        f"📝 Описание:\n{task.text or 'Без описания'}\n"
                        f"───────────────\n"
                        f"#задача{task_id} #закрыта"
                    )

                    if task.photo_id:
                        await context.bot.edit_message_caption(
                            chat_id=CHANNEL_ID,
                            message_id=task.channel_message_id,
                            caption=new_caption
                        )
                    else:
                        await context.bot.edit_message_text(
                            chat_id=CHANNEL_ID,
                            message_id=task.channel_message_id,
                            text=new_caption
                        )

                except Exception as e:
                    logger.error(f"Не удалось обновить сообщение в канале: {e}")

            await query.edit_message_text(
                f"✅ Задача #{task_id} успешно закрыта!",
                reply_markup=get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при закрытии задачи.",
                reply_markup=get_main_keyboard()
            )

    elif data == "cancel_close":
        await query.edit_message_text(
            "Закрытие задачи отменено.",
            reply_markup=get_main_keyboard()
        )


# ========== ОБРАБОТКА ОШИБОК ==========

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена любого действия"""
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=get_main_keyboard(),
        reply_to_message_id=update.message.message_id
    )
    context.user_data.clear()
    return ConversationHandler.END


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")

    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Произошла ошибка. Пожалуйста, попробуйте снова.",
                reply_markup=get_main_keyboard()
            )
    except:
        pass


# ========== ЗАПУСК БОТА ==========

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("Не установлен BOT_TOKEN в переменных окружения!")
        return

    if not CHANNEL_ID:
        logger.error("Не установлен CHANNEL_ID в переменных окружения!")
        return

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler для создания задач
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & filters.Regex('^(📝 Создать задачу)$'), handle_main_menu)
        ],
        states={
            WAITING_FOR_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_text),
                CommandHandler('cancel', cancel),
                CommandHandler('start', start)
            ],
            WAITING_FOR_PHOTO: [
                MessageHandler(filters.PHOTO, receive_task_photo),
                MessageHandler(filters.TEXT & filters.Regex('^(❌ Отменить)$'), receive_task_photo),
                CommandHandler('cancel', cancel),
                CommandHandler('start', start)
            ],
            CONFIRMATION: [
                MessageHandler(filters.TEXT & filters.Regex('^(✅ Подтвердить|❌ Отменить)$'), process_confirmation),
                CommandHandler('cancel', cancel),
                CommandHandler('start', start)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start)
        ],
        allow_reentry=True
    )

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Обработчик для других кнопок главного меню
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex('^(📋 Мои активные задачи|✅ Закрыть задачу)$'),
        handle_main_menu
    ))

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # Запуск бота
    logger.info("🤖 Бот запущен...")
    print("=" * 50)
    print("Бот успешно запущен!")
    print(f"ID канала: {CHANNEL_ID}")
    print("=" * 50)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()