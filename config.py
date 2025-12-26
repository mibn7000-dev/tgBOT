import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Токен бота от @BotFather

    BOT_TOKEN = "8538766694:AAFsOkPugOEEugvcCSEH161meRsb_PM7I44"
    #BOT_TOKEN = os.getenv("BOT_TOKEN")

    # ID канала (например, @my_channel или -1001234567890)
    #CHANNEL_ID = os.getenv("CHANNEL_ID")
    CHANNEL_ID = "-1003576936542"

    # Настройки базы данных
    DATABASE_URL = os.getenv("DATABASE_URL",
                             "sqlite:///tasks.db")  # Для PostgreSQL: postgresql://user:pass@localhost/dbname

    # Состояния FSM (Finite State Machine)
    STATE_TEXT, STATE_PHOTO, STATE_CONFIRM = range(3)