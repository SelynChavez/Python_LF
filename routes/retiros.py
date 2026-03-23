from flask import Blueprint

retiros_bp = Blueprint('retiros', __name__, url_prefix='/')

from . import retiros_routes
