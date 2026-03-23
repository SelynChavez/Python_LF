from flask import Blueprint

bp = Blueprint('contabilidad', __name__, url_prefix='/')

from . import contabilidad_routes
