from flask import render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from flask import current_app
from mysql.connector import Error
from datetime import time
import datetime
from decimal import Decimal
import mysql.connector
import sqlconstants

from .combustibles import bp as combustibles_bp

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
            return redirect(url_for('combustibles.dashboardC'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_rol' not in session or session['user_rol'] != 'ADMIN':
            flash('Acceso denegado. Se requieren privilegios de administrador.', 'danger')
            return redirect(url_for('combustibles.dashboardC'))
        return f(*args, **kwargs)
    return decorated_function

def get_shift_name(current_time=None):
    if current_time is None:
        current_time = datetime.datetime.now().time()
    if time(6, 0) <= current_time < time(14, 0):
        return 'TURNO_2', '6AM - 2PM'
    elif time(14, 0) <= current_time < time(23, 0):
        return 'TURNO_3', '2PM - 11PM'
    else:
        return 'TURNO_1', '11PM - 6AM'


@combustibles_bp.route('/dashboardC')
def dashboardC():
    now = datetime.datetime.now()
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.DASHB_COMB_TOTAL_HOY)
        today_stats = cursor.fetchone()
        cursor.execute(sqlconstants.DASHB_COMB_TURNOS_HOY)
        shift_stats = cursor.fetchall()
        cursor.execute(sqlconstants.DASHB_COMB_TOP_MAQUINAS)
        top_machines = cursor.fetchall()
        cursor.execute(sqlconstants.DASHB_COMB_STOCK_CRITICO)
        low_stock = cursor.fetchall()
        cursor.close()
    return render_template('dashboardC.html',
                          today_stats=today_stats,
                          shift_stats=shift_stats,
                          top_machines=top_machines,
                          low_stock=low_stock,
                          now=now)


@combustibles_bp.route('/cargar_turnos', methods=['GET', 'POST'])
def cargar_turnos():
    usr = session['user_username']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.LISTA_MAQUINAS_X_TURNOS)
    machines = cursor.fetchall()
    shifts = [
        {'code': 'TURNO_1', 'name': '11PM - 6AM'},
        {'code': 'TURNO_2', 'name': '6AM - 2PM'},
        {'code': 'TURNO_3', 'name': '2PM - 11PM'}
    ]
    if request.method == 'POST':
        shift_code = request.form['shift_code']
        shift_date = request.form['shift_date']
        success_count = 0
        errors = []
        for machine in machines:
            machine_id = machine['id']
            initial_key = f'initial_{machine_id}'
            final_key = f'final_{machine_id}'
            if initial_key in request.form and final_key in request.form:
                try:
                    initial_reading = Decimal(request.form[initial_key])
                    final_reading = Decimal(request.form[final_key])
                    if initial_reading == 0 and final_reading == 0:
                        continue
                    gallons_sold = final_reading - initial_reading
                    if gallons_sold < 0:
                        errors.append(f'Máquina {machine["machine_number"]}: Lectura final menor que inicial')
                        continue
                    cursor.execute(sqlconstants.PRECIO_U_COMB, (machine['fuel_type_id'],))
                    fuel = cursor.fetchone()
                    if gallons_sold > 0:
                        cursor.execute(sqlconstants.INSERT_VTAS_COMBUSTIBLE, (machine_id, shift_code,
                              next(s['name'] for s in shifts if s['code'] == shift_code), shift_date,
                              initial_reading, final_reading, gallons_sold, gallons_sold * fuel['unit_price'], usr))
                        cursor.execute(sqlconstants.UPDATE_VTAS_COMB_MAQUINAS, (final_reading, machine_id))
                        cursor.execute(sqlconstants.UPDATE_STOCK_COMBUSTIBLE_VTA, (gallons_sold, machine['fuel_type_id']))
                        success_count += 1
                except Exception as e:
                    errors.append(f'Máquina {machine["machine_number"]}: {str(e)}')
        if success_count > 0:
            connection.commit()
            flash(f'{success_count} máquina(s) actualizada(s) exitosamente', 'success')
        if errors:
            for error in errors:
                flash(error, 'warning')
        return redirect(url_for('combustibles.cargar_turnos'))

    is_admin = (session.get('user_rol') == 'ADMIN')
    if is_admin:
        # El administrador ve las últimas 10 ventas de cualquier usuario/rol.
        cursor.execute(sqlconstants.COUNT_VENTAS_TODAS)
        total_ventas = cursor.fetchone()['total']
        cursor.execute(sqlconstants.LISTA_VENTAS_TODAS)
        ventas = cursor.fetchall()
        page, total_pages = 1, 1
    else:
        # El grifero ve solo sus ventas, paginadas de 5 en 5.
        per_page = 5
        try:
            page = int(request.args.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        if page < 1:
            page = 1
        cursor.execute(sqlconstants.COUNT_VENTAS_X_USUARIO, (usr,))
        total_ventas = cursor.fetchone()['total']
        total_pages = max(1, (total_ventas + per_page - 1) // per_page)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page
        cursor.execute(sqlconstants.LISTA_VENTAS_X_USUARIO, (usr, per_page, offset))
        ventas = cursor.fetchall()
    cursor.close()
    return render_template('cargar_turnos.html', machines=machines, shifts=shifts,
                           today=datetime.datetime.now().strftime('%Y-%m-%d'), usr=usr,
                           ventas=ventas, page=page, total_pages=total_pages,
                           total_ventas=total_ventas, is_admin=is_admin)


@combustibles_bp.route('/ventas_combustible', methods=['GET', 'POST'])
@login_required
def ventas_combustible():
    """Registro y consulta de ventas de combustible por padrón.

    - GRIFERO: registra a su propio nombre y solo ve/elimina sus registros.
    - ADMIN: puede elegir el usuario (selector) y ve todos los registros.
    """
    rol = session.get('user_rol')
    usr = session['user_username']
    is_admin = (rol == 'ADMIN')

    if rol not in ('GRIFERO', 'ADMIN'):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('combustibles.dashboardC') if is_admin
                        else url_for('combustibles.cargar_turnos'))

    cursor = connection.cursor(dictionary=True)
    # Asegurar que la tabla exista (idempotente).
    cursor.execute(sqlconstants.CREATE_VENTAS_COMB_PADRON)

    if request.method == 'POST':
        fecha = request.form.get('fecha')
        padron = request.form.get('padron')
        monto = request.form.get('monto')
        observacion = (request.form.get('observacion') or '').strip()
        # El admin puede asignar la venta a otro usuario; el grifero solo a sí mismo.
        webuser = (request.form.get('webuser') or usr) if is_admin else usr

        if not fecha or not padron or not monto:
            flash('Complete fecha, padrón y monto.', 'danger')
        else:
            try:
                cursor.execute(sqlconstants.INSERT_VENTA_COMB_PADRON,
                               (fecha, int(padron), float(monto), observacion[:255], webuser))
                connection.commit()
                flash('Venta de combustible registrada.', 'success')
                cursor.close()
                connection.close()
                return redirect(url_for('combustibles.ventas_combustible'))
            except (Error, ValueError) as e:
                connection.rollback()
                flash(f'Error al registrar la venta: {e}', 'danger')

    if is_admin:
        cursor.execute(sqlconstants.LISTA_VENTAS_COMB_PADRON_ALL)
    else:
        cursor.execute(sqlconstants.LISTA_VENTAS_COMB_PADRON_USR, (usr,))
    ventas = cursor.fetchall()

    usuarios = []
    if is_admin:
        cursor.execute(sqlconstants.LISTA_USUARIOS_ACTIVOS)
        usuarios = cursor.fetchall()

    total = sum(float(v['monto']) for v in ventas)
    cursor.close()
    connection.close()
    return render_template('ventas_combustible.html', ventas=ventas, usuarios=usuarios,
                           is_admin=is_admin, usr=usr, total=total,
                           today=datetime.datetime.now().strftime('%Y-%m-%d'))


@combustibles_bp.route('/ventas_combustible/eliminar/<int:venta_id>', methods=['POST'])
@login_required
def eliminar_venta_combustible(venta_id):
    """Elimina físicamente una venta. El grifero solo puede eliminar las suyas."""
    rol = session.get('user_rol')
    usr = session['user_username']
    is_admin = (rol == 'ADMIN')

    if rol not in ('GRIFERO', 'ADMIN'):
        return jsonify({'success': False, 'error': 'Acceso denegado.'}), 403

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.CREATE_VENTAS_COMB_PADRON)
        cursor.execute(sqlconstants.SELECT_VENTA_COMB_PADRON, (venta_id,))
        venta = cursor.fetchone()
        if not venta:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Registro no encontrado.'}), 404
        if not is_admin and venta['webuser'] != usr:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Solo puede eliminar sus propios registros.'}), 403
        upd = connection.cursor()
        upd.execute(sqlconstants.DELETE_VENTA_COMB_PADRON, (venta_id,))
        connection.commit()
        upd.close()
        cursor.close()
        connection.close()
        return jsonify({'success': True})
    except Error as e:
        connection.rollback()
        try:
            connection.close()
        except Exception:
            pass
        return jsonify({'success': False, 'error': str(e)})


