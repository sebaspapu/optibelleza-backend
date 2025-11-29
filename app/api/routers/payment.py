from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
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
import stripe
from core.config import settings
from typing import List
from stripe import SignatureVerificationError

router = APIRouter(tags=['Payments'])

# Configurar Stripe con tu clave secreta
stripe.api_key = settings.stripe_secret_key
print(f"🔐 Stripe API key configurada: {stripe.api_key[:8]}********")


# URL base para redirecciones después del pago
YOUR_DOMAIN = "http://localhost:3000"  # Cambiado a 3001 para coincidir con tu frontend

@router.post("/api/checkout/create-session")
async def create_checkout_session(
    db: Session = Depends(get_db),
    current_user: dict = Depends(oauth2.get_current_user)
):
    try:
        print("\n=== Iniciando proceso de checkout ===")
        # Obtener el ID del usuario del token
        user_id = dict(current_user["token_data"])["id"]
        print(f"📱 Usuario ID: {user_id}")
        
        # Obtener los items del carrito del usuario
        cart_items = db.query(models_cart.Cart).filter(models_cart.Cart.owner_id == user_id).all()
        print(f"🛒 Items en carrito encontrados: {len(cart_items)}")

        if not cart_items:
            print("❌ Error: Carrito vacío")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay items en el carrito"
            )

        # Verificar que el usuario exista (fuente de verdad antes de usar user.email)
        user = db.query(models_user.User).filter(models_user.User.id == user_id).first()
        if not user:
            print(f"❌ Usuario no encontrado user_id={user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Transformar items del carrito al formato que Stripe necesita
        print("\n🔄 Transformando items para Stripe:")

        # Agrupar items por product_id para evitar line_items duplicados y tomar precio desde la tabla Shoes
        agg = {}
        for it in cart_items:
            pid = it.product_id
            if pid not in agg:
                agg[pid] = {"qty": 0, "row": it}
            agg[pid]["qty"] += it.product_quantity

        line_items = []
        for pid, info in agg.items():
            row = info["row"]
            total_qty = info["qty"]

            # Validar existencia del producto y obtener precio actual desde la tabla Shoes
            product = db.query(product_models.Shoes).filter(product_models.Shoes.id == pid).first()
            if not product:
                print(f"❌ Producto no encontrado en BD product_id={pid}")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {pid} not found")

            # Verificar stock mínimo
            try:
                stock = int(product.shoes_stock or 0)
            except Exception:
                stock = 0
            if stock < total_qty:
                print(f"❌ Stock insuficiente product_id={pid} stock={stock} requested={total_qty}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient stock for product {product.name}")

            print(f"  📦 Producto: {product.name}")
            print(f"     - Cantidad total: {total_qty}")
            print(f"     - Precio tomado de BD: ${product.price} USD")

            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product.name,
                        'images': [product.product_image] if product.product_image else [],
                    },
                    'unit_amount': int(product.price * 100),  # Stripe necesita el precio en centavos
                },
                'quantity': total_qty,
            })

        print(f"🔢 Line items finales para Stripe: {len(line_items)}")

        print("\n🔐 Configurando sesión de Stripe:")
        print(f"  💳 API Key configurada: {stripe.api_key[:10]}...")
        print(f"  🌐 Domain configurado: {YOUR_DOMAIN}")
        
        try:
            # Obtener el usuario
            user = db.query(models_user.User).filter(models_user.User.id == user_id).first()
            
            # Buscar o crear un cliente de Stripe para este usuario
            customers = stripe.Customer.list(email=user.email, limit=1)
            if customers.data:
                customer = customers.data[0]
                print(f"📋 Cliente existente encontrado: {customer.id}")
            else:
                # Crear nuevo cliente en Stripe
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.user_name,
                    metadata={
                        'user_id': str(user_id)
                    }
                )
                print(f"✨ Nuevo cliente creado: {customer.id}")
            
            # Crear la sesión de checkout en Stripe
            checkout_session = stripe.checkout.Session.create(
                customer=customer.id,  # Usar el ID del cliente en lugar de solo el email
                line_items=line_items,
                mode='payment',
                payment_method_types=['card'],
                payment_intent_data={
                    'setup_future_usage': 'off_session'  # Esto guardará la tarjeta para uso futuro
                },
                success_url=f"{YOUR_DOMAIN}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{YOUR_DOMAIN}/checkout/cancel",
                metadata={
                    'user_id': str(user_id)
                }
            )
            
            print(f"\n✅ Sesión de Stripe creada exitosamente")
            print(f"🔗 URL de checkout: {checkout_session.url}")
            return {"url": checkout_session.url}
            
        except stripe.StripeError as e:
            print(f"\n❌ Error de Stripe: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de Stripe: {str(e)}"
            )

    except HTTPException:
        # Re-raise HTTPException sin envolverla para preservar status codes (400/404 etc.)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/webhook")  # Cambiada la ruta a /webhook para simplicidad
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    print("\n=== Webhook de Stripe recibido ===")
    # Obtener el payload raw para verificar la firma
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    print("📨 Recibida notificación de Stripe")
    
    if not sig_header:
        print("❌ Error: No se encontró la firma de Stripe")
        raise HTTPException(status_code=400, detail="No Stripe signature found")
    
    try:
        # Construir el evento
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        print(f"✅ Firma verificada correctamente")
        print(f"📝 Tipo de evento: {event['type']}")
        
        # Manejar el evento de pago completado
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']

            # Usar la sesión `db` inyectada por Depends; no crear una nueva
            # Evitar `next(get_db())` porque genera una sesión distinta y puede provocar transacciones anidadas
            try:
                print("\n=== Verificando sesión de pago ===")

                # Obtener la sesión completa de Stripe para tener todos los detalles
                checkout_session = stripe.checkout.Session.retrieve(
                    session.id,
                    expand=['payment_intent', 'line_items']
                )
                print(f"💳 ID de sesión: {checkout_session.id}")
                print(f"💰 Estado del pago: {checkout_session.payment_status}")

                # Obtener el user_id de los metadatos
                user_id = int(checkout_session.metadata.get('user_id'))
                print(f"👤 Usuario ID: {user_id}")

                # Obtener los items del carrito
                cart_items = db.query(models_cart.Cart).filter(models_cart.Cart.owner_id == user_id).all()
                if not cart_items:
                    print("⚠️ Advertencia: No se encontraron items en el carrito")

                # Crear la orden
                print("\n=== Procesando pago completado ===")
                user = db.query(models_user.User).filter(models_user.User.id == user_id).first()
                if not user:
                    print("❌ Error: Usuario no encontrado")
                    raise HTTPException(status_code=404, detail="User not found")

                # Debug: mostrar elementos del carrito antes de procesar
                print(f"🛒 Cart items to process: {len(cart_items)}")
                for it in cart_items:
                    print(f"   - cart item product_id={it.product_id} name={it.product_name} qty={it.product_quantity} price={it.price}")

                # Procesar la creación de órdenes y actualización de stock en una transacción
                try:
                    # Si la sesión ya tiene una transacción activa, usamos begin_nested()
                    # para crear un SAVEPOINT y evitar el error de "A transaction is already begun"
                    if getattr(db, 'in_transaction', None) and db.in_transaction():
                        tx = db.begin_nested()
                    else:
                        tx = db.begin()
                    with tx:
                        # Recuperar payment_intent del checkout session expandido si existe
                        payment_intent_id = None
                        try:
                            payment_intent_id = checkout_session.payment_intent
                        except Exception:
                            try:
                                payment_intent_id = checkout_session.get('payment_intent')
                            except Exception:
                                payment_intent_id = None

                        for item in cart_items:
                            new_order = models_orders.Orders(
                                product_id=item.product_id,
                                owner_id=user_id,
                                owner_name=user.user_name,
                                owner_email=item.owner_email,
                                user_address=user.user_address,
                                product_name=item.product_name,
                                product_quantity=item.product_quantity,
                                price=item.price,
                                product_image=item.product_image,
                                size=item.size,
                                shoes_category=item.shoes_category,
                                order_status="confirmed",
                                payment="stripe",
                                shipping_method="standard"
                            )
                            db.add(new_order)
                            print(f"✅ Orden creada para {item.product_name}")

                            # Actualizar el stock con una operación UPDATE
                            db.query(product_models.Shoes).filter(product_models.Shoes.id == item.product_id).update({
                                "shoes_stock": product_models.Shoes.shoes_stock - item.product_quantity
                            }, synchronize_session=False)
                            print(f"📦 Stock programado para decremento product_id={item.product_id} by {item.product_quantity}")

                        # Eliminar todos los items del carrito del usuario en una sola operación
                        deleted = db.query(models_cart.Cart).filter(models_cart.Cart.owner_id == user_id).delete(synchronize_session=False)
                        print(f"🗑️  Carrito limpiado, rows deleted: {deleted}")

                    # Al salir del context la transacción se comitea automáticamente si no hubo excepciones
                    print("✅ Transaction committed: orders created and cart cleared")
                except Exception as te:
                    # Si ocurre cualquier error dentro de la transacción, se hace rollback automáticamente al salir del context
                    print(f"❌ Error durante transacción de ordenes: {te}")
                    raise

            except Exception as e:
                # Si algo falló, aseguramos rollback de la sesión inyectada
                try:
                    db.rollback()
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error procesando la orden: {str(e)}"
                )
            
        return {"status": "success"}
        
    except SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=f"Firma inválida: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )