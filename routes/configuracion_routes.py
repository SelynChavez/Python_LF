from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from functools import wraps
from flask import current_app
from mysql.connector import Error
import sqlconstants

from .configuracion import bp as configuracion_bp

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

def hash_password(password):
    return password.encode()

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

def task_scheduler_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = session.get('user_username')
        usuarios_permitidos = ['selyn', 'matias']
        if username not in usuarios_permitidos:
            flash('Acceso denegado. El Programador de Tareas no está disponible para tu usuario.', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@configuracion_bp.route('/tipos_deudas')
@login_required
@admin_required
def listar_tipos_deudas():
    tipo = 'DEUDA'
    a3 = "Cod.PCGE"
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_TIPOS, (tipo,) )
        tipos = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('tipos_deudas.html', tipos=tipos, tipo=tipo, a3=a3)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return redirect(url_for('dashboard.dashboard'))


@configuracion_bp.route('/tiposdeudas/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_tipo_deuda():
    return render_template('tipo_deuda_form.html', tipo=None)


@configuracion_bp.route('/tiposdeudas/guardar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def guardar_tipo_deuda(id):
    if id > 0:
        connection = get_db_connection()
        if not connection:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('configuracion.listar_tipos_deudas'))
        
        if request.method == 'POST':
            codigo = request.form.get('codigo')
            descripcion = request.form.get('descripcion')
            atributo3 = request.form.get('atributo3') or ''
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.UPDATE_TIPO, (codigo, descripcion, '0','0','','',atributo3,'','', id))
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_tipo_deuda', f'LOG::Editó el tipo: {codigo}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Tipo actualizado exitosamente.', 'success')
                return redirect(url_for('configuracion.listar_tipos_deudas'))
            except Error as e:
                if 'Duplicate entry' in str(e):
                    flash('Codigo ya existe.', 'danger')
                else:
                    flash(f'Error al actualizar tipo: {str(e)}', 'danger')
                connection.rollback()
                cursor.close()
                connection.close()
                return redirect(url_for('configuracion.guardar_tipo_deuda', id=id))
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SELECT_TIPO, (id,))
        tipo = cursor.fetchone()
        cursor.close()
        connection.close()
        if not tipo:
            flash('Tipo/Codigo no encontrado.', 'danger')
            return redirect(url_for('configuracion.listar_tipos_deudas'))
        return render_template('tipo_deuda_form.html', tipo=tipo)
    else:
        if request.method == 'POST':
            tipo = 'DEUDA'
            codigo = request.form.get('codigo')
            descripcion = request.form.get('descripcion')
            atributo3 = request.form.get('atributo3') or ''
            if not all([codigo, descripcion]):
                flash('Por favor, complete todos los campos.', 'danger')
                return render_template('tipo_deuda_form.html', tipo=None)
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_TIPO, (tipo, codigo, descripcion, '0', '0', '', '', atributo3, '', '', session['user_username']))
                    connection.commit()
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_tipo_deuda', f'LOG::Creó el Tipo: {codigo}'))
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Tipo Deuda creado exitosamente.', 'success')
                    return redirect(url_for('configuracion.listar_tipos_deudas'))
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Codigo ya existe.', 'danger')
                    else:
                        flash(f'Error al crear tipo deuda: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            else:
                flash('Error de conexión a la base de datos.', 'danger')    
        return render_template('tipo_deuda_form.html', tipo=None)


@configuracion_bp.route('/tipos/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_tipo(id):
    url = 'configuracion.listar_tipos_aportes'
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.SEL_NM_TIPO, (id,))
            tipo = cursor.fetchone()
            tp = tipo["tipo"]
            if (tp == "DEUDA"):
                url = 'configuracion.listar_tipos_deudas'
            print(tp)
            cursor.execute(sqlconstants.DELETE_TIPO, (id,))
            connection.commit()
            if tipo:
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'eliminar_tipo', f'Eliminó el Tipo: {tipo["codigo"]}'))
                connection.commit()
            cursor.close()
            connection.close()
            flash('Tipo eliminado exitosamente.', 'success')
        except Error as e:
            flash(f'Error al eliminar Tipo: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
    else:
        flash('Error de conexión a la base de datos.', 'danger')   
    return redirect(url_for(url))


@configuracion_bp.route('/tipos_ingresos')
@login_required
@admin_required
def listar_tipos_ingresos():
    tipo = 'INGRESO'
    a2 = "Cta.Contable"
    a3 = "Indice Cta.Cble"
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_TIPOS, (tipo,) )
        tipos = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('tipos_ingresos.html', tipos=tipos, tipo=tipo, a2=a2, a3=a3)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return redirect(url_for('dashboard.dashboard'))


