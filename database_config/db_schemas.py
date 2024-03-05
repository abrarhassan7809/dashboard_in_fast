from pydantic import BaseModel
from typing import Optional, List


# ----------create user------------
class Register(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str

    class Config:
        orm_mode = True
        schema_extra = {
            'example': {
                'first_name': 'test',
                'last_name': 'test',
                'email': 'test@gmail.com',
                'password': 'test1@',
                'confirm_password': 'test1@'
            }
        }


class GetUser(BaseModel):
    email: str
    password: str

    class Config:
        orm_mode = True


class UpdateUser(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None

    class Config:
        orm_mode = True


# ----------token data------------
class Token(BaseModel):
    access_token: str
    token_type: str

    class Config:
        orm_mode = True


class TokenData(BaseModel):
    email: str

    class Config:
        orm_mode = True
