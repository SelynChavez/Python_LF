from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response, Blueprint, current_app
from functools import wraps
from mysql.connector import Error
from io import BytesIO
import datetime
from decimal import Decimal
import base64
import os

from fpdf import FPDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

import sqlconstants

from .reportes import bp as reportes_bp


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


@reportes_bp.route('/reportes')
@login_required
def reportes():
    if session.get('user_rol') not in ('ADMIN', 'CAJA'):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    return render_template('reportes.html')


@reportes_bp.route('/rep_saldos_comb')
@login_required
def rep_saldos_comb():
    """Formulario para reporte de saldos de deuda de combustible por padrón."""
    if session.get('user_rol') not in ('ADMIN', 'GRIFERO', 'CAJA'):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    return render_template('rep_saldos_comb.html')


@reportes_bp.route('/rep1recibos')
def rep1recibos():
    p1 = datetime.datetime.now().strftime('%Y-%m-%d')
    p2 = datetime.datetime.now().strftime('%Y-%m-%d')
    p3 = "0"
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
    return render_template('rep1recibos.html', p1=p1, p2=p2, p3=p3)


@reportes_bp.route('/rep2recibos')
def rep2recibos():
    p1 = datetime.datetime.now().strftime('%Y-%m-%d')
    p2 = datetime.datetime.now().strftime('%Y-%m-%d')
    p3 = "0"
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
    tipos = []
    query = sqlconstants.DROPLIST_APORTES
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        tipos = cursor.fetchall()
        cursor.close()
        connection.close()
    else:
        return jsonify({'error': 'Error de conexión'}), 500
    return render_template('rep2recibos.html', tipos=tipos, p1=p1, p2=p2, p3=p3)


@reportes_bp.route('/rep_recibos_padron')
@login_required
def rep_recibos_padron():
    is_caja = session.get('user_rol') == 'CAJA'
    current_user = session.get('user_username', '')
    current_user_fullname = session.get('user_fullname', current_user)

    if session.get('user_rol') not in ('ADMIN', 'CAJA'):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

    p1 = datetime.datetime.now().strftime('%Y-%m-%d')
    p2 = datetime.datetime.now().strftime('%Y-%m-%d')
    p3 = "0"
    p5 = current_user if is_caja else "0"
    serie = "1"
    tipo_fecha = "fecha"
    usuarios = []

    if not is_caja:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.LISTA_USUARIOS_ACTIVOS)
            usuarios = cursor.fetchall()
            cursor.close()
            connection.close()

    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3', "0")
        p5 = request.form.get('p5', "0")
        serie = request.form.get('serie', "1")
        tipo_fecha = request.form.get('tipo_fecha', 'fecha')

        if is_caja:
            p5 = current_user

    return render_template('rep_recibos_padron.html', p1=p1, p2=p2, p3=p3, p5=p5, serie=serie, tipo_fecha=tipo_fecha, usuarios=usuarios, is_caja=is_caja, current_user=current_user, current_user_fullname=current_user_fullname)


@reportes_bp.route('/rep_recibos_aportes')
@login_required
def rep_recibos_aportes():
    p1 = datetime.datetime.now().strftime('%Y-%m-%d')
    p2 = datetime.datetime.now().strftime('%Y-%m-%d')
    p3 = "0"
    serie = "1"
    tipo_fecha = "fecha"
    tipos = []
    query = sqlconstants.DROPLIST_APORTES
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        tipos = cursor.fetchall()
        cursor.close()
        connection.close()
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3', "0")
        serie = request.form.get('serie', "1")
        tipo_fecha = request.form.get('tipo_fecha', 'fecha')
    return render_template('rep_recibos_aportes.html', tipos=tipos, p1=p1, p2=p2, p3=p3, serie=serie, tipo_fecha=tipo_fecha)


@reportes_bp.route('/rep_salidas_entre_fechas')
@login_required
def rep_salidas_entre_fechas():
    if session.get('user_rol') != 'ADMIN':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

    p1 = datetime.datetime.now().strftime('%Y-%m-%d')
    p2 = datetime.datetime.now().strftime('%Y-%m-%d')
    p3 = "0"
    p4 = "0"
    p5 = ""
    p6 = ""
    p7 = ""

    connection = get_db_connection()
    tipos_salida = []
    tipos_beneficiario = [
        {'codigo': 'PADRON', 'descripcion': '1. Padrón'},
        {'codigo': 'SOCIO', 'descripcion': '2. Socio'},
        {'codigo': 'EMPLEADO', 'descripcion': '3. Empleado'},
        {'codigo': 'PROVEEDOR', 'descripcion': '4. Proveedor'},
        {'codigo': 'TERCERO_DEF', 'descripcion': '5. Tercero Definido'},
        {'codigo': 'TERCERO_ABIERTO', 'descripcion': '6. Tercero Abierto'}
    ]

    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_TIPO_SALIDAS)
        tipos_salida = cursor.fetchall()
        cursor.close()
        connection.close()

    return render_template('rep_salidas_entre_fechas.html',
                         p1=p1, p2=p2, p3=p3, p4=p4, p5=p5, p6=p6, p7=p7,
                         tipos_salida=tipos_salida, tipos_beneficiario=tipos_beneficiario)


@reportes_bp.route('/rep_ventas_comb')
@login_required
def rep_ventas_comb():
    if session.get('user_rol') not in ('ADMIN', 'GRIFERO'):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    p1 = datetime.datetime.now().strftime('%Y-%m-%d')
    p2 = datetime.datetime.now().strftime('%Y-%m-%d')
    p3 = "0"
    p4 = "TODOS"
    p5 = "0"

    connection = get_db_connection()
    usuarios = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_USUARIOS_ACTIVOS)
        usuarios = cursor.fetchall()
        cursor.close()
        connection.close()

    return render_template('rep_ventas_comb.html', p1=p1, p2=p2, p3=p3, p4=p4, p5=p5, usuarios=usuarios)


@reportes_bp.route('/rep_ventas_comb_maquina')
@login_required
def rep_ventas_comb_maquina():
    if session.get('user_rol') not in ('ADMIN', 'GRIFERO', 'CAJA'):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

    is_caja_or_grifero = session.get('user_rol') in ('CAJA', 'GRIFERO')
    current_user = session.get('user_username', '')

    p1 = datetime.datetime.now().strftime('%Y-%m-%d')
    p2 = datetime.datetime.now().strftime('%Y-%m-%d')
    p3 = "0"
    p5 = current_user if is_caja_or_grifero else "0"

    # Cargar máquinas y usuarios
    maquinas = []
    usuarios = []
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, numero FROM a_maquinas ORDER BY numero")
        maquinas = cursor.fetchall()
        if not is_caja_or_grifero:
            cursor.execute(sqlconstants.LISTA_USUARIOS_ACTIVOS)
            usuarios = cursor.fetchall()
        cursor.close()
        connection.close()

    return render_template('rep_ventas_comb_maquina.html', p1=p1, p2=p2, p3=p3, p5=p5, maquinas=maquinas, usuarios=usuarios, is_caja_or_grifero=is_caja_or_grifero, current_user=current_user)


