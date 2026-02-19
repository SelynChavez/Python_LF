from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, make_response
import mysql.connector
from mysql.connector import Error
import pymysql
import hashlib
import os
from functools import wraps
from config import Config
import sqlconstants

from io import BytesIO
import tempfile
from fpdf import FPDF
import base64
import datetime
from decimal import Decimal
from datetime import time
## from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

app = Flask(__name__)
app.config.from_object(Config)

# Decorador para requerir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorador para requerir rol admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_rol' not in session or session['user_rol'] != 'ADMIN':
            flash('Acceso denegado. Se requieren privilegios de administrador.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Conexión a la base de datos
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DATABASE'],
            port=app.config['MYSQL_PORT']
        )
        return connection
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

# Función para hashear contraseñas (simplificada para desarrollo)
def hash_password(password):
    # En producción usaría bcrypt o similar
    return password.encode()

def get_nombre_padron(pad):
    nombre_default = ''
    connection1 = get_db_connection()
    if connection1:
        cursor = connection1.cursor(dictionary=True)
        cursor.execute(sqlconstants.GET_NOMBRE_PADRON, (pad,))
        reg0 = cursor.fetchone()
        if reg0:
            nombre_default = reg0['n0']
        cursor.close()
        connection1.close()
    return nombre_default

# Rutas principales
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')        
        if not username or not password:
            flash('Por favor, complete todos los campos.', 'danger')
            return render_template('login.html')
        hashed_password = hash_password(password)
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM applicationuser WHERE username = %s AND password = %s AND status = 'ACTIVE'"
            cursor.execute(query, (username, hashed_password))
            user = cursor.fetchone()
            cursor.close()
            connection.close()
            if user:
                session['user_id'] = user['id']
                session['user_name'] = user['fullname']
                session['user_username'] = user['username']
                session['user_rol'] = user['roles']
                connection = get_db_connection()
                if connection:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (user['id'], 'login', 'Inicio de sesión exitoso'))
                    connection.commit()
                    cursor.close()
                    connection.close()
                flash(f'Bienvenido, {user["fullname"]}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Usuario o contraseña incorrectos.', 'danger')
        else:
            flash('Error de conexión a la base de datos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        # Registrar logout en logs
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'logout', 'Cierre de sesión'))
            connection.commit()
            cursor.close()
            connection.close()
    session.clear()
    flash('Ha cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/administracion')
@login_required
@admin_required
def administracion():
    return render_template('administracion.html')

@app.route('/configuracion')
@login_required
@admin_required
def configuracion():
    return render_template('configuracion.html')

## ========================== CONSULTAS ====================================
# lista aportes HLF
@app.route('/aportes', methods=['GET', 'POST'])
@login_required
@admin_required
def aportes():
    total = 0
    line0 = 0
    recs = []
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Ini
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Fin
        p3 = request.form.get('p3')  # Padron
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = sqlconstants.REP1APORTES
            query = query.replace("$p1$", str(p1))
            query = query.replace("$p2$", str(p2))
            query = query.replace("$p3$", str(p3))
            cursor.execute(query)
            recibos = cursor.fetchall()
            cursor.close()
            connection.close() 
            for reg in recibos:
                line0 += 1
                reg['d0'] = str(line0)
                total += float(reg['d7'])
            return render_template('aportes.html', recibos=recibos, total=total, p1=p1, p2=p2, p3=p3)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard'))
    else:
        px = datetime.datetime.now().strftime('%Y-%m-%d')  # Fecha Ini
        flash('Listo para consultar.', 'success')
        return render_template('aportes.html', p1=px, p2=px, p3=0, recibos=recs, total=total)

# ------------------------------------------------------------------------------------
# RECIBOS (para demostrar funcionalidad reactiva) ## SERIE 001
@app.route('/recibos/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_recibo():
    if request.method == 'POST':
        act = request.form.get('act')
        fec = request.form.get('fec')
        pad = request.form.get('pad')
        com = request.form.get('com')
        lid = request.form.get('lid')
        nom = ""
        if not all([fec, pad]):
            flash('Por favor, complete todos los campos con (*).', 'danger')
            return render_template('crear_recibo.html')
        connection = get_db_connection()
        if act == '-':
            if connection:
                try:
                    cursor = connection.cursor()
                    query = sqlconstants.INSERT_RECIBO_1
                    cursor.execute(query, (fec, pad, com, act, session['user_username'])) 
                    lid = cursor.lastrowid
                    connection.commit()
                    act = '*'
                    # --- comenzar con detalle
                    cursor = connection.cursor(dictionary=True)
                    consulta = sqlconstants.DETALLE_SERIE_1
                    consulta = consulta.replace("$pad$", pad)
                    cursor.execute(consulta)
                    items = cursor.fetchall()
                    cursor.close()
                    nom = get_nombre_padron(pad)
                    connection.close()
                    flash('Continuar con detalles.', 'success')
                    return render_template('crear_recibo.html', 
                    act=act, fec=fec, pad=pad, com=com, nom=nom, but='Registrar', items=items, lid=lid)
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
        if act == '*':
            if connection:
                try:
                    lin = 0
                    total = 0
                    nom = request.form.get('nom')
                    cursor = connection.cursor(dictionary=True)
                    consulta = sqlconstants.DETALLE_SERIE_1
                    consulta = consulta.replace("$pad$", pad)
                    cursor.execute(consulta)
                    items = cursor.fetchall()
                    for i0 in items:
                        lin += 1
                        mnt = request.form.get(i0['codigo'])
                        mnt0 = float(mnt)
                        if mnt and mnt0 > 0:
                            i0['monto'] = Decimal(mnt0)
                            query = sqlconstants.INSERT_DETREC_1
                            query = query.replace("$apo$", i0['codigo'])
                            query = query.replace("$rec$", lid)
                            query = query.replace("$mnt$", mnt)
                            query = query.replace("$pre$", str(i0['prestamo']))
                            query = query.replace("$tip$", i0['tipodeuda'])
                            query = query.replace("$usr$", session['user_username'])
                            cursor = connection.cursor()
                            cursor.execute(query)
                    query9 = sqlconstants.UPDATE_RECIBO_1
                    query9 = query9.replace("$recibo$",lid)
                    cursor = connection.cursor()
                    cursor.execute(query9)
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Recibo registrado.', 'success')

                    # Datos de ejemplo
                    serie = '1'
                    codigo_padron = pad
                    nombre_socio = nom
                    fecha_recibo = datetime.datetime.now().strftime('%d-%m-%Y')
                    date_format = '%Y-%m-%d'
                    date_obj = datetime.datetime.strptime(fec, date_format)
                    fecha_giro = date_obj.strftime('%d-%m-%Y')
                    # Generar recibo
                    archivo = generar_recibo('RECIBO DE PAGO', serie, lid, codigo_padron, nombre_socio, fecha_recibo, fecha_giro, items)
                    # Intentar abrir el archivo automáticamente (dependiendo del sistema operativo)
                    try:
                        if os.name == 'nt':  # Windows
                            os.startfile(archivo)
                        elif os.name == 'posix':  # Linux o macOS
                            os.system(f'open "{archivo}"')
                    except:
                        print(f"Recibo guardado en: {os.path.abspath(archivo)}")

                    return render_template('crear_recibo.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar')
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
       
    return render_template('crear_recibo.html', act='-',but='Continuar')

@app.route('/imprimir_recibo/<int:l_id>', methods=['GET', 'POST'])
@login_required
def imprimir_recibo(l_id):
    lid = str(l_id)
    if request.method == 'GET':
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            queryHead = sqlconstants.SELECT_RECIBO_1
            queryHead = queryHead.replace("$pX$", lid)
            cursor.execute(queryHead)
            recibo = cursor.fetchone()
            pad = recibo['padron']
            nom = recibo['nombre']
            fec = recibo['fecha']
            date_format = '%Y-%m-%d'
            date_obj = datetime.datetime.strptime(recibo['fec'], date_format)
            fec = date_obj.strftime('%d-%m-%Y')
            date_obj = datetime.datetime.strptime(recibo['gir'], date_format)
            gir = date_obj.strftime('%d-%m-%Y')
            consulta = sqlconstants.SELECT_DETALLE1
            consulta = consulta.replace("$pX$", lid)
            cursor.execute(consulta)
            items = cursor.fetchall()
            archivo = generar_recibo('RECIBO DE PAGO', '1', lid, pad, nom, fec, gir, items)
            try:     ### Intentar abrir el archivo automáticamente (dependiendo del sistema operativo)
                if os.name == 'nt':  # Windows
                    os.startfile(archivo)
                elif os.name == 'posix':  # Linux o macOS
                    os.system(f'open "{archivo}"')
            except:
                print(f"Recibo guardado en: {os.path.abspath(archivo)}")

# ------------------------------------------------------------------------------------
# TIPOS DEUDAS (para demostrar funcionalidad reactiva)
@app.route('/tipos_deudas')
@login_required
@admin_required
def listar_tipos_deudas():
    tipo = 'DEUDA'
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_TIPOS, (tipo,) )
        tipos = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('tipos_deudas.html', tipos=tipos, tipo=tipo)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return redirect(url_for('configuracion'))

