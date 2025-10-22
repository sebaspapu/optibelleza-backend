from fastapi import FastAPI,Depends,HTTPException,APIRouter,status,UploadFile,File,Header,Query
from sqlalchemy.orm import Session
from db.session import get_db
import models.product as models
import core.oauth2 as oauth2
import schemas.product as schemas
from core.config import settings
from typing import List, Optional
import base64
from infra.websocket import websocket_connections,websocket_connections_admin

import boto3
AWS_ACCESS_KEY = "AKIAVRUVPPBZ74UNU3OZ"  # Replace with the actual Access Key ID
  # Replace with the actual Secret Access Key
AWS_REGION = "ap-south-1"
S3_BUCKET_NAME = "abhishek-jain-786"

# Create an S3 client
s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=settings.aws_secret_key, region_name=AWS_REGION)

router=APIRouter()
s3_bucket_name="abhishek-jain-786"
async def client_signal():
       for client in websocket_connections:
                            try:
                                
                                    await client.send_text("user login")
                                    
                            except Exception as e:
                    # Handle disconnected clients if needed
                                            print("Error",e)
                                            pass
       return

#CRUD

# CREATE PRODUCT MOUNTS
@router.post("/api/products")
async def create_product_mounts(product_mounts:schemas.ProductMountsCreate,db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user),origin: str = Header(None)):
    new_product_mounts=models.Product(**product_mounts.dict())

    db.add(new_product_mounts)
    
    db.commit()
    db.refresh(new_product_mounts)
    if str(origin)=="http://localhost:3000":
        # Iterate over connected WebSocket clients and send a message
        
        await client_signal()
    return new_product_mounts

# GET ALL PRODUCT MOUNTS (MORE COMPLETE WITH FILTERS)
@router.get("/api/products", response_model=List[schemas.ProductMounts])
def get_products_mounts(
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    type: Optional[str] = Query(None, description="Filtrar por tipo (Featured/New)"),
    limit: int = Query(10, ge=1, le=100, description="Límite de resultados por página"),
    skip: int = Query(0, ge=0, description="Offset de resultados"),
):
    query = db.query(models.Product)
    if category:
        query = query.filter(models.Product.product_mounts_category.ilike(f"%{category}%"))
    if type:
        query = query.filter(models.Product.product_mounts_type == type.capitalize())
    
    products = query.offset(skip).limit(limit).all()
    return products

# GET TYPE=FEATURED
@router.get("/api/featured_product_mounts", response_model=List[schemas.ProductMounts])
def read(db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user)):
     
     
    product_mounts_list = db.query(models.Product).filter(models.Product.product_mounts_type=="Featured").all()

   
    # Prepare a dictionary with all the required fields
    
    

    return product_mounts_list

# GET TYPE=NEW
@router.get("/api/new_product_mounts", response_model=List[schemas.ProductMounts])
def read(db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user)):
     
     
    product_mounts_list = db.query(models.Product).filter(models.Product.product_mounts_type=="New").all()

   
    # Prepare a dictionary with all the required fields
    
    

    return product_mounts_list