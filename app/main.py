from fastapi import FastAPI,Depends,HTTPException
from fastapi.params import Body

from db.session import engine, SessionLocal

import models.user as models
import schemas.user as schemas
import socketio as socketio

from sqlalchemy.orm import Session
from sqlalchemy import text

# Routers
from api.routers import auth

# Middleware setup
from middlewares.cors import setup_cors

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configurar middlewares
setup_cors(app)

# Registrar routers
app.include_router(auth.router)

print("hello")

@app.get("/")
def root():
    return {"message": "🚀 Optibelleza API is running successfully!"}







    
    