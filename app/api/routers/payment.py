
import logging
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

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=['Payments'])

# Configurar Stripe con tu clave secreta
# CRITERIO: SDK oficial de Stripe integrado y configurado (clave API)
stripe.api_key = settings.stripe_secret_key
logger.info(f"🔐 Stripe API key configurada: {stripe.api_key[:8]}********")


# URL base para redirecciones después del pago
YOUR_DOMAIN = "http://localhost:3000"  # Cambiado a 3001 para coincidir con tu frontend

@router.post("/api/checkout/create-session")
async def create_checkout_session(
    db: Session = Depends(get_db),
    current_user: dict = Depends(oauth2.get_current_user)
):
    try:
        logger.info("=== Iniciando proceso de checkout ===")
        # CRITERIO: Endpoint que genera la sesión de checkout usando los items del carrito en BD
        # Obtener el ID del usuario del token
        user_id = dict(current_user["token_data"])["id"]
        logger.info(f"📱 Usuario ID: {user_id}")
        
        # Obtener los items del carrito del usuario
        cart_items = db.query(models_cart.Cart).filter(models_cart.Cart.owner_id == user_id).all()
        logger.info(f"🛒 Items en carrito encontrados: {len(cart_items)}")

        if not cart_items:
            logger.warning("❌ Error: Carrito vacío")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay items en el carrito"
            )

        # Verificar que el usuario exista (fuente de verdad antes de usar user.email)
        user = db.query(models_user.User).filter(models_user.User.id == user_id).first()
        if not user:
            logger.warning(f"❌ Usuario no encontrado user_id={user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Transformar items del carrito al formato que Stripe necesita
        # CRITERIO: Se construyen los `line_items` desde la BD (precio tomado de `Shoes`) y se agrupan por producto
        logger.info("🔄 Transformando items para Stripe:")

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
                # CRITERIO: Manejo de flujo de negocio — producto inexistente devuelve 404
                logger.warning(f"❌ Producto no encontrado en BD product_id={pid}")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {pid} not found")

            # Verificar stock mínimo
            try:
                stock = int(product.shoes_stock or 0)
            except Exception:
                stock = 0
            if stock < total_qty:
                # CRITERIO: Manejo de flujo de negocio — stock insuficiente devuelve 400
                logger.warning(f"❌ Stock insuficiente product_id={pid} stock={stock} requested={total_qty}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient stock for product {product.name}")

            logger.info(f"  📦 Producto: {product.name}")
            logger.info(f"     - Cantidad total: {total_qty}")
            logger.info(f"     - Precio tomado de BD: ${product.price} USD")

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

        # CRITERIO: `line_items` ya están consolidados y validados para enviar a Stripe
        logger.info(f"🔢 Line items finales para Stripe: {len(line_items)}")

        logger.info("🔐 Configurando sesión de Stripe:")
        logger.info(f"  💳 API Key configurada: {stripe.api_key[:10]}...")
        logger.info(f"  🌐 Domain configurado: {YOUR_DOMAIN}")
        
        try:
            # Obtener el usuario
            user = db.query(models_user.User).filter(models_user.User.id == user_id).first()
            
            # Buscar o crear un cliente de Stripe para este usuario
            customers = stripe.Customer.list(email=user.email, limit=1)
            if customers.data:
                customer = customers.data[0]
                logger.info(f"📋 Cliente existente encontrado: {customer.id}")
            else:
                # Crear nuevo cliente en Stripe
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.user_name,
                    metadata={
                        'user_id': str(user_id)
                    }
                )
                logger.info(f"✨ Nuevo cliente creado: {customer.id}")
            
            # CRITERIO: success_url y cancel_url están configurados en la creación de la sesión de Stripe
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
            
            logger.info("✅ Sesión de Stripe creada exitosamente")
            logger.info(f"🔗 URL de checkout: {checkout_session.url}")
            # CRITERIO: El endpoint devuelve la URL de la sesión de pago al cliente
            return {"url": checkout_session.url}
            
        except stripe.StripeError as e:
            # CRITERIO: Manejo de errores de la API de Stripe — se captura y se devuelve 500
            logger.error(f"❌ Error de Stripe: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de Stripe: {str(e)}"
            )

    except HTTPException:
        logger.warning("HTTPException lanzada en checkout: será propagada")
        raise
    except Exception as e:
        logger.error(f"Error inesperado en checkout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/webhook")  # Cambiada la ruta a /webhook para simplicidad
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    logger.info("=== Webhook de Stripe recibido ===")
    # Obtener el payload raw para verificar la firma
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    logger.info("📨 Recibida notificación de Stripe")
    
    if not sig_header:
        logger.warning("❌ Error: No se encontró la firma de Stripe")
        raise HTTPException(status_code=400, detail="No Stripe signature found")
    
    try:
        # Construir el evento
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        logger.info(f"✅ Firma verificada correctamente")
        logger.info(f"📝 Tipo de evento: {event['type']}")
        
        # Manejar el evento de pago completado
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']

            # Usar la sesión `db` inyectada por Depends; no crear una nueva
            # Evitar `next(get_db())` porque genera una sesión distinta y puede provocar transacciones anidadas
            try:
                logger.info("=== Verificando sesión de pago ===")

                # Obtener la sesión completa de Stripe para tener todos los detalles
                checkout_session = stripe.checkout.Session.retrieve(
                    session.id,
                    expand=['payment_intent', 'line_items']
                )
                logger.info(f"💳 ID de sesión: {checkout_session.id}")
                logger.info(f"💰 Estado del pago: {checkout_session.payment_status}")

                # Obtener el user_id de los metadatos
                user_id = int(checkout_session.metadata.get('user_id'))
                logger.info(f"👤 Usuario ID: {user_id}")

                # Obtener los items del carrito
                cart_items = db.query(models_cart.Cart).filter(models_cart.Cart.owner_id == user_id).all()
                if not cart_items:
                    logger.warning("⚠️ Advertencia: No se encontraron items en el carrito")

                # Crear la orden
                logger.info("=== Procesando pago completado ===")
                user = db.query(models_user.User).filter(models_user.User.id == user_id).first()
                if not user:
                    logger.warning("❌ Error: Usuario no encontrado")
                    raise HTTPException(status_code=404, detail="User not found")

                # Debug: mostrar elementos del carrito antes de procesar
                logger.info(f"🛒 Cart items to process: {len(cart_items)}")
                for it in cart_items:
                    logger.info(f"   - cart item product_id={it.product_id} name={it.product_name} qty={it.product_quantity} price={it.price}")

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
                            logger.info(f"✅ Orden creada para {item.product_name}")

                            # Actualizar el stock con una operación UPDATE
                            db.query(product_models.Shoes).filter(product_models.Shoes.id == item.product_id).update({
                                "shoes_stock": product_models.Shoes.shoes_stock - item.product_quantity
                            }, synchronize_session=False)
                            logger.info(f"📦 Stock programado para decremento product_id={item.product_id} by {item.product_quantity}")

                        # Eliminar todos los items del carrito del usuario en una sola operación
                        deleted = db.query(models_cart.Cart).filter(models_cart.Cart.owner_id == user_id).delete(synchronize_session=False)
                        logger.info(f"🗑️  Carrito limpiado, rows deleted: {deleted}")

                    # Al salir del context la transacción se comitea automáticamente si no hubo excepciones
                    logger.info("✅ Transaction committed: orders created and cart cleared")
                except Exception as te:
                    # Si ocurre cualquier error dentro de la transacción, se hace rollback automáticamente al salir del context
                    logger.error(f"❌ Error durante transacción de ordenes: {te}")
                    raise

            except Exception as e:
                # Si algo falló, aseguramos rollback de la sesión inyectada
                try:
                    db.rollback()
                except Exception:
                    pass
                logger.error(f"Error procesando la orden: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error procesando la orden: {str(e)}"
                )
            
        return {"status": "success"}
        
    except SignatureVerificationError as e:
        logger.warning(f"Firma inválida: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Firma inválida: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado en webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )