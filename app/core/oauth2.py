import jwt
from datetime import datetime,timedelta
from db.session import get_db
from fastapi import Depends,status,HTTPException
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from db.session import get_db
import schemas.user as schemas
import models.user as models

from typing import Dict,Any

from sqlalchemy import select
from core.config import settings
#oauth2_scheme= OAuth2PasswordBearer(tokenUrl='login_admin')
oauth2_scheme = HTTPBearer()

target_endpoint = '/login_admin'

# Function to check if an endpoint is present in the app



  
SECREAT_KEY = settings.secret_key
ALGORITHM = settings.algorithm
print(oauth2_scheme)
ACCESS_TOKEN_EXPIRE_MINUTES=5

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECREAT_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str,credintials_exception):
        try:
           payload = jwt.decode(token, SECREAT_KEY, algorithms=[ALGORITHM])
        except Exception as e:
             print(e) 
             raise HTTPException(status_code=403, detail=f"error: {e}")
       
        role:str=payload.get("role")
        id:str=payload.get("user_id")
        print(id,role)
        if id is None or role is None:
            raise credintials_exception
        token_data=schemas.Token_data(id=id,role=role)
      
        
        return token_data

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credintials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials  # 🔹 Ahora viene en el header
    token_data = verify_access_token(token, credintials_exception)
   
    user = db.query(models.User).filter(models.User.id == token_data.id).first()
    if not user:
        raise credintials_exception

    return {"user": user, "token_data": token_data}

