from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from microblog.app import  login
from flask_login import UserMixin
import json
from bson import ObjectId
from hashlib import md5
from pymongo import MongoClient 
from werkzeug.security import generate_password_hash, check_password_hash
import jwt 
from time import time
from flask import current_app





class User(UserMixin):
    def __init__(self,user_data):
        self._id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.password_hash = user_data['password_hash']
        self.about_me = user_data.get('about_me','')  # Obtener el campo 'about_me' o establecerlo en una cadena vacía por defecto
        self.last_seen = user_data.get('last_seen')
        self.followers = user_data.get("followers", [])
        self.following = user_data.get("following", []) 
        self.avatar_url = user_data.get('avatar_url',self.avatar(36))

    def get_id(self):
        return self._id
  
    def save(self):
        from microblog.microblog import mongo
        users_collection = mongo.db.users
        if not self.password_hash:
            raise ValueError("La contraseña debe ser establecida antes de guardar el usuario.")
        self.id = users_collection.insert_one(self.__dict__).inserted_id
        print("Usuario guardado con ID:", self.id)

    
    def update(self, update_values):
        from microblog.microblog import mongo
        users_collection = mongo.db.users        
        result = users_collection.update_one({"_id": self._id},{'$set': update_values})
        print("Update Result:", result.modified_count)
    
    def update_opt(self):
        from microblog.microblog import mongo
        users_collection = mongo.db.users
        
        result = users_collection.update_one({"_id": self._id},{'$set': self.__dict__})
        print("Update Result:", result.modified_count)
        
    def is_following(self, user_id):
            return str(user_id) in self.following 
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def find_by_username(username):
        from microblog.microblog import mongo
        users_collection = mongo.db.users
        user_data = users_collection.find_one({'username': username})
        if user_data:
            return User(user_data)
        return None

    @staticmethod
    def find_by_email(email):
        from microblog.microblog import mongo
        users_collection = mongo.db.users
        user_data = users_collection.find_one({'email': email})
        if user_data:
            return User(user_data)
        return None
    
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)
    
    def follow(self, user_to_follow):
        if user_to_follow._id != self._id and user_to_follow._id not in self.following:
            self.following.append(user_to_follow._id)
            self.update({"following": self.following})  # Actualiza el campo 'following' del usuario actual


    def unfollow(self, user_to_unfollow):
        if user_to_unfollow._id != self._id and user_to_unfollow._id in self.following:
            self.following.remove(user_to_unfollow._id)
            self.update({"following": self.following})

             
    def followed_posts(self):
        from microblog.microblog import mongo
        posts_collection = mongo.db.posts
        # Obtener la lista de IDs de usuarios seguidos
        followed_ids = self.following
        
        # Agregar también el ID del propio usuario
        followed_ids.append(self._id)
        
        # Consultar las publicaciones de los usuarios seguidos
        followed_posts = posts_collection.find({"user_id": {"$in": followed_ids}})
        
        # Ordenar las publicaciones por fecha descendente
        followed_posts = followed_posts.sort("timestamp", -1)
        
        return followed_posts
    
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': str(self._id), 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256')



    @staticmethod
    def verify_reset_password_token(token):
        from microblog.microblog import mongo
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload.get('reset_password')
            if user_id:
                user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
                if user_data:
                    return User(user_data)
        except jwt.ExpiredSignatureError:
            pass  # Token expirado
        except (jwt.DecodeError, jwt.InvalidTokenError):
            pass  # Token inválido
        return None


@login.user_loader
def load_user(user_id):
    # Debes buscar el usuario por su ID en la colección de usuarios en MongoDB
    from microblog.microblog import mongo
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
        from microblog.microblog import mongo
        posts_collection = mongo.db.posts
        post_data = {
            "body": self.body,
            "timestamp": self.timestamp,
            "user_id": self.user_id
        }
        result = posts_collection.insert_one(post_data)
        self.id = result.inserted_id

    @staticmethod
    def find_all_with_user_info():
        from microblog.microblog import mongo
        posts_collection = mongo.db.posts
        users_collection = mongo.db.users
        
        # Realiza una agregación para unir la información del usuario y la publicación
        pipeline = [
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {
                "$unwind": "$user"
            }
        ]
        
        posts = posts_collection.aggregate(pipeline)
        
        return posts

    @staticmethod
    def find_by_user_id(user_id):
        from microblog.microblog import mongo
        posts_collection = mongo.db.posts
        return posts_collection.find({'user_id': user_id})
