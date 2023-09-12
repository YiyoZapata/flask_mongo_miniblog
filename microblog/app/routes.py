from flask import render_template, flash, redirect, url_for, request, g
from werkzeug.urls import url_parse
from app import app
from app import mongo
from app.forms import LoginForm, EditProfileForm
from app.models import User, Post
from flask_login import current_user, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash
from app.forms import RegistrationForm, EditProfileForm, EmptyForm, PostForm
from bson import ObjectId
from datetime import datetime
from pymongo import MongoClient


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        # Guardar el valor actualizado de last_seen en MongoDB
        user_collection = mongo.db.users
        user_collection.update_one(
            {'_id': ObjectId(current_user._id)},  # Usar el _id del usuario actual
            {
                '$set': {
                    'last_seen': current_user.last_seen,
                    'username': current_user.username,
                    'about_me': current_user.about_me
                }
            }
        )


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        # Crea un nuevo documento de publicación en MongoDB
        post_data = {
            'body': form.post.data,
            'author_id': current_user._id,  # Usa el ID del autor
            'timestamp': datetime.utcnow()  # Agrega la fecha y hora actual
        }
        posts_collection = mongo.db.posts
        posts_collection.insert_one(post_data)
        flash('Your post is now live!')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    
    # Realiza una agregación para unir la información del usuario y la publicación
    pipeline = [
        {
            "$lookup": {
                "from": "users",
                "localField": "author_id",
                "foreignField": "_id",
                "as": "user"
            }
        },
        {
            "$unwind": "$user"
        },
        {
            "$sort": {"timestamp": -1}
        },
        {
            "$skip": (page - 1) * app.config['POSTS_PER_PAGE']
        },
        {
            "$limit": app.config['POSTS_PER_PAGE']
        }
    ]
    
    posts_collection = mongo.db.posts
    posts = list(posts_collection.aggregate(pipeline))
    
    next_url = url_for('index', page=page + 1) if len(posts) == app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('index', page=page - 1) if page > 1 else None
    
    return render_template('index.html', title='Home', form=form,
                           posts=posts, next_url=next_url,
                           prev_url=prev_url, user=current_user)

                                                                                                          

@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts_collection = mongo.db.posts
    posts = posts_collection.find().sort('timestamp', -1).skip((page - 1) * app.config['POSTS_PER_PAGE']).limit(app.config['POSTS_PER_PAGE'])
    
    # Contar el número total de documentos en la colección
    total_posts = posts_collection.count_documents({})
    
    next_url = url_for('explore', page=page + 1) if total_posts > page * app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('explore', page=page - 1) if page > 1 else None
    
    return render_template('index.html', title='Explore', posts=posts, next_url=next_url, prev_url=prev_url, user=current_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():
        # Buscar el usuario en la colección de usuarios en MongoDB por su nombre de usuario
        user_data = mongo.db.users.find_one({'username': form.username.data})

        if user_data and User(user_data).check_password(form.password.data):
            user = User(user_data)
            login_user(user, remember=form.remember_me.data)

            # Obtener el valor de 'next' de la solicitud
            next_page = request.args.get('next')

            # Verificar si 'next' es válido y seguro
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('index')  # O redirige a la página de inicio predeterminada

            return redirect(next_page)

        flash('Invalid username or password')
        return redirect(url_for('login'))

    return render_template('login.html', title='Sign In', form=form)



@app.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()

    if form.validate_on_submit():
        # Verificar si ya existe un usuario con el mismo nombre de usuario o correo electrónico
        existing_user = User.find_by_username(form.username.data)
        if existing_user:
            flash('Username already exists. Please choose a different one.')
            return redirect(url_for('register'))
        
        existing_email = User.find_by_email(form.email.data)
        if existing_email:
            flash('Email address already in use. Please use a different one.')
            return redirect(url_for('register'))
        
        # Crear un nuevo usuario
        
        new_user_data = {
            '_id': str(ObjectId()),
            'username': form.username.data,
            'email': form.email.data,
            'password_hash': None,  # Deberás establecer la contraseña antes de guardar
            'about_me': '',
            'last_seen': datetime.utcnow()
        }
        
        new_user = User(new_user_data)
        new_user.set_password(form.password.data)
        new_user.save()

        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = User.find_by_username(username)
    if not user:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    
    # Consultar las publicaciones del usuario y ordenarlas por fecha descendente
    user_posts_cursor = mongo.db.posts.find({'user_id': ObjectId(user._id)}).sort('timestamp', -1)
    
    # Contar el número total de publicaciones del usuario
    total_posts = mongo.db.posts.count_documents({'user_id': ObjectId(user._id)})
    
    # Paginar las publicaciones
    posts = user_posts_cursor.skip((page - 1) * app.config['POSTS_PER_PAGE']).limit(app.config['POSTS_PER_PAGE'])
    
    next_url = url_for('user', username=username, page=page + 1) if total_posts > page * app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('user', username=username, page=page - 1) if page > 1 else None
    
    form = EmptyForm()
    
    return render_template('user.html', user=user, posts=posts,
                           next_url=next_url, prev_url=prev_url, form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data

        app.logger.info(f'Updating user with ID: {current_user._id}')
        app.logger.info(f'New username: {current_user.username}')
        app.logger.info(f'New about_me: {current_user.about_me}')
        
        # Actualizar el documento de usuario en MongoDB
        user_collection = mongo.db.users
      
        result = user_collection.update_one(
            {'_id': current_user._id},  # Usar el _id del usuario actual
            
            {
                '$set': {
                    'username': current_user.username,
                    'about_me': current_user.about_me
                }
            },
            upsert=False  # Agregar el parámetro upsert 
            
        )
        print(current_user._id)

        app.logger.info(f'MongoDB update result: {result.modified_count}')
        print(result.modified_count)
        flash('Your changes have been saved.')
        
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me

    return render_template('edit_profile.html', title='Edit Profile', form=form)

@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user_to_follow = User.find_by_username(username)
        if user_to_follow is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('index'))
        if user_to_follow == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('user', username=username))
        
        current_user.follow(user_to_follow)
        if not user_to_follow.is_following(current_user._id):
            user_to_follow.followers.append(current_user._id)  # Agrega el seguidor al usuario que está siendo seguido
        user_to_follow.update_opt()  # Guardar los cambios en el usuario que está siendo seguido
        flash('You are following {}!'.format(username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user_to_unfollow = User.find_by_username(username)
        if user_to_unfollow is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('index'))
        if user_to_unfollow == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('user', username=username))
        
        current_user.unfollow(user_to_unfollow)
        user_to_unfollow.followers.remove(current_user._id)  # Elimina el seguidor del usuario que está siendo dejado de seguir
        user_to_unfollow.update_opt()  # Guardar los cambios en el usuario que está siendo dejado de seguir
        flash('You are not following {}.'.format(username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))



