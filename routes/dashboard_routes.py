from flask import render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from flask import current_app
from mysql.connector import Error
import datetime
import sqlconstants

from .dashboard import bp as dashboard_bp

def get_db_connection():
    try:
        from mysql import connector
        connection = connector.connect(
            host=current_app.config['MYSQL_HOST'],
            user=current_app.config['MYSQL_USER'],
            password=current_app.config['MYSQL_PASSWORD'],
            database=current_app.config['MYSQL_DATABASE'],
            port=current_app.config['MYSQL_PORT']
        )
        return connection
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_rol' not in session or session['user_rol'] != 'ADMIN':
            flash('Acceso denegado. Se requieren privilegios de administrador.', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@dashboard_bp.route('/administracion')
@login_required
@admin_required
def administracion():
    return render_template('administracion.html')


@dashboard_bp.route('/configuracion')
@login_required
@admin_required
def configuracion():
    return render_template('configuracion.html')


@dashboard_bp.route('/menurecibos')
@login_required
def menurecibos():
    return render_template('menurecibos.html')


@dashboard_bp.route('/menuiocash')
@login_required
def menuiocash():
    return render_template('menuiocash.html')


@dashboard_bp.route('/dashboardP')
def dashboardP():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sqlconstants.DASHB_PRRET_SOCIOS)
        data = cursor.fetchone()
        total_socios_mes = str(data['total'])

        cursor.execute(sqlconstants.DASHB_PRRET_RETIROS)
        total_retiros = cursor.fetchone()['total']

        cursor.execute(sqlconstants.DASHB_PRRET_APORTES)
        total_aportes = cursor.fetchone()['total']

        cursor.execute(sqlconstants.DASHB_PRRET_PRESTAMOS)
        total_prestamos = cursor.fetchone()['total']

        cursor.execute(sqlconstants.DASHB_PRRET_PRESTAMOS_ESTADO)
        prestamos_por_estado = cursor.fetchall()

        cursor.execute(sqlconstants.DASHB_PRRET_PRESTAMOS_TIPOS)
        prestamos_por_tipo = cursor.fetchall()

        cursor.execute(sqlconstants.DASHB_PRRET_PAD_MAY_APORTES)
        top_padrones = cursor.fetchall()

        cursor.execute(sqlconstants.DASHB_PRRET_MOVS_RET_PREST)
        ultimos_movimientos = cursor.fetchall()

    conn.close()
    return render_template('dashboardP.html',
                         now=datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                         total_socios_mes=total_socios_mes,
                         total_retiros=total_retiros,
                         total_aportes=total_aportes,
                         total_prestamos=total_prestamos,
                         prestamos_por_estado=prestamos_por_estado,
                         prestamos_por_tipo=prestamos_por_tipo,
                         top_padrones=top_padrones,
                         ultimos_movimientos=ultimos_movimientos)