@combustibles_bp.route('/maquinas')
def maquinas():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.LISTA_MAQUINAS)
    machines = cursor.fetchall()
    cursor.execute(sqlconstants.LISTA_COMBUSTIBLE_TODOS)
    fuels = cursor.fetchall()
    cursor.close()
    return render_template('maquinas.html', machines=machines, fuels=fuels)


@combustibles_bp.route('/maquinas/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_maquina():
    if request.method == 'POST':
        machine_number = request.form['numero']
        fuel_type_id = request.form['tipo_combustible']
        initial_reading = request.form['lectura_inicial']
        stock_capacity = request.form['capacidad_stock']
        stock_available = request.form['disponible_stock']
        ubicacion = request.form['ubicacion']
        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(sqlconstants.INS_MAQUINAS, (machine_number, fuel_type_id, initial_reading, stock_capacity, stock_available, ubicacion))
            connection.commit()
            flash('Máquina agregada exitosamente', 'success')
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'danger')
        finally:
            cursor.close()
        return redirect(url_for('combustibles.maquinas'))
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM a_combustible')
    fuels = cursor.fetchall()
    cursor.close()
    return render_template('crear_maquina.html', fuels=fuels)


@combustibles_bp.route('/stock')
def stock():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.SEL_COMBUSTIBLE)
    fuels = cursor.fetchall()
    cursor.execute(sqlconstants.STOCK_POR_MAQUINA)
    machine_stock = cursor.fetchall()
    cursor.close()
    return render_template('stock.html', fuels=fuels, machine_stock=machine_stock)


