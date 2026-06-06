"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: email_service.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Servicio de notificaciones por email (SMTP Gmail).
             Envía alertas al administrador cuando se crea un usuario demo.
FECHA CREACIÓN: 2026-05-12
ÚLTIMA MODIFICACIÓN: 2026-05-12
REF. TICKET: #FS-GCP-001
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.core.logger import forensic_log as logger


def send_demo_user_notification(user_email: str, full_name: str) -> bool:
    """
    Envía email de notificación a EMAIL_NOTIFICATIONS_TO cuando se crea un usuario demo.
    Retorna True si el envío fue exitoso, False en caso de error (no lanza excepción).
    """
    recipient = settings.EMAIL_NOTIFICATIONS_TO
    subject   = "Usuario Demo en la app"

    body_html = f"""
    <html>
    <head>
      <style>
        body  {{ font-family: Lato, Arial, sans-serif; color: #333; margin: 0; padding: 0; }}
        .wrap {{ max-width: 600px; margin: 40px auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }}
        .hdr  {{ background: #003DAD; padding: 24px 32px; }}
        .hdr h1 {{ color: #fff; margin: 0; font-size: 22px; }}
        .hdr span {{ color: #00B4D8; font-size: 14px; }}
        .body {{ padding: 28px 32px; }}
        .tag  {{ display: inline-block; background: #EBF4FF; color: #003DAD;
                 padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        td    {{ padding: 8px 12px; border: 1px solid #e8e8e8; font-size: 14px; }}
        td:first-child {{ background: #F5F7FA; font-weight: bold; width: 140px; }}
        .footer {{ background: #F5F7FA; padding: 14px 32px; font-size: 11px; color: #999; }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="hdr">
          <h1>FlowLexAI</h1>
          <span>Asistente Legislativo con IA · FlowState AI</span>
        </div>
        <div class="body">
          <p><span class="tag">NUEVO USUARIO DEMO</span></p>
          <p>Se ha registrado un nuevo usuario demo en la plataforma:</p>
          <table>
            <tr><td>Nombre</td><td>{full_name}</td></tr>
            <tr><td>Email</td><td>{user_email}</td></tr>
            <tr><td>Rol</td><td>readonly</td></tr>
            <tr><td>Tenant</td><td>Demo / Parlamento Principal</td></tr>
          </table>
          <p style="font-size:13px; color:#555;">
            Podés gestionar este usuario desde el panel de administración de FlowLexAI.
          </p>
        </div>
        <div class="footer">
          FlowState AI © 2026 · Gustavo Berton · Este es un mensaje automático, no responder.
        </div>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"FlowLexAI <{settings.EMAIL_USERNAME}>"
    msg["To"]      = recipient

    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.EMAIL_SMTP_HOST, settings.EMAIL_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_USERNAME, recipient, msg.as_string())

        logger.info(f"✅ [OK] Notificación demo enviada → {recipient} | usuario={user_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ [FAULT] SMTP auth fallida. Verificar EMAIL_USERNAME y EMAIL_PASSWORD en .env")
        return False
    except Exception as e:
        logger.error(f"❌ [FAULT] Error al enviar email demo: {e}")
        return False