@configuracion_bp.route('/tiposingresos/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_tipo_ingreso():
    return render_template('tipo_ingreso_form.html', tipo=None)


@configuracion_bp.route('/tiposingresos/guardar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def guardar_tipo_ingreso(id):
    if id > 0:
        connection = get_db_connection()
        if not connection:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('configuracion.listar_tipos_ingresos'))
        
        if request.method == 'POST':
            codigo = request.form.get('codigo')
            descripcion = request.form.get('descripcion')
            atributo2 = request.form.get('atributo2') or ''
            atributo3 = request.form.get('atributo3') or ''
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.UPDATE_TIPO, (codigo, descripcion, '0','0','',atributo2,atributo3,'','', id))
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_tipo_ingreso', f'LOG::Editó el tipo: {codigo}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Tipo actualizado exitosamente.', 'success')
                return redirect(url_for('configuracion.listar_tipos_ingresos'))
            except Error as e:
                if 'Duplicate entry' in str(e):
                    flash('Codigo ya existe.', 'danger')
                else:
                    flash(f'Error al actualizar tipo: {str(e)}', 'danger')
                connection.rollback()
                cursor.close()
                connection.close()
                return redirect(url_for('configuracion.guardar_tipo_ingreso', id=id))
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SELECT_TIPO, (id,))
        tipo = cursor.fetchone()
        cursor.close()
        connection.close()
        if not tipo:
            flash('Tipo/Codigo no encontrado.', 'danger')
            return redirect(url_for('configuracion.listar_tipos_ingresos'))
        return render_template('tipo_ingreso_form.html', tipo=tipo)
    else:
        if request.method == 'POST':
            tipo = 'INGRESO'
            codigo = request.form.get('codigo')
            descripcion = request.form.get('descripcion')
            atributo2 = request.form.get('atributo2') or ''
            atributo3 = request.form.get('atributo3') or ''
            if not all([codigo, descripcion]):
                flash('Por favor, complete todos los campos.', 'danger')
                return render_template('tipo_ingreso_form.html', tipo=None)
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_TIPO, (tipo, codigo, descripcion, '0', '0', '', atributo2, atributo3, '', '', session['user_username']))
                    connection.commit()
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_tipo_ingreso', f'LOG::Creó el Tipo: {codigo}'))
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Tipo Ingreso creado exitosamente.', 'success')
                    return redirect(url_for('configuracion.listar_tipos_ingresos'))
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Codigo ya existe.', 'danger')
                    else:
                        flash(f'Error al crear tipo: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            else:
                flash('Error de conexión a la base de datos.', 'danger')    
        return render_template('tipo_ingreso_form.html', tipo=None)


@configuracion_bp.route('/tipos_salidas')
@login_required
@admin_required
def listar_tipos_salidas():
    tipo = 'SALIDA'
    a3 = "Cta.Contable"
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_TIPOS, (tipo,) )
        tipos = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('tipos_salidas.html', tipos=tipos, tipo=tipo, a3=a3 )
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return redirect(url_for('dashboard.dashboard'))


@configuracion_bp.route('/tipossalidas/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_tipo_salida():
    return render_template('tipo_salida_form.html', tipo=None)


@configuracion_bp.route('/tipossalidas/guardar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def guardar_tipo_salida(id):
    if id > 0:
        connection = get_db_connection()
        if not connection:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('configuracion.listar_tipos_salidas'))

        if request.method == 'POST':
            codigo = request.form.get('codigo')
            descripcion = request.form.get('descripcion')
            atributo3 = request.form.get('atributo3') or ''
            atributo4 = request.form.get('atributo4') or ''
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.UPDATE_TIPO, (codigo, descripcion, '0','0','','',atributo3,atributo4,'', id))
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_tipo_salida', f'LOG::Editó el tipo: {codigo}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Tipo actualizado exitosamente.', 'success')
                return redirect(url_for('configuracion.listar_tipos_salidas'))
            except Error as e:
                if 'Duplicate entry' in str(e):
                    flash('Codigo ya existe.', 'danger')
                else:
                    flash(f'Error al actualizar tipo: {str(e)}', 'danger')
                connection.rollback()
                cursor.close()
                connection.close()
                return redirect(url_for('configuracion.guardar_tipo_salida', id=id))
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SELECT_TIPO, (id,))
        tipo = cursor.fetchone()
        cursor.close()
        connection.close()
        if not tipo:
            flash('Tipo/Codigo no encontrado.', 'danger')
            return redirect(url_for('configuracion.listar_tipos_salidas'))
        return render_template('tipo_salida_form.html', tipo=tipo)
    else:
        if request.method == 'POST':
            tipo = 'SALIDA'
            codigo = request.form.get('codigo')
            descripcion = request.form.get('descripcion')
            atributo3 = request.form.get('atributo3') or ''
            atributo4 = request.form.get('atributo4') or ''
            if not all([codigo, descripcion]):
                flash('Por favor, complete todos los campos.', 'danger')
                return render_template('tipo_salida_form.html', tipo=None)
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_TIPO, (tipo, codigo, descripcion, '0', '0', '', '', atributo3, atributo4, '', session['user_username']))
                    connection.commit()
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_tipo_salida', f'LOG::Creó el Tipo: {codigo}'))
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Tipo Salida creado exitosamente.', 'success')
                    return redirect(url_for('configuracion.listar_tipos_salidas'))
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Codigo ya existe.', 'danger')
                    else:
                        flash(f'Error al crear tipo: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            else:
                flash('Error de conexión a la base de datos.', 'danger')    
        return render_template('tipo_salida_form.html', tipo=None)


@configuracion_bp.route('/tipos_terceros')
@login_required
@admin_required
def listar_tipos_terceros():
    tipo = 'TERCERO'
    a1 = "RUC/Identificacion"
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_TIPOS, (tipo,) )
        tipos = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('tipos_terceros.html', tipos=tipos, tipo=tipo, a1=a1 )
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return redirect(url_for('dashboard.dashboard'))


