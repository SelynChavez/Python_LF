from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file, Blueprint, current_app
from functools import wraps
from mysql.connector import Error
import datetime
import os

from werkzeug.utils import secure_filename

import sqlconstants

from .io_cash import bp as io_cash_bp


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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}


def get_usuarios_caja_grifero():
    """Obtiene lista de usuarios con rol CAJA, GRIFERO o ADMIN (excluyendo selyn y matias)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, fullname, roles FROM applicationuser WHERE roles IN ('CAJA', 'GRIFERO', 'ADMIN') AND status = 'ACTIVE' AND username NOT IN ('selyn', 'matias') ORDER BY fullname")
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        return usuarios
    except Exception as e:
        print(f"Error obteniendo usuarios: {e}")
        return []


@io_cash_bp.route('/reg_salidas', methods=['GET', 'POST'])
def reg_salidas():
    hoy = datetime.datetime.now().date()
    hoy_str = hoy.strftime('%Y-%m-%d')

    periodo = request.args.get('periodo', 'hoy')

    fecha_fin = hoy
    if periodo == 'hoy':
        fecha_inicio = hoy
    elif periodo == 'semana':
        fecha_inicio = hoy - datetime.timedelta(days=7)
    elif periodo == 'mes':
        fecha_inicio = hoy - datetime.timedelta(days=30)
    elif periodo == 'trimestre':
        fecha_inicio = hoy - datetime.timedelta(days=90)
    elif periodo == 'anio':
        fecha_inicio = hoy - datetime.timedelta(days=365)
    else:
        fecha_inicio = hoy

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(sqlconstants.LISTA_SALIDAS, (fecha_inicio, fecha_fin))
        salidas_hoy = cursor.fetchall()

        total_dia = 0
        for s0 in salidas_hoy:
            total_dia += float(s0['monto'])

        cursor.execute(sqlconstants.LISTA_TIPO_SALIDAS)
        tipos_salida = cursor.fetchall()

        cursor.execute(sqlconstants.LISTA_2_PADRONES)
        padrones = cursor.fetchall()

        cursor.execute(sqlconstants.LISTA_2_SOCIOS)
        socios = cursor.fetchall()

        cursor.execute(sqlconstants.LISTA_2_EMPLEADOS)
        empleados = cursor.fetchall()

        cursor.execute(sqlconstants.LISTA_2_PROVEEDORES)
        proveedores = cursor.fetchall()

        cursor.execute(sqlconstants.LISTA_2_TERCEROS)
        terceros_def = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    usuarios_caja_grifero = get_usuarios_caja_grifero()

    return render_template(
        "reg_salidas.html",
        salidas_hoy=salidas_hoy,
        tipos_salida=tipos_salida,
        padrones=padrones,
        socios=socios,
        empleados=empleados,
        proveedores=proveedores,
        terceros_def=terceros_def,
        hoy=hoy_str,
        total_dia=total_dia,
        periodo_seleccionado=periodo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        usuarios_caja_grifero=usuarios_caja_grifero
    )


@io_cash_bp.route('/guardar_salida', methods=['POST'])
def guardar_salida():
    conn = None
    cursor = None
    try:
        data = request.json
        current_app.logger.debug(f"Datos recibidos: {data}")

        conn = get_db_connection()
        cursor = conn.cursor()

        if data['id'] and int(data['id']) > 0:
            sql = sqlconstants.UPD_9_SALIDAS
            params = (
                data['fecha_solicitud'],
                data['tipo_salida'],
                data['tipo_beneficiario'],
                data.get('beneficiario'),
                data['beneficiario_nombre'],
                data['monto'],
                data.get('observaciones', ''),
                data['tipo_doc'],
                data['numero_doc'],
                data['periodo'],
                data.get('tipo_caja', 'EFECTIVO'),
                data.get('cajero', ''),
                session.get('user_username', 'sistema'),
                data['id']
            )
        else:
            sql = sqlconstants.INS_9_SALIDAS
            params = (
                data['fecha_solicitud'],
                data['tipo_salida'],
                data['tipo_beneficiario'],
                data.get('beneficiario'),
                data['beneficiario_nombre'],
                data['monto'],
                data.get('observaciones', ''),
                data['tipo_doc'],
                data['numero_doc'],
                data['periodo'],
                data.get('tipo_caja', 'EFECTIVO'),
                data.get('cajero', ''),
                session.get('user_username', 'sistema')
            )

        current_app.logger.debug(f"SQL: {sql}")
        current_app.logger.debug(f"Params: {params}")

        cursor.execute(sql, params)
        conn.commit()

        return jsonify({'success': True, 'id': data['id'] if data['id'] else cursor.lastrowid})

    except Exception as e:
        current_app.logger.error(f"Error al guardar: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@io_cash_bp.route('/obtener_salida/<int:id>')
def obtener_salida(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sqlconstants.SELECT_1_SALIDA, (id,))
        salida = cursor.fetchone()
        if salida:
            if salida['fecha_solicitud']:
                salida['fecha_solicitud'] = salida['fecha_solicitud'].strftime('%Y-%m-%d')
            return jsonify(salida)
        else:
            return jsonify({'error': 'Salida no encontrada'}), 404
    finally:
        cursor.close()
        conn.close()


@io_cash_bp.route('/buscar_beneficiarios/<tipo>')
def buscar_beneficiarios(tipo):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if tipo == 'PADRON':
            cursor.execute(sqlconstants.LISTA_3_PADRONES)
        elif tipo == 'SOCIO':
            cursor.execute(sqlconstants.LISTA_2_SOCIOS)
        elif tipo == 'EMPLEADO':
            cursor.execute(sqlconstants.LISTA_2_EMPLEADOS)
        elif tipo == 'PROVEEDOR':
            cursor.execute(sqlconstants.LISTA_2_PROVEEDORES)
        elif tipo == 'TERCERO_DEF':
            cursor.execute(sqlconstants.LISTA_3_TERCEROS)
        else:
            return jsonify([])
        resultados = cursor.fetchall()
        return jsonify(resultados)
    finally:
        cursor.close()
        conn.close()


@io_cash_bp.route('/salidas', methods=['GET', 'POST'])
def salidas():
    hoy = datetime.datetime.now()
    fecha_desde = hoy.replace(day=1).strftime('%Y-%m-%d')
    fecha_hasta = hoy.strftime('%Y-%m-%d')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sqlconstants.LISTA_DISCT_TIPO_SALIDAS)
        tipos_salida = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template("salidas.html", tipos_salida=tipos_salida, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)


@io_cash_bp.route('/buscar_salidas')
def buscar_salidas():
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    tipo_salida = request.args.get('tipo_salida', '')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = sqlconstants.LISTA_FILTRO_SALIDAS
        params = [fecha_desde, fecha_hasta]
        if tipo_salida:
            query += " AND tipo_salida = %s"
            params.append(tipo_salida)
        query += " ORDER BY fecha_solicitud DESC, id DESC"
        cursor.execute(query, params)
        resultados = cursor.fetchall()

        # Convertir beneficiarios en mayúsculas a TitleCase
        for resultado in resultados:
            if 'beneficiario_nombre' in resultado and resultado['beneficiario_nombre']:
                beneficiario = str(resultado['beneficiario_nombre']).strip()
                if beneficiario == beneficiario.upper():
                    resultado['beneficiario_nombre'] = ' '.join(word.capitalize() for word in beneficiario.split())

        return jsonify({
            'success': True,
            'data': resultados
        })
    except Exception as e:
        current_app.logger.error(f"Error en búsqueda: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })
    finally:
        cursor.close()
        conn.close()


@io_cash_bp.route('/subir_archivo', methods=['POST'])
def subir_archivo():
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'error': 'No se envió archivo'})
        archivo = request.files['archivo']
        id_registro = request.form.get('id')
        if archivo.filename == '':
            return jsonify({'success': False, 'error': 'Nombre de archivo vacío'})
        if not allowed_file(archivo.filename):
            return jsonify({'success': False, 'error': 'Tipo de archivo no permitido'})
        extension = archivo.filename.rsplit('.', 1)[1].lower()
        nombre_archivo = f"salida_{id_registro}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
        ruta_archivo = os.path.join(current_app.config['UPLOAD_FOLDER'], nombre_archivo)
        archivo.save(ruta_archivo)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(sqlconstants.UPD_SALIDA_ARCHIVO, (nombre_archivo, id_registro) )
            conn.commit()
            return jsonify({'success': True})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        current_app.logger.error(f"Error al subir archivo: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@io_cash_bp.route('/ver_pdf/<int:id>')
def ver_pdf(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sqlconstants.SEL_SALIDA_ARCHIVO , (id,))
        resultado = cursor.fetchone()
        if resultado and resultado['archivo']:
            ruta_archivo = os.path.join(current_app.config['UPLOAD_FOLDER'], resultado['archivo'])
            if os.path.exists(ruta_archivo):
                return send_file(ruta_archivo, mimetype='application/pdf')
        return "Archivo no encontrado", 404
    finally:
        cursor.close()
        conn.close()


@io_cash_bp.route('/anular_salida', methods=['POST'])
def anular_salida():
    try:
        data = request.json
        id_registro = data.get('id')
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(sqlconstants.UPD_SALIDA_ANULADO, (id_registro,) )
            conn.commit()
            return jsonify({'success': True})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        current_app.logger.error(f"Error al anular: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@io_cash_bp.route('/reg_ingresos', methods=['GET'])
def reg_ingresos():
    hoy = datetime.datetime.now().date()
    hoy_str = hoy.strftime('%Y-%m-%d')

    periodo = request.args.get('periodo', 'hoy')

    fecha_fin = hoy
    if periodo == 'hoy':
        fecha_inicio = hoy
    elif periodo == 'semana':
        fecha_inicio = hoy - datetime.timedelta(days=7)
    elif periodo == 'mes':
        fecha_inicio = hoy - datetime.timedelta(days=30)
    elif periodo == 'trimestre':
        fecha_inicio = hoy - datetime.timedelta(days=90)
    elif periodo == 'anio':
        fecha_inicio = hoy - datetime.timedelta(days=365)
    else:
        fecha_inicio = hoy

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(sqlconstants.LISTA_INGRESOS, (fecha_inicio, fecha_fin))
        ingresos = cursor.fetchall()

        total_periodo = 0
        for ingreso in ingresos:
            total_periodo += float(ingreso['monto'])

        cursor.execute(sqlconstants.LISTA_TIPO_INGRESOS)
        tipos_ingreso = cursor.fetchall()

        cursor.execute(sqlconstants.LISTA_2_PADRONES)
        padrones = cursor.fetchall()

        cursor.execute(sqlconstants.LISTA_3_SOCIOS)
        socios = cursor.fetchall()

        cursor.execute(sqlconstants.LISTA_3_EMPLEADOS)
        empleados = cursor.fetchall()

        cursor.execute(sqlconstants.LISTA_3_PROVEEDORES)
        proveedores = cursor.fetchall()

        cursor.execute(sqlconstants.LISTA_4_TERCEROS)
        terceros_def = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    usuarios_caja_grifero = get_usuarios_caja_grifero()

    return render_template(
        "reg_ingresos.html",
        ingresos=ingresos,
        tipos_ingreso=tipos_ingreso,
        padrones=padrones,
        socios=socios,
        empleados=empleados,
        proveedores=proveedores,
        terceros_def=terceros_def,
        hoy=hoy_str,
        total_periodo=total_periodo,
        periodo_seleccionado=periodo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        usuarios_caja_grifero=usuarios_caja_grifero
    )


@io_cash_bp.route('/guardar_ingreso', methods=['POST'])
def guardar_ingreso():
    conn = None
    cursor = None
    try:
        data = request.json
        current_app.logger.debug(f"Datos recibidos: {data}")

        conn = get_db_connection()
        cursor = conn.cursor()

        if data['id'] and int(data['id']) > 0:
            sql = sqlconstants.UPD_9_INGRESOS
            params = (
                data['fecha_solicitud'],
                data['tipo_ingreso'],
                data['tipo_tercero'],
                data.get('tercero_nombre', data.get('tercero', '')),
                data['monto'],
                data.get('observaciones', ''),
                data['tipo_doc'],
                data['numero_doc'],
                data['periodo'],
                data.get('cajero', ''),
                session.get('user_username', 'sistema'),
                data['id']
            )
        else:
            sql = sqlconstants.INS_9_INGRESOS
            params = (
                data['fecha_solicitud'],
                data['tipo_ingreso'],
                data['tipo_tercero'],
                data.get('tercero_nombre', data.get('tercero', '')),
                data['monto'],
                data.get('observaciones', ''),
                data['tipo_doc'],
                data['numero_doc'],
                data['periodo'],
                data.get('cajero', ''),
                session.get('user_username', 'sistema')
            )

        current_app.logger.debug(f"SQL: {sql}")
        current_app.logger.debug(f"Params: {params}")

        cursor.execute(sql, params)
        conn.commit()

        return jsonify({'success': True, 'id': data['id'] if data.get('id') else cursor.lastrowid})

    except Exception as e:
        current_app.logger.error(f"Error al guardar: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@io_cash_bp.route('/obtener_ingreso/<int:id>')
def obtener_ingreso(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sqlconstants.SELECT_1_INGRESO, (id,))
        ingreso = cursor.fetchone()
        if ingreso:
            if ingreso['fecha_solicitud']:
                ingreso['fecha_solicitud'] = ingreso['fecha_solicitud'].strftime('%Y-%m-%d')
            return jsonify(ingreso)
        else:
            return jsonify({'error': 'Ingreso no encontrado'}), 404
    finally:
        cursor.close()
        conn.close()
