import requests
from app.core.config import settings
import logging

logger = logging.getLogger("uvicorn.error")

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


def send_sale_notification(to_email: str, subject: str, html_content: str) -> bool:
    """Enviar un correo usando la API de SendGrid.

    Retorna True si el envío fue aceptado (202) o False en caso contrario.
    """
    api_key = settings.sendgrid_api_key
    if not api_key:
        logger.warning("SendGrid API key no configurada; no se enviará correo.")
        return False

    from_email = settings.sendgrid_from_email or settings.notification_email or "no-reply@optibelleza.local"

    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject,
            }
        ],
        "from": {"email": from_email, "name": "Optibelleza"},
        "content": [
            {"type": "text/html", "value": html_content}
        ]
    }

    # Si estamos en modo sandbox (pruebas), agregar la configuración para que SendGrid no entregue el correo
    if getattr(settings, 'sendgrid_sandbox_mode', False):
        payload["mail_settings"] = {"sandbox_mode": {"enable": True}}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(SENDGRID_API_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 202):
            logger.info(f"Notificación de venta enviada a {to_email}")
            return True
        else:
            logger.error(f"Error enviando correo SendGrid: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción enviando correo SendGrid: {e}")
        return False

def send_order_notification(orders: list) -> bool:
    """
    Envía una única notificación con todas las órdenes creadas para una compra.
    """
    if not orders:
        return False

    buyer_name = orders[0].owner_name
    total_cents = sum([(o.paid_amount or 0) for o in orders])
    total_dollars = total_cents / 100

    # Crear lista HTML
    items_html = "<ul>"
    for o in orders:
        items_html += (
            f"<li>{o.product_name} — qty: {o.product_quantity} "
            f"— pagado: ${(o.paid_amount or 0)/100:.2f}</li>"
        )
    items_html += "</ul>"

    subject = f"Nueva venta en Optibelleza — Total: ${total_dollars:.2f}"

    html = (
        f"<p>Cliente: <strong>{buyer_name}</strong></p>"
        f"<p>Total de la compra: <strong>${total_dollars:.2f}</strong></p>"
        f"<h4>Productos comprados:</h4>{items_html}"
    )

    recipient = settings.notification_email or "diana@example.com"

    return send_sale_notification(recipient, subject, html)