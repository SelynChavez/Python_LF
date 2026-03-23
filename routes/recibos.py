from flask import Blueprint

recibos_bp = Blueprint('recibos', __name__, url_prefix='/recibos')

from . import recibos_routes
