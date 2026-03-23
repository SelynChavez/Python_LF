from flask import Blueprint

bp = Blueprint('productos', __name__, url_prefix='/')

from . import productos_routes
