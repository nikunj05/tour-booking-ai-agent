from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pathlib import Path

conf = ConnectionConfig(
    MAIL_USERNAME="dfd3ced3b3694d",
    MAIL_PASSWORD="fad2855ae6ec4c",  # Gmail App Password
    MAIL_FROM="test@gmail.com",
    MAIL_FROM_NAME="my inbox",
    MAIL_SERVER="sandbox.smtp.mailtrap.io",
    MAIL_PORT=587,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER=Path(__file__).parent.parent / "templates" / "emails",
)

fast_mail = FastMail(conf)
