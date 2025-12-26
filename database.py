from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import Config

Base = declarative_base()


class Task(Base):
    """Модель задачи в базе данных"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String(20), default='в работе')
    text = Column(Text, nullable=True)
    photo_id = Column(String(255), nullable=True)
    channel_message_id = Column(Integer, nullable=True)
    username = Column(String(100), nullable=True)


class Database:
    def __init__(self):
        self.engine = create_engine(Config.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def create_task(self, user_id, username, text=None, photo_id=None):
        """Создание новой задачи"""
        task = Task(
            user_id=user_id,
            username=username,
            text=text,
            photo_id=photo_id
        )
        self.session.add(task)
        self.session.commit()
        return task.id

    def get_active_tasks(self, user_id=None):
        """Получение активных задач"""
        query = self.session.query(Task).filter(Task.status == 'в работе')
        if user_id:
            query = query.filter(Task.user_id == user_id)
        return query.order_by(Task.id).all()

    def get_task(self, task_id):
        """Получение задачи по ID"""
        return self.session.query(Task).filter(Task.id == task_id).first()

    def close_task(self, task_id):
        """Закрытие задачи"""
        task = self.get_task(task_id)
        if task:
            task.status = 'закрыта'
            self.session.commit()
            return True
        return False

    def update_channel_message_id(self, task_id, message_id):
        """Обновление ID сообщения в канале"""
        task = self.get_task(task_id)
        if task:
            task.channel_message_id = message_id
            self.session.commit()
            return True
        return False


# Создаем глобальный экземпляр БД
db = Database()