@app.route('/tiposdeudas/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_tipo_deuda():
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        codigo = request.form.get('codigo')
        descripcion = request.form.get('descripcion')
        if not all([codigo, descripcion]):
            flash('Por favor, complete todos los campos.', 'danger')
            return render_template('crear_tipo_deuda.html')
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.INSERT_TIPO, (tipo, codigo, descripcion, session['user_username']))
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_tipo_deuda', f'LOG::Creó el Tipo: {codigo}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Tipo Deuda creado exitosamente.', 'success')
                return redirect(url_for('listar_tipos_deudas'))
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
    return render_template('crear_tipo_deuda.html')

@app.route('/tiposdeudas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_tipo_deuda(id):
    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('listar_tipos_deudas'))    
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        descripcion = request.form.get('descripcion')
        try:
            cursor = connection.cursor()
            cursor.execute(sqlconstants.UPDATE_TIPO, (codigo, descripcion, '0','0','','','','','', id))
            connection.commit()
            cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_tipo_deuda', f'LOG::Editó el tipo: {codigo}'))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Codigo actualizado exitosamente.', 'success')
            return redirect(url_for('listar_tipos_deudas'))
        except Error as e:
            if 'Duplicate entry' in str(e):
                flash('Codigo ya existe.', 'danger')
            else:
                flash(f'Error al actualizar tipo: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
            return redirect(url_for('editar_tipo_deuda', id=id))    
    # GET: Obtener datos del socio
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.SELECT_TIPO, (id,))
    tipo = cursor.fetchone()
    cursor.close()
    connection.close()
    if not tipo:
        flash('Tipo/Codigo no encontrado.', 'danger')
        return redirect(url_for('listar_tipos_deudas'))
    return render_template('editar_tipo_deuda.html', id=id, tipo=tipo)

@app.route('/tipos/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_tipo(id):
    url = 'listar_tipos_aportes'
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sqlconstants.SEL_NM_TIPO, (id,))
            tipo = cursor.fetchone()
            tp = tipo["tipo"]
            if (tp == "DEUDA"):
                url = 'listar_tipos_deudas'
            print(tp)
            cursor.execute(sqlconstants.DELETE_TIPO, (id,))
            connection.commit()
            # Logs
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

# ------------------------------------------------------------------------------------
# TIPOS APORTES (para demostrar funcionalidad reactiva)
@app.route('/tipos_aportes')
@login_required
@admin_required
def listar_tipos_aportes():
    tipo = 'APORTE'
    m1 = "Aporte Fijo"
    a1 = "Serie"
    a4 = "Retiros?"
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.LISTA_TIPOS, (tipo,) )
        tipos = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('tipos_aportes.html', tipos=tipos, tipo=tipo, m1=m1, a1= a1, a4=a4)
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return redirect(url_for('configuracion'))

@app.route('/tipos/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_tipo_aporte():
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        codigo = request.form.get('codigo')
        descripcion = request.form.get('descripcion')
        if not all([codigo, descripcion]):
            flash('Por favor, complete todos los campos.', 'danger')
            return render_template('crear_tipo_aporte.html')
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.INSERT_TIPO, (tipo, codigo, descripcion, session['user_username']))
                connection.commit()
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_tipo_aporte', f'LOG::Creó el Tipo: {codigo}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Tipo Aporte creado exitosamente.', 'success')
                return redirect(url_for('listar_tipos_aportes'))
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
    return render_template('crear_tipo_aporte.html')

@app.route('/tipos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_tipo_aporte(id):
    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('listar_tipos_aportes'))    
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        descripcion = request.form.get('descripcion')
        monto1 = request.form.get('monto1')
        atributo1 = request.form.get('atributo1')
        atributo2 = request.form.get('atributo2')
        atributo3 = request.form.get('atributo3')
        atributo4 = request.form.get('atributo4')
        try:
            cursor = connection.cursor()
            cursor.execute(sqlconstants.UPDATE_TIPO, (codigo, descripcion, monto1,'0',atributo1,atributo2,atributo3,atributo4,'', id))
            connection.commit()
            cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_tipo_aporte', f'LOG::Editó el tipo: {codigo}'))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Codigo actualizado exitosamente.', 'success')
            return redirect(url_for('listar_tipos_aportes'))
        except Error as e:
            if 'Duplicate entry' in str(e):
                flash('Codigo ya existe.', 'danger')
            else:
                flash(f'Error al actualizar tipo: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
            return redirect(url_for('editar_tipo_aporte', id=id))    
    # GET: Obtener datos del socio
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.SELECT_TIPO, (id,))
    tipo = cursor.fetchone()
    cursor.close()
    connection.close()
    if not tipo:
        flash('Tipo/Codigo no encontrado.', 'danger')
        return redirect(url_for('listar_tipos_aportes'))
    return render_template('editar_tipo_aporte.html', id=id, tipo=tipo)

# ------------------------------------------------------------------------------------
# PADRONES (para demostrar funcionalidad reactiva)
@app.route('/padrones')
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
        return redirect(url_for('configuracion'))

@app.route('/padrones/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_padron():
    if request.method == 'POST':
        placa = request.form.get('placa')
        socio = request.form.get('socio')
        active = request.form.get('active')
        monto1 = request.form.get('monto1')
        monto2 = request.form.get('monto2')
        monto3 = request.form.get('monto3')
        monto4 = request.form.get('monto4')
        monto5 = request.form.get('monto5')
        monto6 = request.form.get('monto6')
        if not all([placa, socio]):
            flash('Por favor, complete todos los campos.', 'danger')
            return render_template('crear_padron.html')
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.INSERT_PADRON, (placa, socio, active, monto1, monto2, monto3, monto4, session['user_username']))
                connection.commit()                
                # Log
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_padron', f'Creó el padron: {placa}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Padron creado exitosamente.', 'success')
                return redirect(url_for('listar_padrones'))
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
    return render_template('crear_padron.html')

