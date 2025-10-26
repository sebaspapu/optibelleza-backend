from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    user_name:str
    email:EmailStr
    password:str

class UserOut(BaseModel):
    id:int
    email:EmailStr
    class Config:
        from_attributes=True

class UserInfo(BaseModel):
    id:int
    user_name:str
    email:EmailStr
    user_address:str
    user_phone_no:str
    login_status:bool
    online_status:bool
    created_at:datetime
    class Config:
        from_attributes=True

class UserLogin(BaseModel):
    email:EmailStr
    password:str

class Token(BaseModel):
    access_token:str
    token_type:str
    
class Token_data(BaseModel):
    id:int
    role:str

class CurrentUserInfo(BaseModel):
    
    user_name:str
    email:EmailStr
    user_address:str
    user_phone_no:str 
   
    class Config:
        from_attributes=True 