@combustibles_bp.route('/editar_turno/<int:machine_id>', methods=['GET', 'POST'])
def editar_turno(machine_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.SEL_1_MAQUINA, (machine_id,))
    machine = cursor.fetchone()
    if request.method == 'POST':
        shift_code, shift_name = get_shift_name()
        initial_reading = Decimal(request.form['initial_reading'])
        final_reading = Decimal(request.form['final_reading'])
        shift_date = request.form['shift_date']
        gallons_sold = final_reading - initial_reading
        if gallons_sold < 0:
            flash('La lectura final no puede ser menor que la inicial', 'danger')
            return redirect(url_for('combustibles.editar_turno', machine_id=machine_id))
        if gallons_sold > machine['stock_available']:
            flash(f'Stock insuficiente. Disponible: {machine["stock_available"]} galones', 'danger')
            return redirect(url_for('combustibles.editar_turno', machine_id=machine_id))
        try:
            cursor.execute(sqlconstants.INS_VENTAS_COMB, (machine_id, shift_code, shift_name, shift_date, initial_reading, final_reading, gallons_sold, gallons_sold * machine['unit_price']))
            cursor.execute(sqlconstants.UPD_MAQUINAS_VTAS_COMB, (gallons_sold, final_reading, machine_id))
            connection.commit()
            cursor.execute(sqlconstants.UPD_COMBUSTIBLE_CTAS_COMB, (gallons_sold, machine['fuel_type_id']))
            connection.commit()
            flash(f'Turno registrado exitosamente. Galones vendidos: {gallons_sold}', 'success')
        except mysql.connector.Error as err:
            connection.rollback()
            flash(f'Error: {err}', 'danger')
        finally:
            cursor.close()
        return redirect(url_for('combustibles.maquinas'))
    cursor.execute(sqlconstants.LISTA_TURNOS_MAQUINA_COMB, (machine_id,))
    today_shifts = cursor.fetchall()
    cursor.close()
    shift_code, shift_name = get_shift_name()
    return render_template('editar_turno.html',
                          machine=machine,
                          today_shifts=today_shifts,
                          current_shift={'code': shift_code, 'name': shift_name},
                          today=datetime.datetime.now().strftime('%Y-%m-%d'))