@app.route('/padrones/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_padron(id):
    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('listar_padrones'))    
    if request.method == 'POST':
        placa = request.form.get('placa')
        socio = request.form.get('socio')
        active = request.form.get('active')
        monto1 = request.form.get('monto1')
        monto2 = request.form.get('monto2')
        monto3 = request.form.get('monto3')
        monto4 = request.form.get('monto4')
        monto5 = request.form.get('monto5')
        monto6 = request.form.get('monto6')
        try:
            cursor = connection.cursor()
            cursor.execute(sqlconstants.UPDATE_PADRON, (placa, socio, active, monto1, monto2, monto3, monto4, id))
            connection.commit()
            # Logs
            cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_placa', f'Editó el padron: {placa}'))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Padron actualizado exitosamente.', 'success')
            return redirect(url_for('listar_padrones'))
        except Error as e:
            if 'Duplicate entry' in str(e):
                flash('La placa/socio ya existe.', 'danger')
            else:
                flash(f'Error al actualizar padron: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
            return redirect(url_for('editar_padron', id=id))    
    # GET: Obtener datos del socio
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.SELECT_PADRON, (id,))
    padron = cursor.fetchone()
    cursor.close()
    connection.close()
    if not padron:
        flash('Padron no encontrado.', 'danger')
        return redirect(url_for('listar_padrones'))
    return render_template('editar_padron.html', padron=padron)

@app.route('/padrones/eliminar/<int:id>')
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
            # Logs
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
    return redirect(url_for('listar_padrones'))
# ------------------------------------------------------------------------------------
# SOCIOS (para demostrar funcionalidad reactiva)
@app.route('/socios')
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
        return redirect(url_for('configuracion'))

@app.route('/socios/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_socio():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        dni = request.form.get('dni')
        fono = request.form.get('fono')
        tipo = request.form.get('tipo')
        email = request.form.get('email')
        comentarios = request.form.get('comentarios')
        if not all([dni, fono, nombre, tipo, email, comentarios]):
            flash('Por favor, complete todos los campos.', 'danger')
            return render_template('crear_socio.html')
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.INSERT_SOCIO, (nombre, fono, dni, comentarios, tipo, email, session['user_username']))
                connection.commit()                
                # Log
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_socio', f'Creó el socio: {nombre}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Socio creado exitosamente.', 'success')
                return redirect(url_for('listar_socios'))
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
    return render_template('crear_socio.html')

@app.route('/socios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_socio(id):
    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('listar_socios'))    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        fono = request.form.get('fono')
        dni = request.form.get('dni')
        comentarios = request.form.get('comentarios')
        tipo = request.form.get('tipo')
        email = request.form.get('email')
        active = request.form.get('active')
        try:
            cursor = connection.cursor()
            cursor.execute(sqlconstants.UPDATE_SOCIO, (nombre, fono, dni, comentarios, tipo, active, email, id))            
            connection.commit()
            # Logs
            cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_socio', f'Editó el socio: {nombre}'))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Socio actualizado exitosamente.', 'success')
            return redirect(url_for('listar_socios'))
        except Error as e:
            if 'Duplicate entry' in str(e):
                flash('El nombre/dni de socio ya existe.', 'danger')
            else:
                flash(f'Error al actualizar socio: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
            return redirect(url_for('editar_socio', id=id))    
    # GET: Obtener datos del socio
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.SELECT_SOCIO, (id,))
    socio = cursor.fetchone()
    cursor.close()
    connection.close()
    if not socio:
        flash('Socio no encontrado.', 'danger')
        return redirect(url_for('listar_socios'))
    return render_template('editar_socio.html', socio=socio)

@app.route('/socios/eliminar/<int:id>')
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
            # Logs
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
    return redirect(url_for('listar_socios'))

# ------------------------------------------------------------------------------------------
# API para consulta de usuarios (para demostrar funcionalidad reactiva)
# CRUD de USUARIOS
@app.route('/usuarios')
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
        return redirect(url_for('dashboard'))

@app.route('/usuarios/crear', methods=['GET', 'POST'])
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
                # Registrar creación en logs
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'crear_usuario', f'Creó el usuario: {username}'))
                connection.commit()
                cursor.close()
                connection.close()
                flash('Usuario creado exitosamente.', 'success')
                return redirect(url_for('listar_usuarios'))
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

@app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(id):
    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('listar_usuarios'))    
    if request.method == 'POST':
        username = request.form.get('username')
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        rol = request.form.get('rol')
        activo = request.form.get('activo')
        cambiar_password = request.form.get('cambiar_password')
        nueva_password = request.form.get('nueva_password')
        ## activo_bool = True if activo == '1' else False
        try:
            cursor = connection.cursor()
            if cambiar_password and nueva_password:
                hashed_password = hash_password(nueva_password)
                cursor.execute(sqlconstants.UPDAT1_USUARIO, (username, nombre, email, rol, activo, hashed_password, id))
            else:
                cursor.execute(sqlconstants.UPDAT2_USUARIO, (username, nombre, email, rol, activo, id))
            connection.commit()
            # Registrar edición en logs
            cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'editar_usuario', f'Editó el usuario: {username}'))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Usuario actualizado exitosamente.', 'success')
            return redirect(url_for('listar_usuarios'))
        except Error as e:
            if 'Duplicate entry' in str(e):
                flash('El nombre de usuario o email ya existe.', 'danger')
            else:
                flash(f'Error al actualizar usuario: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
            return redirect(url_for('editar_usuario', id=id))    
    # GET: Obtener datos del usuario
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.SELECT_USUARIO, (id,))
    usuario = cursor.fetchone()
    cursor.close()
    connection.close()
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('listar_usuarios'))
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/usuarios/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_usuario(id):
    # No permitir eliminarse a sí mismo
    if id == session['user_id']:
        flash('No puede eliminar su propio usuario.', 'danger')
        return redirect(url_for('listar_usuarios'))
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Obtener info del usuario antes de eliminar para el log
            cursor.execute(sqlconstants.SEL_NM_USUARIO, (id,))
            usuario = cursor.fetchone()
            # Eliminar usuario
            cursor.execute(sqlconstants.DELETE_USUARIO, (id,))
            connection.commit()
            # Registrar eliminación en logs
            if usuario:
                cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'eliminar_usuario', f'Eliminó el usuario: {usuario["username"]}'))
                connection.commit()
            cursor.close()
            connection.close()
            flash('Usuario eliminado exitosamente.', 'success')
        except Error as e:
            flash(f'Error al eliminar usuario: {str(e)}', 'danger')
            connection.rollback()
            cursor.close()
            connection.close()
    else:
        flash('Error de conexión a la base de datos.', 'danger')
    return redirect(url_for('listar_usuarios'))

@app.route('/api/usuarios')
@login_required
def api_usuarios():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        # Parámetros de búsqueda/filtro
        buscar = request.args.get('buscar', '')
        query = sqlconstants.QRY1USUARIOS
        if not buscar:
            buscar = ""
        cursor.execute(query, (f'%{buscar}%', f'%{buscar}%', f'%{buscar}%'))      
        usuarios = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(usuarios)
    else:
        return jsonify({'error': 'Error de conexión'}), 500

## REPORTES ----------------------------------------------------------------------------------------------------------
@app.route('/reportes')
@login_required
@admin_required
def reportes():
    return render_template('reportes.html')

@app.route('/rep1recibos')
def rep1recibos():
    p1 = datetime.datetime.now().strftime('%Y-%m-%d')
    p2 = datetime.datetime.now().strftime('%Y-%m-%d')
    p3 = "0"
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Ini
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Fin
        p3 = request.form.get('p3')  # Padron
    return render_template('rep1recibos.html', p1=p1, p2=p2, p3=p3)

@app.route('/rep2recibos')
def rep2recibos():
    tipos = []
    query = sqlconstants.DROPLIST_APORTES
    # Filtrar datos
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        tipos = cursor.fetchall()
        cursor.close()
        connection.close()
    else:
        return jsonify({'error': 'Error de conexión'}), 500
    return render_template('rep2recibos.html', tipos=tipos)

## REPORT PDF CREATION ----------------------------------------------------------------------------------------------------------
def generar_pdf_cabecera(pdf, cod, titulo, subtitulo, sum4, p1, p2, p3, p4, p5, p6):    
    pdf.set_font("Arial", 'B', 10)
    hora1 = str(datetime.datetime.now())[0:19] + "  -  Pag. # " + str(pdf.page_no()+sum4)
    usr = session['user_username']
    spc = " " * 70
    pdf.cell(0, 8, f"E.T.Las Flores :: [{cod}] - [{usr}] - {spc} {hora1}", 0, 1, 'R')
    # Título
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 4, f"{titulo}", 0, 1, 'C')
    pdf.ln()
    # Parametros
    pdf.set_font("Arial", 'B', 10)
    subtitulo = subtitulo.replace("$p1$", p1)
    subtitulo = subtitulo.replace("$p2$", p2)
    subtitulo = subtitulo.replace("$p3$", p3)
    subtitulo = subtitulo.replace("$p4$", p4)
    subtitulo = subtitulo.replace("$p5$", p5)
    subtitulo = subtitulo.replace("$p6$", p6)
    pdf.cell(0, 4, f"::{subtitulo}::", 0, 1, 'C')
    pdf.ln()    
    # Encabezados de tabla
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
    else:
        pdf.cell(15, 5, "ID", 1)
    pdf.ln()

def generar_pdf_reporte(cod, titulo, subtitulo, p1, p2, p3, p4, p5, p6):
    buffer = BytesIO()
    # Usando FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_left_margin(3.5)   
    print('Comenzando Reporte.. CABECERA')
    generar_pdf_cabecera(pdf, cod, titulo, subtitulo, 0, p1, p2, p3, p4, p5, p6)    
    print('Procesando Reporte..')
    # Determinar SQL query
    query = sqlconstants.REP1APORTES
    if (cod=="REP2APORTES"):
        query = sqlconstants.REP2APORTES
    # Filtrar datos
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
    # Datos de la tabla
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
            pdf.cell(60, 5, dato["d6"], 1)
            pdf.cell(20, 5, dato["d7"], 1, 0, 'R')
            pdf.cell(15, 5, dato["d8"], 1)
            pdf.cell(18, 5, dato["d9"], 1)
            pdf.cell(15, 5, dato["d10"], 1)
            to1 += float(dato["d7"])  
        elif(cod=='REP2APORTES'):
            pdf.cell(18, 5, dato["d1"], 1)
            pdf.cell(18, 5, dato["d2"], 1)
            pdf.cell(18, 5, dato["d3"], 1)
            pdf.cell(60, 5, dato["d4"], 1)
            pdf.cell(18, 5, dato["d5"], 1)
            pdf.cell(15, 5, dato["d6"], 1)
            pdf.cell(20, 5, dato["d7"], 1, 0, 'R')
            to1 += float(dato["d7"])
        else:
            pdf.cell(15, 5, str(lin), 1)
        pdf.ln()
        if lin==47:
            pdf.ln(6)
            lin = 0
            generar_pdf_cabecera(pdf, cod, titulo, subtitulo, 1, p1, p2, p3, p4, p5, p6)
            pdf.set_font("Arial", '', 8)          
    # Pie de página
    print('Finalizando Reporte..')
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"#REGS:...{rgt} :: TOTAL APORTADO:... {to1}", 0, 1)
    pdf_output = pdf.output(dest='S').encode('latin-1')
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer

@app.route('/generar_reporte', methods=['POST'])
def generar_reporte():
    try:
        # Obtener parámetros del formulario
        cod = request.form.get('cod', 'Rep1')
        titulo = request.form.get('titulo', 'Reporte')
        subtitulo = request.form.get('subtitulo', '($p1$)')
        p1 = request.form.get('p1', '') ##datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', '') ##datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3', '')
        p4 = request.form.get('p4', '')
        p5 = request.form.get('p5', '')
        p6 = request.form.get('p6', '')
        print("p3:"+p3)
        print("p4:"+p4)        
        # Generar PDF
        pdf_buffer = generar_pdf_reporte(cod, titulo, subtitulo, p1, p2, p3, p4, p5, p6)
        # Convertir a base64 para mostrar en HTML
        pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
        return render_template('mostrar_pdf.html', pdf_data=pdf_base64, cod=cod)    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
## ---- END PDF ----------------------------------------------------------------------------------------------------------

class ReciboTicket(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format=(80, 200))
        self.set_auto_page_break(auto=True, margin=10)
        self.set_margins(5, 5, 5)
        self.width = 80
        self.max_chars = 30
    
    def header(self):    # Encabezado del recibo
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, 'E.T.Las Flores', 0, 1, 'C')
        self.set_font('Arial', '', 8)
        self.cell(0, 4, 'RUC: 20172781005', 0, 1, 'C')
        ## self.set_font('Arial', '', 7)
        ## self.cell(0, 4, 'Av.Wiese Mza J Lt#24 Urb.M.Caceres - SJL', 0, 1, 'C')
        self.ln(1)
        self.line(5, self.get_y(), self.width - 5, self.get_y())
        self.ln(1)
    
    def footer(self):    # Pie de página
        self.set_y(-15)
        self.set_font('Arial', 'I', 7)
        self.cell(0, 4, 'Gracias por su pago', 0, 1, 'C')
        self.cell(0, 4, 'Recibo válido como comprobante de pago', 0, 1, 'C')
        self.cell(0, 4, f'Impreso el: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
    
    def add_receipt_info(self, data):    # Título
        self.set_font('Arial', 'B', 10)
        self.cell(0, 6, data['titulo'], 0, 1, 'C')
        self.set_font('Arial', 'B', 9)
        self.cell(0, 4, '[ S0'+data['serie']+'-0'+data['numero']+' ]', 0, 1, 'C')
        self.ln(1)
        # Información del socio
        self.set_font('Arial', 'B', 7)
        self.cell(20, 4, 'Padron/Socio:', 0, 0)
        self.set_font('Arial', '', 7)
        # Dividir el nombre si es muy largo
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
    
    def add_items_table(self, items):  ### TABLA DE ITEMS DE RECIBO
        self.set_font('Courier', 'B', 7)
        self.cell(15, 6, 'COD', 0, 0, 'L')
        self.cell(30, 6, 'DESCRIPCION', 0, 0, 'L')
        self.cell(15, 6, 'MONTO', 0, 1, 'R')
        self.line(5, self.get_y(), self.width - 5, self.get_y())
        self.ln(2)
        # Items
        self.set_font('Courier', '', 7)
        total = 0
        for item in items:
            codigo = item['codigo']
            descripcion = item['descripcion']
            monto = item['monto']
            total += monto
            self.cell(15, 4, codigo, 0, 0, 'L')
            if len(descripcion) > 18:
                desc_line1 = descripcion[:18]
                self.cell(30, 4, desc_line1, 0, 0, 'L')
            else:
                self.cell(30, 4, descripcion, 0, 0, 'L')
            self.cell(15, 4, f"S/. {monto:.2f}", 0, 1, 'R')
        self.ln(1)
        self.line(5, self.get_y(), self.width - 5, self.get_y())
        self.ln(1)
        # Total
        self.set_font('Courier', 'B', 8)
        self.cell(40, 8, 'TOTAL PAGADO:______', 0, 0, 'R')
        self.cell(15, 8, f"S/. {total:.2f}", 0, 1, 'R')
        self.ln(5)
        # Línea para firma
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, '_________________________', 0, 1, 'C')
        self.cell(0, 5, 'Firma y Sello', 0, 1, 'C')
        return total

