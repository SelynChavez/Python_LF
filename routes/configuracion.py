from flask import Blueprint

bp = Blueprint('configuracion', __name__, url_prefix='/')

from . import configuracion_routes