@configuracion_bp.route('/tiposterceros/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_tipo_tercero():
    return render_template('tipo_tercero_form.html', tipo=None)


@configuracion_bp.route('/tipostercero/guardar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def guardar_tipo_tercero(id):
    if id > 0:
        connection = get_db_connection()
        if not connection:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('configuracion.listar_tipos_terceros'))
        
        if request.method == 'POST':
            codigo = request.form.get('codigo')
            descripcion = request.form.get('descripcion')
            atributo1 = request.form.get('atributo1') or ''
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.UPDATE_TIPO, (codigo, descripcion, '0','0',atributo1,'','','','', id))
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_tipo_tercero', f'LOG::Editó el tercero id: {id} con {codigo}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Tercero actualizado exitosamente.', 'success')
                return redirect(url_for('configuracion.listar_tipos_terceros'))
            except Error as e:
                if 'Duplicate entry' in str(e):
                    flash('Codigo ya existe.', 'danger')
                else:
                    flash(f'Error al actualizar tipo: {str(e)}', 'danger')
                connection.rollback()
                cursor.close()
                connection.close()
                return redirect(url_for('configuracion.guardar_tipo_tercero', id=id))
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SELECT_TIPO, (id,))
        tipo = cursor.fetchone()
        cursor.close()
        connection.close()
        if not tipo:
            flash('Tipo/Codigo no encontrado.', 'danger')
            return redirect(url_for('configuracion.listar_tipos_terceros'))
        return render_template('tipo_tercero_form.html', tipo=tipo)
    else:
        if request.method == 'POST':
            tipo = 'TERCERO'
            codigo = request.form.get('codigo')
            descripcion = request.form.get('descripcion')
            atributo1 = request.form.get('atributo1') or ''
            if not all([codigo, descripcion]):
                flash('Por favor, complete todos los campos.', 'danger')
                return render_template('tipo_tercero_form.html', tipo=None)
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_TIPO, (tipo, codigo, descripcion, '0', '0', atributo1, '', '', '', '', session['user_username']))
                    xid = cursor.lastrowid
                    connection.commit()
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_tipo_tercero', f'LOG::Creó el tercero id:{xid} con {codigo}'))
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Tercero creado exitosamente.', 'success')
                    return redirect(url_for('configuracion.listar_tipos_terceros'))
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Codigo ya existe.', 'danger')
                    else:
                        flash(f'Error al crear tipo: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            else:
                flash('Error de conexión a la base de datos.', 'danger')    
        return render_template('tipo_tercero_form.html', tipo=None)


@configuracion_bp.route('/tipos_aportes')
@login_required
@admin_required
def listar_tipos_aportes():
    tipo = 'APORTE'
    m1 = "Aporte Fijo"
    a1 = "Serie"
    a3 = "Cod.PCGE"
    a4 = "Retiros?"
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_TIPOS_APORTE, (tipo,) )
        tipos = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('tipos_aportes.html', tipos=tipos, tipo=tipo, m1=m1, a1= a1, a3=a3, a4=a4)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return redirect(url_for('dashboard.dashboard'))


@configuracion_bp.route('/tipos/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_tipo_aporte():
    return render_template('tipo_aporte_form.html', tipo=None)


@configuracion_bp.route('/tipos/guardar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def guardar_tipo_aporte(id):
    if id > 0:
        connection = get_db_connection()
        if not connection:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('configuracion.listar_tipos_aportes'))
        
        if request.method == 'POST':
            codigo = request.form.get('codigo')
            descripcion = request.form.get('descripcion')
            monto1 = request.form.get('monto1') or '0'
            atributo1 = request.form.get('atributo1') or '1'
            atributo2 = request.form.get('atributo2') or ''
            atributo3 = request.form.get('atributo3') or ''
            atributo4 = request.form.get('atributo4') or 'N'
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.UPDATE_TIPO, (codigo, descripcion, monto1, '0', atributo1, atributo2, atributo3, atributo4, '', id))
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_tipo_aporte', f'LOG::Editó el tipo: {codigo}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Tipo actualizado exitosamente.', 'success')
                return redirect(url_for('configuracion.listar_tipos_aportes'))
            except Error as e:
                if 'Duplicate entry' in str(e):
                    flash('Codigo ya existe.', 'danger')
                else:
                    flash(f'Error al actualizar tipo: {str(e)}', 'danger')
                connection.rollback()
                cursor.close()
                connection.close()
                return redirect(url_for('configuracion.guardar_tipo_aporte', id=id))
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SELECT_TIPO, (id,))
        tipo = cursor.fetchone()
        cursor.close()
        connection.close()
        if not tipo:
            flash('Tipo/Codigo no encontrado.', 'danger')
            return redirect(url_for('configuracion.listar_tipos_aportes'))
        return render_template('tipo_aporte_form.html', tipo=tipo)
    else:
        if request.method == 'POST':
            tipo = 'APORTE'
            codigo = request.form.get('codigo')
            descripcion = request.form.get('descripcion')
            monto1 = request.form.get('monto1') or '0'
            atributo1 = request.form.get('atributo1') or '1'
            atributo2 = request.form.get('atributo2') or ''
            atributo3 = request.form.get('atributo3') or ''
            atributo4 = request.form.get('atributo4') or 'N'
            if not all([codigo, descripcion]):
                flash('Por favor, complete todos los campos.', 'danger')
                return render_template('tipo_aporte_form.html', tipo=None)
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_TIPO, (tipo, codigo, descripcion, monto1, '0', atributo1, atributo2, atributo3, atributo4, '', session['user_username']))
                    connection.commit()
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_tipo_aporte', f'LOG::Creó el Tipo: {codigo}'))
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Tipo Aporte creado exitosamente.', 'success')
                    return redirect(url_for('configuracion.listar_tipos_aportes'))
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Codigo ya existe.', 'danger')
                    else:
                        flash(f'Error al crear tipo aporte: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            else:
                flash('Error de conexión a la base de datos.', 'danger')    
        return render_template('tipo_aporte_form.html', tipo=None)


@configuracion_bp.route('/padrones')
@login_required
@admin_required
def listar_padrones():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_PADRONES)
        padrones = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('padrones.html', padrones=padrones)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('dashboard.dashboard'))


