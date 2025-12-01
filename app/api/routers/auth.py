from fastapi import FastAPI,Depends,HTTPException,APIRouter,status,Header
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import user as models
from app.models import admin as models_admin
from app.core import security as utils
from app.core import oauth2
from sqlalchemy.exc import IntegrityError
from app.core.security import pwd_context
from typing import List
from app.schemas import user as schemas
from app.schemas import admin as schemas_admin

from passlib.context import CryptContext
from passlib.exc import UnknownHashError


from app.infra.websocket import websocket_connections,websocket_connections_admin
from app.core.config import settings, origin_matches_frontend
import websockets

user_dict={}

from sqlalchemy import select


router=APIRouter()
async def admin_signal():
       for client in websocket_connections_admin:
                            try:
                                
                                    await client.send_text("user login")
                                    
                            except Exception as e:
                    # Handle disconnected clients if needed
                                            print("Error",e)
                                            pass
       return

#@router.post("/users",response_model=schemas.UserOut)
@router.post("/api/auth/register",response_model=schemas.UserOut, tags=["Auth - User"])
async def create_user(users:schemas.UserCreate,db: Session= Depends(get_db),origin: str = Header(None)):
    hashed_password=pwd_context.hash(users.password)
    users.password=hashed_password
    try:
        new_user=models.User(**users.dict())
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(new_user,"+++++++++++++++++++++++++++++++++")

        if not origin_matches_frontend(origin):
            await admin_signal()
        return new_user
    
   
    except IntegrityError as e:
        # Handle the unique constraint violation error
          # Rollback the transaction to avoid database changes
        db.rollback()  # Rollback the transaction to avoid database changes
        raise HTTPException(status_code=400, detail="Unique constraint violation: User with the same unique field already exists.")


#@router.post("/login_user")
@router.post("/api/auth/login", tags=["Auth - User"])
async def login_user(
    user_cred: schemas.UserLogin,
    db: Session = Depends(get_db),
    origin: str = Header(None),
):
    print(str(origin))
    print(not origin_matches_frontend(origin))
   
    user_query = db.query(models.User).filter(models.User.email == user_cred.email)
    user = user_query.first()
   

    if not user:
        return  HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid credentials"
        )

    if not utils.verify(user_cred.password, user.password):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid credentials"
        )
    if user.id not in user_dict:
       user_dict[user.id]=1
    else:
           user_dict[user.id]+=1
    print(user_dict)
    user_query.update({"login_status": True}, synchronize_session=False)
    db.commit()
    
    if not origin_matches_frontend(origin):
        # Iterate over connected WebSocket clients and send a message
        
        await admin_signal()

    # Update login status in the database
   

    # Create an access token for the user
    access_token = oauth2.create_access_token(
        data={"user_id": user.id, "role": "user"}
    )
    
    # For testing password hashing for admin creation
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    print(pwd_context.hash("123456"))

    return {"token": access_token, "status": "ok"}


#@router.get("/current_user_info",response_model=schemas.UserInfo)
@router.get("/api/users/me",response_model=schemas.CurrentUserInfo, tags=["Auth - User"])
def get_current_user_info(current_user:int=Depends(oauth2.get_current_user)):
    # El usuario ya viene validado desde el middleware oauth2.get_current_user
    user = current_user["user"]
    return user

#login admin (v1)
#@router.post("/login_admin")
@router.post("/api/auth/admin", tags=["Auth - Admin"])
def login_admin(admin_cred: schemas_admin.AdminLogin, db: Session = Depends(get_db)):
    admin_query = db.query(models_admin.Admin).filter(models_admin.Admin.email == admin_cred.email)
    admin = admin_query.first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="invalid credentials"
        )

    try:
        if not utils.verify(admin_cred.password, admin.password):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="invalid credentials"
            )
    except UnknownHashError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password format or unsupported hash."
        )

    access_token = oauth2.create_access_token(data={"user_id": admin.id, "role": "admin"})
    db.commit()

    return {"token": access_token, "status": "ok"}

#logout user
@router.get("/docs/api/logout_user", tags=["Auth - User"])
async def logout_user(db: Session = Depends(get_db),current_user:dict=Depends(oauth2.get_current_user),origin: str = Header(None)):
   
    user_id=dict(current_user["token_data"])["id"]
    
    user_query=db.query(models.User).filter(models.User.id==user_id)
    user_query.update({"login_status":False}, synchronize_session=False)
       
    db.commit()
        
       
       
    
    if not origin_matches_frontend(origin):
        await admin_signal()
    
    return {"status":"ok"}