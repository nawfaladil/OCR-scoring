"""
You can refer to FastApi Users documentation for more info in these schemas used to build users account management
I simply followed their step by step guide, they provide an already built user management system.
"""
import uuid
from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass
