from flask import Blueprint

bp = Blueprint('io_cash', __name__, url_prefix='/')

from . import io_cash_routes
