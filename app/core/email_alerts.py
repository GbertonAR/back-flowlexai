"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: email_alerts.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Handler de logging que envía alertas por email ante errores
             del sistema. Batching con rate-limit de 5 minutos para evitar
             flooding. Hilo daemon no-bloqueante.
FECHA CREACIÓN: 2026-06-18
ÚLTIMA MODIFICACIÓN: 2026-06-18
REF. TICKET: #FS-OPS-001
"""

import logging
import queue
import smtplib
import threading
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class ErrorEmailHandler(logging.Handler):
    """
    Handler de logging que captura registros ERROR/CRITICAL y envía
    un email de alerta agrupando los errores del período (rate-limit 5 min).

    - emit() es no-bloqueante: encola el mensaje formateado.
    - Un hilo daemon procesa la cola cada 30s y envía si hay errores pendientes
      y el intervalo mínimo fue superado.
    """

    MIN_INTERVAL_SECONDS = 300  # 5 minutos entre envíos
    CHECK_INTERVAL_SECONDS = 30
    QUEUE_MAX = 500

    def __init__(self):
        super().__init__(level=logging.ERROR)
        self._queue: queue.Queue = queue.Queue(maxsize=self.QUEUE_MAX)
        self._last_sent: float = 0.0
        self._thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="flowlexai-email-alert",
        )
        self._thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put_nowait(self.format(record))
        except queue.Full:
            pass  # Nunca bloquear el logging principal

    def _worker(self) -> None:
        buffer: list[str] = []
        while True:
            # Drena toda la cola disponible
            try:
                while True:
                    buffer.append(self._queue.get_nowait())
            except queue.Empty:
                pass

            now = time.time()
            if buffer and (now - self._last_sent >= self.MIN_INTERVAL_SECONDS):
                self._send_email(list(buffer))
                buffer.clear()
                self._last_sent = now

            time.sleep(self.CHECK_INTERVAL_SECONDS)

    def _send_email(self, messages: list[str]) -> None:
        # Import lazy para evitar circular imports al inicializar el logger
        try:
            from app.core.config import settings
        except Exception:
            return

        host = settings.EMAIL_SMTP_HOST
        port = settings.EMAIL_PORT
        user = settings.EMAIL_USERNAME
        password = settings.EMAIL_PASSWORD
        to_addr = settings.EMAIL_NOTIFICATIONS_TO

        if not all([host, user, password, to_addr]):
            return

        count = len(messages)
        subject = f"[FlowLexAI] ❌ {count} error{'es' if count > 1 else ''} detectado{'s' if count > 1 else ''} en Backend"

        body_lines = [
            "Sistema: FlowLexAI Backend",
            f"Errores detectados: {count}",
            f"Período: últimos {self.MIN_INTERVAL_SECONDS // 60} minutos",
            "",
            "─" * 60,
            "",
        ]
        for i, msg in enumerate(messages, 1):
            body_lines.append(f"[{i}] {msg}")
            body_lines.append("")

        body_lines += [
            "─" * 60,
            "",
            "KAI · FlowState AI · Sistema de Alertas Forense",
        ]

        body = "\n".join(body_lines)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = user
            msg["To"] = to_addr
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(host, port, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(user, password)
                smtp.sendmail(user, to_addr, msg.as_string())
        except Exception:
            pass  # Silencioso: el alerting no puede romper el sistema principal


error_email_handler = ErrorEmailHandler()