# Crear PDF
def generar_recibo(tipo_doc, serie, numero_doc, codigo_padron, nombre_socio, fecha_recibo, fecha_giro, items, nombre_archivo=None):
    pdf = ReciboTicket()
    pdf.add_page()
    datos = {
        'serie': serie,
        'titulo': tipo_doc,
        'numero': numero_doc,
        'codigo_padron': codigo_padron,
        'nombre_socio': nombre_socio,
        'fecha_recibo': fecha_recibo,
        'fecha_giro': fecha_giro
    }    
    pdf.add_receipt_info(datos)
    total = pdf.add_items_table(items)
    if nombre_archivo is None:
        nombre_archivo = f"recibo_{codigo_padron}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    # Guardar PDF
    pdf.output(nombre_archivo)
    print(f"Recibo generado: {nombre_archivo}")
    print(f"Total del recibo: S/. {total:.2f}")
    return nombre_archivo

#### ************************************ COMBUSTIBLE **********************************************
@app.route('/dashboardC')
def dashboardC():   ### DASHBOARD COMBUSTIBLE
    now = datetime.datetime.now()
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        # Total de galones vendidos hoy
        cursor.execute(sqlconstants.DASHB_COMB_TOTAL_HOY)
        today_stats = cursor.fetchone()        
        # Ventas por turno hoy
        cursor.execute(sqlconstants.DASHB_COMB_TURNOS_HOY)
        shift_stats = cursor.fetchall()
        # Top máquinas
        cursor.execute(sqlconstants.DASHB_COMB_TOP_MAQUINAS)
        top_machines = cursor.fetchall()
        # Stock crítico (menos del 20%)
        cursor.execute(sqlconstants.DASHB_COMB_STOCK_CRITICO)
        low_stock = cursor.fetchall()
        cursor.close()
    return render_template('dashboardC.html',
                          today_stats=today_stats,
                          shift_stats=shift_stats,
                          top_machines=top_machines,
                          low_stock=low_stock, 
                          now=now)

@app.route('/cargar_turnos', methods=['GET', 'POST'])
def cargar_turnos():  ##Actualización masiva de todas las máquinas en una página
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.LISTA_MAQUINAS_X_TURNOS)       # Obtener todas las máquinas
    machines = cursor.fetchall()
    shifts = [              # Obtener turnos disponibles
        {'code': 'TURNO_1', 'name': '11AM - 6PM'},
        {'code': 'TURNO_2', 'name': '6PM - 2AM'},
        {'code': 'TURNO_3', 'name': '2AM - 11AM'}
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
                        continue  # Saltar si no hay datos
                    gallons_sold = final_reading - initial_reading
                    if gallons_sold < 0:
                        errors.append(f'Máquina {machine["machine_number"]}: Lectura final menor que inicial')
                        continue
                    # Obtener precio unitario
                    cursor.execute(sqlconstants.PRECIO_U_COMB, (machine['fuel_type_id'],))
                    fuel = cursor.fetchone()
                    if gallons_sold > 0:     # Registrar venta
                        cursor.execute(sqlconstants.INSERT_VTAS_COMBUSTIBLE, (machine_id, shift_code, 
                              next(s['name'] for s in shifts if s['code'] == shift_code), shift_date, 
                              initial_reading, final_reading, gallons_sold, gallons_sold * fuel['unit_price']))
                        # Actualizar stock
                        cursor.execute(sqlconstants.UPDATE_VTAS_COMB_MAQUINAS, (gallons_sold, final_reading, machine_id))   
                        success_count += 1
                except Exception as e:
                    errors.append(f'Máquina {machine["machine_number"]}: {str(e)}')
        if success_count > 0:
            connection.commit()
            flash(f'{success_count} máquina(s) actualizada(s) exitosamente', 'success')
        if errors:
            for error in errors:
                flash(error, 'warning')        
        return redirect(url_for('cargar_turnos'))
    cursor.close()
    return render_template('cargar_turnos.html', machines=machines, shifts=shifts, today=datetime.datetime.now().strftime('%Y-%m-%d'))

@app.route('/maquinas')
def maquinas(): ## Listar todas las máquinas
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sqlconstants.LISTA_MAQUINAS)
    machines = cursor.fetchall()
    cursor.execute(sqlconstants.LISTA_COMBUSTIBLE_TODOS)
    fuels = cursor.fetchall()
    cursor.close()
    return render_template('maquinas.html', machines=machines, fuels=fuels)

@app.route('/maquinas/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_maquina():
    if request.method == 'POST':
        machine_number = request.form['numero']
        fuel_type_id = request.form['tipo_combustible']
        initial_reading = request.form['lectura_inicial']
        stock_capacity = request.form['capacidad_stock']
        stock_available = request.form['disponible_stock']        
        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(sqlconstants.INS_MAQUINAS,(machine_number, fuel_type_id, initial_reading, stock_capacity, stock_available))
            connection.commit()
            flash('Máquina agregada exitosamente', 'success')
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'danger')
        finally:
            cursor.close()
        return redirect(url_for('maquinas'))
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM a_combustible')
    fuels = cursor.fetchall()
    cursor.close()
    return render_template('crear_maquina.html', fuels=fuels)

@app.route('/stock')
def stock(): ### Gestión de stock de combustibles
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)    # Obtener stock de combustibles
    cursor.execute(sqlconstants.SEL_COMBUSTIBLE)
    fuels = cursor.fetchall()     # Obtener stock por máquina
    cursor.execute(sqlconstants.DASHB_COMB_STOCK_CRITICO)
    machine_stock = cursor.fetchall()
    cursor.close()
    return render_template('stock.html', fuels=fuels, machine_stock=machine_stock)

@app.route('/editar_turno/<int:machine_id>', methods=['GET', 'POST'])
def editar_turno(machine_id): ### Actualizar lecturas por turno
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)      # Obtener información de la máquina
    cursor.execute(sqlconstants.SEL_1_MAQUINA, (machine_id,))
    machine = cursor.fetchone()
    if request.method == 'POST':
        shift_code, shift_name = get_shift_name()
        initial_reading = Decimal(request.form['initial_reading'])
        final_reading = Decimal(request.form['final_reading'])
        shift_date = request.form['shift_date']
        # Calcular galones vendidos
        gallons_sold = final_reading - initial_reading
        if gallons_sold < 0:
            flash('La lectura final no puede ser menor que la inicial', 'danger')
            return redirect(url_for('editar_turno', machine_id=machine_id))
        # Verificar stock disponible
        if gallons_sold > machine['stock_available']:
            flash(f'Stock insuficiente. Disponible: {machine["stock_available"]} galones', 'danger')
            return redirect(url_for('editar_turno', machine_id=machine_id))
        try:
            # Registrar la venta
            cursor.execute(sqlconstants.INS_VENTAS_COMB, (machine_id,shift_code,shift_name,shift_date,initial_reading,final_reading,gallons_sold,gallons_sold * machine['unit_price']))
            # Actualizar stock de la máquina
            cursor.execute(sqlconstants.UPD_MAQUINAS_VTAS_COMB, (gallons_sold, final_reading, machine_id))
            connection.commit()   # Actualizar stock general del combustible
            cursor.execute(sqlconstants.UPD_COMBUSTIBLE_CTAS_COMB, (gallons_sold, machine['fuel_type_id']))
            connection.commit()
            flash(f'Turno registrado exitosamente. Galones vendidos: {gallons_sold}', 'success')
        except mysql.connector.Error as err:
            connection.rollback()
            flash(f'Error: {err}', 'danger')
        finally:
            cursor.close()
        return redirect(url_for('maquinas'))
    # Obtener registros de turnos para hoy
    cursor.execute(sqlconstants.LISTA_TURNOS_MAQUINA_COMB, (machine_id,))
    today_shifts = cursor.fetchall()
    cursor.close()
    # Obtener turno actual
    shift_code, shift_name = get_shift_name()
    return render_template('editar_turno.html', 
                          machine=machine, 
                          today_shifts=today_shifts,
                          current_shift={'code': shift_code, 'name': shift_name},
                          today=datetime.datetime.now().strftime('%Y-%m-%d'))

