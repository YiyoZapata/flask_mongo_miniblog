from flask import render_template, flash, redirect, url_for, request
from werkzeug.urls import url_parse
from flask_login import current_user, login_user, login_required, logout_user
from flask_babel import _
from microblog.app.auth import bp
from microblog.app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from microblog.app.models import User
from pymongo import MongoClient
from microblog.app.auth.email import send_password_reset_email 
from bson import ObjectId
from datetime import datetime


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()

    if form.validate_on_submit():
        # Buscar el usuario en la colección de usuarios en MongoDB por su nombre de usuario
        from microblog.microblog import mongo
        
        user_data = mongo.db.users.find_one({'username': form.username.data})

        if user_data and User(user_data).check_password(form.password.data):
            user = User(user_data)
            login_user(user, remember=form.remember_me.data)

            # Obtener el valor de 'next' de la solicitud
            next_page = request.args.get('next')

            # Verificar si 'next' es válido y seguro
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('main.index')  # O redirige a la página de inicio predeterminada

            return redirect(next_page)

        flash(_('Invalid username or password'))
        return redirect(url_for('auth.login'))

    return render_template('auth/login.html', title=_('Sign In'), form=form)



@bp.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()

    if form.validate_on_submit():
        # Verificar si ya existe un usuario con el mismo nombre de usuario o correo electrónico
        existing_user = User.find_by_username(form.username.data)
        if existing_user:
            flash(_('Username already exists. Please choose a different one.'))
            return redirect(url_for('auth/register'))
        
        existing_email = User.find_by_email(form.email.data)
        if existing_email:
            flash(_('Email address already in use. Please use a different one.'))
            return redirect(url_for('auth/register'))
        
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

        flash(_('Congratulations, you are now a registered user!'))
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', title=_('Register'), form=form)

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user_data = request.mongo.db.users.find_one({'email': form.email.data})
        if user_data:
            send_password_reset_email(User(user_data))
        flash(_('Check your email for the instructions to reset your password'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title=_('Reset Password'), form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user_data = request.mongo.db.users.find_one({'reset_password_token': token})
    if not user_data:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User(user_data)
        user.set_password(form.password.data)
        user.save()
        flash(_('Your password has been reset.'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

