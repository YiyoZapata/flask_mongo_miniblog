from flask import render_template, flash, redirect, url_for, request, g
from werkzeug.urls import url_parse
from app import app
from app import mongo
from app.forms import LoginForm, EditProfileForm
from app.models import User, Post
from flask_login import current_user, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash
from app.forms import RegistrationForm, EditProfileForm
from bson import ObjectId
from datetime import datetime

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
                    
                    'about_me': current_user.about_me
                }
            }
        )


@app.route('/')
@app.route('/index')
@login_required
def index():
    posts = [
        {
            'author': {'username': 'John'},
            'body': 'Beautiful day in Portland!'
        },
        {
            'author': {'username': 'Susan'},
            'body': 'The Avengers movie was so cool!'
        }
    ]
    return render_template('index.html', title='Home', user=user, posts=posts)


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
    # Buscar al usuario en la colección de usuarios en MongoDB por su nombre de usuario
    user_data = mongo.db.users.find_one({'username': username})
    
    if user_data:
        user = User(user_data)
        posts = [
            {'author': user, 'body': 'Test post #1'},
            {'author': user, 'body': 'Test post #2'}
        ]
        return render_template('user.html', user=user, posts=posts)
    else:
        #abort(404)  # Devuelve una respuesta HTTP 404 si el usuario no se encuentra
        flash('Usuario no encontrado')


        
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

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()

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