@combustibles_bp.route('/reg_combustible', methods=['GET'])
def reg_combustible():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute('SELECT * FROM a_combustible ORDER BY id DESC')
        combustibles = cursor.fetchall()
        cursor.close()
        connection.close()
        total1 = 0
        total2 = 0
        total3 = 0
        for x0 in combustibles:
            total1 += 1
            total2 += float(x0['precio_unitario'])
            if (float(x0['stock_actual']) < float(x0['stock_minimo'])):
                total3 += 1
        total2f = total2 / total1
        return render_template('reg_combustible.html', combustibles=combustibles, total1=total1, total2=total2f, total3=total3)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@combustibles_bp.route('/api/combustibles/<int:id>', methods=['GET'])
def get_combustible(id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sqlconstants.SELECT_1_COMBUSTIBLE, (id,))
        combustible = cursor.fetchone()
        cursor.close()
        connection.close()
        return jsonify(combustible)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@combustibles_bp.route('/api/combustibles', methods=['POST'])
def create_combustible():
    data = request.json
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor()
    try:
        cursor.execute(sqlconstants.INS_1_COMBUSTIBLE, (
            data['nombre'],
            data['descripcion'],
            data['precio_unitario'],
            data.get('stock_actual'),
            data.get('stock_minimo')
        ))
        connection.commit()
        new_id = cursor.lastrowid
        return jsonify({
            'id': new_id,
            'message': 'Registro creado exitosamente'
        }), 201
    except Error as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@combustibles_bp.route('/api/combustibles/<int:id>', methods=['PUT'])
def update_combustible(id):
    data = request.json
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor()
    try:
        cursor.execute(sqlconstants.UPD_1_COMBUSTIBLE, (
            data['nombre'],
            data['descripcion'],
            data['precio_unitario'],
            data.get('stock_actual'),
            data.get('stock_minimo'),
            id
        ))
        connection.commit()
        if cursor.rowcount > 0:
            return jsonify({'message': 'Registro actualizado exitosamente'})
        return jsonify({'error': 'Registro no encontrado'}), 404
    except Error as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@combustibles_bp.route('/api/combustibles/<int:id>', methods=['DELETE'])
def delete_combustible(id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor()
    try:
        cursor.execute(sqlconstants.DEL_1_COMBUSTIBLE, (id,))
        connection.commit()
        if cursor.rowcount > 0:
            return jsonify({'message': 'Registro eliminado exitosamente'})
        return jsonify({'error': 'Registro no encontrado'}), 404
    except Error as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()
