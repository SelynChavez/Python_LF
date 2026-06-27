from flask import render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from flask import current_app
from mysql.connector import Error
import datetime
import sqlconstants
from utils.database import get_db_connection

from .compras_comb import compras_comb_bp

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('dashboard.dashboard'))
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


@compras_comb_bp.route('/compras_comb')
@login_required
def lista_compras():
    connection = get_db_connection()
    compras = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_COMPRAS_COMB)
        compras = cursor.fetchall()
        cursor.close()
        connection.close()
    return render_template('compras_comb.html', compras=compras)


@compras_comb_bp.route('/compras_comb/nueva', methods=['GET', 'POST'])
@login_required
def nueva_compra():
    connection = get_db_connection()
    combustibles = []
    maquinas = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_COMB_PARA_COMPRA)
        combustibles = cursor.fetchall()
        cursor.execute(sqlconstants.LISTA_MAQUINAS_COMPRA)
        maquinas = cursor.fetchall()
        cursor.close()

    if request.method == 'POST':
        usr = session['user_username']
        ruc = request.form.get('ruc', '')
        fecha = request.form.get('fecha', '')
        numero = request.form.get('numero', '')
        tipo = request.form.get('tipo', '')
        moneda = request.form.get('moneda', 'PEN')
        condicion = request.form.get('condicion', '')
        descuentos = float(request.form.get('descuentos', 0) or 0)
        adicionales = float(request.form.get('adicionales', 0) or 0)
        observaciones = request.form.get('observaciones', '')

        productos = request.form.getlist('item_producto[]')
        descripciones = request.form.getlist('item_descripcion[]')
        cantidades = request.form.getlist('item_cantidad[]')
        uoms = request.form.getlist('item_uom[]')
        precios = request.form.getlist('item_precio[]')
        maquina_ids = request.form.getlist('item_maquina[]')

        subtotal = 0.0
        items = []
        for i in range(len(productos)):
            if not productos[i]:
                continue
            cant = float(cantidades[i] or 0)
            prec = float(precios[i] or 0)
            sub = cant * prec
            subtotal += sub
            items.append({
                'producto': productos[i],
                'descripcion': descripciones[i] if i < len(descripciones) else '',
                'cantidad': cant,
                'uom': uoms[i] if i < len(uoms) else '',
                'precio': prec,
                'subtotal': sub,
                'maquina_id': maquina_ids[i] if i < len(maquina_ids) else ''
            })

        igv = round(subtotal * 0.18, 2)
        total = round(subtotal + igv - descuentos + adicionales, 2)
        subtotal = round(subtotal, 2)

        conn = get_db_connection()
        if not conn:
            flash('Error de conexión a la base de datos', 'danger')
            return render_template('compras_comb_form.html', combustibles=combustibles, maquinas=maquinas)

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(sqlconstants.INS_COMPRA_COMB, (
                ruc, fecha, numero, subtotal, igv, descuentos, adicionales,
                total, moneda, tipo, observaciones, usr
            ))
            factura_id = cursor.lastrowid

            for item in items:
                cursor.execute(sqlconstants.INS_COMPRA_COMB_DET, (
                    factura_id, item['producto'], item['descripcion'],
                    item['cantidad'], item['uom'], item['precio'], item['subtotal'], usr
                ))
                cursor.execute(sqlconstants.UPD_COMB_STOCK_COMPRA, (
                    item['cantidad'], item['cantidad'], item['precio'],
                    item['cantidad'], item['precio'], item['cantidad'], item['producto']
                ))
                # Guardar precio histórico
                cursor.execute(sqlconstants.INS_PRECIO_HISTORICO_COMB, (
                    item['producto'], fecha, item['precio'], item['cantidad'], moneda, factura_id
                ))
                if item['maquina_id']:
                    cursor.execute(sqlconstants.UPD_MAQUINA_STOCK_COMPRA, (
                        item['cantidad'], item['maquina_id']
                    ))

            conn.commit()
            flash('Compra registrada exitosamente', 'success')
            return redirect(url_for('compras_comb.lista_compras'))
        except Error as err:
            conn.rollback()
            flash(f'Error al guardar: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('compras_comb_form.html', combustibles=combustibles, maquinas=maquinas)


@compras_comb_bp.route('/compras_comb/ver/<int:id>')
@login_required
def ver_compra(id):
    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('compras_comb.lista_compras'))

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.*, p.nombre as nombre_proveedor
            FROM a_compras_comb c
            LEFT JOIN a_proveedores p ON c.ruc = p.ruc
            WHERE c.id = %s
        """, (id,))
        compra = cursor.fetchone()

        if not compra:
            flash('Compra no encontrada', 'warning')
            return redirect(url_for('compras_comb.lista_compras'))

        cursor.execute("""
            SELECT * FROM a_compras_comb_detalles WHERE factura_id = %s
        """, (id,))
        detalles = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('compra_detalle.html', compra=compra, detalles=detalles)
    except Error as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('compras_comb.lista_compras'))
    finally:
        cursor.close()
        connection.close()


@compras_comb_bp.route('/compras_comb/anular/<int:id>', methods=['POST'])
@login_required
def anular_compra(id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500

    cursor = connection.cursor(dictionary=True)
    try:
        # Obtener datos de la compra
        cursor.execute(sqlconstants.SEL_COMPRAS_COMB_BY_ID, (id,))
        compra = cursor.fetchone()

        if not compra:
            return jsonify({'success': False, 'message': 'Compra no encontrada'}), 404

        if compra.get('estado') == 'ANULADO':
            return jsonify({'success': False, 'message': 'Esta compra ya fue anulada'}), 400

        # Obtener detalles de la compra
        cursor.execute(sqlconstants.SEL_COMPRAS_COMB_DETALLES, (id,))
        detalles = cursor.fetchall()

        # Revertir cambios en stock y precio promedio
        for detalle in detalles:
            producto = detalle['producto']
            cantidad = detalle['cantidad']
            precio = detalle['precio']

            # Obtener stock actual y precio promedio actual
            cursor.execute("""
                SELECT stock_actual, COALESCE(precio_promedio, precio_unitario) as precio_promedio
                FROM a_combustible WHERE nombre = %s
            """, (producto,))
            comb = cursor.fetchone()

            if comb:
                stock_actual = float(comb['stock_actual'])
                precio_promedio_actual = float(comb['precio_promedio'])

                # Calcular nuevo precio promedio
                new_stock = max(0, stock_actual - cantidad)
                if new_stock > 0:
                    # Revertir el promedio: extraer el costo del producto anulado del total
                    total_costo = precio_promedio_actual * stock_actual
                    costo_anulado = precio * cantidad
                    new_precio_promedio = (total_costo - costo_anulado) / new_stock if new_stock > 0 else precio
                else:
                    new_precio_promedio = precio

                # Actualizar stock y precio promedio
                cursor.execute("""
                    UPDATE a_combustible
                    SET stock_actual = %s, precio_promedio = %s
                    WHERE nombre = %s
                """, (new_stock, new_precio_promedio, producto))

        # Marcar compra como anulada
        cursor.execute("""
            UPDATE a_compras_comb SET estado = 'ANULADO' WHERE id = %s
        """, (id,))

        connection.commit()
        return jsonify({'success': True, 'message': 'Compra anulada correctamente'})
    except Error as err:
        connection.rollback()
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        cursor.close()
        connection.close()


@compras_comb_bp.route('/api/proveedor_ruc/<ruc>')
@login_required
def api_proveedor_ruc(ruc):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sqlconstants.SEL_PROVEEDOR_POR_RUC, (ruc,))
        proveedor = cursor.fetchone()
        cursor.close()
        connection.close()
        if proveedor:
            return jsonify(proveedor)
        return jsonify({'error': 'Proveedor no encontrado'}), 404
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()