@configuracion_bp.route('/padrones/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_padron():
    return render_template('padron_form.html', padron=None)


@configuracion_bp.route('/padrones/guardar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def guardar_padron(id):
    if id > 0:
        connection = get_db_connection()
        if not connection:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('configuracion.listar_padrones'))
        
        if request.method == 'POST':
            placa = request.form.get('placa')
            socio = request.form.get('socio')
            active = request.form.get('active')
            monto1 = request.form.get('monto1')
            monto2 = request.form.get('monto2')
            monto3 = request.form.get('monto3')
            monto4 = request.form.get('monto4')
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.UPDATE_PADRON, (placa, socio, active, monto1, monto2, monto3, monto4, id))
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_placa', f'Editó el padron: {placa}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Padrón actualizado exitosamente.', 'success')
                return redirect(url_for('configuracion.listar_padrones'))
            except Error as e:
                if 'Duplicate entry' in str(e):
                    flash('La placa/socio ya existe.', 'danger')
                else:
                    flash(f'Error al actualizar padron: {str(e)}', 'danger')
                connection.rollback()
                cursor.close()
                connection.close()
                return redirect(url_for('configuracion.guardar_padron', id=id))
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SELECT_PADRON, (id,))
        padron = cursor.fetchone()
        cursor.close()
        connection.close()
        if not padron:
            flash('Padrón no encontrado.', 'danger')
            return redirect(url_for('configuracion.listar_padrones'))
        return render_template('padron_form.html', padron=padron)
    else:
        if request.method == 'POST':
            placa = request.form.get('placa')
            socio = request.form.get('socio')
            active = request.form.get('active')
            monto1 = request.form.get('monto1')
            monto2 = request.form.get('monto2')
            monto3 = request.form.get('monto3')
            monto4 = request.form.get('monto4')
            if not all([placa, socio]):
                flash('Por favor, complete todos los campos.', 'danger')
                return render_template('padron_form.html', padron=None)
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_PADRON, (placa, socio, active, monto1, monto2, monto3, monto4, session['user_username']))
                    connection.commit()                
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_padron', f'Creó el padron: {placa}'))
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Padrón creado exitosamente.', 'success')
                    return redirect(url_for('configuracion.listar_padrones'))
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Placa - socio ya existe.', 'danger')
                    else:
                        flash(f'Error al crear placa: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            else:
                flash('Error de conexión a la base de datos.', 'danger')    
        return render_template('padron_form.html', padron=None)


@configuracion_bp.route('/padrones/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_padron(id):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.SEL_NM_PADRON, (id,))
            padron = cursor.fetchone()
            cursor.execute(sqlconstants.DELETE_PADRON, (id,))
            connection.commit()
            if padron:
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'eliminar_padron', f'Eliminó el padron: {padron["placa"]}'))
                connection.commit()
            cursor.close()
            connection.close()
            flash('Padron eliminado exitosamente.', 'success')
        except Error as e:
            flash(f'Error al eliminar padron: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
    else:
        flash('Error de conexión a la base de datos.', 'danger')   
    return redirect(url_for('configuracion.listar_padrones'))


@configuracion_bp.route('/socios')
@login_required
@admin_required
def listar_socios():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_SOCIOS)
        socios = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('socios.html', socios=socios)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('dashboard.dashboard'))


@configuracion_bp.route('/socios/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_socio():
    return render_template('socio_form.html', socio=None)


@configuracion_bp.route('/socios/guardar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def guardar_socio(id):
    if id > 0:
        connection = get_db_connection()
        if not connection:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('configuracion.listar_socios'))
        
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            fono = request.form.get('fono')
            dni = request.form.get('dni')
            comentarios = request.form.get('comentarios')
            tipo = request.form.get('tipo')
            email = request.form.get('email')
            active = request.form.get('active')
            usuario = request.form.get('usuario')
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.UPDATE_SOCIO, (nombre, fono, dni, comentarios, tipo, active, email, usuario, id))            
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_socio', f'Editó el socio: {nombre}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Socio actualizado exitosamente.', 'success')
                return redirect(url_for('configuracion.listar_socios'))
            except Error as e:
                if 'Duplicate entry' in str(e):
                    flash('El nombre/dni de socio ya existe.', 'danger')
                else:
                    flash(f'Error al actualizar socio: {str(e)}', 'danger')
                connection.rollback()
                cursor.close()
                connection.close()
                return redirect(url_for('configuracion.guardar_socio', id=id))
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SELECT_SOCIO, (id,))
        socio = cursor.fetchone()
        cursor.close()
        connection.close()
        if not socio:
            flash('Socio no encontrado.', 'danger')
            return redirect(url_for('configuracion.listar_socios'))
        return render_template('socio_form.html', socio=socio)
    else:
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            dni = request.form.get('dni')
            fono = request.form.get('fono')
            tipo = request.form.get('tipo')
            email = request.form.get('email')
            comentarios = request.form.get('comentarios')
            if not all([dni, fono, nombre, tipo, email, comentarios]):
                flash('Por favor, complete todos los campos.', 'danger')
                return render_template('socio_form.html', socio=None)
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_SOCIO, (nombre, fono, dni, comentarios, tipo, email, session['user_username']))
                    connection.commit()                
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_socio', f'Creó el socio: {nombre}'))
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Socio creado exitosamente.', 'success')
                    return redirect(url_for('configuracion.listar_socios'))
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('El nombre/dni de socio o email ya existe.', 'danger')
                    else:
                        flash(f'Error al crear socio: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            else:
                flash('Error de conexión a la base de datos.', 'danger')    
        return render_template('socio_form.html', socio=None)


@configuracion_bp.route('/socios/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_socio(id):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.SEL_NM_SOCIO, (id,))
            socio = cursor.fetchone()
            cursor.execute(sqlconstants.DELETE_SOCIO, (id,))
            connection.commit()
            if socio:
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'eliminar_socio', f'Eliminó el socio: {socio["nombre"]}'))
                connection.commit()
            cursor.close()
            connection.close()
            flash('Socio eliminado exitosamente.', 'success')
        except Error as e:
            flash(f'Error al eliminar socio: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
    else:
        flash('Error de conexión a la base de datos.', 'danger')   
    return redirect(url_for('configuracion.listar_socios'))


@configuracion_bp.route('/choferes')
@login_required
@admin_required
def listar_choferes():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_CHOFERES)
        choferes = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('choferes.html', choferes=choferes)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('dashboard.dashboard'))


