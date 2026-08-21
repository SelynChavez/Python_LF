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
    # Asegurar que la tabla y la columna forma_pago existan (idempotente).
    cursor.execute(sqlconstants.CREATE_VENTAS_COMB_PADRON)
    cursor.execute(sqlconstants.COLCHECK_VCP_FORMA_PAGO)
    if cursor.fetchone()['c'] == 0:
        cursor.execute(sqlconstants.ALTER_VCP_ADD_FORMA_PAGO)

    if request.method == 'POST':
        fecha = request.form.get('fecha')
        padron = request.form.get('padron')
        monto = request.form.get('monto')
        observacion = (request.form.get('observacion') or '').strip()
        # Forma de pago: solo se aceptan 'Contado' o 'Credito'.
        forma_pago = request.form.get('forma_pago')
        if forma_pago not in ('Contado', 'Credito'):
            forma_pago = 'Contado'
        # El admin puede asignar la venta a otro usuario; el grifero solo a sí mismo.
        webuser = (request.form.get('webuser') or usr) if is_admin else usr

        if not fecha or not padron or not monto:
            flash('Complete fecha, padrón y monto.', 'danger')
        else:
            try:
                cursor.execute(sqlconstants.INSERT_VENTA_COMB_PADRON,
                               (fecha, int(padron), float(monto), observacion[:255], forma_pago, webuser))
                connection.commit()
                flash('Venta de combustible registrada.', 'success')
                cursor.close()
                connection.close()
                return redirect(url_for('combustibles.ventas_combustible'))
            except (Error, ValueError) as e:
                connection.rollback()
                flash(f'Error al registrar la venta: {e}', 'danger')

    # Filtros para GET
    filtro_usuario = request.args.get('filtro_usuario', '')
    filtro_fecha_desde = request.args.get('filtro_fecha_desde', '')
    filtro_padron = request.args.get('filtro_padron', '')
    filtro_forma_pago = request.args.get('filtro_forma_pago', '')

    # Límite de filas (por defecto 10)
    try:
        filtro_limite = int(request.args.get('filtro_limite', 10))
        if filtro_limite not in (10, 20, 50, 100, 1000):
            filtro_limite = 10
    except (ValueError, TypeError):
        filtro_limite = 10

    if is_admin:
        cursor.execute(sqlconstants.LISTA_VENTAS_COMB_PADRON_ALL)
    else:
        cursor.execute(sqlconstants.LISTA_VENTAS_COMB_PADRON_USR, (usr,))
    ventas_all = cursor.fetchall()

    # Ordenar por fecha descendente y aplicar filtros localmente
    ventas_all = sorted(ventas_all, key=lambda x: x['fecha'] or '', reverse=True)

    ventas = []
    for v in ventas_all:
        if filtro_usuario and v['webuser'] != filtro_usuario:
            continue
        if filtro_fecha_desde and str(v['fecha']) < filtro_fecha_desde:
            continue
        if filtro_padron and int(filtro_padron) > 0 and v['padron'] != int(filtro_padron):
            continue
        if filtro_forma_pago and v['forma_pago'] != filtro_forma_pago:
            continue
        ventas.append(v)

    # Aplicar límite de filas
    ventas = ventas[:filtro_limite]

    usuarios = []
    if is_admin:
        cursor.execute(sqlconstants.LISTA_USUARIOS_ACTIVOS)
        usuarios = cursor.fetchall()

    total = sum(float(v['monto']) for v in ventas)
    cursor.close()
    connection.close()
    return render_template('ventas_combustible.html', ventas=ventas, usuarios=usuarios,
                           is_admin=is_admin, usr=usr, total=total,
                           today=datetime.datetime.now().strftime('%Y-%m-%d'),
                           filtro_usuario=filtro_usuario,
                           filtro_fecha_desde=filtro_fecha_desde,
                           filtro_padron=filtro_padron,
                           filtro_forma_pago=filtro_forma_pago,
                           filtro_limite=str(filtro_limite))


