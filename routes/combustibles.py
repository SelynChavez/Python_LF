from flask import Blueprint

bp = Blueprint('combustibles', __name__, url_prefix='/')

from . import combustibles_routes