@configuracion_bp.route('/choferes/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_chofer():
    return render_template('chofer_form.html', chofer=None)


@configuracion_bp.route('/choferes/guardar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def guardar_chofer(id):
    if id > 0:
        connection = get_db_connection()
        if not connection:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('configuracion.listar_choferes'))

        if request.method == 'POST':
            nombre = request.form.get('nombre')
            fono = request.form.get('fono')
            dni = request.form.get('dni')
            licencia = request.form.get('licencia')
            comentarios = request.form.get('comentarios')
            tipo = request.form.get('tipo')
            rating = request.form.get('rating')
            active = request.form.get('active')
            email = request.form.get('email')
            usuario = request.form.get('usuario')
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.UPDATE_CHOFER, (nombre, fono, dni, licencia, comentarios, tipo, rating, active, email, usuario, id))
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_chofer', f'Editó el chofer: {nombre}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Chofer actualizado exitosamente.', 'success')
                return redirect(url_for('configuracion.listar_choferes'))
            except Error as e:
                if 'Duplicate entry' in str(e):
                    flash('El nombre/dni de chofer ya existe.', 'danger')
                else:
                    flash(f'Error al actualizar chofer: {str(e)}', 'danger')
                connection.rollback()
                cursor.close()
                connection.close()
                return redirect(url_for('configuracion.guardar_chofer', id=id))

        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SELECT_CHOFER, (id,))
        chofer = cursor.fetchone()
        cursor.close()
        connection.close()
        if not chofer:
            flash('Chofer no encontrado.', 'danger')
            return redirect(url_for('configuracion.listar_choferes'))
        return render_template('chofer_form.html', chofer=chofer)
    else:
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            dni = request.form.get('dni')
            fono = request.form.get('fono')
            licencia = request.form.get('licencia')
            tipo = request.form.get('tipo')
            rating = request.form.get('rating')
            email = request.form.get('email')
            comentarios = request.form.get('comentarios')
            if not all([dni, fono, nombre, tipo, email, comentarios]):
                flash('Por favor, complete todos los campos.', 'danger')
                return render_template('chofer_form.html', chofer=None)
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_CHOFER, (nombre, fono, dni, licencia, comentarios, tipo, rating, email, session['user_username']))
                    connection.commit()
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_chofer', f'Creó el chofer: {nombre}'))
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Chofer creado exitosamente.', 'success')
                    return redirect(url_for('configuracion.listar_choferes'))
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('El nombre/dni de chofer o email ya existe.', 'danger')
                    else:
                        flash(f'Error al crear chofer: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            else:
                flash('Error de conexión a la base de datos.', 'danger')
        return render_template('chofer_form.html', chofer=None)


@configuracion_bp.route('/choferes/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_chofer(id):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.SEL_NM_CHOFER, (id,))
            chofer = cursor.fetchone()
            cursor.execute(sqlconstants.DELETE_CHOFER, (id,))
            connection.commit()
            if chofer:
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'eliminar_chofer', f'Eliminó el chofer: {chofer["nombre"]}'))
                connection.commit()
            cursor.close()
            connection.close()
            flash('Chofer eliminado exitosamente.', 'success')
        except Error as e:
            flash(f'Error al eliminar chofer: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return redirect(url_for('configuracion.listar_choferes'))


@configuracion_bp.route('/proveedores')
@login_required
@admin_required
def listar_proveedores():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_PROVEEDORES)
        proveedores = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('proveedores.html', proveedores=proveedores)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('dashboard.dashboard'))


@configuracion_bp.route('/proveedores/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_proveedor():
    return render_template('proveedor_form.html', proveedor=None)


@configuracion_bp.route('/proveedores/guardar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def guardar_proveedor(id):
    if id > 0:
        connection = get_db_connection()
        if not connection:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('configuracion.listar_proveedores'))
        
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            ruc = request.form.get('ruc')
            fono = request.form.get('fono')
            cargo = request.form.get('cargo')
            email = request.form.get('email')
            direccion = request.form.get('direccion')
            contacto = request.form.get('contacto')
            tipo = request.form.get('tipo')
            observaciones = request.form.get('observaciones')
            active = request.form.get('active')
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.UPDATE_PROVEEDOR, (nombre, ruc, contacto, cargo, fono, email, tipo, direccion, observaciones, active, session['user_username'], id))            
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_proveedor', f'Editó el proveedor: {nombre}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Proveedor actualizado exitosamente.', 'success')
                return redirect(url_for('configuracion.listar_proveedores'))
            except Error as e:
                if 'Duplicate entry' in str(e):
                    flash('El nombre/dni ya existe.', 'danger')
                else:
                    flash(f'Error al actualizar proveedor: {str(e)}', 'danger')
                connection.rollback()
                cursor.close()
                connection.close()
                return redirect(url_for('configuracion.guardar_proveedor', id=id))
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SELECT_PROVEEDOR, (id,))
        proveedor = cursor.fetchone()
        cursor.close()
        connection.close()
        if not proveedor:
            flash('Proveedor no encontrado.', 'danger')
            return redirect(url_for('configuracion.listar_proveedores'))
        return render_template('proveedor_form.html', proveedor=proveedor)
    else:
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            ruc = request.form.get('ruc')
            fono = request.form.get('fono')
            cargo = request.form.get('cargo')
            email = request.form.get('email')
            direccion = request.form.get('direccion')
            contacto = request.form.get('contacto')
            tipo = request.form.get('tipo')
            observaciones = request.form.get('observaciones')
            if not all([ruc, fono, nombre, cargo, email, direccion, contacto, tipo]):
                flash('Por favor, complete todos los campos.', 'danger')
                return render_template('proveedor_form.html', proveedor=None)
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_PROVEEDOR, (nombre, ruc, contacto, cargo, fono, email, tipo, direccion, observaciones, session['user_username']))
                    connection.commit() 
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_proveedor', f'Creó el proveedor: {nombre}'))  
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Proveedor creado exitosamente.', 'success')
                    return redirect(url_for('configuracion.listar_proveedores'))
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('El nombre/dni / email ya existe.', 'danger')
                    else:
                        flash(f'Error al crear proveedor: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            else:
                flash('Error de conexión a la base de datos.', 'danger')    
        return render_template('proveedor_form.html', proveedor=None)


@configuracion_bp.route('/proveedor/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_proveedor(id):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.SEL_NM_PROVEEDOR, (id,))
            proveedor = cursor.fetchone()
            cursor.execute(sqlconstants.DELETE_PROVEEDOR, (id,))
            connection.commit()
            if proveedor:
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'eliminar_proveedor', f'Eliminó el proveedor: {proveedor["nombre"]}'))
                connection.commit()
            cursor.close()
            connection.close()
            flash('Proveedor eliminado exitosamente.', 'success')
        except Error as e:
            flash(f'Error al eliminar proveedor: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
    else:
        flash('Error de conexión a la base de datos.', 'danger')   
    return redirect(url_for('configuracion.listar_proveedores'))


@configuracion_bp.route('/empleados')
@login_required
@admin_required
def listar_empleados():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_EMPLEADOS)
        empleados = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('empleados.html', empleados=empleados)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('dashboard.dashboard'))


