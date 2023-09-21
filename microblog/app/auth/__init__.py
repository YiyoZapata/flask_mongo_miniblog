from flask import Blueprint

bp = Blueprint('auth', __name__)

from microblog.app.auth import routes