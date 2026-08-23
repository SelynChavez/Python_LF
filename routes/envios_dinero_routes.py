from flask import render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from flask import current_app
from mysql.connector import Error
import datetime
from decimal import Decimal
import mysql.connector

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

from flask import Blueprint
envios_bp = Blueprint('envios', __name__, url_prefix='/envios')

@envios_bp.route('/dinero_cajero', methods=['GET', 'POST'])
@login_required
def envios_dinero_cajero():
    """Página para que el CAJERO registre envíos de dinero sin asociarlos a una venta"""
    rol = session.get('user_rol', '').upper()

    # Verificar que solo CAJA o ADMIN accedan
    if rol not in ['CAJA', 'ADMIN']:
        flash('Acceso denegado. Solo los cajeros pueden acceder a esta página.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

    usuario_sesion = session['user_username']
    fecha_hoy = datetime.datetime.now().strftime('%Y-%m-%d')

    # Obtener filtros (fecha por defecto es hoy)
    filtro_fecha = request.args.get('filtro_fecha', fecha_hoy)
    filtro_usuario = request.args.get('filtro_usuario', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    cursor = connection.cursor(dictionary=True)
    try:
        # Construir query base
        where_clause = "WHERE venta_id = -1"
        params = []

        if filtro_fecha:
            where_clause += " AND DATE(fecha) = %s"
            params.append(filtro_fecha)

        if filtro_usuario:
            where_clause += " AND webuser = %s"
            params.append(filtro_usuario)

        # Contar total de envíos
        count_query = f"""
            SELECT COUNT(*) as total FROM a_envios_dinero {where_clause}
        """
        cursor.execute(count_query, params)
        total_envios = cursor.fetchone()['total']
        total_pages = (total_envios + per_page - 1) // per_page

        # Obtener envíos con paginación
        offset = (page - 1) * per_page
        query = f"""
            SELECT id, numero_envio, fecha, moneda_5_soles, moneda_2_soles, moneda_1_sol,
                   moneda_0_50_cent, moneda_0_20_cent, moneda_0_10_cent, billete, webuser,
                   (moneda_5_soles + moneda_2_soles + moneda_1_sol +
                    moneda_0_50_cent + moneda_0_20_cent + moneda_0_10_cent + billete) as total
            FROM a_envios_dinero
            {where_clause}
            ORDER BY numero_envio ASC
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])
        cursor.execute(query, params)
        envios = cursor.fetchall()

        # Formatear fechas a string para comparación en template
        for envio in envios:
            if envio['fecha']:
                envio['fecha'] = envio['fecha'].strftime('%Y-%m-%d') if hasattr(envio['fecha'], 'strftime') else str(envio['fecha'])[:10]

        # Obtener suma total
        sum_query = f"""
            SELECT SUM(moneda_5_soles + moneda_2_soles + moneda_1_sol +
                       moneda_0_50_cent + moneda_0_20_cent + moneda_0_10_cent + billete) as suma_total
            FROM a_envios_dinero
            {where_clause}
        """
        cursor.execute(sum_query, params[:-2])  # Sin LIMIT y OFFSET
        suma_result = cursor.fetchone()
        suma_total = suma_result['suma_total'] or 0

        # Obtener lista de usuarios únicos para el dropdown
        cursor.execute("SELECT DISTINCT webuser FROM a_envios_dinero WHERE venta_id = -1 ORDER BY webuser")
        usuarios_unicos = cursor.fetchall()

        # Calcular siguiente número de envío para hoy
        hoy_query = f"""
            SELECT MAX(numero_envio) as max_numero FROM a_envios_dinero
            WHERE venta_id = -1 AND DATE(fecha) = %s
        """
        cursor.execute(hoy_query, (fecha_hoy,))
        result = cursor.fetchone()
        siguiente_numero = (result['max_numero'] or 0) + 1

        cursor.close()
        connection.close()

        return render_template('envios_dinero_cajero.html',
                             usuario_sesion=usuario_sesion,
                             fecha_hoy=fecha_hoy,
                             envios=envios,
                             siguiente_numero=siguiente_numero,
                             suma_total=suma_total,
                             page=page,
                             total_pages=total_pages,
                             filtro_fecha=filtro_fecha,
                             filtro_usuario=filtro_usuario,
                             usuarios_unicos=usuarios_unicos)

    except Error as e:
        flash(f'Error al obtener envíos: {str(e)}', 'danger')
        cursor.close()
        connection.close()
        return redirect(url_for('dashboard.dashboard'))

@envios_bp.route('/dinero_cajero/guardar', methods=['POST'])
@login_required
def guardar_envio_cajero():
    """Guarda un envío de dinero registrado por el cajero"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión'}), 500

    try:
        data = request.get_json()
        usuario = session['user_username']
        fecha_hoy = datetime.datetime.now().strftime('%Y-%m-%d')

        # Obtener siguiente número de envío del día
        cursor = connection.cursor(dictionary=True)
        query = "SELECT MAX(numero_envio) as max_numero FROM a_envios_dinero WHERE venta_id = -1 AND DATE(fecha) = %s"
        cursor.execute(query, (fecha_hoy,))
        result = cursor.fetchone()
        numero_envio = (result['max_numero'] or 0) + 1

        # Insertar envío
        insert_query = """
            INSERT INTO a_envios_dinero
            (venta_id, numero_envio, fecha, moneda_5_soles, moneda_2_soles, moneda_1_sol,
             moneda_0_50_cent, moneda_0_20_cent, moneda_0_10_cent, billete, webuser)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            -1,  # venta_id = -1 para envíos del cajero
            numero_envio,
            fecha_hoy,
            float(data.get('moneda_5_soles', 0)),
            float(data.get('moneda_2_soles', 0)),
            float(data.get('moneda_1_sol', 0)),
            float(data.get('moneda_0_50_cent', 0)),
            float(data.get('moneda_0_20_cent', 0)),
            float(data.get('moneda_0_10_cent', 0)),
            float(data.get('billete', 0)),
            usuario
        ))

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({
            'success': True,
            'message': f'Envío #{numero_envio} guardado exitosamente',
            'numero_envio': numero_envio
        })

    except Error as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@envios_bp.route('/api/envios/<int:envio_id>', methods=['GET'])
def obtener_envio(envio_id):
    """Obtiene los datos de un envío específico"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM a_envios_dinero WHERE id = %s", (envio_id,))
        envio = cursor.fetchone()
        cursor.close()
        conn.close()

        if not envio:
            return jsonify({'error': 'Envío no encontrado'}), 404

        return jsonify({
            'id': envio['id'],
            'moneda_5_soles': float(envio['moneda_5_soles']) if envio['moneda_5_soles'] else 0,
            'moneda_2_soles': float(envio['moneda_2_soles']) if envio['moneda_2_soles'] else 0,
            'moneda_1_sol': float(envio['moneda_1_sol']) if envio['moneda_1_sol'] else 0,
            'moneda_0_50_cent': float(envio['moneda_0_50_cent']) if envio['moneda_0_50_cent'] else 0,
            'moneda_0_20_cent': float(envio['moneda_0_20_cent']) if envio['moneda_0_20_cent'] else 0,
            'moneda_0_10_cent': float(envio['moneda_0_10_cent']) if envio['moneda_0_10_cent'] else 0,
            'billete': float(envio['billete']) if envio['billete'] else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@envios_bp.route('/api/envios/<int:envio_id>', methods=['PUT'])
def actualizar_envio(envio_id):
    """Actualiza un envío existente"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión'}), 500

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE a_envios_dinero SET
                moneda_5_soles = %s,
                moneda_2_soles = %s,
                moneda_1_sol = %s,
                moneda_0_50_cent = %s,
                moneda_0_20_cent = %s,
                moneda_0_10_cent = %s,
                billete = %s
            WHERE id = %s
        """, (
            float(data.get('moneda_5_soles', 0)),
            float(data.get('moneda_2_soles', 0)),
            float(data.get('moneda_1_sol', 0)),
            float(data.get('moneda_0_50_cent', 0)),
            float(data.get('moneda_0_20_cent', 0)),
            float(data.get('moneda_0_10_cent', 0)),
            float(data.get('billete', 0)),
            envio_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Envío actualizado correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
