# -*- coding: utf-8 -*-
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pymongo.errors import ServerSelectionTimeoutError
from pymongo.errors import PyMongoError
from pymongo.errors import InvalidName
from pymongo.errors import InvalidOperation
from pymongo.errors import InvalidURI
from pymongo.errors import InvalidURI
 
_default_mongo_client = None
_default_mongo_db = None
_default_mongo_collection = None

def _get_mongo_client() -> MongoClient:
    global _default_mongo_client
    if _default_mongo_client is None:
        _default_mongo_client = MongoClient(os.getenv("MONGO_URI"))
    return _default_mongo_client
