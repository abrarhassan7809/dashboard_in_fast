from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP, Boolean
from database_config.db_creation import Base


class Register(Base):
    __tablename__ = 'register'

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, unique=False, nullable=False)
    last_name = Column(String, unique=False, nullable=False)
    email = Column(String, unique=False, nullable=False)
    password = Column(String, unique=False, nullable=False)
    confirm_password = Column(String, unique=False, nullable=False)

    created_at = Column(TIMESTAMP, nullable=False)
    is_admin = Column(Boolean, default=False)
