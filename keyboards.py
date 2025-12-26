from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu():
    """Главное меню бота"""
    keyboard = [
        ['📝 Задача'],
        ['📋 Список активных задач'],
        ['✅ Закрытие задачи']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def task_type_menu():
    """Меню выбора типа контента для задачи"""
    keyboard = [
        ['📝 Добавить текст', '🖼️ Добавить фото'],
        ['📝✏️ Текст + фото', '🔙 Назад']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def cancel_button():
    """Кнопка отмены"""
    return ReplyKeyboardMarkup([['❌ Отменить']], resize_keyboard=True, one_time_keyboard=True)


def tasks_list_keyboard(tasks):
    """Инлайн-клавиатура со списком задач для закрытия"""
    keyboard = []
    for task in tasks:
        # Обрезаем текст для кнопки
        text_preview = task.text[:30] + "..." if task.text and len(task.text) > 30 else task.text or "Без текста"
        button_text = f"#{task.id} - {text_preview}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"task_{task.id}")])

    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])

    return InlineKeyboardMarkup(keyboard)


def confirm_close_keyboard(task_id):
    """Клавиатура подтверждения закрытия задачи"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, закрыть", callback_data=f"confirm_close_{task_id}"),
            InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_close")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)