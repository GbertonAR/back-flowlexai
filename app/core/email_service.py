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
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.core.logger import forensic_log as logger


def _send_email(subject: str, body_html: str) -> bool:
    """Envía un email HTML al destinatario configurado en EMAIL_NOTIFICATIONS_TO."""
    recipient = settings.EMAIL_NOTIFICATIONS_TO
    if not all([settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD, settings.EMAIL_SMTP_HOST, recipient]):
        logger.warning("⚠️ [WORKFLOW] Email no configurado — verificar EMAIL_* en Azure App Settings.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"FlowLexAI <{settings.EMAIL_USERNAME}>"
    msg["To"]      = recipient
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        import ssl as _ssl
        ctx = _ssl.create_default_context()
        with smtplib.SMTP(settings.EMAIL_SMTP_HOST, settings.EMAIL_PORT) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_USERNAME, recipient, msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ [FAULT] SMTP auth fallida. Verificar EMAIL_USERNAME y EMAIL_PASSWORD.")
        return False
    except Exception as e:
        logger.error(f"❌ [FAULT] Error enviando email: {e}")
        return False


def send_login_notification(user_email: str, full_name: str, role: str, tenant_id: int) -> bool:
    """Notifica al administrador cuando un usuario se loguea en el sistema."""
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    body_html = f"""
    <html><head>
      <style>
        body {{ font-family: Lato, Arial, sans-serif; color: #333; margin: 0; padding: 0; }}
        .wrap {{ max-width: 600px; margin: 40px auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }}
        .hdr {{ background: #003DAD; padding: 24px 32px; }}
        .hdr h1 {{ color: #fff; margin: 0; font-size: 22px; }}
        .hdr span {{ color: #00B4D8; font-size: 14px; }}
        .body {{ padding: 28px 32px; }}
        .tag {{ display: inline-block; background: #E8F5E9; color: #2E7D32;
                padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        td {{ padding: 8px 12px; border: 1px solid #e8e8e8; font-size: 14px; }}
        td:first-child {{ background: #F5F7FA; font-weight: bold; width: 140px; }}
        .footer {{ background: #F5F7FA; padding: 14px 32px; font-size: 11px; color: #999; }}
      </style>
    </head><body>
      <div class="wrap">
        <div class="hdr">
          <h1>FlowLexAI</h1>
          <span>Asistente Legislativo con IA · FlowState AI</span>
        </div>
        <div class="body">
          <p><span class="tag">✅ NUEVO LOGIN</span></p>
          <p>Un usuario acaba de ingresar al sistema:</p>
          <table>
            <tr><td>Nombre</td><td>{full_name}</td></tr>
            <tr><td>Email</td><td>{user_email}</td></tr>
            <tr><td>Rol</td><td>{role}</td></tr>
            <tr><td>Tenant ID</td><td>{tenant_id}</td></tr>
            <tr><td>Timestamp</td><td>{ts}</td></tr>
          </table>
        </div>
        <div class="footer">FlowState AI © 2026 · Gustavo Berton · Mensaje automático.</div>
      </div>
    </body></html>
    """
    ok = _send_email(f"[FlowLexAI] Login: {full_name} ({role})", body_html)
    if ok:
        logger.info(f"✅ [OK] Notificación login enviada → {settings.EMAIL_NOTIFICATIONS_TO} | usuario={user_email}")
    return ok


def send_demo_user_notification(user_email: str, full_name: str) -> bool:
    """Notifica cuando se registra un usuario demo."""
    body_html = f"""
    <html><head>
      <style>
        body {{ font-family: Lato, Arial, sans-serif; color: #333; margin: 0; padding: 0; }}
        .wrap {{ max-width: 600px; margin: 40px auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }}
        .hdr {{ background: #003DAD; padding: 24px 32px; }}
        .hdr h1 {{ color: #fff; margin: 0; font-size: 22px; }}
        .hdr span {{ color: #00B4D8; font-size: 14px; }}
        .body {{ padding: 28px 32px; }}
        .tag {{ display: inline-block; background: #EBF4FF; color: #003DAD;
                padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        td {{ padding: 8px 12px; border: 1px solid #e8e8e8; font-size: 14px; }}
        td:first-child {{ background: #F5F7FA; font-weight: bold; width: 140px; }}
        .footer {{ background: #F5F7FA; padding: 14px 32px; font-size: 11px; color: #999; }}
      </style>
    </head><body>
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
        </div>
        <div class="footer">FlowState AI © 2026 · Gustavo Berton · Mensaje automático.</div>
      </div>
    </body></html>
    """
    ok = _send_email("Usuario Demo en la app", body_html)
    if ok:
        logger.info(f"✅ [OK] Notificación demo enviada → {settings.EMAIL_NOTIFICATIONS_TO} | usuario={user_email}")
    return ok
