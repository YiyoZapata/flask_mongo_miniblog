from flask import render_template, flash, redirect, url_for, request, g, current_app
from werkzeug.urls import url_parse
from microblog.app.main import bp
from microblog.app.main.forms import EditProfileForm, \
    EmptyForm, PostForm
#from app.models import User, Post
from flask_login import current_user , login_required
from microblog.app.main.forms import EditProfileForm, EmptyForm, PostForm
from bson import ObjectId
from datetime import datetime
from pymongo import MongoClient
from flask_babel import _, get_locale



@bp.before_request
def before_request():
    
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        # Guardar el valor actualizado de last_seen en MongoDB
        from microblog.microblog import mongo
        
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
    g.locale = str(get_locale())


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    from microblog.microblog import mongo
        
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
        flash(_('Your post is now live!'))
        return redirect(url_for('main.index'))
    
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
            "$skip": (page - 1) * current_app.config['POSTS_PER_PAGE']
        },
        {
            "$limit": current_app.config['POSTS_PER_PAGE']
        }
    ]
    
    posts_collection = mongo.db.posts
    posts = list(posts_collection.aggregate(pipeline))
    
    next_url = url_for('main.index', page=page + 1) if len(posts) == current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.index', page=page - 1) if page > 1 else None
    
    return render_template('index.html', title=_('Home'), form=form,
                           posts=posts, next_url=next_url,
                           prev_url=prev_url, user=current_user)

                                                                                                          

@bp.route('/explore')
@login_required
def explore():
    from microblog.microblog import mongo
    page = request.args.get('page', 1, type=int)
    posts_collection = mongo.db.posts
    
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
            "$skip": (page - 1) * current_app.config['POSTS_PER_PAGE']
        },
        {
            "$limit": current_app.config['POSTS_PER_PAGE']
        }
    ]
    
    posts = list(posts_collection.aggregate(pipeline))
    
    total_posts = posts_collection.count_documents({})
    
    next_url = url_for('explore', page=page + 1) if total_posts > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('explore', page=page - 1) if page > 1 else None
    
    return render_template('index.html', title=_('Explore'), posts=posts, next_url=next_url, prev_url=prev_url, user=current_user)


@bp.route('/user/<username>')
@login_required
def user(username):
    from microblog.microblog import mongo
    from microblog.app.models import User
    target_user = mongo.db.users.find_one({'username':username})
    if not target_user:
        flash(_('User {} not found.'.format(username)))
        return redirect(url_for('main.index'))
    
     # Crear una instancia de User a partir de los datos del usuario en MongoDB
    user_instance = User(target_user)
    
    page = request.args.get('page', 1, type=int)

    target_user_id = user_instance.get_id()
    
    # Consultar las publicaciones del usuario y ordenarlas por fecha descendente
    user_posts_cursor = mongo.db.posts.find({'user_id': target_user_id}).sort('timestamp', -1)

    
    # Contar el número total de publicaciones del usuario
    total_posts = mongo.db.posts.count_documents({'user_id': target_user_id})
    
    # Paginar las publicaciones
    posts = user_posts_cursor.skip((page - 1) * current_app.config['POSTS_PER_PAGE']).limit(current_app.config['POSTS_PER_PAGE'])
    
    next_url = url_for('user', username=username, page=page + 1) if total_posts > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('user', username=username, page=page - 1) if page > 1 else None
    
    form = EmptyForm()
    
    return render_template('user.html', target_user=user_instance, posts=posts,
                           next_url=next_url, prev_url=prev_url, form=form)




@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    from microblog.microblog import mongo
    form = EditProfileForm(current_user.username)

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data

        
        
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

        
        print(result.modified_count)
        flash(_('Your changes have been saved.'))
        
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me

    return render_template('edit_profile.html', title=_('Edit Profile'), form=form)

  # Asegúrate de importar la clase User desde tu modelo

@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    from microblog.app.models import User
    form = EmptyForm()
    if form.validate_on_submit():
        user_to_follow = User.find_by_username(username)
        if user_to_follow is None:
            flash(_('User {} not found.'.format(username)))
            return redirect(url_for('main.index'))
        if user_to_follow == current_user:
            flash(_('You cannot follow yourself!'))
            return redirect(url_for('main.user', username=username))

        current_user_id_str = str(current_user.get_id())  # Convertir el ID a str
        user_to_follow_id_str = str(user_to_follow.get_id())  # Convertir el ID a str

        if user_to_follow_id_str not in current_user.following:
            current_user.follow(user_to_follow)
            user_to_follow.followers.append(current_user_id_str)
            user_to_follow.update_opt()
            flash(_('You are following {}!'.format(username)))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    from microblog.app.models import User
    form = EmptyForm()
    if form.validate_on_submit():
        user_to_unfollow = User.find_by_username(username)
        if user_to_unfollow is None:
            flash(_('User {} not found.'.format(username)))
            return redirect(url_for('main.index'))
        if user_to_unfollow == current_user:
            flash(_('You cannot unfollow yourself!'))
            return redirect(url_for('main.user', username=username))

        current_user_id_str = str(current_user.get_id())  # Convertir el ID a str
        user_to_unfollow_id_str = str(user_to_unfollow.get_id())  # Convertir el ID a str

        if user_to_unfollow_id_str in current_user.following:
            current_user.unfollow(user_to_unfollow)
            user_to_unfollow.followers.remove(current_user_id_str)
            user_to_unfollow.update_opt()
            flash(_('You are not following {}.'.format(username)))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))

