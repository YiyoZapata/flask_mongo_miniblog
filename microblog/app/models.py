from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import mongo
from app import login 
from flask_login import UserMixin
import json
from bson import ObjectId
from hashlib import md5

class User(UserMixin):
    def __init__(self,user_data):
        self._id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.password_hash = user_data['password_hash']
        self.about_me = user_data.get('about_me','')  # Obtener el campo 'about_me' o establecerlo en una cadena vacía por defecto
        self.last_seen = user_data.get('last_seen') 

    def get_id(self):
        return self._id
  

    def save(self):
        users_collection = mongo.db.users
        if not self.password_hash:
            raise ValueError("La contraseña debe ser establecida antes de guardar el usuario.")
        self.id = users_collection.insert_one(self.__dict__).inserted_id
        print("Usuario guardado con ID:", self.id)
  

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def find_by_username(username):
        users_collection = mongo.db.users
        user_data = users_collection.find_one({'username': username})
        if user_data:
            return User(user_data)
        return None

    @staticmethod
    def find_by_email(email):
        users_collection = mongo.db.users
        user_data = users_collection.find_one({'email': email})
        if user_data:
            return User(user_data)
        return None
    
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)



@login.user_loader
def load_user(user_id):
    # Debes buscar el usuario por su ID en la colección de usuarios en MongoDB
    user_data = mongo.db.users.find_one({'_id': user_id})
    if user_data:
        return User(user_data)
    return None

class Post:
    def __init__(self, body, user_id):
        self.body = body
        self.timestamp = datetime.utcnow()
        self.user_id = user_id

    def save(self):
        posts_collection = mongo.db.posts
        post_data = {
            "body": self.body,
            "timestamp": self.timestamp,
            "user_id": self.user_id
        }
        result = posts_collection.insert_one(post_data)
        self.id = result.inserted_id

    @staticmethod
    def find_all():
        posts_collection = mongo.db.posts
        return posts_collection.find()

    @staticmethod
    def find_by_user_id(user_id):
        posts_collection = mongo.db.posts
        return posts_collection.find({'user_id': user_id})