def generar_pdf_saldos_comb(pdf, titulo, subtitulo):
    buffer = BytesIO()
    pdf.set_left_margin(15)
    pdf.set_right_margin(5)

    # Cabecera
    pdf.set_font("Arial", 'B', 10)
    hora = str(datetime.datetime.now())[0:19]
    usr = session['user_username']
    pag = pdf.page_no()
    pdf.cell(0, 8, f"E.T. Las Flores :: {usr} :: {hora} :: Pag. {pag}", 0, 1, 'L')
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 6, titulo, 0, 1, 'C')
    pdf.ln()

    # Subtítulo
    pdf.set_font("Arial", 'B', 10)
    subtitulo_clean = subtitulo.replace("−", "-")
    pdf.cell(0, 4, f"::{subtitulo_clean}::", 0, 1, 'C')
    pdf.ln(12)

    # Encabezados
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(10, 5, "#", 1, 0, 'C', True)
    pdf.cell(12, 5, "Padron", 1, 0, 'C', True)
    pdf.cell(75, 5, "Socio", 1, 0, 'L', True)
    pdf.cell(25, 5, "Ventas Cred", 1, 0, 'R', True)
    pdf.cell(25, 5, "Cobrado", 1, 0, 'R', True)
    pdf.cell(28, 5, "Saldo Pendiente", 1, 1, 'R', True)

    connection = get_db_connection()
    if not connection:
        return None

    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.REP_SALDOS_COMB)
    saldos = cursor.fetchall()
    cursor.close()
    connection.close()

    # Listar datos
    pdf.set_font("Arial", '', 8)
    total_general = 0
    lin = 0
    for idx, saldo in enumerate(saldos, 1):
        lin += 1
        nombre = saldo['nombre'][:50] if saldo['nombre'] else ""

        pdf.cell(10, 5, str(idx), 1, 0, 'C')
        pdf.cell(12, 5, str(saldo['padron']), 1, 0, 'C')
        pdf.cell(75, 5, nombre, 1, 0, 'L')
        pdf.cell(25, 5, f"S/. {float(saldo['ventas']):.2f}", 1, 0, 'R')
        pdf.cell(25, 5, f"S/. {float(saldo['cobrado']):.2f}", 1, 0, 'R')
        pdf.cell(28, 5, f"S/. {float(saldo['saldo']):.2f}", 1, 1, 'R')

        total_general += float(saldo['saldo'])

        if lin == 35:
            pdf.add_page()
            pdf.set_left_margin(15)
            pdf.set_right_margin(5)

            # Cabecera para nueva página
            pdf.set_font("Arial", 'B', 10)
            hora = str(datetime.datetime.now())[0:19]
            usr = session['user_username']
            pag = pdf.page_no()
            pdf.cell(0, 8, f"E.T. Las Flores :: {usr} :: {hora} :: Pag. {pag}", 0, 1, 'L')
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 6, titulo, 0, 1, 'C')
            pdf.ln()

            pdf.set_font("Arial", 'B', 10)
            subtitulo_clean = subtitulo.replace("−", "-")
            pdf.cell(0, 4, f"::{subtitulo_clean}::", 0, 1, 'C')
            pdf.ln(12)

            lin = 0
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(10, 5, "#", 1, 0, 'C', True)
            pdf.cell(12, 5, "Padron", 1, 0, 'C', True)
            pdf.cell(75, 5, "Socio", 1, 0, 'L', True)
            pdf.cell(25, 5, "Ventas Cred", 1, 0, 'R', True)
            pdf.cell(25, 5, "Cobrado", 1, 0, 'R', True)
            pdf.cell(28, 5, "Saldo Pendiente", 1, 1, 'R', True)
            pdf.set_font("Arial", '', 8)

    # Total general
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(150, 200, 150)
    pdf.cell(0, 8, f"#REGS: {len(saldos)} :: TOTAL SALDO PENDIENTE: S/. {total_general:.2f}", 0, 1, True)

    pdf_output = pdf.output(dest='S').encode('latin-1')
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer


