from pydantic import BaseModel, EmailStr
from datetime import datetime
from fastapi import UploadFile,File,Form
from typing import Optional,List

class OrderAdd(BaseModel):
    payment:str
    user_address:str
    shipping_method:str

class status_update(BaseModel):
    order_status:str