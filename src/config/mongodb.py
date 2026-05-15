from pymongo import MongoClient
from src.config.settings import MONGO_URI, MONGO_DB

client = MongoClient(MONGO_URI)

db = client[MONGO_DB]


def get_database():
    return db