def generar_pdf_ventas_comb(pdf, p1, p2, p3, p4, p5, titulo, subtitulo):
    buffer = BytesIO()
    pdf.set_left_margin(15)
    pdf.set_right_margin(5)

    # Cabecera
    pdf.set_font("Arial", 'B', 10)
    hora = str(datetime.datetime.now())[0:19]
    usr = session['user_username']
    pag = pdf.page_no()
    pdf.cell(0, 8, f"E.T. Las Flores :: {usr} :: {hora} :: Pag. {pag}", 0, 1, 'L')
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 6, titulo, 0, 1, 'C')
    pdf.ln()

    # Subtítulo con filtros
    pdf.set_font("Arial", 'B', 10)
    subtitulo = subtitulo.replace("$p1$", p1)
    subtitulo = subtitulo.replace("$p2$", p2)
    subtitulo = subtitulo.replace("$p3$", p3 if p3 != "0" else "Todos")
    subtitulo = subtitulo.replace("$p4$", p4)
    subtitulo = subtitulo.replace("$p5$", p5 if p5 != "0" else "Todos")
    subtitulo_clean = subtitulo.replace("−", "-")
    pdf.cell(0, 4, f"::{subtitulo_clean}::", 0, 1, 'C')
    pdf.ln(12)

    # Encabezados
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(18, 5, "Fecha", 1, 0, 'C', True)
    pdf.cell(12, 5, "Padron", 1, 0, 'C', True)
    pdf.cell(70, 5, "Nombre Padron", 1, 0, 'L', True)
    pdf.cell(25, 5, "Forma Pago", 1, 0, 'C', True)
    pdf.cell(20, 5, "Monto", 1, 0, 'R', True)
    pdf.cell(30, 5, "Observacion", 1, 0, 'L', True)
    pdf.cell(10, 5, "Usr", 1, 1, 'C', True)

    connection = get_db_connection()
    if not connection:
        return None

    cursor = connection.cursor(dictionary=True)
    query = sqlconstants.REP_VENTAS_COMB
    query = query.replace("$p1$", p1)
    query = query.replace("$p2$", p2)
    query = query.replace("$p3$", p3)
    query = query.replace("$p4$", p4)
    query = query.replace("$p5$", p5)
    cursor.execute(query)
    datos = cursor.fetchall()

    # Datos por día para totales
    query_dia = sqlconstants.REP_VENTAS_COMB_TOTAL_DIA
    query_dia = query_dia.replace("$p1$", p1)
    query_dia = query_dia.replace("$p2$", p2)
    query_dia = query_dia.replace("$p3$", p3)
    query_dia = query_dia.replace("$p4$", p4)
    query_dia = query_dia.replace("$p5$", p5)
    cursor.execute(query_dia)
    datos_dia = cursor.fetchall()
    cursor.close()
    connection.close()

    # Listar datos detallados
    pdf.set_font("Arial", '', 7)
    total_general = 0
    lin = 0
    for dato in datos:
        lin += 1
        fecha_str = dato['fecha'].strftime('%d-%m-%Y') if hasattr(dato['fecha'], 'strftime') else str(dato['fecha'])
        nombre = dato['nombre_padron'][:35] if dato['nombre_padron'] else ""
        obs = (dato['observacion'][:15] if dato['observacion'] else "")
        usr_short = dato['webuser'][:6] if dato['webuser'] else ""

        pdf.cell(18, 4, fecha_str, 1, 0, 'C')
        pdf.cell(12, 4, str(dato['padron']), 1, 0, 'C')
        pdf.cell(70, 4, nombre, 1, 0, 'L')
        pdf.cell(25, 4, dato['forma_pago'], 1, 0, 'C')
        pdf.cell(20, 4, f"S/. {float(dato['monto']):.2f}", 1, 0, 'R')
        pdf.cell(30, 4, obs, 1, 0, 'L')
        pdf.cell(10, 4, usr_short, 1, 1, 'C')

        total_general += float(dato['monto'])

        if lin == 40:
            pdf.add_page()
            pdf.set_left_margin(15)
            pdf.set_right_margin(5)

            # Cabecera para nueva página
            pdf.set_font("Arial", 'B', 10)
            hora = str(datetime.datetime.now())[0:19]
            usr = session['user_username']
            pag = pdf.page_no()
            pdf.cell(0, 8, f"E.T. Las Flores :: {usr} :: {hora} :: Pag. {pag}", 0, 1, 'L')
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 6, titulo, 0, 1, 'C')
            pdf.ln()

            pdf.set_font("Arial", 'B', 10)
            subtitulo_new = subtitulo.replace("$p1$", p1)
            subtitulo_new = subtitulo_new.replace("$p2$", p2)
            subtitulo_new = subtitulo_new.replace("$p3$", p3 if p3 != "0" else "Todos")
            subtitulo_new = subtitulo_new.replace("$p4$", p4)
            subtitulo_new = subtitulo_new.replace("−", "-")
            pdf.cell(0, 4, f"::{subtitulo_new}::", 0, 1, 'C')
            pdf.ln(12)

            lin = 0
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(18, 5, "Fecha", 1, 0, 'C', True)
            pdf.cell(12, 5, "Padron", 1, 0, 'C', True)
            pdf.cell(70, 5, "Nombre Padron", 1, 0, 'L', True)
            pdf.cell(25, 5, "Forma Pago", 1, 0, 'C', True)
            pdf.cell(20, 5, "Monto", 1, 0, 'R', True)
            pdf.cell(30, 5, "Observacion", 1, 0, 'L', True)
            pdf.cell(10, 5, "Usr", 1, 1, 'C', True)
            pdf.set_font("Arial", '', 7)

    # Resumen por día
    pdf.ln(3)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 5, "RESUMEN DIARIO", 0, 1, 'L')
    pdf.ln(1)

    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(220, 220, 200)
    pdf.cell(25, 5, "Fecha", 1, 0, 'C', True)
    pdf.cell(60, 5, "Forma Pago", 1, 0, 'L', True)
    pdf.cell(35, 5, "Total", 1, 0, 'R', True)
    pdf.cell(20, 5, "Cant", 1, 1, 'C', True)

    pdf.set_font("Arial", '', 8)
    fecha_anterior = None
    for dato_dia in datos_dia:
        fecha_str = dato_dia['fecha'].strftime('%d-%m-%Y') if hasattr(dato_dia['fecha'], 'strftime') else str(dato_dia['fecha'])
        pdf.cell(25, 5, fecha_str, 1, 0, 'C')
        pdf.cell(60, 5, dato_dia['forma_pago'], 1, 0, 'L')
        pdf.cell(35, 5, f"S/. {float(dato_dia['total_monto']):.2f}", 1, 0, 'R')
        pdf.cell(20, 5, str(dato_dia['cantidad']), 1, 1, 'C')

    # Total general
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(150, 200, 150)
    pdf.cell(0, 8, f"#REGS: {len(datos)} :: TOTAL GENERAL: S/. {total_general:.2f}", 0, 1, True)

    pdf_output = pdf.output(dest='S').encode('latin-1')
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer


def generar_pdf_ventas_comb_maquina(p1, p2, p3, p5, titulo, subtitulo):
    buffer = BytesIO()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_left_margin(10)
    pdf.set_right_margin(5)

    # Cabecera
    pdf.set_font("Arial", 'B', 10)
    hora = str(datetime.datetime.now())[0:19]
    usr = session['user_username']
    pag = pdf.page_no()
    pdf.cell(0, 8, f"E.T. Las Flores :: {usr} :: {hora} :: Pag. {pag}", 0, 1, 'L')
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 6, titulo, 0, 1, 'C')
    pdf.ln()

    # Subtítulo con filtros
    pdf.set_font("Arial", 'B', 10)
    subtitulo = subtitulo.replace("$p1$", p1)
    subtitulo = subtitulo.replace("$p2$", p2)
    subtitulo = subtitulo.replace("$p3$", p3 if p3 != "0" else "Todas")
    subtitulo = subtitulo.replace("$p5$", p5 if p5 != "0" else "Todos")
    subtitulo_clean = subtitulo.replace("−", "-")
    pdf.cell(0, 4, f"::{subtitulo_clean}::", 0, 1, 'C')
    pdf.ln(8)

    # Encabezados
    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(12, 5, "Maquina", 1, 0, 'C', True)
    pdf.cell(18, 5, "Turno", 1, 0, 'L', True)
    pdf.cell(20, 5, "Local", 1, 0, 'L', True)
    pdf.cell(16, 5, "Fecha", 1, 0, 'C', True)
    pdf.cell(12, 5, "L.Inicial", 1, 0, 'R', True)
    pdf.cell(12, 5, "L.Final", 1, 0, 'R', True)
    pdf.cell(13, 5, "Galones", 1, 0, 'R', True)
    pdf.cell(17, 5, "Total S/.", 1, 0, 'R', True)
    pdf.cell(15, 5, "Usuario", 1, 1, 'C', True)

    connection = get_db_connection()
    if not connection:
        return buffer

    cursor = connection.cursor(dictionary=True)
    query = sqlconstants.REP_VENTAS_COMB_MAQUINA
    query = query.replace("$p1$", p1)
    query = query.replace("$p2$", p2)
    query = query.replace("$p3$", p3)
    query = query.replace("$p5$", p5)
    cursor.execute(query)
    datos = cursor.fetchall()
    cursor.close()
    connection.close()

    # Listar datos
    pdf.set_font("Arial", '', 7)
    total_general_galones = 0
    total_general_soles = 0
    maquina_actual = None
    subtotal_maquina_galones = 0
    subtotal_maquina_soles = 0
    lin = 0

    for dato in datos:
        # Cambio de máquina
        if maquina_actual != dato['machine_number']:
            if maquina_actual is not None:
                # Subtotal de máquina anterior
                pdf.set_font("Arial", 'B', 8)
                pdf.cell(90, 5, f"Subtotal Maquina {maquina_actual}:", 0, 0, 'R')
                pdf.cell(13, 5, f"{subtotal_maquina_galones:.2f}", 0, 0, 'R')
                pdf.cell(17, 5, f"S/. {subtotal_maquina_soles:.2f}", 0, 1, 'R')
                pdf.ln(2)
                lin += 2

            maquina_actual = dato['machine_number']
            subtotal_maquina_galones = 0
            subtotal_maquina_soles = 0

        lin += 1
        fecha_str = dato['fecha'].strftime('%d-%m-%Y') if hasattr(dato['fecha'], 'strftime') else str(dato['fecha'])
        nombre = dato['nombre'] if dato['nombre'] else ""
        local = dato['local'] if dato['local'] else ""
        usr_short = dato['webuser'][:12] if dato['webuser'] else ""

        galones = float(dato['galones_vendidos']) if dato['galones_vendidos'] else 0
        total_soles = float(dato['total_precio']) if dato['total_precio'] else 0

        subtotal_maquina_galones += galones
        subtotal_maquina_soles += total_soles
        total_general_galones += galones
        total_general_soles += total_soles

        pdf.set_font("Arial", '', 7)
        pdf.cell(12, 4, str(maquina_actual), 1, 0, 'C')
        pdf.cell(18, 4, nombre[:18], 1, 0, 'L')
        pdf.cell(20, 4, local[:12], 1, 0, 'L')
        pdf.cell(16, 4, fecha_str, 1, 0, 'C')
        pdf.cell(12, 4, f"{dato['lectura_inicial']:.0f}", 1, 0, 'R')
        pdf.cell(12, 4, f"{dato['lectura_final']:.0f}", 1, 0, 'R')
        pdf.cell(13, 4, f"{galones:.2f}", 1, 0, 'R')
        pdf.cell(17, 4, f"S/. {total_soles:.2f}", 1, 0, 'R')
        pdf.cell(15, 4, usr_short, 1, 1, 'C')

        if lin == 40:
            pdf.add_page()
            pdf.set_left_margin(10)
            pdf.set_right_margin(5)

            # Cabecera para nueva página
            pdf.set_font("Arial", 'B', 10)
            hora = str(datetime.datetime.now())[0:19]
            usr = session['user_username']
            pag = pdf.page_no()
            pdf.cell(0, 8, f"E.T. Las Flores :: {usr} :: {hora} :: Pag. {pag}", 0, 1, 'L')
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 6, titulo, 0, 1, 'C')
            pdf.ln()

            pdf.set_font("Arial", 'B', 10)
            subtitulo_new = subtitulo.replace("$p1$", p1)
            subtitulo_new = subtitulo_new.replace("$p2$", p2)
            subtitulo_new = subtitulo_new.replace("$p3$", p3 if p3 != "0" else "Todas")
            subtitulo_new = subtitulo_new.replace("$p5$", p5 if p5 != "0" else "Todos")
            subtitulo_new = subtitulo_new.replace("−", "-")
            pdf.cell(0, 4, f"::{subtitulo_new}::", 0, 1, 'C')
            pdf.ln(8)

            lin = 0
            pdf.set_font("Arial", 'B', 8)
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(12, 5, "Maquina", 1, 0, 'C', True)
            pdf.cell(18, 5, "Turno", 1, 0, 'L', True)
            pdf.cell(20, 5, "Local", 1, 0, 'L', True)
            pdf.cell(16, 5, "Fecha", 1, 0, 'C', True)
            pdf.cell(12, 5, "L.Inicial", 1, 0, 'R', True)
            pdf.cell(12, 5, "L.Final", 1, 0, 'R', True)
            pdf.cell(13, 5, "Galones", 1, 0, 'R', True)
            pdf.cell(17, 5, "Total S/.", 1, 0, 'R', True)
            pdf.cell(15, 5, "Usuario", 1, 1, 'C', True)
            pdf.set_font("Arial", '', 7)

    # Subtotal de última máquina
    if maquina_actual is not None:
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(90, 5, f"Subtotal Maquina {maquina_actual}:", 0, 0, 'R')
        pdf.cell(13, 5, f"{subtotal_maquina_galones:.2f}", 0, 0, 'R')
        pdf.cell(17, 5, f"S/. {subtotal_maquina_soles:.2f}", 0, 1, 'R')
        pdf.ln(2)

    # Total general
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(150, 200, 150)
    pdf.cell(0, 8, f"#REGS: {len(datos)} :: TOTAL GALONES: {total_general_galones:.2f} :: TOTAL S/.: S/. {total_general_soles:.2f}", 0, 1, True)

    pdf_output = pdf.output(dest='S').encode('latin-1')
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer


def generar_pdf_cabecera(pdf, cod, titulo, subtitulo, sum4, p1, p2, p3, p4, p5, p6, serie="1"):
    pdf.set_font("Arial", 'B', 10)
    hora1 = str(datetime.datetime.now())[0:19] + "  -  Pag. # " + str(pdf.page_no()+sum4)
    usr = session['user_username']
    spc = " " * 70
    pdf.cell(0, 8, f"E.T.Las Flores :: [{cod}] - [{usr}] - {spc} {hora1}", 0, 1, 'R')
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 4, f"{titulo}", 0, 1, 'C')
    pdf.ln()
    pdf.set_font("Arial", 'B', 10)
    subtitulo = subtitulo.replace("$p1$", p1)
    subtitulo = subtitulo.replace("$p2$", p2)
    subtitulo = subtitulo.replace("$p3$", p3)
    subtitulo = subtitulo.replace("$p4$", p4)
    subtitulo = subtitulo.replace("$p5$", p5 if p5 != "0" else "Todos")
    subtitulo = subtitulo.replace("$p6$", p6)
    subtitulo = subtitulo.replace("$serie$", serie)
    subtitulo = subtitulo.replace("−", "-")
    pdf.cell(0, 4, f"::{subtitulo}::", 0, 1, 'C')
    pdf.ln()
    pdf.set_font("Arial", 'B', 9)
    if (cod in ('REP1APORTES', 'REP_FLEX_PAD')):
        pdf.cell(18, 5, "Nro.Rec", 1)
        pdf.cell(18, 5, "Registro", 1)
        pdf.cell(18, 5, "Girado..", 1)
        pdf.cell(18, 5, "TpRec", 1)
        pdf.cell(60, 5, "Padron Socio", 1)
        pdf.cell(20, 5, "Aportado", 1)
        pdf.cell(8, 5, "Act?", 1)
        pdf.cell(18, 5, "Usuario", 1)
        pdf.cell(15, 5, "IdCtrl", 1)
    elif(cod in ('REP2APORTES', 'REP_FLEX_APO')):
        pdf.cell(18, 5, "Nro.Rec.", 1)
        pdf.cell(18, 5, "Registro", 1)
        pdf.cell(18, 5, "Girado", 1)
        pdf.cell(60, 5, "Emitido A", 1)
        pdf.cell(18, 5, "TipRec", 1)
        pdf.cell(15, 5, "Mon", 1)
        pdf.cell(20, 5, "Aportado", 1, 0, 'R')
        pdf.cell(20, 5, "Tp.Aporte", 1)
    elif(cod=="REP-PCGE"):
        pdf.cell(15, 5, "Elmnto", 1)
        pdf.cell(20, 5, "Cuenta", 1)
        pdf.cell(140, 5, "Nombre de la Cuenta Contable", 1)
        pdf.cell(10, 5, "ID", 1)
    else:
        pdf.cell(15, 5, "ID", 1)
    pdf.ln()


def generar_pdf_salidas_entre_fechas(p1, p2, p3, p4, p5, p6, p7, titulo, subtitulo):
    buffer = BytesIO()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_left_margin(8)

    # Encabezado
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, titulo, 0, 1, 'C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5, subtitulo, 0, 1, 'C')
    pdf.ln(3)

    # Encabezados de columna
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(10, 5, 'Id', 1)
    pdf.cell(15, 5, 'Fecha', 1)
    pdf.cell(30, 5, 'Salida', 1)
    pdf.cell(30, 5, 'Beneficiario', 1)
    pdf.cell(12, 5, 'T.Doc', 1)
    pdf.cell(16, 5, 'Nro Doc', 1)
    pdf.cell(16, 5, 'Monto', 1, 'R')
    pdf.cell(15, 5, 'Tipo Salida', 1, 1)

    # Obtener datos
    connection = get_db_connection()
    if not connection:
        return None

    cursor = connection.cursor(dictionary=True)
    query = sqlconstants.REP_SALIDAS_ENTRE_FECHAS
    query = query.replace("$p1$", p1)
    query = query.replace("$p2$", p2)
    query = query.replace("$p3$", p3)
    query = query.replace("$p4$", p4)
    query = query.replace("$p5$", p5 if p5 else '')
    query = query.replace("$p6$", p6 if p6 else '')
    query = query.replace("$p7$", p7 if p7 else '')

    cursor.execute(query)
    datos = cursor.fetchall()
    cursor.close()
    connection.close()

    # Procesar datos
    pdf.set_font("Arial", '', 8)
    total_general = 0
    total_dia = 0
    fecha_actual = None
    linea = 0

    for dato in datos:
        # Si cambia la fecha, mostrar subtotal del día anterior
        if fecha_actual and dato['fecha_orden'] != fecha_actual:
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(129, 5, f'Total del Día {fecha_actual}:', 1)
            pdf.cell(16, 5, f'{total_dia:.2f}', 1, 'R')
            pdf.cell(15, 5, '', 1, 1)
            total_dia = 0
            pdf.set_font("Arial", '', 8)

        fecha_actual = dato['fecha_orden']
        linea += 1

        # Abrevar tipo de doc
        tipo_doc_abrevia = dato['tipo_doc'][:3] if dato['tipo_doc'] else ''

        # Mostrar fila
        pdf.cell(10, 5, str(dato['id']), 1)
        pdf.cell(15, 5, dato['fecha'], 1)
        pdf.cell(30, 5, dato['salida_desc'][:18], 1)
        pdf.cell(30, 5, dato['beneficiario'][:18], 1)
        pdf.cell(12, 5, tipo_doc_abrevia, 1)
        pdf.cell(16, 5, str(dato['numero_doc']), 1)
        pdf.cell(16, 5, f"{float(dato['monto']):.2f}", 1, 'R')
        pdf.cell(15, 5, dato['tipo_salida'], 1, 1)

        total_dia += float(dato['monto'])
        total_general += float(dato['monto'])

        # Nueva página si es necesario
        if linea >= 40:
            pdf.ln(2)
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(129, 5, f'Total del Día {fecha_actual}:', 1)
            pdf.cell(16, 5, f'{total_dia:.2f}', 1, 'R')
            pdf.cell(15, 5, '', 1, 1)
            pdf.add_page()
            pdf.set_left_margin(8)
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(10, 5, 'Id', 1)
            pdf.cell(15, 5, 'Fecha', 1)
            pdf.cell(30, 5, 'Salida', 1)
            pdf.cell(30, 5, 'Beneficiario', 1)
            pdf.cell(12, 5, 'T.Doc', 1)
            pdf.cell(16, 5, 'Nro Doc', 1)
            pdf.cell(16, 5, 'Monto', 1, 'R')
            pdf.cell(15, 5, 'Tipo Salida', 1, 1)
            total_dia = 0
            linea = 0
            pdf.set_font("Arial", '', 8)

    # Último total del día
    if fecha_actual:
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(129, 5, f'Total del Día {fecha_actual}:', 1)
        pdf.cell(16, 5, f'{total_dia:.2f}', 1, 'R')
        pdf.cell(15, 5, '', 1, 1)

    # Total final
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(129, 7, 'TOTAL FINAL:', 1)
    pdf.cell(16, 7, f'{total_general:.2f}', 1, 'R')
    pdf.cell(15, 7, '', 1, 1)

    pdf_output = pdf.output(dest='S').encode('latin-1')
    return BytesIO(pdf_output)


