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
@admin_required
def reportes():
    return render_template('reportes.html')


@reportes_bp.route('/rep_saldos_comb')
@login_required
def rep_saldos_comb():
    """Reporte de saldos de deuda de combustible por padrón."""
    if session.get('user_rol') not in ('ADMIN', 'GRIFERO', 'CAJA'):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    saldos = []
    total = 0.0
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.REP_SALDOS_COMB)
        saldos = cursor.fetchall()
        cursor.close()
        connection.close()
        total = sum(float(s['saldo']) for s in saldos)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return render_template('rep_saldos_comb.html', saldos=saldos, total=total,
                           hoy=datetime.datetime.now().strftime('%d-%m-%Y %H:%M'))


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


def generar_pdf_cabecera(pdf, cod, titulo, subtitulo, sum4, p1, p2, p3, p4, p5, p6):
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
    subtitulo = subtitulo.replace("$p5$", p5)
    subtitulo = subtitulo.replace("$p6$", p6)
    pdf.cell(0, 4, f"::{subtitulo}::", 0, 1, 'C')
    pdf.ln()
    pdf.set_font("Arial", 'B', 9)
    if (cod=='REP1APORTES'):
        pdf.cell(18, 5, "Nro.Rec", 1)
        pdf.cell(18, 5, "Registro", 1)
        pdf.cell(18, 5, "Girado..", 1)
        pdf.cell(18, 5, "TpRec", 1)
        pdf.cell(60, 5, "Padron Socio", 1)
        pdf.cell(20, 5, "Aportado", 1)
        pdf.cell(15, 5, "Act?", 1)
        pdf.cell(18, 5, "Usuario", 1)
        pdf.cell(15, 5, "IdCtrl", 1)
    elif(cod=='REP2APORTES'):
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


def generar_pdf_reporte(cod, titulo, subtitulo, p1, p2, p3, p4, p5, p6):
    buffer = BytesIO()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_left_margin(3.5)
    print('Comenzando Reporte.. CABECERA')
    generar_pdf_cabecera(pdf, cod, titulo, subtitulo, 0, p1, p2, p3, p4, p5, p6)
    print('Procesando Reporte..')
    query = sqlconstants.REP1APORTES
    if (cod=="REP2APORTES"):
        query = sqlconstants.REP2APORTES
    if (cod=="REP-PCGE"):
        query = sqlconstants.REP0PCGE
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        query = query.replace("$p1$", p1)
        query = query.replace("$p2$", p2)
        query = query.replace("$p3$", p3)
        query = query.replace("$p4$", p4)
        query = query.replace("$p5$", p5)
        query = query.replace("$p6$", p6)
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
        if cod=='REP1APORTES':
            pdf.cell(18, 5, dato["d1"], 1)
            pdf.cell(18, 5, dato["d2"], 1)
            pdf.cell(18, 5, dato["d3"], 1)
            pdf.cell(18, 5, dato["d4"], 1)
            d6 = dato["d6"]
            pdf.cell(60, 5, d6[:33], 1)
            pdf.cell(20, 5, dato["d7"], 1, 0, 'R')
            pdf.cell(15, 5, dato["d8"], 1)
            pdf.cell(18, 5, dato["d9"], 1)
            pdf.cell(15, 5, dato["d10"], 1)
            to1 += float(dato["d7"])
        elif(cod=='REP2APORTES'):
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
            generar_pdf_cabecera(pdf, cod, titulo, subtitulo, 1, p1, p2, p3, p4, p5, p6)
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
        p5 = request.form.get('p5', '')
        p6 = request.form.get('p6', '')
        print("p3:"+p3)
        print("p4:"+p4)
        pdf_buffer = generar_pdf_reporte(cod, titulo, subtitulo, p1, p2, p3, p4, p5, p6)
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
