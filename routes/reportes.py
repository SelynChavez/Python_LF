from flask import Blueprint

bp = Blueprint('reportes', __name__, url_prefix='/')

from . import reportes_routes