def get_shift_name(current_time=None): ### Determinar el turno actual basado en la hora
    if current_time is None:
        current_time = datetime.datetime.now().time()
    if time(11, 0) <= current_time < time(18, 0):
        return 'TURNO_1', '11AM - 6PM'
    elif time(18, 0) <= current_time < time(2, 0):
        return 'TURNO_2', '6PM - 2AM'
    else:
        return 'TURNO_3', '2AM - 11AM'
### ???????????????????????????????????????????????????????????????????????????????????????
# Rutas para préstamos y retiros
@app.route('/prestamos', methods=['GET', 'POST'])
def prestamos():
    total = 0
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Ini
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Fin
        p3 = request.form.get('p3')  # Padron
        p4 = request.form.get('p4')  # Aprobados?
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = sqlconstants.SELECT_PRESTAMOS_1
        query = query.replace("$p1$", str(p1))
        query = query.replace("$p2$", str(p2))
        query = query.replace("$p3$", str(p3))
        query = query.replace("$p4$", str(p4))
        cursor.execute(query)
        prestamos = cursor.fetchall()
        conn.close()
        for r0 in prestamos:
            total += float(r0['mnt_aprobado'])
        return render_template('prestamos.html', prestamos=prestamos, total=total, p1=p1, p2=p2, p3=p3, p4=p4)
    else:
        px = datetime.datetime.now().strftime('%Y-%m-%d')  # Fecha Hoy
        flash('Listo para consultar.', 'success')
        return render_template('prestamos.html', prestamos=[],p1=px, p2=px, p3=0, p4='off', total=total)

@app.route('/prestamos/nuevo', methods=['GET', 'POST'])
def crear_prestamo():
    conn = get_db_connection()    
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sqlconstants.DROPLIST_DEUDAS)
    tipos = cursor.fetchall()
    if request.method == 'POST':
        act = request.form['act']
        pad = request.form['pad']
        fec = request.form['fec']
        tip = request.form['tip']
        mnt = float(request.form['mnt'])
        cuo = request.form['cuo']
        des = request.form['des']
        gar = 'gar' in request.form
        nom = ""
        lid = request.form.get('lid')
        if not all([fec, pad, mnt]):
            flash('Por favor, complete todos los campos con (*).', 'danger')
            return render_template('crear_prestamo.html')
        if act == '-':
            try:
                cursor = conn.cursor()
                cursor.execute(sqlconstants.INS_PRESTAMO, (pad, fec, tip, mnt, des, cuo, gar, act))
                lid = cursor.lastrowid
                conn.commit()
                act = "pendiente"
                conn.close()
                nom = get_nombre_padron(pad)
                flash('Préstamo solicitado exitosamente', 'success')
                return render_template('crear_prestamo.html',
                                act=act, fec=fec, pad=pad, des=des, mnt=mnt, cuo=cuo, 
                                tip=tip, gar=gar, but='Confirmar', lid=lid, nom = nom,
                                tipos=tipos)
            except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Prestamo existe.', 'danger')
                    else:
                        flash(f'Error al crear prestamo: {str(e)}', 'danger')
                    conn.rollback()
        if act == 'pendiente':
            try:
                nom = request.form.get('nom')
                usr = session['user_username']
                query9 = sqlconstants.ACT_PRESTAMO
                query9 = query9.replace("$lid$",lid)
                query9 = query9.replace("$usr$",usr)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query9)
                ## px = datetime.datetime.now().strftime('%Y-%m-%d')  # Fecha Hoy
                query = sqlconstants.SELECT_PRESTAMOS_1
                query = query.replace("$p1$", fec)
                query = query.replace("$p2$", fec)
                query = query.replace("$p3$", pad)
                query = query.replace("$p4$", "on")
                cursor.execute(query)
                prestamos = cursor.fetchall()
                conn.commit()
                flash('Confirmacion de solicitud del Préstamo fue exitosa.', 'success')
                return render_template('prestamos.html', prestamos=prestamos, total=0, p1=fec, p2=fec, p3=pad, p4="on")
            except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Prestamo existe.', 'danger')
                    else:
                        flash(f'Error al crear prestamo: {str(e)}', 'danger')
                    conn.rollback()
    cursor.close()
    conn.close()
    return render_template('crear_prestamo.html', act='-',but='Registrar', tipos=tipos)

@app.route('/prestamos/aprobar/<int:prestamo_id>', methods=['POST'])
def aprobar_prestamo(prestamo_id):
    total = 0
    p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Ini
    p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Fin
    p3 = request.form.get('p3')  # Padron
    p4 = request.form.get('p4')  # Aprobados?
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sqlconstants.APR_PRESTAMO, (prestamo_id,))
    query = sqlconstants.SELECT_PRESTAMOS_1
    query = query.replace("$p1$", str(p1))
    query = query.replace("$p2$", str(p2))
    query = query.replace("$p3$", str(p3))
    query = query.replace("$p4$", str(p4))
    cursor.execute(query)
    prestamos = cursor.fetchall()
    for r0 in prestamos:
            total += float(r0['mnt_aprobado'])
    conn.commit()
    conn.close()    
    flash('Préstamo aprobado exitosamente', 'success')
    return redirect(url_for('prestamos', prestamos=prestamos, total=total, p1=p1, p2=p2, p3=p3, p4=p4))

@app.route('/prestamos/rechazar/<int:prestamo_id>', methods=['POST'])
def rechazar_prestamo(prestamo_id):
    total = 0
    p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Ini
    p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Fin
    p3 = request.form.get('p3')  # Padron
    p4 = request.form.get('p4')  # Aprobados?
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sqlconstants.RCH_PRESTAMO, (prestamo_id,))
    query = sqlconstants.SELECT_PRESTAMOS_1
    query = query.replace("$p1$", str(p1))
    query = query.replace("$p2$", str(p2))
    query = query.replace("$p3$", str(p3))
    query = query.replace("$p4$", str(p4))
    cursor.execute(query)
    prestamos = cursor.fetchall()
    for r0 in prestamos:
            total += float(r0['mnt_aprobado'])
    conn.commit()
    conn.close()
    flash('Préstamo rechazado', 'info')
    return redirect(url_for('prestamos', prestamos=prestamos, total=total, p1=p1, p2=p2, p3=p3, p4=p4))

