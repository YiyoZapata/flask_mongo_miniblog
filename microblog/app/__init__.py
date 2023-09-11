from flask import Flask
from pymongo import MongoClient
from config import Config
from flask_login import LoginManager


app = Flask(__name__)
app.config.from_object(Config)

mongo = MongoClient(app.config['MONGO_URI'])
login = LoginManager(app)
login.login_view = 'login'

# Obtener la colección de usuarios
users_collection = mongo.db.users

# Crear un índice único en el campo 'username'
users_collection.create_index([('username', 1)], unique=True)

from app import routes,models,errors