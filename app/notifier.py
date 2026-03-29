import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


async def send_notification(
    domain_name: str,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    smtp_use_tls: bool,
    smtp_from_email: str,
    notification_email: str,
):
    """Send email notification when a domain becomes available."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🟢 Domain Available: {domain_name}"
    msg["From"] = smtp_from_email or smtp_username
    msg["To"] = notification_email

    text = f"""Good news!

The domain {domain_name} is now available for registration.

Go grab it before someone else does!

— Domee"""

    html = f"""\
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 40px;">
  <div style="max-width: 500px; margin: 0 auto; background: #141414; border-radius: 16px; padding: 40px; border: 1px solid #222;">
    <div style="font-size: 48px; text-align: center; margin-bottom: 16px;">🟢</div>
    <h1 style="color: #4ade80; text-align: center; font-size: 20px; margin: 0 0 8px;">Domain Available</h1>
    <p style="text-align: center; font-size: 28px; font-weight: 700; color: #fff; margin: 0 0 24px;">{domain_name}</p>
    <p style="text-align: center; color: #888; font-size: 14px;">Go grab it before someone else does!</p>
    <hr style="border: none; border-top: 1px solid #222; margin: 24px 0;">
    <p style="text-align: center; color: #555; font-size: 12px;">Sent by Domee</p>
  </div>
</body>
</html>"""

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    await aiosmtplib.send(
        msg,
        hostname=smtp_host,
        port=smtp_port,
        username=smtp_username,
        password=smtp_password,
        start_tls=smtp_use_tls,
    )