# Rutas para retiros -------------------------------------------------------------------------------|||
@app.route('/retiros', methods=['GET', 'POST'])
def retiros():
    total = 0
    tipos = []
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    querA = sqlconstants.DROPLIST_APORTES
    cursor.execute(querA)
    tipos = cursor.fetchall()
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Ini
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Fin
        p3 = request.form.get('p3')  # Padron
        p4 = request.form.get('p4')  # Aprobados?
        query = sqlconstants.SELECT_RETIROS_1
        query = query.replace("$p1$", str(p1))
        query = query.replace("$p2$", str(p2))
        query = query.replace("$p3$", str(p3))
        query = query.replace("$p4$", str(p4))
        cursor.execute(query)
        retiros = cursor.fetchall()
        querA = sqlconstants.DROPLIST_APORTES
        cursor.execute(querA)
        tipos = cursor.fetchall()
        conn.close()
        for r0 in retiros:
            total += float(r0['mnt_retirado'])
        return render_template('retiros.html', retiros=retiros, tipos=tipos, total=total, p1=p1, p2=p2, p3=p3, p4=p4)
    else:
        conn.close()           
        px = datetime.datetime.now().strftime('%Y-%m-%d')  # Fecha Hoy
        flash('Listo para consultar.', 'success')
        return render_template('retiros.html', retiros=[], tipos=tipos, p1=px, p2=px, p3=0, p4='', total=total)

@app.route('/retiros/nuevo', methods=['GET', 'POST'])
def crear_retiro():
    conn = get_db_connection()    
    if request.method == 'POST':
        act = request.form['act']
        pad = request.form['pad']
        fec = request.form['fec']
        des = request.form['des']
        nom = ""
        lid = request.form.get('lid')
        if not all([fec, pad]):
            flash('Por favor, complete todos los campos con (*).', 'danger')
            return render_template('crear_retiro.html')
        if act == '-':
            try:
                cursor = conn.cursor(dictionary=True)
                query = sqlconstants.DROPLIST_APORTES_SALDO_X_PADRON
                query = query.replace("$pad$", str(pad))
                cursor.execute(query)
                tipos = cursor.fetchall()
                act = "pendiente"
                cursor.close()
                conn.close()
                nom = get_nombre_padron(pad)
                flash('Confirmar tipo de saldo y monto del retiro ', 'success')
                return render_template('crear_retiro.html',
                                act=act, fec=fec, pad=pad, des=des, mnt=0, 
                                tip='', but='Confirmar', lid=lid, nom = nom,
                                tipos=tipos)
            except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Retiro existe.', 'danger')
                    else:
                        flash(f'Error al crear retiro: {str(e)}', 'danger')
                    conn.rollback()
        if act == 'pendiente':
            tip = request.form['tip']
            mnt = float(request.form['mnt'])
            total = 0
            try:
                sld = 0
                nom = request.form.get('nom')
                usr = session['user_username']
                cursor = conn.cursor(dictionary=True)
                quer4 = sqlconstants.DROPLIST_APORTES_SALDO_X_PADRON
                quer4 = quer4.replace("$pad$", str(pad))
                cursor.execute(quer4)
                saldos = cursor.fetchall()
                for s0 in saldos:
                    if (s0['codigo']==tip):
                        sld = s0['saldo']
                        if (mnt > sld):
                            flash('Debes colocar un monto menor al saldo actual, trata de nuevo, por favor.', 'danger')
                            return render_template('crear_retiro.html')
                query9 = sqlconstants.INS_RETIRO
                cursor.execute(query9, (pad, fec, tip, mnt, sld, des, act, usr))
                lid = cursor.lastrowid
                conn.commit()
                ### px = datetime.datetime.now().strftime('%Y-%m-%d')  # Fecha Hoy
                query = sqlconstants.SELECT_RETIROS_1
                query = query.replace("$p1$", fec)
                query = query.replace("$p2$", fec)
                query = query.replace("$p3$", pad)
                query = query.replace("$p4$", tip)
                cursor.execute(query)
                retiros = cursor.fetchall()
                querA = sqlconstants.DROPLIST_APORTES
                cursor.execute(querA)
                tipos = cursor.fetchall()
                cursor.close()
                conn.commit()
                flash('Confirmacion de Solicitud del Retiro fue exitosa.', 'success')
                return render_template('retiros.html', retiros=retiros, tipos=tipos, total=0, p1=fec, p2=fec, p3=pad, p4=tip)
            except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Retiro existe.', 'danger')
                    else:
                        flash(f'Error al crear retiro: {str(e)}', 'danger')
                    conn.rollback()
    conn.close()
    return render_template('crear_retiro.html', act='-',but='Consultar', lid=0)

@app.route('/retiros/aprobar/<int:retiro_id>', methods=['POST'])
def aprobar_retiro(retiro_id):
    total = 0
    p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Ini
    p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Fin
    p3 = request.form.get('p3')  # Padron
    p4 = request.form.get('p4')  # Tipo
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sqlconstants.APR_RETIRO, (retiro_id,))
    query = sqlconstants.SELECT_RETIROS_1
    query = query.replace("$p1$", str(p1))
    query = query.replace("$p2$", str(p2))
    query = query.replace("$p3$", str(p3))
    query = query.replace("$p4$", str(p4))
    cursor.execute(query)
    retiros = cursor.fetchall()
    for r0 in retiros:
            total += float(r0['mnt_retirado'])
    querA = sqlconstants.DROPLIST_APORTES
    cursor.execute(querA)
    tipos = cursor.fetchall()
    conn.commit()
    conn.close()
    flash('Retiro aprobado exitosamente', 'success')
    return redirect(url_for('retiros', retiros=retiros, tipos=tipos, total=total, p1=p1, p2=p2, p3=p3, p4=p4))

@app.route('/retiros/rechazar/<int:retiro_id>', methods=['POST'])
def rechazar_retiro(retiro_id):
    total = 0
    p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Ini
    p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))  # Fecha Fin
    p3 = request.form.get('p3')  # Padron
    p4 = request.form.get('p4')  # Tipo
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sqlconstants.RCH_RETIRO, (retiro_id,))
    query = sqlconstants.SELECT_RETIROS_1
    query = query.replace("$p1$", str(p1))
    query = query.replace("$p2$", str(p2))
    query = query.replace("$p3$", str(p3))
    query = query.replace("$p4$", str(p4))
    cursor.execute(query)
    retiros = cursor.fetchall()
    for r0 in retiros:
            total += float(r0['mnt_retirado'])
    querA = sqlconstants.DROPLIST_APORTES
    cursor.execute(querA)
    tipos = cursor.fetchall()
    conn.commit()
    conn.close()
    flash('Retiro rechazado', 'info')
    return redirect(url_for('retiros', retiros=retiros, tipos=tipos, total=total, p1=p1, p2=p2, p3=p3, p4=p4))