@combustibles_bp.route('/ventas_combustible/actualizar/<int:venta_id>', methods=['POST'])
@login_required
def actualizar_venta_combustible(venta_id):
    """Actualiza una venta existente. Solo el administrador puede editar."""
    rol = session.get('user_rol')
    is_admin = (rol == 'ADMIN')

    if not is_admin:
        return jsonify({'success': False, 'error': 'Acceso denegado. Solo los administradores pueden editar.'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Datos no proporcionados.'}), 400

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

        fecha = data.get('fecha')
        padron = data.get('padron')
        monto = data.get('monto')
        forma_pago = data.get('forma_pago', 'Contado')

        if not fecha or not padron or not monto:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Campos requeridos faltantes.'}), 400

        if forma_pago not in ('Contado', 'Credito'):
            forma_pago = 'Contado'

        upd = connection.cursor()
        upd.execute("""
            UPDATE a_ventas_comb_padron
            SET fecha = %s, padron = %s, monto = %s, forma_pago = %s
            WHERE id = %s
        """, (fecha, int(padron), float(monto), forma_pago, venta_id))
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


@combustibles_bp.route('/ventas_combustible/eliminar/<int:venta_id>', methods=['POST'])
@login_required
def eliminar_venta_combustible(venta_id):
    """Elimina físicamente una venta. Solo el administrador puede eliminar."""
    rol = session.get('user_rol')
    is_admin = (rol == 'ADMIN')

    if not is_admin:
        return jsonify({'success': False, 'error': 'Acceso denegado. Solo los administradores pueden eliminar.'}), 403

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

        # Filtrar solo combustibles activos para estadísticas
        combustibles_activos = [c for c in combustibles if c.get('active', 'S') == 'S']

        total1 = 0
        total_precio_compra = 0
        total_precio_venta = 0
        total_stock_bajo = 0
        for x0 in combustibles_activos:
            total1 += 1
            total_precio_compra += float(x0['precio_compra'] or 0)
            total_precio_venta += float(x0['precio_unitario'])
            if (float(x0['stock_actual']) < float(x0['stock_minimo'])):
                total_stock_bajo += 1
        precio_compra_promedio = total_precio_compra / total1 if total1 > 0 else 0
        precio_venta_promedio = total_precio_venta / total1 if total1 > 0 else 0
        return render_template('reg_combustible.html', combustibles=combustibles, total1=total1, total2=precio_compra_promedio, total3=precio_venta_promedio, total4=total_stock_bajo)
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
            data.get('precio_compra'),
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
            data.get('precio_compra'),
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


@combustibles_bp.route('/api/combustibles/<int:id>/estado', methods=['PUT'])
def update_combustible_estado(id):
    data = request.json
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor()
    try:
        active = data.get('active', 'S')
        if active not in ('S', 'N'):
            active = 'S'

        cursor.execute(sqlconstants.UPD_COMBUSTIBLE_ACTIVE, (active, id))
        connection.commit()
        if cursor.rowcount > 0:
            return jsonify({'message': 'Estado actualizado exitosamente'})
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


@combustibles_bp.route('/combustibles/editar/<nombre>', methods=['GET', 'POST'])
@admin_required
def editar_combustible(nombre):
    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('combustibles.dashboardC'))

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sqlconstants.SEL_COMBUSTIBLE_BY_NOMBRE, (nombre,))
        combustible = cursor.fetchone()

        if not combustible:
            flash('Combustible no encontrado', 'warning')
            return redirect(url_for('combustibles.dashboardC'))

        if request.method == 'POST':
            nuevo_nombre = request.form.get('nombre', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            precio_compra = float(request.form.get('precio_compra', 0) or 0)
            precio = float(request.form.get('precio_unitario', 0) or 0)
            stock_actual = float(request.form.get('stock_actual', 0) or 0)
            stock_minimo = float(request.form.get('stock_minimo', 0) or 0)
            active = request.form.get('active', 'S')

            if active not in ('S', 'N'):
                active = 'S'

            try:
                cursor.execute(sqlconstants.UPD_COMBUSTIBLE_COMPLETO, (nuevo_nombre, descripcion, precio_compra, precio, stock_actual, stock_minimo, active, nombre))

                connection.commit()
                flash('Combustible actualizado correctamente', 'success')
                return redirect(url_for('combustibles.dashboardC'))
            except Error as e:
                connection.rollback()
                flash(f'Error al actualizar: {str(e)}', 'danger')

        cursor.close()
        connection.close()
        return render_template('editar_combustible.html', combustible=combustible)
    except Error as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('combustibles.dashboardC'))
    finally:
        cursor.close()
        connection.close()


