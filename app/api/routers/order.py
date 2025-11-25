from fastapi import FastAPI,Depends,HTTPException,APIRouter,status,Header
from sqlalchemy.orm import Session
from db.session import get_db

#modelos
import models.orders as models_orders
import models.product as product_models
import models.user as models_user
import models.cart as models_cart

#schemas
import schemas.order as schemas_order
import schemas.product as schemas_product
import schemas.user as schemas_user
import schemas.cart as schemas_cart


import core.oauth2 as oauth2
from infra.websocket import websocket_connections,websocket_connections_admin

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

# obtener todas las órdenes del sistema
@router.get("/api/order/all_order", tags=["Order Management"])
def get_all_orders(db: Session = Depends(get_db),current_user:dict=Depends(oauth2.get_current_user)):
    orders=db.query(models_orders.Orders).all()
    return orders

#Obtener todas las órdenes del usuario actual
@router.get("/api/order/current_user_all_order", tags=["Order Management"])
def get_current_user_orders(db: Session = Depends(get_db),current_user:dict=Depends(oauth2.get_current_user)):
    id=dict(current_user["token_data"])["id"]
    orders=db.query(models_orders.Orders).filter(models_orders.Orders.owner_id==id).all()
    return orders

# crear una nueva orden
@router.post("/api/order/add_order", tags=["Order Management"])
async def create_order(order:schemas_order.OrderAdd,db: Session = Depends(get_db),current_user:dict=Depends(oauth2.get_current_user),origin: str = Header(None)):
    id=dict(current_user["token_data"])["id"]
    user_email=db.query(models_user.User).filter(models_user.User.id==id).first()
    cart_items=db.query(models_cart.Cart).filter(models_cart.Cart.owner_id==id).all()
    products=db.query(product_models.Shoes).all()
    for cart_item in cart_items:
        # Create an order item with data from the cart item
        order_item = models_orders.Orders()
        for column in models_orders.Orders.__table__.columns:
            if column.name == "order_id":
                continue  # No copiar el ID

            if hasattr(cart_item, column.name):
                setattr(order_item, column.name, getattr(cart_item, column.name))
        
        # Manually set additional attributes for the order item
         # Set the order ID for the order item
        shoes_stock=db.query(product_models.Shoes).filter(product_models.Shoes.id==cart_item.product_id).first().shoes_stock
        if shoes_stock>=cart_item.product_quantity:
            db.query(product_models.Shoes).filter(product_models.Shoes.id==cart_item.product_id).update({"shoes_stock":shoes_stock-cart_item.product_quantity},synchronize_session=False)
        
        order_item.user_address = order.user_address
        order_item.payment = order.payment 
        order_item.shipping_method = order.shipping_method
        order_item.owner_id=id
        order_item.owner_name=user_email.user_name
        order_item.owner_email = user_email.email   # Set additional attribute
        
        db.add(order_item)
    db.query(models_cart.Cart).filter(models_cart.Cart.owner_id==id).delete(synchronize_session=False)
    
   
   
    db.commit()
    if str(origin)!="http://localhost:3000":
            await admin_signal()
    
    
    return order_item

# eliminar una orden
@router.get("/api/order/delete_order/{id}", tags=["Order Management"])
def delete_order_by_id(id:int,db: Session = Depends(get_db),current_user:dict=Depends(oauth2.get_current_user)):
     order_query=db.query(models_orders.Orders).filter(models_orders.Orders.order_id==id)
     order=order_query.first()
     if order==None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post with id:{id} not found")
    
     order_query.delete(synchronize_session=False)
     db.commit()
     return {"message":"deleted"}

# actualizar estado de una orden
@router.put("/api/order/update_status/{id}", tags=["Order Management"])
async def update_order_status_by_id(id:int,order_status:schemas_order.status_update,db: Session = Depends(get_db),current_user:dict=Depends(oauth2.get_current_user),origin: str = Header(None)):
    order_query=db.query(models_orders.Orders).filter(models_orders.Orders.order_id==id)
    order=order_query.first()
    if order==None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post with id:{id} not found")
    order_query.update(order_status.dict(),synchronize_session=False)
    db.commit()
    if str(origin)=="http://localhost:3000":
        # Iterate over connected WebSocket clients and send a message
        await client_signal()
    return {"data":"sucess"}