def generar_pdf_reporte(cod, titulo, subtitulo, p1, p2, p3, p4, p5, p6, p7="", serie="1", tipo_fecha="fecha"):
    buffer = BytesIO()
    pdf = FPDF()
    pdf.add_page()

    if cod == "REP_VENTAS_COMB":
        return generar_pdf_ventas_comb(pdf, p1, p2, p3, p4, p5, titulo, subtitulo)
    elif cod == "REP_SALDOS_COMB":
        return generar_pdf_saldos_comb(pdf, titulo, subtitulo)
    elif cod == "REP_SALIDAS_ENTRE_FECHAS":
        return generar_pdf_salidas_entre_fechas(p1, p2, p3, p4, p5, p6, p7, titulo, subtitulo)

    # Configurar margen izquierdo
    if cod in ('REP_FLEX_PAD', 'REP_FLEX_APO'):
        pdf.set_left_margin(13.5)
    else:
        pdf.set_left_margin(3.5)
    print('Comenzando Reporte.. CABECERA')
    generar_pdf_cabecera(pdf, cod, titulo, subtitulo, 0, p1, p2, p3, p4, p5, p6, serie)
    print('Procesando Reporte..')
    query = sqlconstants.REP1APORTES
    if (cod=="REP2APORTES"):
        query = sqlconstants.REP2APORTES
    elif (cod=="REP-PCGE"):
        query = sqlconstants.REP0PCGE
    elif (cod=="REP_FLEX_PAD"):
        query = sqlconstants.REP_FLEX_RECIBOS_PADRON
    elif (cod=="REP_FLEX_APO"):
        query = sqlconstants.REP_FLEX_RECIBOS_APORTES

    # Convertir serie a formato SQL IN()
    serie_map = {'1': "'1'", '2': "'2'", '3-5': "'3','4','5'", '5': "'5'", '6': "'6'"}
    serie_sql = serie_map.get(serie, "'1'")

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        query = query.replace("$p1$", p1)
        query = query.replace("$p2$", p2)
        query = query.replace("$p3$", p3)
        query = query.replace("$p4$", p4)
        query = query.replace("$p5$", p5)
        query = query.replace("$p6$", p6)
        query = query.replace("$serie$", serie_sql)
        query = query.replace("$tipo_fecha$", tipo_fecha)
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
    else:
        return jsonify({'error': 'Error de conexión'}), 500
    pdf.set_font("Arial", '', 8)
    to1 = 0
    rgt = 0
    lin = 0
    for dato in datos:
        lin += 1
        rgt += 1
        if cod in ('REP1APORTES', 'REP_FLEX_PAD'):
            pdf.cell(18, 5, dato["d1"], 1)
            pdf.cell(18, 5, dato["d2"], 1)
            pdf.cell(18, 5, dato["d3"], 1)
            pdf.cell(18, 5, dato["d4"], 1)
            d6 = dato["d6"]
            pdf.cell(60, 5, d6[:33], 1)
            pdf.cell(20, 5, dato["d7"], 1, 0, 'R')
            pdf.cell(8, 5, dato["d8"], 1)
            pdf.cell(18, 5, dato["d9"], 1)
            pdf.cell(15, 5, dato["d10"], 1)
            to1 += float(dato["d7"])
        elif(cod in ('REP2APORTES', 'REP_FLEX_APO')):
            pdf.cell(18, 5, dato["d1"], 1)
            pdf.cell(18, 5, dato["d2"], 1)
            pdf.cell(18, 5, dato["d3"], 1)
            d4 = dato["d4"]
            pdf.cell(60, 5, d4[:33], 1)
            pdf.cell(18, 5, dato["d5"], 1)
            pdf.cell(15, 5, dato["d6"], 1)
            pdf.cell(20, 5, dato["d7"], 1, 0, 'R')
            pdf.cell(20, 5, dato["d8"], 1)
            to1 += float(dato["d7"])
        elif(cod=="REP-PCGE"):
            pdf.cell(15, 5, str(dato["d1"]), 1)
            pdf.cell(20, 5, str(dato["d2"]), 1)
            pdf.cell(140, 5, str(dato["d3"]), 1)
            pdf.cell(10, 5, str(dato["d4"]), 1)
        else:
            pdf.cell(15, 5, str(lin), 1)
        pdf.ln()
        if lin==47:
            pdf.ln(6)
            lin = 0
            generar_pdf_cabecera(pdf, cod, titulo, subtitulo, 1, p1, p2, p3, p4, p5, p6, serie)
            pdf.set_font("Arial", '', 8)
    print('Finalizando Reporte..')
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 12)
    total9 = f"TOTAL APORTADO:... {to1}"
    if(cod=="REP-PCGE"):
        total9 = ""
    pdf.cell(0, 10, f"#REGS:...{rgt} :: {total9}", 0, 1)
    pdf_output = pdf.output(dest='S').encode('latin-1')
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer


@reportes_bp.route('/generar_reporte_vtas_maquina', methods=['POST'])
def generar_reporte_vtas_maquina():
    try:
        titulo = request.form.get('titulo', 'Reporte')
        subtitulo = request.form.get('subtitulo', '')
        p1 = request.form.get('p1', '')
        p2 = request.form.get('p2', '')
        p3 = request.form.get('p3', '0')
        p5 = request.form.get('p5', '0')

        pdf_buffer = generar_pdf_ventas_comb_maquina(p1, p2, p3, p5, titulo, subtitulo)
        pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
        return render_template('mostrar_pdf.html', pdf_data=pdf_base64, cod='REP_VENTAS_COMB_MAQUINA')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reportes_bp.route('/generar_reporte', methods=['POST'])
def generar_reporte():
    try:
        cod = request.form.get('cod', 'Rep1')
        titulo = request.form.get('titulo', 'Reporte')
        subtitulo = request.form.get('subtitulo', '($p1$)')
        p1 = request.form.get('p1', '')
        p2 = request.form.get('p2', '')
        p3 = request.form.get('p3', '')
        p4 = request.form.get('p4', '')
        p5 = request.form.get('p5', '0')
        p6 = request.form.get('p6', '')
        p7 = request.form.get('p7', '')
        serie = request.form.get('serie', '1')
        tipo_fecha = request.form.get('tipo_fecha', 'fecha')

        # Validación para rol CAJA: asegurar que p5 es el usuario autenticado (solo en reportes que usan p5)
        if session.get('user_rol') == 'CAJA' and cod == 'REP_FLEX_PAD':
            current_user = session.get('user_username', '')
            if p5 != current_user:
                flash('Acceso denegado. No puede generar reportes de otros usuarios.', 'danger')
                return redirect(url_for('reportes.rep_recibos_padron'))

        print("p3:"+p3)
        print("p4:"+p4)
        print("p5:"+p5)
        print("serie:"+serie)
        print("tipo_fecha:"+tipo_fecha)

        pdf_buffer = generar_pdf_reporte(cod, titulo, subtitulo, p1, p2, p3, p4, p5, p6, p7, serie, tipo_fecha)
        pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
        return render_template('mostrar_pdf.html', pdf_data=pdf_base64, cod=cod)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reportes_bp.route('/generar_reporte_plan_contable', methods=['POST', 'GET'])
