from flask import Blueprint

bp = Blueprint('main', __name__)

from microblog.app.main import routes