# Dashboard
@app.route('/dashboardP')
def dashboardP():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sqlconstants.DASHB_PRRET_SOCIOS)
        data = cursor.fetchone()
        total_socios_mes = str(data['total'])
        
        cursor.execute(sqlconstants.DASHB_PRRET_RETIROS)
        total_retiros = cursor.fetchone()['total']
        
        cursor.execute(sqlconstants.DASHB_PRRET_APORTES)
        total_aportes = cursor.fetchone()['total']
        
        cursor.execute(sqlconstants.DASHB_PRRET_PRESTAMOS) 
        total_prestamos = cursor.fetchone()['total']
        
        # Préstamos por estado
        cursor.execute(sqlconstants.DASHB_PRRET_PRESTAMOS_ESTADO)
        prestamos_por_estado = cursor.fetchall()

        # Préstamos por tipo
        cursor.execute(sqlconstants.DASHB_PRRET_PRESTAMOS_TIPOS)
        prestamos_por_tipo = cursor.fetchall()
        
        # Top 6 padrones con más aportes
        cursor.execute(sqlconstants.DASHB_PRRET_PAD_MAY_APORTES)
        top_padrones = cursor.fetchall()
        
        # Últimos movimientos
        cursor.execute(sqlconstants.DASHB_PRRET_MOVS_RET_PREST)
        ultimos_movimientos = cursor.fetchall()
    
    conn.close()
    return render_template('dashboardP.html',
                         now=datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 
                         total_socios_mes=total_socios_mes,
                         total_retiros=total_retiros,
                         total_aportes=total_aportes,
                         total_prestamos=total_prestamos,
                         prestamos_por_estado=prestamos_por_estado,
                         prestamos_por_tipo=prestamos_por_tipo,
                         top_padrones=top_padrones,
                         ultimos_movimientos=ultimos_movimientos)

# API para obtener saldo
@app.route('/api/padron/<int:padron_id>/saldo')
def obtener_saldo(padron_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT monto0 FROM a_padrones WHERE id = %s", (padron_id,))
        result = cursor.fetchone()
    conn.close()    
    if result:
        return jsonify({'saldo': float(result['monto0'])})
    return jsonify({'error': 'Padrón no encontrado'}), 404

# Agregar estas rutas después de las rutas existentes

# Ruta para generar PDF de solicitud de préstamo
@app.route('/prestamos/pdf/<int:prestamo_id>')
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
   # Crear el PDF en memoria
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=72, leftMargin=72,
                           topMargin=32, bottomMargin=18)
    # Contenedor para los elementos del PDF
    Story = []
    # Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, fontSize=14, spaceAfter=10))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, fontSize=10))
    styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT, fontSize=12, spaceAfter=10))
    ##styles.add(ParagraphStyle(name='Title', alignment=TA_CENTER, fontSize=16, spaceAfter=30, fontName='Helvetica-Bold'))
    # Encabezado
    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")
    Story.append(Paragraph(f"<b>E.T. LAS FLORES</b>", styles['Title']))
    Story.append(Spacer(1, 0.1*inch))
    Story.append(Paragraph(f"<i>Fecha de emisión: {fecha_actual}</i>", styles['Right']))
    Story.append(Spacer(1, 0.1*inch))
    # Título de la carta
    Story.append(Paragraph(f"<b>CARTA DE SOLICITUD DE PRÉSTAMO #{prestamo['id']}.</b>", styles['Center']))
    Story.append(Spacer(1, 0.3*inch))
    # Datos del solicitante
    Story.append(Paragraph(f"<b>Señores</b>", styles['Left']))
    Story.append(Paragraph("Comité de Préstamos", styles['Left']))
    Story.append(Paragraph("Presente.", styles['Left']))
    Story.append(Spacer(1, 0.2*inch))
    # Cuerpo de la carta
    Story.append(Paragraph(f"Yo, <b>{prestamo['socio_nombre']}</b>, con DNI _{prestamo['dni']}_, ", styles['Left']))
    Story.append(Paragraph(f"por medio de la presente solicito a ustedes un préstamo por la suma de ", styles['Left']))
    Story.append(Paragraph(f"<b>S/. {prestamo['monto_solicitado']:,.2f}</b>, el cual será destinado para <b>{prestamo['descripcion'] or 'No especificado'}</b>.", styles['Left']))
    Story.append(Spacer(1, 0.2*inch))
    
    # Detalles del préstamo
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
    
    # Declaración de garantía
    if prestamo['garantia_aporte']:
        Story.append(Paragraph("<b>DECLARACIÓN DE GARANTÍA</b>", styles['Left']))
        Story.append(Paragraph("Declaro que este préstamo está garantizado con mis aportes, ", styles['Left']))
       ### Story.append(Paragraph(f"los cuales ascienden a la fecha a <b>$ {prestamo['monto_aportado']:,.2f}</b>.", styles['Left']))
        Story.append(Spacer(1, 0.2*inch))
    
    # Compromiso
    Story.append(Paragraph("<b>COMPROMISO DE PAGO</b>", styles['Left']))
    Story.append(Paragraph("Me comprometo a cancelar el monto adeudado más los intereses ", styles['Left']))
    Story.append(Paragraph("generados en los plazos y condiciones establecidos por la institución.", styles['Left']))
    Story.append(Spacer(1, 0.5*inch))
    
    # Firmas
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
    
    # Construir el PDF
    doc.build(Story)
    
    # Obtener el valor del buffer y crear respuesta
    pdf = buffer.getvalue()
    buffer.close()
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=solicitud_prestamo_{prestamo_id}.pdf'
    
    return response

# Ruta para generar PDF de solicitud de retiro
@app.route('/retiros/pdf/<int:retiro_id>')
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
    # Crear el PDF en memoria
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    # Contenedor para los elementos del PDF
    Story = []
    # Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, fontSize=14, spaceAfter=20))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, fontSize=10))
    styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT, fontSize=12, spaceAfter=12))
    ##styles.add(ParagraphStyle(name='Title', alignment=TA_CENTER, fontSize=16, spaceAfter=30, fontName='Helvetica-Bold'))
    
    # Encabezado
    fecha_actual = datetime.datetime.now().strftime("%d de %B de %Y")
    Story.append(Paragraph(f"<b>E.T. LAS FLORES</b>", styles['Title']))
    Story.append(Spacer(1, 0.2*inch))
    Story.append(Paragraph(f"<i>Fecha de emisión: {fecha_actual}</i>", styles['Right']))
    Story.append(Spacer(1, 0.3*inch))
    
    # Título de la carta
    Story.append(Paragraph(f"<b>CARTA DE SOLICITUD DE RETIRO DE APORTES #00{retiro['id']}</b>", styles['Center']))
    Story.append(Spacer(1, 0.3*inch))
    
    # Datos del solicitante
    Story.append(Paragraph(f"<b>Señores</b>", styles['Left']))
    Story.append(Paragraph("Dpto. de Administracion.", styles['Left']))
    Story.append(Paragraph("Presente.-", styles['Left']))
    Story.append(Spacer(1, 0.2*inch))
    
    # Cuerpo de la carta 
    Story.append(Paragraph(f"Yo, <b>{retiro['nombre_socio']}</b>, por medio de la presente solicito ", styles['Left']))
    Story.append(Paragraph(f"el retiro de la suma de <b>S/ {retiro['monto_retirado']:,.2f}</b> de mis aportes del tipo : <b>{retiro['tipo_aporte']}</b>,", styles['Left']))
    Story.append(Paragraph(f"correspondientes al padrón placa número <b>{retiro['placa']}</b>.", styles['Left']))
    Story.append(Spacer(1, 0.2*inch))
    
    # Detalles del retiro
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
    
    # Autorización
    Story.append(Paragraph("<b>AUTORIZACIÓN</b>", styles['Left']))
    Story.append(Paragraph("Autorizo al sistema a realizar el débito correspondiente de mis aportes ", styles['Left']))
    Story.append(Paragraph("por el monto indicado en esta solicitud.", styles['Left']))
    Story.append(Spacer(1, 0.5*inch))
    
    # Firmas
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
    
    # Construir el PDF
    doc.build(Story)
    
    # Obtener el valor del buffer y crear respuesta
    pdf = buffer.getvalue()
    buffer.close()
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=solicitud_retiro_{retiro_id}.pdf'
    
    return response

### ???????????????????????????????????????????????????????????????????????????????????????

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