@configuracion_bp.route('/empleados/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_empleado():
    return render_template('empleado_form.html', empleado=None)


@configuracion_bp.route('/empleados/guardar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def guardar_empleado(id):
    if id > 0:
        connection = get_db_connection()
        if not connection:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('configuracion.listar_empleados'))
        
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            fono = request.form.get('fono')
            dni = request.form.get('dni')
            email = request.form.get('email')
            active = request.form.get('active')
            cargo = request.form.get('cargo')
            direccion = request.form.get('direccion')
            afp = request.form.get('afp')
            sueldo = request.form.get('sueldo')
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.UPDATE_EMPLEADO, (nombre, fono, dni, email, cargo, direccion, afp, sueldo, active, id))            
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_empleado', f'Editó el empleado: {nombre}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Empleado actualizado exitosamente.', 'success')
                return redirect(url_for('configuracion.listar_empleados'))
            except Error as e:
                if 'Duplicate entry' in str(e):
                    flash('El nombre/dni ya existe.', 'danger')
                else:
                    flash(f'Error al actualizar empleado: {str(e)}', 'danger')
                connection.rollback()
                cursor.close()
                connection.close()
                return redirect(url_for('configuracion.guardar_empleado', id=id))
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SELECT_EMPLEADO, (id,))
        empleado = cursor.fetchone()
        cursor.close()
        connection.close()
        if not empleado:
            flash('Empleado no encontrado.', 'danger')
            return redirect(url_for('configuracion.listar_empleados'))
        return render_template('empleado_form.html', empleado=empleado)
    else:
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            dni = request.form.get('dni')
            fono = request.form.get('fono')
            cargo = request.form.get('cargo')
            email = request.form.get('email')
            direccion = request.form.get('direccion')
            afp = request.form.get('afp')
            sueldo = request.form.get('sueldo')
            if not all([dni, fono, nombre, cargo, email, direccion, afp, sueldo]):
                flash('Por favor, complete todos los campos.', 'danger')
                return render_template('empleado_form.html', empleado=None)
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_EMPLEADO, (nombre, fono, dni, email, cargo, direccion, afp, sueldo, session['user_username']))
                    connection.commit() 
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_empleado', f'Creó el empleado: {nombre}'))  
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Empleado creado exitosamente.', 'success')
                    return redirect(url_for('configuracion.listar_empleados'))
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('El nombre/dni / email ya existe.', 'danger')
                    else:
                        flash(f'Error al crear empleado: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            else:
                flash('Error de conexión a la base de datos.', 'danger')    
        return render_template('empleado_form.html', empleado=None)


@configuracion_bp.route('/empleado/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_empleado(id):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.SEL_NM_EMPLEADO, (id,))
            empleado = cursor.fetchone()
            cursor.execute(sqlconstants.DELETE_EMPLEADO, (id,))
            connection.commit()
            if empleado:
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'eliminar_empleado', f'Eliminó el empleado: {empleado["nombre"]}'))
                connection.commit()
            cursor.close()
            connection.close()
            flash('Empleado eliminado exitosamente.', 'success')
        except Error as e:
            flash(f'Error al eliminar empleado: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
    else:
        flash('Error de conexión a la base de datos.', 'danger')   
    return redirect(url_for('configuracion.listar_empleados'))


@configuracion_bp.route('/usuarios')
@login_required
@admin_required
def listar_usuarios():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_USUARIOS)
        usuarios = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('usuarios.html', usuarios=usuarios)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('dashboard.dashboard'))


@configuracion_bp.route('/usuarios/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_usuario():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        rol = request.form.get('rol')        
        if not all([username, password, nombre, email, rol]):
            flash('Por favor, complete todos los campos.', 'danger')
            return render_template('crear_usuario.html')
        hashed_password = hash_password(password)
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.INSERT_USUARIO, (username, hashed_password, nombre, email, rol))
                connection.commit()                
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_usuario', f'Creó el usuario: {username}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Usuario creado exitosamente.', 'success')
                return redirect(url_for('configuracion.listar_usuarios'))
            except Error as e:
                if 'Duplicate entry' in str(e):
                    flash('El nombre de usuario o email ya existe.', 'danger')
                else:
                    flash(f'Error al crear usuario: {str(e)}', 'danger')
                connection.rollback()
                cursor.close()
                connection.close()
        else:
            flash('Error de conexión a la base de datos.', 'danger')    
    return render_template('crear_usuario.html')


