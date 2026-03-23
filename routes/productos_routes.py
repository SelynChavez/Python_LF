from flask import render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from flask import current_app
from mysql.connector import Error
import sqlconstants

from .productos import bp as productos_bp

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
            return redirect(url_for('productos.reg_productos'))
        return f(*args, **kwargs)
    return decorated_function


@productos_bp.route('/reg_productos', methods=['GET'])
def reg_productos():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor(dictionary=True)
    try:
        usr = session['user_username']
        cursor.execute(sqlconstants.LISTA_PRODUCTOS)
        productos = cursor.fetchall()

        total_registros = len(productos)
        total_precio = 0
        stock_bajo = 0

        repuestos_count = 0
        illas_count = 0
        uniformes_count = 0

        for producto in productos:
            total_precio += float(producto['precio_unitario'] or 0)
            if producto['stock_actual'] and producto['stock_minimo']:
                if float(producto['stock_actual']) < float(producto['stock_minimo']):
                    stock_bajo += 1

            if producto['tipo'] == 'REPUESTO':
                repuestos_count += 1
            elif producto['tipo'] == 'LLANTA':
                illas_count += 1
            elif producto['tipo'] == 'UNIFORME':
                uniformes_count += 1

        precio_promedio = total_precio / total_registros if total_registros > 0 else 0

        return render_template('reg_productos.html',
                             productos=productos,
                             total1=total_registros,
                             total2=precio_promedio,
                             total3=stock_bajo,
                             repuestos=repuestos_count,
                             illas=illas_count,
                             uniformes=uniformes_count, usr=usr)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@productos_bp.route('/api/productos/<int:id>', methods=['GET'])
def get_producto(id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sqlconstants.SELECT_1_PRODUCTO, (id,))
        producto = cursor.fetchone()
        return jsonify(producto)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@productos_bp.route('/api/productos', methods=['POST'])
def create_producto():
    data = request.json
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor()
    try:
        cursor.execute(sqlconstants.INSERT_PRODUCTO, (
            data['nombre'],
            data.get('tipo', 'REPUESTO'),
            data['precio_unitario'],
            data.get('stock_actual'),
            data.get('stock_minimo'),
            data.get('active', 'S'),
            data.get('observaciones'),
            data.get('webuser', 'SYSTEM')
        ))
        connection.commit()
        new_id = cursor.lastrowid
        return jsonify({
            'id': new_id,
            'message': 'Producto creado exitosamente'
        }), 201
    except Error as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@productos_bp.route('/api/productos/<int:id>', methods=['PUT'])
def update_producto(id):
    data = request.json
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor()
    try:
        cursor.execute(sqlconstants.UPDATE_PRODUCTO, (
            data['nombre'],
            data.get('tipo', 'REPUESTO'),
            data['precio_unitario'],
            data.get('stock_actual'),
            data.get('stock_minimo'),
            data.get('active', 'S'),
            data.get('observaciones'),
            data.get('webuser', 'SYSTEM'),
            id
        ))
        connection.commit()
        if cursor.rowcount > 0:
            return jsonify({'message': 'Producto actualizado exitosamente'})
        return jsonify({'error': 'Producto no encontrado'}), 404
    except Error as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@productos_bp.route('/api/productos/<int:id>', methods=['DELETE'])
def delete_producto(id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor()
    try:
        cursor.execute(sqlconstants.DELETE_PRODUCTO, (id,))
        connection.commit()
        if cursor.rowcount > 0:
            return jsonify({'message': 'Producto eliminado exitosamente'})
        return jsonify({'error': 'Producto no encontrado'}), 404
    except Error as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()
