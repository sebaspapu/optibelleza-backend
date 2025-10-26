from fastapi import FastAPI,Depends,HTTPException,APIRouter,status,UploadFile,File,Header,Query
from sqlalchemy.orm import Session
from db.session import get_db
import models.product as product_models
import models.cart as cart_models
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

# GET ALL PRODUCT MOUNTS (MORE COMPLETE WITH FILTERS)
@router.get("/api/products", response_model=List[schemas.ProductMounts])
def get_products_mounts_all(
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    type: Optional[str] = Query(None, description="Filtrar por tipo (Featured/New)"),
    limit: int = Query(10, ge=1, le=100, description="Límite de resultados por página"),
    skip: int = Query(0, ge=0, description="Offset de resultados"),
):
    query = db.query(product_models.Product)
    if category:
        query = query.filter(product_models.Product.product_mounts_category.ilike(f"%{category}%"))
    if type:
        query = query.filter(product_models.Product.product_mounts_type == type.capitalize())
    
    products = query.offset(skip).limit(limit).all()
    return products

# GET TYPE=FEATURED (OPTIONAL)
@router.get("/api/featured_product_mounts", response_model=List[schemas.ProductMounts])
def read(db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user)):
     
    product_mounts_list = db.query(product_models.Product).filter(product_models.Product.product_mounts_type=="Featured").all()

    # Prepare a dictionary with all the required fields
    return product_mounts_list

# GET TYPE=NEW (OPTIONAL)
@router.get("/api/new_product_mounts", response_model=List[schemas.ProductMounts])
def read(db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user)):
     
    product_mounts_list = db.query(product_models.Product).filter(product_models.Product.product_mounts_type=="New").all()
   
    # Prepare a dictionary with all the required fields
    return product_mounts_list

# GET A PRODUCT MOUNTS BY ID
#@router.get("/get_post/{id}",response_model=schemas.Shoes)
@router.get("/api/products/{id}",response_model=schemas.ProductMounts)
def get_product_mount_by_id(id:int,db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user)):
    #posts=db.execute(text("SELECT * FROM POSTS WHERE id=:id"),{"id":id})
    product_mount_by_id=db.query(product_models.Product).filter(product_models.Product.id==id).first()
    if product_mount_by_id==None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"Montura con id: {id}, no fue encontrada")
    return product_mount_by_id

# CREATE PRODUCT MOUNTS
@router.post("/api/admin/products")
async def create_product_mounts(product_mounts:schemas.ProductMountsCreate,db: Session = Depends(get_db),current_user:int=Depends(oauth2.verify_admin),origin: str = Header(None)):
    new_product_mounts=product_models.Product(**product_mounts.dict())

    db.add(new_product_mounts)
    
    db.commit()
    db.refresh(new_product_mounts)
    if str(origin)=="http://localhost:3000":
        # Iterate over connected WebSocket clients and send a message
        
        await client_signal()
    return new_product_mounts

# UPDATE A PRODUCT MOUNTS BY ID
#@router.put("/updateshoes/{id}")
@router.put("/api/admin/products/{id}")
async def update_product_mount_by_id(id:int,post:schemas.ProductMountsUpdate,db: Session = Depends(get_db),current_user:int=Depends(oauth2.verify_admin),origin: str = Header(None)):
    product_query=db.query(product_models.Product).filter(product_models.Product.id==id)
    cart_query=db.query(cart_models.Cart).filter(cart_models.Cart.product_id==id)
    product = product_query.first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con id: {id} no encontrado"
        )
    
    # Actualiza nombre en carrito si existe
    if cart_query.first() is not None:
        cart_query.update({"product_name": post.name}, synchronize_session=False)

    # Actualiza el producto
    product_query.update(post.dict(), synchronize_session=False)
    db.commit()
    
    # Notifica vía WebSocket si es origen local
    if str(origin)=="http://localhost:3000":
        # Iterate over connected WebSocket clients and send a message
        await client_signal()

    return {"data":"Producto actualizado exitosamente"}

# DELETE A PRODUCT MOUNTS BY ID
#@router.get("/delete_shoes/{id}")
@router.delete("/api/admin/products/{id}")
async def delete_product_mount_by_id(id:int,db: Session = Depends(get_db),current_user:int=Depends(oauth2.verify_admin),origin: str = Header(None)):
    
    product_query = db.query(product_models.Product).filter(product_models.Product.id == id)
    product = product_query.first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con id {id} no encontrado"
        )
    
    product_query.delete(synchronize_session=False)
    db.commit()

    if str(origin)=="http://localhost:3000":
        # Iterate over connected WebSocket clients and send a message
        
        await client_signal()
    return {"message":"Producto eliminado exitosamente"}