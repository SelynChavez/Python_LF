from flask import Blueprint

compras_comb_bp = Blueprint('compras_comb', __name__, url_prefix='/')

from . import compras_comb_routes
