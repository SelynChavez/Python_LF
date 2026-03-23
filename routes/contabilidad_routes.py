from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from functools import wraps
from flask import current_app
from mysql.connector import Error
import sqlconstants

from .contabilidad import bp as contabilidad_bp

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


@contabilidad_bp.route('/cuentas_contables', methods=['GET', 'POST'])
@login_required
@admin_required
def cuentas_contables():
    cuentas = []
    if request.method == 'POST':
        p1 = request.form.get('p1', '')  
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = sqlconstants.LISTA_CTAS_CONTABLES
            query = query.replace("$p1$", str(p1))
            print(query)
            cursor.execute(query)
            cuentas = cursor.fetchall()
            cursor.close()
            connection.close() 
            return render_template('cuentas_contables.html', cuentas=cuentas, p1=p1)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard.dashboard'))
    else:
        flash('Listo para consultar.', 'success')
        return render_template('cuentas_contables.html', p1='', cuentas=[])


@contabilidad_bp.route('/cuentas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_cuenta(id):
    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('contabilidad.cuentas_contables'))    
    if request.method == 'POST':
        ele = request.form.get('ele')
        cta = request.form.get('cta')
        nom = request.form.get('nom')
        din = request.form.get('din')
        ent = request.form.get('ent')
        cod = request.form.get('cod')
        aux = request.form.get('aux')
        obs = request.form.get('obs')
        try:
            cursor = connection.cursor()
            cursor.execute(sqlconstants.UPDATE_CUENTA_CONTABLE, (ele, cta, nom, din, ent, cod, aux, obs, id))            
            connection.commit()
            cursor.close()
            connection.close()
            flash('Cuenta contable actualizada exitosamente.', 'success')
            return redirect(url_for('contabilidad.cuentas_contables'))
        except Error as e:
            if 'Duplicate entry' in str(e):
                flash('La cuenta ya existe.', 'danger')
            else:
                flash(f'Error al actualizar cta: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
            return redirect(url_for('contabilidad.editar_cuenta', id=id))
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.SELECT_CUENTA_CONTABLE, (id,))
    cuenta = cursor.fetchone()
    cursor.close()
    connection.close()
    if not cuenta:
        flash('Cuenta no encontrada.', 'danger')
        return redirect(url_for('contabilidad.cuentas_contables'))
    return render_template('editar_cuenta.html', cuenta=cuenta)


@contabilidad_bp.route('/cuentas/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_cuenta(id):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.SEL_NM_CUENTA_CONTABLE, (id,))
            socio = cursor.fetchone()
            cursor.execute(sqlconstants.DELETE_CUENTA_CONTABLE, (id,))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Cuenta eliminada exitosamente.', 'success')
        except Error as e:
            flash(f'Error al eliminar cuenta: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
    else:
        flash('Error de conexión a la base de datos.', 'danger')   
    return redirect(url_for('contabilidad.cuentas_contables'))
