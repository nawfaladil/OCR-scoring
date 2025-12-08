"""
Define a function to send email with token in case of forgot password
"""
import os
from dotenv import load_dotenv
import aiosmtplib
from email.message import EmailMessage

load_dotenv()

async def send_email(recipients: list[str], subject: str, body: str):
    """
    We use an email to send the forgot password emails,
    don't forget to setup the .env file with secret key and these credentials.
    """
    message = EmailMessage()
    message["From"] = "Scoring tool <u4511679295@gmail.com>"
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname="smtp.gmail.com",  # replace as needed
        port=587,
        start_tls=True,
        username = os.environ.get("mail_username"),
        password = os.environ.get("mail_password"),
    )