def generar_reporte_plan_contable():
    try:
        cod = 'REP-PCGE'
        titulo = 'PLAN CONTABLE GENERAL'
        subtitulo = 'LISTADO DE CUENTA CONTABLES'
        pdf_buffer = generar_pdf_reporte(cod, titulo, subtitulo, p1='', p2='', p3='', p4='', p5='', p6='')
        pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
        return render_template('mostrar_pdf.html', pdf_data=pdf_base64, cod=cod)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


class ReciboTicket(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format=(80, 140))
        self.set_auto_page_break(auto=True, margin=10)
        self.set_margins(5, 5, 5)
        self.width = 80
        self.max_chars = 30

    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, 'E.T.Las Flores', 0, 1, 'C')
        self.set_font('Arial', '', 8)
        self.cell(0, 4, 'RUC: 20172781005', 0, 1, 'C')
        self.ln(1)
        self.line(5, self.get_y(), self.width - 5, self.get_y())
        self.ln(1)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 7)
        self.cell(0, 4, 'Gracias por su pago', 0, 1, 'C')
        self.cell(0, 4, 'Documento válido como comprobante de pago', 0, 1, 'C')
        self.cell(0, 4, f'Impreso el: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')

    def add_receipt_info(self, data):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 6, data['titulo'], 0, 1, 'C')
        self.set_font('Arial', 'B', 9)
        dserie = "RP0"
        if (data['serie'] == '1'):
            dserie = "RI0"
        if (data['serie'] == '2'):
            dserie = "BE0"
        num9 = data['numero']
        print(num9)
        formatted_str = str(num9).zfill(5)
        self.cell(0, 4, '[ '+dserie+data['serie']+'-'+formatted_str+' ]', 0, 1, 'C')
        self.ln(1)
        self.set_font('Arial', 'B', 7)
        self.cell(20, 4, 'Padron/Socio:', 0, 0)
        self.set_font('Arial', '', 7)
        nombre = data['nombre_socio']
        if len(nombre) > self.max_chars:
            nombre_line1 = nombre[:self.max_chars]
            self.cell(0, 4, nombre_line1, 0, 1)
        else:
            self.cell(0, 4, nombre, 0, 1)
        self.set_font('Arial', 'B', 7)
        self.cell(20, 4, 'Fec.Registro:', 0, 0)
        self.set_font('Arial', '', 7)
        self.cell(0, 4, data['fecha_recibo'], 0, 1)
        self.set_font('Arial', 'B', 7)
        self.cell(20, 4, 'Fec.de Giro:', 0, 0)
        self.set_font('Arial', '', 7)
        self.cell(0, 4, data['fecha_giro'], 0, 1)
        self.ln(1)
        self.line(5, self.get_y(), self.width - 5, self.get_y())
        self.ln(1)

    def add_items_table(self, items, data):
        self.set_font('Courier', 'B', 7)
        self.cell(15, 6, 'COD', 0, 0, 'L')
        self.cell(30, 6, 'DESCRIPCION', 0, 0, 'L')
        self.cell(15, 6, 'MONTO', 0, 1, 'R')
        self.line(5, self.get_y(), self.width - 5, self.get_y())
        self.ln(2)
        self.set_font('Courier', '', 6)
        total = 0
        for item in items:
            codigo = item['codigo']
            descripcion = item['descripcion']
            monto = item['monto']
            if float(monto) > 0:
                total += monto
                self.cell(15, 4, codigo, 0, 0, 'L')
                if len(descripcion) > 22:
                    desc_line1 = descripcion[:22]
                    self.cell(30, 4, desc_line1, 0, 0, 'L')
                else:
                    self.cell(30, 4, descripcion, 0, 0, 'L')
                self.cell(15, 4, f"S/. {monto:.2f}", 0, 1, 'R')
        self.ln(1)
        self.line(5, self.get_y(), self.width - 5, self.get_y())
        self.ln(1)
        self.set_font('Courier', 'B', 8)
        self.cell(40, 8, 'TOTAL PAGADO:______', 0, 0, 'R')
        self.cell(15, 8, f"S/. {total:.2f}", 0, 1, 'R')
        self.ln(6)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, '_________________________', 0, 1, 'C')
        self.cell(0, 5, 'Firma y Sello', 0, 1, 'C')
        return total


def generar_recibo(tipo_doc, serie, numero_doc, codigo_padron, nombre_socio, fecha_recibo, fecha_giro, items, nombre_archivo=None):
    pdf = ReciboTicket()
    pdf.add_page()
    igv = 'N'
    datos = {
        'serie': serie,
        'titulo': tipo_doc,
        'numero': numero_doc,
        'codigo_padron': codigo_padron,
        'nombre_socio': nombre_socio,
        'fecha_recibo': fecha_recibo,
        'fecha_giro': fecha_giro,
        'igv': igv
    }
    pdf.add_receipt_info(datos)
    total = pdf.add_items_table(items, datos)
    if nombre_archivo is None:
        nombre_archivo = f"recibos_/recibo_{serie}_{codigo_padron}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(nombre_archivo)
    print(f"Recibo generado: {nombre_archivo}")
    print(f"Total del recibo: S/. {total:.2f}")
    return nombre_archivo


