"""
You can refer to FastApi Users documentation for the choice of cookies and JWT as transport and session management
"""
import os
import uuid
from dotenv import load_dotenv
from typing import Union
from fastapi import Depends, Request
from fastapi_users import (
    BaseUserManager,
    UUIDIDMixin,
    InvalidPasswordException,
    FastAPIUsers,
)
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from main_tool.core.database.db_test import User, get_user_db
from main_tool.core.api.schemas import UserCreate
from main_tool.core.api.email_config import send_email

load_dotenv()

SECRET = os.environ.get("SECRET_KEY")

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """
    In this class we can define course of actions to take after register, log in etc...
    As well as password validation conditions
    """
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Request | None = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ):
        """
        This function defines the forgot password mechanism
        Traditionnaly, we would send a token to the mail of the account,
        but BPCE's firewall blocks the email smtp, we just print the token in the api console
        replace with an internal or non blocked email smtp service, and uncomment this section
        and remove the unclean print.
        """
        # Uncomment when you have a solution
        # subject = "Password Reset"
        # body = f"Hi {user.email},\n\nReset your password with this token: {token}"
        # await send_email([user.email], subject, body)

        print(f"Password reset token for {user.email}: {token}")

    async def validate_password(
        self,
        password: str,
        user: Union[UserCreate, User],
    ) -> None:
        """
        This is the function that defines the password setting conditions,
        modify as you want.
        """
        if len(password) < 8:
            raise InvalidPasswordException(
                reason="Password should be at least 8 characters"
            )
        if user.email in password:
            raise InvalidPasswordException(
                reason="Password should not contain e-mail"
            )


async def get_user_manager(user_db=Depends(get_user_db)):
    """
    Check FastAPI Users for more details
    """
    yield UserManager(user_db)


cookie_transport = CookieTransport(cookie_max_age=3600)


def get_jwt_strategy() -> JWTStrategy:
    """
    Check FastAPI Users for more details
    """
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