@configuracion_bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(id):
    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('configuracion.listar_usuarios'))    
    if request.method == 'POST':
        username = request.form.get('username')
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        rol = request.form.get('rol')
        activo = request.form.get('activo')
        cambiar_password = request.form.get('cambiar_password')
        nueva_password = request.form.get('nueva_password')
        try:
            cursor = connection.cursor()
            if cambiar_password and nueva_password:
                hashed_password = hash_password(nueva_password)
                cursor.execute(sqlconstants.UPDAT1_USUARIO, (username, nombre, email, rol, activo, hashed_password, id))
            else:
                cursor.execute(sqlconstants.UPDAT2_USUARIO, (username, nombre, email, rol, activo, id))
            connection.commit()
            cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_usuario', f'Editó el usuario: {username}'))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Usuario actualizado exitosamente.', 'success')
            return redirect(url_for('configuracion.listar_usuarios'))
        except Error as e:
            if 'Duplicate entry' in str(e):
                flash('El nombre de usuario o email ya existe.', 'danger')
            else:
                flash(f'Error al actualizar usuario: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
            return redirect(url_for('configuracion.editar_usuario', id=id))    
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.SELECT_USUARIO, (id,))
    usuario = cursor.fetchone()
    cursor.close()
    connection.close()
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('configuracion.listar_usuarios'))
    return render_template('editar_usuario.html', usuario=usuario)


