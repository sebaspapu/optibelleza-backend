from fastapi import FastAPI,Depends,HTTPException,APIRouter,status,Header
from sqlalchemy.orm import Session
from db.session import get_db
import models,core.oauth2
from sqlalchemy.exc import IntegrityError
from core.security import pwd_context
from typing import List
import schemas.user as schemas


from infra.websocket import websocket_connections,websocket_connections_admin
import websockets


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
@router.post("/api/auth/register,",response_model=schemas.UserOut)
async def create_post(users:schemas.UserCreate,db: Session= Depends(get_db),origin: str = Header(None)):
    hashed_password=pwd_context.hash(users.password)
    users.password=hashed_password
    try:
        new_user=models.User(**users.dict())
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(new_user,"+++++++++++++++++++++++++++++++++")

        if str(origin)!="http://localhost:3000":
            await admin_signal()
        return new_user
    
   
    except IntegrityError as e:
        # Handle the unique constraint violation error
          # Rollback the transaction to avoid database changes
        db.rollback()  # Rollback the transaction to avoid database changes
        raise HTTPException(status_code=400, detail="Unique constraint violation: User with the same unique field already exists.")
    