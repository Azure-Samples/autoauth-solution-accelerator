#
import motor.motor_asyncio
from fastapi_users_db_beanie import BeanieBaseUserDocument, BeanieUserDatabase

#
from .config import settings

DATABASE_URL = str(settings.DATABASE_ASYNC_URL)
DATABASE_NAME = settings.AZURE_COSMOS_DB_DATABASE_NAME

client = motor.motor_asyncio.AsyncIOMotorClient(
    DATABASE_URL, uuidRepresentation="standard"
)

db = client[DATABASE_NAME]


class User(BeanieBaseUserDocument):
    pass


async def get_user_db():
    yield BeanieUserDatabase(User)