@configuracion_bp.route('/usuarios/desactivar/<int:id>')
@login_required
@admin_required
def desactivar_usuario(id):
    if id == session['user_id']:
        flash('No puede desactivar su propio usuario.', 'danger')
        return redirect(url_for('configuracion.listar_usuarios'))
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.SEL_NM_USUARIO, (id,))
            usuario = cursor.fetchone()
            cursor.execute("UPDATE applicationuser SET status = %s WHERE id = %s", ('INACTIVE', id))
            connection.commit()
            if usuario:
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'desactivar_usuario', f'Desactivó el usuario: {usuario["username"]}'))
                connection.commit()
            cursor.close()
            connection.close()
            flash('Usuario desactivado exitosamente.', 'success')
        except Error as e:
            flash(f'Error al desactivar usuario: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return redirect(url_for('configuracion.listar_usuarios'))


@configuracion_bp.route('/usuarios/activar/<int:id>')
@login_required
@admin_required
def activar_usuario(id):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.SEL_NM_USUARIO, (id,))
            usuario = cursor.fetchone()
            cursor.execute("UPDATE applicationuser SET status = %s WHERE id = %s", ('ACTIVE', id))
            connection.commit()
            if usuario:
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'activar_usuario', f'Activó el usuario: {usuario["username"]}'))
                connection.commit()
            cursor.close()
            connection.close()
            flash('Usuario activado exitosamente.', 'success')
        except Error as e:
            flash(f'Error al activar usuario: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return redirect(url_for('configuracion.listar_usuarios'))


# ========== TASK SCHEDULER ==========
@configuracion_bp.route('/programar_tareas')
@login_required
@task_scheduler_required
def programar_tareas():
    connection = get_db_connection()
    tareas = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(sqlconstants.LISTAR_PROGRAMAS_TAREAS)
            tareas = cursor.fetchall()
        except Error as e:
            flash(f'Error al cargar tareas: {str(e)}', 'danger')
        finally:
            cursor.close()
            connection.close()
    return render_template('programar_tareas.html', tareas=tareas)


@configuracion_bp.route('/crear_tarea', methods=['GET', 'POST'])
@login_required
@task_scheduler_required
def crear_tarea():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        tipo = request.form.get('tipo', '').strip()
        sql_query = request.form.get('sql_query', '').strip()
        hora_ejecucion = request.form.get('hora_ejecucion', '').strip()
        dias_semana = request.form.get('dias_semana', '').strip()

        if not nombre or not tipo or not sql_query:
            flash('Por favor complete los campos obligatorios', 'warning')
            return render_template('crear_tarea.html')

        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            try:
                username = session.get('username') or session.get('user_name') or 'admin'
                cursor.execute(sqlconstants.CREAR_PROGRAMA_TAREA,
                    (nombre, descripcion, tipo, sql_query, hora_ejecucion, dias_semana, 'S', username))
                connection.commit()
                tarea_id = cursor.lastrowid

                # Agendar la tarea
                from task_scheduler import agendar_tarea, scheduler
                tarea_data = {
                    'id': tarea_id,
                    'nombre': nombre,
                    'hora_ejecucion': hora_ejecucion,
                    'dias_semana': dias_semana,
                    'activo': 'S'
                }
                agendar_tarea(tarea_data)

                flash('Tarea creada y agendada exitosamente', 'success')
                return redirect(url_for('configuracion.programar_tareas'))
            except Error as e:
                connection.rollback()
                flash(f'Error al crear tarea: {str(e)}', 'danger')
            finally:
                cursor.close()
                connection.close()
        else:
            flash('Error de conexión a la base de datos', 'danger')

    return render_template('crear_tarea.html')


@configuracion_bp.route('/editar_tarea/<int:id>', methods=['GET', 'POST'])
@login_required
@task_scheduler_required
def editar_tarea(id):
    connection = get_db_connection()
    tarea = None

    if connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(sqlconstants.OBTENER_PROGRAMA_TAREA, (id,))
            tarea = cursor.fetchone()
        except Error as e:
            flash(f'Error al cargar tarea: {str(e)}', 'danger')
        finally:
            cursor.close()
            connection.close()

    if not tarea:
        flash('Tarea no encontrada', 'danger')
        return redirect(url_for('configuracion.programar_tareas'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        tipo = request.form.get('tipo', '').strip()
        sql_query = request.form.get('sql_query', '').strip()
        hora_ejecucion = request.form.get('hora_ejecucion', '').strip()
        dias_semana = request.form.get('dias_semana', '').strip()
        activo = request.form.get('activo', 'S').strip()

        if not nombre or not tipo or not sql_query:
            flash('Por favor complete los campos obligatorios', 'warning')
            return render_template('editar_tarea.html', tarea=tarea)

        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sqlconstants.ACTUALIZAR_PROGRAMA_TAREA,
                    (nombre, descripcion, tipo, sql_query, hora_ejecucion, dias_semana, activo, id))
                connection.commit()

                # Re-agendar la tarea
                from task_scheduler import agendar_tarea
                tarea_data = {
                    'id': id,
                    'nombre': nombre,
                    'hora_ejecucion': hora_ejecucion,
                    'dias_semana': dias_semana,
                    'activo': activo
                }
                agendar_tarea(tarea_data)

                flash('Tarea actualizada y re-agendada exitosamente', 'success')
                return redirect(url_for('configuracion.programar_tareas'))
            except Error as e:
                connection.rollback()
                flash(f'Error al actualizar tarea: {str(e)}', 'danger')
            finally:
                cursor.close()
                connection.close()
        else:
            flash('Error de conexión a la base de datos', 'danger')

    return render_template('editar_tarea.html', tarea=tarea)


@configuracion_bp.route('/eliminar_tarea/<int:id>')
@login_required
@task_scheduler_required
def eliminar_tarea(id):
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute(sqlconstants.ELIMINAR_PROGRAMA_TAREA, (id,))
            connection.commit()

            # Remover del scheduler
            from task_scheduler import scheduler
            try:
                scheduler.remove_job(f"tarea_{id}")
            except:
                pass

            flash('Tarea eliminada exitosamente', 'success')
        except Error as e:
            connection.rollback()
            flash(f'Error al eliminar tarea: {str(e)}', 'danger')
        finally:
            cursor.close()
            connection.close()
    else:
        flash('Error de conexión a la base de datos', 'danger')
    return redirect(url_for('configuracion.programar_tareas'))


@configuracion_bp.route('/historial_ejecuciones/<int:id>')
@login_required
@task_scheduler_required
def historial_ejecuciones(id):
    from math import ceil

    page = request.args.get('page', 1, type=int)
    items_por_pagina = 10
    total_items = 100

    connection = get_db_connection()
    tarea = None
    ejecuciones = []
    total_ejecuciones = 0

    if connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(sqlconstants.OBTENER_PROGRAMA_TAREA, (id,))
            tarea = cursor.fetchone()
            if tarea:
                # Obtener total de ejecuciones
                cursor.execute("SELECT COUNT(*) as total FROM a_ejecuciones_tareas WHERE tarea_id = %s", (id,))
                result = cursor.fetchone()
                total_ejecuciones = min(result['total'] or 0, total_items)

                # Obtener ejecuciones paginadas
                offset = (page - 1) * items_por_pagina
                cursor.execute("""
                    SELECT id, tarea_id as programa_id, fecha_inicio as fecha_ejecucion,
                           estado, CEIL(TIMESTAMPDIFF(SECOND, fecha_inicio, IFNULL(fecha_fin, NOW())) * 1000) as tiempo_ejecucion_ms,
                           registros_afectados, mensaje_error, archivo_salida
                    FROM a_ejecuciones_tareas
                    WHERE tarea_id = %s
                    ORDER BY fecha_inicio DESC
                    LIMIT %s OFFSET %s
                """, (id, items_por_pagina, offset))
                ejecuciones = cursor.fetchall()
        except Error as e:
            flash(f'Error al cargar historial: {str(e)}', 'danger')
        finally:
            cursor.close()
            connection.close()

    if not tarea:
        flash('Tarea no encontrada', 'danger')
        return redirect(url_for('configuracion.programar_tareas'))

    # Calcular información de paginación
    total_paginas = ceil(total_ejecuciones / items_por_pagina) if total_ejecuciones > 0 else 1
    if page > total_paginas:
        page = total_paginas

    paginacion = {
        'pagina_actual': page,
        'total_paginas': total_paginas,
        'total_items': total_ejecuciones,
        'items_por_pagina': items_por_pagina,
        'mostrar_anterior': page > 1,
        'mostrar_siguiente': page < total_paginas
    }

    return render_template('historial_ejecuciones.html', tarea=tarea, ejecuciones=ejecuciones, paginacion=paginacion)


@configuracion_bp.route('/ejecutar_tarea/<int:id>')
@login_required
@task_scheduler_required
def ejecutar_tarea(id):
    import time
    from datetime import datetime

    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('configuracion.programar_tareas'))

    exec_cursor = connection.cursor(dictionary=True)
    try:
        exec_cursor.execute(sqlconstants.OBTENER_PROGRAMA_TAREA, (id,))
        tarea = exec_cursor.fetchone()

        if not tarea:
            flash('Tarea no encontrada', 'danger')
            return redirect(url_for('configuracion.programar_tareas'))

        # Ejecutar tarea
        inicio = time.time()
        fecha_inicio = datetime.now()
        estado = 'EXITOSO'
        registros_afectados = 0
        mensaje_error = None

        try:
            # Crear un cursor separado para ejecutar la tarea
            task_cursor = connection.cursor()
            task_cursor.execute(tarea['sql_query'])
            registros_afectados = task_cursor.rowcount
            connection.commit()
            task_cursor.close()
            estado = 'EXITOSO'
        except Exception as e:
            estado = 'ERROR'
            mensaje_error = str(e)
            connection.rollback()
            flash(f'Error al ejecutar tarea: {mensaje_error}', 'danger')

        # Registrar ejecución
        fecha_fin = datetime.now()
        duracion_segundos = int((time.time() - inicio))

        try:
            reg_cursor = connection.cursor()
            reg_cursor.execute("""
                INSERT INTO a_ejecuciones_tareas
                (tarea_id, fecha_inicio, fecha_fin, duracion_segundos, estado, registros_afectados, mensaje_error)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (id, fecha_inicio, fecha_fin, duracion_segundos, estado, registros_afectados, mensaje_error))
            connection.commit()
            reg_cursor.close()

            if estado == 'EXITOSO':
                flash(f'Tarea ejecutada en {duracion_segundos}s. Registros afectados: {registros_afectados}', 'success')

        except Exception as e:
            flash(f'Error al registrar ejecución: {str(e)}', 'danger')

    except Error as e:
        flash(f'Error en la base de datos: {str(e)}', 'danger')
    finally:
        exec_cursor.close()
        connection.close()

    return redirect(url_for('configuracion.historial_ejecuciones', id=id))
