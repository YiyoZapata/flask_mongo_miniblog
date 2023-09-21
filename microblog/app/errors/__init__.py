from flask import Blueprint

bp = Blueprint('errors', __name__)

from microblog.app.errors import handlers