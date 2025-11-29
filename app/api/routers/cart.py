from fastapi import FastAPI,Depends,HTTPException,APIRouter,status,Header
from sqlalchemy.orm import Session
from db.session import get_db

#modelos
import models.product as product_models
import models.user as models
import models.cart as models_cart

#schemas
import schemas.cart as cart
import schemas.user as schemas
import schemas.product as schemas_product

import core.oauth2 as oauth2
from sqlalchemy.exc import IntegrityError
from infra.websocket import websocket_connections,websocket_connections_admin
from typing import List, Optional,Union

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

async def client_signal():
       for client in websocket_connections:
                            try:
                                
                                    await client.send_text("user login")
                                    
                            except Exception as e:
                    # Handle disconnected clients if needed
                                            print("Error",e)
                                            pass
       return

# añadir productos al carro
@router.post("/api/cart/add_item_cart",response_model=Union[cart.CartOut, cart.OutOfStockMessage], tags=["Shopping Cart"])
async def add_item_cart(shoes_id:cart.CartAdd,db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user),origin: str = Header(None)):
    print("\n=== Agregando producto al carrito ===")
    id=dict(current_user["token_data"])["id"]
    print(current_user["token_data"])
    print(f"👤 Usuario ID: {id}")
    user_email=db.query(models.User).filter(models.User.id==id).first()
    shoes=db.query(product_models.Shoes).filter(product_models.Shoes.id==shoes_id.id).first()
    print(f"📦 Producto ID: {shoes_id.id}")
    print(f"👞 Nombre del producto: {product_models.Shoes.name}")
    print(f"💰 Precio: ${product_models.Shoes.price}")
    print(f"📧 Email del usuario: {user_email.email}")
    cart_all=db.query(models_cart.Cart).filter(models_cart.Cart.owner_email==user_email.email).all()
    new_item=models_cart.Cart(product_id=shoes.id,size=shoes_id.size,product_quantity=shoes_id.product_quantity,owner_email=user_email.email,owner_id=id,product_image=shoes.product_image,price=shoes.price,product_name=shoes.name, shoes_category=shoes.shoes_category)
    shoes_stock=db.query(product_models.Shoes).filter(product_models.Shoes.id==shoes_id.id).first().shoes_stock
    try:
        if shoes_stock!=0:
                db.add(new_item)
                db.commit()
                db.refresh(new_item)
                if str(origin)=="http://localhost:3001":
                # Iterate over connected WebSocket clients and send a message
                   await client_signal()
                return new_item
        else:
               return {"status":"out of stock"}
    except IntegrityError as e:
        db.rollback()
        
        raise HTTPException(status_code=400, detail="Unique constraint violation: Item already exists")
    

# obtener todos los items del carrito
@router.get("/api/cart/all_cart_items",response_model=List[cart.CartOut], tags=["Shopping Cart"])
def get_all_item_cart(db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user),origin: str = Header(None)):
    id=dict(current_user["token_data"])["id"]
    print(current_user["token_data"])
    user_email=db.query(models.User).filter(models.User.id==id).first()
    cart_all=db.query(models_cart.Cart).filter(models_cart.Cart.owner_email==user_email.email).all()

    return cart_all

# Aumentar cantidad de un producto
@router.put("/api/cart/increase_cart_item", tags=["Shopping Cart"])
async def increase_item_cart(cart_increase:cart.CartIncresase,db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user),origin: str = Header(None)):
        id=dict(current_user["token_data"])["id"] 
        user_email=db.query(models.User).filter(models.User.id==id).first()
        cart_all=db.query(models_cart.Cart).filter(models_cart.Cart.owner_email==user_email.email, models_cart.Cart.product_name==cart_increase.product_name)
        shoes_stock=db.query(product_models.Shoes).filter(product_models.Shoes.name==cart_increase.product_name).first().shoes_stock
      
        if cart_all.first()==None:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post with id:{id} not found")
        cart_value=cart_all.first().product_quantity
        if shoes_stock<=cart_value:
             return {"status":"not in stock"}
             

        cart_all.update({"product_quantity":cart_value+1},synchronize_session=False)
        db.commit()
        if str(origin)=="http://localhost:3001":
         # Iterate over connected WebSocket clients and send a message
         await client_signal()
        return {"status":"ok"}

# disminuir cantidad de un producto
@router.put("/api/cart/decrease_cart_item", tags=["Shopping Cart"])
async def decrease_item_cart(cart_increase:cart.CartIncresase,db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user),origin: str = Header(None)):
        id=dict(current_user["token_data"])["id"] 
        user_email=db.query(models.User).filter(models.User.id==id).first()
        cart_all=db.query(models_cart.Cart).filter(models_cart.Cart.owner_email==user_email.email, models_cart.Cart.product_name==cart_increase.product_name)
        if cart_all.first()==None:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post with id:{id} not found")
        cart_value=cart_all.first().product_quantity
        cart_all.update({"product_quantity":cart_value-1},synchronize_session=False)
        db.commit()
        if str(origin)=="http://localhost:3001":
         # Iterate over connected WebSocket clients and send a message
         await client_signal()
        return {"status":"ok"}

# eliminar item del carrito
@router.get("/api/cart/delete_cart_item/{name}", tags=["Shopping Cart"])
async def delete_item_cart(name:str,db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user),origin: str = Header(None)):
        id=dict(current_user["token_data"])["id"] 
        user_email=db.query(models.User).filter(models.User.id==id).first()
        cart_all=db.query(models_cart.Cart).filter(models_cart.Cart.owner_email==user_email.email, models_cart.Cart.product_name==name)
        if cart_all.first()==None:
           raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"cart item with name:{name} not found")
        cart_all.delete(synchronize_session=False)
        db.commit()
        if str(origin)=="http://localhost:3001":
         # Iterate over connected WebSocket clients and send a message
         await client_signal()
        return {"message":"deleted"}

# actualizar talla de la montura
## queda pendiente cambiar el tipo de string 
@router.put("/api/cart/set_item_size", tags=["Shopping Cart"])
async def update_size_mount_in_cart(size:schemas_product.ProductSize,db: Session = Depends(get_db),current_user:int=Depends(oauth2.get_current_user),origin: str = Header(None)):  
       id=dict(current_user["token_data"])["id"] 
       user_email=db.query(models.User).filter(models.User.id==id).first()
       cart_all=db.query(models_cart.Cart).filter(models_cart.Cart.owner_email==user_email.email, models_cart.Cart.product_name==size.product_name)
       if cart_all.first()==None:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post with id:{id} not found")
       cart_all.update({"size":size.size},synchronize_session=False)
       db.commit()
       if str(origin)=="http://localhost:3001":
         # Iterate over connected WebSocket clients and send a message
         await client_signal()
       return {"message":"size set"}