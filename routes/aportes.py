from flask import Blueprint

aportes_bp = Blueprint('aportes', __name__, url_prefix='/')

from . import aportes_routes
