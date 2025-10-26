from pydantic import BaseModel, EmailStr
from datetime import datetime

class AdminLogin(BaseModel):
    email:EmailStr
    password:str