@combustibles_bp.route('/editar_lectura_final/<int:venta_id>', methods=['GET', 'POST'])
@login_required
def editar_lectura_final(venta_id):
    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('combustibles.cargar_turnos'))

    cursor = connection.cursor(dictionary=True)

    # Obtener datos de la venta
    cursor.execute("""
        SELECT v.*, m.numero as machine_number, m.tipo_combustible
        FROM a_ventas_comb v
        LEFT JOIN a_maquinas m ON v.maquina = m.id
        WHERE v.id = %s
    """, (venta_id,))
    venta = cursor.fetchone()

    if not venta:
        cursor.close()
        connection.close()
        flash('Venta no encontrada', 'warning')
        return redirect(url_for('combustibles.cargar_turnos'))

    if request.method == 'POST':
        try:
            nueva_lectura = float(request.form.get('lectura_final', 0))
            lectura_inicial = float(venta['lectura_inicial'])

            if nueva_lectura < lectura_inicial:
                flash('La lectura final debe ser mayor o igual a la lectura inicial', 'warning')
            else:
                galones_vendidos = nueva_lectura - lectura_inicial

                # Obtener precio unitario
                cursor.execute("""
                    SELECT precio_unitario FROM a_combustible WHERE id = %s
                """, (venta['tipo_combustible'],))
                combustible = cursor.fetchone()
                precio_unitario = float(combustible['precio_unitario']) if combustible else 0
                total_precio = galones_vendidos * precio_unitario

                # Actualizar venta
                cursor.execute("""
                    UPDATE a_ventas_comb
                    SET lectura_final = %s, galones_vendidos = %s, total_precio = %s
                    WHERE id = %s
                """, (nueva_lectura, galones_vendidos, total_precio, venta_id))

                connection.commit()
                flash('Lectura actualizada correctamente', 'success')
                cursor.close()
                connection.close()
                return redirect(url_for('combustibles.cargar_turnos'))

        except ValueError:
            flash('Valor inválido para la lectura', 'danger')

    cursor.close()
    connection.close()
    return render_template('editar_lectura_final.html', venta=venta)


@combustibles_bp.route('/editar_lectura_inicial/<int:venta_id>', methods=['GET', 'POST'])
@login_required
def editar_lectura_inicial(venta_id):
    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('combustibles.cargar_turnos'))

    cursor = connection.cursor(dictionary=True)

    # Obtener datos de la venta
    cursor.execute("""
        SELECT v.*, m.numero as machine_number, m.tipo_combustible
        FROM a_ventas_comb v
        LEFT JOIN a_maquinas m ON v.maquina = m.id
        WHERE v.id = %s
    """, (venta_id,))
    venta = cursor.fetchone()

    if not venta:
        cursor.close()
        connection.close()
        flash('Venta no encontrada', 'warning')
        return redirect(url_for('combustibles.cargar_turnos'))

    if request.method == 'POST':
        try:
            nueva_lectura = float(request.form.get('lectura_inicial', 0))
            lectura_final = float(venta['lectura_final'])

            if nueva_lectura > lectura_final:
                flash('La lectura inicial debe ser menor o igual a la lectura final', 'warning')
            else:
                galones_vendidos = lectura_final - nueva_lectura

                # Obtener precio unitario
                cursor.execute("""
                    SELECT precio_unitario FROM a_combustible WHERE id = %s
                """, (venta['tipo_combustible'],))
                combustible = cursor.fetchone()
                precio_unitario = float(combustible['precio_unitario']) if combustible else 0
                total_precio = galones_vendidos * precio_unitario

                # Actualizar venta
                cursor.execute("""
                    UPDATE a_ventas_comb
                    SET lectura_inicial = %s, galones_vendidos = %s, total_precio = %s
                    WHERE id = %s
                """, (nueva_lectura, galones_vendidos, total_precio, venta_id))

                connection.commit()
                flash('Lectura inicial actualizada correctamente', 'success')
                cursor.close()
                connection.close()
                return redirect(url_for('combustibles.cargar_turnos'))

        except ValueError:
            flash('Valor inválido para la lectura', 'danger')

    cursor.close()
    connection.close()
    return render_template('editar_lectura_inicial.html', venta=venta)


