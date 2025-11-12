import aiosmtplib
from email.message import EmailMessage

async def send_email(recipients: list[str], subject: str, body: str):
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
        username="u4511679295@gmail.com",
        password="scoring.tool@",  # i know very insecure, change later.
    )
