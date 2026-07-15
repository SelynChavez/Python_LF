from flask import Blueprint

facturacion_bp = Blueprint('facturacion', __name__, url_prefix='/facturacion')

from . import facturacion_routes