@reportes_bp.route('/prestamos/pdf/<int:prestamo_id>')
def generar_pdf_prestamo(prestamo_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
            SELECT p.*, pr.placa, pr.monto0, s.nombre, s.email, s.fono telefono, s.dni,
                   tp.descripcion as tipo_nombre, tp.monto1 tasa_interes,
                   s.nombre as socio_nombre, p.id padron
            FROM a_prestamos p
            JOIN a_padrones pr ON p.padron = pr.id
            JOIN a_socios s ON pr.socio = s.id
            JOIN a_tipos tp ON tp.tipo='DEUDA' AND p.tipo_prestamo = tp.codigo
            WHERE p.id = %s
        """, (prestamo_id,))
    prestamo = cursor.fetchone()
    conn.close()
    if not prestamo:
        return "Préstamo no encontrado", 404
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=72, leftMargin=72,
                           topMargin=32, bottomMargin=18)
    Story = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, fontSize=14, spaceAfter=10))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, fontSize=10))
    styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT, fontSize=12, spaceAfter=10))
    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")
    Story.append(Paragraph(f"<b>E.T. LAS FLORES</b>", styles['Title']))
    Story.append(Spacer(1, 0.1*inch))
    Story.append(Paragraph(f"<i>Fecha de emisión: {fecha_actual}</i>", styles['Right']))
    Story.append(Spacer(1, 0.1*inch))
    Story.append(Paragraph(f"<b>CARTA DE SOLICITUD DE PRÉSTAMO #{prestamo['id']}.</b>", styles['Center']))
    Story.append(Spacer(1, 0.3*inch))
    Story.append(Paragraph(f"<b>Señores</b>", styles['Left']))
    Story.append(Paragraph("Comité de Préstamos", styles['Left']))
    Story.append(Paragraph("Presente.", styles['Left']))
    Story.append(Spacer(1, 0.2*inch))
    Story.append(Paragraph(f"Yo, <b>{prestamo['socio_nombre']}</b>, con DNI _{prestamo['dni']}_, ", styles['Left']))
    Story.append(Paragraph(f"por medio de la presente solicito a ustedes un préstamo por la suma de ", styles['Left']))
    Story.append(Paragraph(f"<b>S/. {prestamo['monto_solicitado']:,.2f}</b>, el cual será destinado para <b>{prestamo['descripcion'] or 'No especificado'}</b>.", styles['Left']))
    Story.append(Spacer(1, 0.2*inch))

    data = [
        ['Detalle de la Solicitud', ''],
        ['Tipo de Préstamo:', prestamo['tipo_nombre']],
        ['Número de Padrón:', prestamo['padron']],
        ['Placa de Padrón:', prestamo['placa']],
        ['Monto Solicitado:', f"S/. {prestamo['monto_solicitado']:,.2f}"],
        ['Tasa de Interés:', f"{prestamo['tasa_interes']}%"],
        ['Cuota Diaria:', f"S/. {prestamo['cuota']:,.2f}"],
        ['Garantía:', 'Con garantía de aportes' if prestamo['garantia_aporte'] else 'Sin garantía específica'],
        ['Fecha de solicitud:', prestamo['fecha_solicitud'].strftime('%d/%m/%Y')],
        ['Estado de solicitud:', prestamo['estado'].upper()],
    ]

    tabla = Table(data, colWidths=[2*inch, 3*inch])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    Story.append(tabla)
    Story.append(Spacer(1, 0.3*inch))

    if prestamo['garantia_aporte']:
        Story.append(Paragraph("<b>DECLARACIÓN DE GARANTÍA</b>", styles['Left']))
        Story.append(Paragraph("Declaro que este préstamo está garantizado con mis aportes, ", styles['Left']))
        Story.append(Spacer(1, 0.2*inch))

    Story.append(Paragraph("<b>COMPROMISO DE PAGO</b>", styles['Left']))
    Story.append(Paragraph("Me comprometo a cancelar el monto adeudado más los intereses ", styles['Left']))
    Story.append(Paragraph("generados en los plazos y condiciones establecidos por la institución.", styles['Left']))
    Story.append(Spacer(1, 0.5*inch))

    data_firmas = [
        ['_________________________', '_________________________'],
        [prestamo['socio_nombre'], 'Comité de Préstamos'],
        ['Solicitante', 'Autorizado por']
    ]

    tabla_firmas = Table(data_firmas, colWidths=[3*inch, 3*inch])
    tabla_firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, 1), 5),
    ]))
    Story.append(tabla_firmas)

    doc.build(Story)

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=solicitud_prestamo_{prestamo_id}.pdf'

    return response


@reportes_bp.route('/retiros/pdf/<int:retiro_id>')
def generar_pdf_retiro(retiro_id):
    conn = get_db_connection()
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("""
            SELECT r.*, pr.placa, r.saldo_final_dia monto_aportado,
                   s.nombre, s.email, s.fono telefono,
                   s.nombre as nombre_socio
            FROM a_retiros r
            JOIN a_padrones pr ON r.padron = pr.id
            JOIN a_socios s ON pr.socio = s.id
            WHERE r.id = %s
        """, (retiro_id,))
        retiro = cursor.fetchone()
    conn.close()
    if not retiro:
        return "Retiro no encontrado", 404
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    Story = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, fontSize=14, spaceAfter=20))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, fontSize=10))
    styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT, fontSize=12, spaceAfter=12))

    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")
    Story.append(Paragraph(f"<b>E.T. LAS FLORES</b>", styles['Title']))
    Story.append(Spacer(1, 0.2*inch))
    Story.append(Paragraph(f"<i>Fecha de emisión: {fecha_actual}</i>", styles['Right']))
    Story.append(Spacer(1, 0.3*inch))

    Story.append(Paragraph(f"<b>CARTA DE SOLICITUD DE RETIRO DE APORTES #00{retiro['id']}</b>", styles['Center']))
    Story.append(Spacer(1, 0.3*inch))

    Story.append(Paragraph(f"<b>Señores</b>", styles['Left']))
    Story.append(Paragraph("Dpto. de Administracion.", styles['Left']))
    Story.append(Paragraph("Presente.-", styles['Left']))
    Story.append(Spacer(1, 0.2*inch))

    Story.append(Paragraph(f"Yo, <b>{retiro['nombre_socio']}</b>, por medio de la presente solicito ", styles['Left']))
    Story.append(Paragraph(f"el retiro de la suma de <b>S/ {retiro['monto_retirado']:,.2f}</b> de mis aportes del tipo : <b>{retiro['tipo_aporte']}</b>,", styles['Left']))
    Story.append(Paragraph(f"correspondientes al padrón placa número <b>{retiro['placa']}</b>.", styles['Left']))
    Story.append(Spacer(1, 0.2*inch))

    data = [
        ['Detalle del Retiro', ''],
        ['Número de Padrón:', retiro['padron']],
        ['Monto a Retirar:', f"S/ {retiro['monto_retirado']:,.2f}"],
        ['Saldo cuando se solicito:', f"S/ {retiro['saldo_final_dia']:,.2f}"],
        ['Tipo de Aporte:', retiro['tipo_aporte']],
        ['Motivo:', retiro['descripcion'] or 'No especificado'],
        ['Fecha de Retiro:', retiro['fecha_retiro'].strftime('%d/%m/%Y')],
    ]

    tabla = Table(data, colWidths=[2*inch, 3*inch])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.aliceblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    Story.append(tabla)
    Story.append(Spacer(1, 0.3*inch))

    Story.append(Paragraph("<b>AUTORIZACIÓN</b>", styles['Left']))
    Story.append(Paragraph("Autorizo al sistema a realizar el débito correspondiente de mis aportes ", styles['Left']))
    Story.append(Paragraph("por el monto indicado en esta solicitud.", styles['Left']))
    Story.append(Spacer(1, 0.5*inch))

    data_firmas = [
        ['_________________________', '_________________________'],
        [retiro['nombre_socio'], 'Departamento de Administracion'],
        ['Solicitante', 'Autorizado por']
    ]

    tabla_firmas = Table(data_firmas, colWidths=[3*inch, 3*inch])
    tabla_firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, 1), 5),
    ]))
    Story.append(tabla_firmas)

    doc.build(Story)

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=solicitud_retiro_{retiro_id}.pdf'

    return response
