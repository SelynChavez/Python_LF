from .auth import bp as auth_bp
from .contabilidad import bp as contabilidad_bp
from .configuracion import bp as configuracion_bp
from .reportes import bp as reportes_bp
from .io_cash import bp as io_cash_bp
from .combustibles import bp as combustibles_bp
from .productos import bp as productos_bp
from .dashboard import bp as dashboard_bp
from .aportes import aportes_bp
from .prestamos import prestamos_bp
from .retiros import retiros_bp
from .recibos import recibos_bp

__all__ = [
    'auth_bp', 
    'contabilidad_bp', 
    'configuracion_bp', 
    'reportes_bp', 
    'io_cash_bp', 
    'combustibles_bp', 
    'productos_bp', 
    'dashboard_bp',
    'aportes_bp',
    'prestamos_bp',
    'retiros_bp',
    'recibos_bp'
]
