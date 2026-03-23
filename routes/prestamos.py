from flask import Blueprint

prestamos_bp = Blueprint('prestamos', __name__, url_prefix='/')

from . import prestamos_routes
