from pymongo import MongoClient
import certifi
import os
from config import MONGO_URL


client_mongo = MongoClient(MONGO_URL, tls=True, tlsCAFile=certifi.where())
db = client_mongo["ai_database"]
collection = db["posts"]