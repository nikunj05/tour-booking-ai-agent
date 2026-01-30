from fastapi_mail import MessageSchema
from pydantic import EmailStr
from app.core.email import fast_mail


async def send_company_created_email(
    email: EmailStr,
    company_name: str,
    password: str,
    login_url: str,
):
    message = MessageSchema(
        subject="Your Company Account Has Been Created",
        recipients=[email],
        template_body={
            "email": email,
            "company_name": company_name,
            "password": password,
            "login_url": login_url,
        },
        subtype="html",
    )

    await fast_mail.send_message(
        message,
        template_name="company_created.html",
    )


async def send_reset_password_email(
    email: EmailStr,
    reset_url: str,
):
    message = MessageSchema(
        subject="Reset Your Password",
        recipients=[email],
        template_body={
            "email": email,
            "reset_url": reset_url,
        },
        subtype="html",
    )

    await fast_mail.send_message(
        message,
        template_name="reset_password.html",
    )