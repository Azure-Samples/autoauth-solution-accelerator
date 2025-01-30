#
from fastapi_users import schemas
from beanie import PydanticObjectId

class UserRead(schemas.BaseUser[PydanticObjectId]):
    pass

class UserCreate(schemas.BaseUserCreate):
    pass

class UserUpdate(schemas.BaseUserUpdate):
    pass