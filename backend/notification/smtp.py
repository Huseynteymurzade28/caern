"""Async SMTP email notifications."""
from __future__ import annotations

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from common_utils.config import settings
from common_utils.logger import get_logger

log = get_logger(__name__)


async def send_email(to: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        log.info("email_sent", to=to, subject=subject)
    except Exception as exc:
        log.error("email_failed", to=to, exc=str(exc))


async def notify_job_complete(user_email: str, job_id: str) -> None:
    await send_email(
        to=user_email,
        subject="CAERN — Analiz Tamamlandı",
        html_body=f"""
        <h2>Analiz tamamlandı</h2>
        <p>Job ID: <code>{job_id}</code> başarıyla tamamlandı.</p>
        <p>Sonuçları görüntülemek için platforma giriş yapın.</p>
        """,
    )


async def notify_job_failed(user_email: str, job_id: str, reason: str) -> None:
    await send_email(
        to=user_email,
        subject="CAERN — Analiz Başarısız",
        html_body=f"""
        <h2>Analiz başarısız</h2>
        <p>Job ID: <code>{job_id}</code> başarısız oldu.</p>
        <p>Sebep: {reason}</p>
        """,
    )
