from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file
from functools import wraps
from mysql.connector import Error
from io import BytesIO
import sqlconstants
from utils.database import get_db_connection
import datetime

from .facturacion import facturacion_bp

USUARIOS_PERMITIDOS = ['selyn', 'matias']


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def usuario_permitido(f):
    """Decorator para restringir acceso solo a usuarios autorizados."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = session.get('user_username', '')
        if usuario not in USUARIOS_PERMITIDOS:
            flash('Acceso denegado. Solo administradores pueden realizar esta acción.', 'danger')
            return redirect(url_for('facturacion.listar_facturacion'))
        return f(*args, **kwargs)
    return decorated_function


@facturacion_bp.route('/listar')
@login_required
def listar_facturacion():
    """Listar todos los registros de facturación ordenados descendentemente por fecha."""
    connection = get_db_connection()
    facturaciones = []

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.LISTA_FACTURACION)
            facturaciones = cursor.fetchall()
            cursor.close()
            connection.close()
        except Error as e:
            flash(f'Error al cargar facturaciones: {str(e)}', 'danger')
            connection.close()

    return render_template('facturacion.html', facturaciones=facturaciones)


@facturacion_bp.route('/descargar_sustento/<int:id>')
@login_required
def descargar_sustento(id):
    """Obtener archivo sustento (imagen en base64 o descarga PDF)."""
    connection = get_db_connection()

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.SELECT_FACTURACION, (id,))
            registro = cursor.fetchone()
            cursor.close()
            connection.close()

            if registro and registro['sustento']:
                import base64
                contenido = registro['sustento']

                # Intentar detectar si es imagen o PDF por el contenido
                # PNG starts with: 89 50 4E 47
                # JPG starts with: FF D8 FF
                # PDF starts with: 25 50 44 46

                es_imagen = False
                tipo_imagen = 'image/png'

                if contenido[:4] == b'\x89PNG':
                    es_imagen = True
                    tipo_imagen = 'png'
                elif contenido[:3] == b'\xFF\xD8\xFF':
                    es_imagen = True
                    tipo_imagen = 'jpeg'

                if es_imagen:
                    # Convertir a base64 para mostrar en modal
                    b64 = base64.b64encode(contenido).decode('utf-8')
                    return jsonify({
                        'tipo': 'imagen',
                        'data': f'data:image/{tipo_imagen};base64,{b64}',
                        'id': id
                    })
                else:
                    # Es PDF, devolver para descargar
                    archivo = BytesIO(contenido)
                    return send_file(archivo,
                                   mimetype='application/pdf',
                                   as_attachment=True,
                                   download_name=f'sustento_{id}.pdf')
            else:
                return jsonify({'error': 'No hay archivo disponible'}), 404
        except Error as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Error de conexión'}), 500


@facturacion_bp.route('/actualizar_pagado', methods=['POST'])
@login_required
def actualizar_pagado():
    """Actualizar estado pagado de un registro."""
    data = request.get_json()
    id_fac = data.get('id')
    pagado = data.get('pagado')

    connection = get_db_connection()

    if connection:
        try:
            cursor = connection.cursor()
            # Actualizar solo el campo pagado
            query = "UPDATE a_facturacion_sys SET pagado = %s WHERE id = %s"
            cursor.execute(query, (pagado, id_fac))
            connection.commit()
            cursor.close()
            connection.close()

            return jsonify({'success': True, 'message': 'Estado actualizado correctamente'})
        except Error as e:
            connection.rollback()
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    else:
        return jsonify({'success': False, 'message': 'Error de conexión'}), 500


@facturacion_bp.route('/guardar_sustento', methods=['POST'])
@login_required
def guardar_sustento():
    """Guardar archivo sustento en el registro."""
    id_fac = request.form.get('id')
    archivo = request.files.get('archivo')

    if not id_fac or not archivo:
        return jsonify({'success': False, 'message': 'Faltan datos'}), 400

    # Validar tipo de archivo
    tipos_permitidos = {'application/pdf', 'image/png', 'image/jpeg', 'image/jpg'}
    if archivo.content_type not in tipos_permitidos:
        return jsonify({'success': False, 'message': 'Tipo de archivo no permitido'}), 400

    # Validar tamaño (máximo 5MB)
    if len(archivo.read()) > 5 * 1024 * 1024:
        return jsonify({'success': False, 'message': 'Archivo demasiado grande'}), 400

    # Volver al inicio del archivo para leerlo
    archivo.seek(0)

    connection = get_db_connection()

    if connection:
        try:
            cursor = connection.cursor()
            archivo_contenido = archivo.read()
            # Actualizar el sustento
            query = "UPDATE a_facturacion_sys SET sustento = %s WHERE id = %s"
            cursor.execute(query, (archivo_contenido, id_fac))
            connection.commit()
            cursor.close()
            connection.close()

            return jsonify({'success': True, 'message': 'Sustento guardado correctamente'})
        except Error as e:
            connection.rollback()
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    else:
        return jsonify({'success': False, 'message': 'Error de conexión'}), 500


@facturacion_bp.route('/crear', methods=['GET', 'POST'])
@login_required
@usuario_permitido
def crear_facturacion():
    """Crear nuevo registro de facturación."""
    if request.method == 'POST':
        descripcion = request.form.get('descripcion', '').strip()
        fecha = request.form.get('fecha', '')
        pago = request.form.get('pago', 'N')
        costo = request.form.get('costo', '0')

        if not descripcion or not fecha:
            flash('Por favor, completa todos los campos obligatorios', 'danger')
            return render_template('crear_facturacion.html')

        try:
            costo = float(costo)
        except ValueError:
            flash('El costo debe ser un número válido', 'danger')
            return render_template('crear_facturacion.html')

        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                query = sqlconstants.INSERT_FACTURACION
                cursor.execute(query, (descripcion, fecha, costo, pago, 'N', None, session['user_username']))
                connection.commit()
                cursor.close()
                connection.close()

                flash('Registro creado exitosamente', 'success')
                return redirect(url_for('facturacion.listar_facturacion'))
            except Error as e:
                flash(f'Error al crear: {str(e)}', 'danger')
                connection.close()
        else:
            flash('Error de conexión a la base de datos', 'danger')

    return render_template('crear_facturacion.html', fecha_hoy=datetime.date.today())


@facturacion_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@usuario_permitido
def editar_facturacion(id):
    """Editar registro de facturación."""
    connection = get_db_connection()
    registro = None

    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SELECT_FACTURACION, (id,))
        registro = cursor.fetchone()
        cursor.close()
        connection.close()

    if not registro:
        flash('Registro no encontrado', 'danger')
        return redirect(url_for('facturacion.listar_facturacion'))

    if request.method == 'POST':
        descripcion = request.form.get('descripcion', '').strip()
        fecha = request.form.get('fecha', '')
        pago = request.form.get('pago', 'N')
        costo = request.form.get('costo', '0')

        if not descripcion or not fecha:
            flash('Por favor, completa todos los campos obligatorios', 'danger')
            return render_template('editar_facturacion.html', registro=registro)

        try:
            costo = float(costo)
        except ValueError:
            flash('El costo debe ser un número válido', 'danger')
            return render_template('editar_facturacion.html', registro=registro)

        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                query = "UPDATE a_facturacion_sys SET descripcion=%s, fecha=%s, costo=%s, pago=%s WHERE id=%s"
                cursor.execute(query, (descripcion, fecha, costo, pago, id))
                connection.commit()
                cursor.close()
                connection.close()

                flash('Registro actualizado exitosamente', 'success')
                return redirect(url_for('facturacion.listar_facturacion'))
            except Error as e:
                flash(f'Error al actualizar: {str(e)}', 'danger')
                connection.close()
        else:
            flash('Error de conexión a la base de datos', 'danger')

    return render_template('editar_facturacion.html', registro=registro)


@facturacion_bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
@usuario_permitido
def eliminar_facturacion(id):
    """Eliminar registro de facturación."""
    connection = get_db_connection()

    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(sqlconstants.DELETE_FACTURACION, (id,))
            connection.commit()
            cursor.close()
            connection.close()

            flash('Registro eliminado exitosamente', 'success')
        except Error as e:
            flash(f'Error al eliminar: {str(e)}', 'danger')
            connection.close()
    else:
        flash('Error de conexión a la base de datos', 'danger')

    return redirect(url_for('facturacion.listar_facturacion'))