@combustibles_bp.route('/obtener_envios/<int:venta_id>')
@login_required
def obtener_envios(venta_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión'}), 500

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sqlconstants.LISTA_ENVIOS_DINERO, (venta_id,))
        envios = cursor.fetchall()
        return jsonify({'envios': envios})
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@combustibles_bp.route('/obtener_venta/<int:venta_id>')
@login_required
def obtener_venta(venta_id):
    """Obtiene los datos de una venta para llenar la cabecera del modal de envío"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión'}), 500

    cursor = connection.cursor(dictionary=True)
    try:
        # Obtener datos de la venta (turno, nombre están guardados como strings en a_ventas_comb)
        query = """
            SELECT v.id, v.fecha, v.turno, v.nombre, v.webuser, v.maquina,
                   m.numero AS machine_number, m.ubicacion
            FROM a_ventas_comb v
            LEFT JOIN a_maquinas m ON v.maquina = m.id
            WHERE v.id = %s
        """
        cursor.execute(query, (venta_id,))
        venta = cursor.fetchone()

        if not venta:
            print(f"Venta {venta_id} no encontrada")
            return jsonify({'error': 'Venta no encontrada'}), 404

        # Preparar respuesta
        fecha_str = venta['fecha'].strftime('%Y-%m-%d') if venta['fecha'] else ''

        resultado = {
            'id': venta['id'],
            'fecha': fecha_str,
            'turno': venta.get('turno') or '',
            'machine_number': venta.get('machine_number') or '',
            'ubicacion': venta.get('ubicacion') or '',
            'usuario': venta.get('nombre') or venta.get('webuser') or ''
        }

        print(f"Venta obtenida: {resultado}")
        return jsonify(resultado)
    except Error as e:
        print(f"Error en obtener_venta: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@combustibles_bp.route('/obtener_envio/<int:envio_id>')
@login_required
def obtener_envio(envio_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión'}), 500

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sqlconstants.SELECT_ENVIO_DINERO, (envio_id,))
        envio = cursor.fetchone()
        if not envio:
            return jsonify({'error': 'Envío no encontrado'}), 404
        return jsonify(envio)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@combustibles_bp.route('/guardar_envio', methods=['POST'])
@login_required
def guardar_envio():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión'}), 500

    cursor = connection.cursor()
    try:
        data = request.get_json()
        venta_id = data.get('venta_id')
        envio_id = data.get('envio_id')

        moneda_5_soles = float(data.get('moneda_5_soles', 0))
        moneda_2_soles = float(data.get('moneda_2_soles', 0))
        moneda_1_sol = float(data.get('moneda_1_sol', 0))
        moneda_0_50_cent = float(data.get('moneda_0_50_cent', 0))
        moneda_0_20_cent = float(data.get('moneda_0_20_cent', 0))
        moneda_0_10_cent = float(data.get('moneda_0_10_cent', 0))
        billete = float(data.get('billete', 0))

        if envio_id:
            # Actualizar envío existente
            cursor.execute(sqlconstants.UPDATE_ENVIO_DINERO, (
                moneda_5_soles, moneda_2_soles, moneda_1_sol,
                moneda_0_50_cent, moneda_0_20_cent, moneda_0_10_cent,
                billete, session.get('user_username', 'unknown'), envio_id
            ))
        else:
            # Crear nuevo envío
            cursor.execute(sqlconstants.GET_MAX_NUMERO_ENVIO, (venta_id,))
            result = cursor.fetchone()
            numero_envio = result[0] if result else 1

            cursor.execute(sqlconstants.INSERT_ENVIO_DINERO, (
                venta_id, numero_envio,
                moneda_5_soles, moneda_2_soles, moneda_1_sol,
                moneda_0_50_cent, moneda_0_20_cent, moneda_0_10_cent,
                billete, session.get('user_username', 'unknown')
            ))

        connection.commit()
        return jsonify({'success': True, 'message': 'Envío guardado exitosamente'})

    except Error as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()
