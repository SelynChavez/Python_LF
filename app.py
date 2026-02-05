from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import mysql.connector
from mysql.connector import Error
import hashlib
import os
from functools import wraps
from config import Config

from io import BytesIO
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from fpdf import FPDF
import base64
import datetime
import sqlconstants

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

# lista padrones
@app.route('/padrones')
@login_required
@admin_required
def listar_padrones():
    return render_template('padrones.html')

# lista aportes
@app.route('/tipos_aportes')
@login_required
@admin_required
def listar_tipos_aportes():
    return render_template('tipos_aportes.html')

# lista deudas
@app.route('/tipos_deudas')
@login_required
@admin_required
def listar_tipos_deudas():
    return render_template('tipos_deudas.html')

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
# RECIBOS (para demostrar funcionalidad reactiva)
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
                    return render_template('crear_recibo.html', act=act, fec=fec, pad=pad, com=com, nom=nom, but='Registrar', items=items, lid=lid)
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

@app.route('/api/socios')
@login_required
def api_socios():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        buscar = request.args.get('buscar', '')
        query = sqlconstants.QRY1SOCIOS
        if not buscar:
            buscar = ""
        cursor.execute(query, (f'%{buscar}%', f'%{buscar}%', f'%{buscar}%'))      
        socios = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(socios)
    else:
        return jsonify({'error': 'Error de conexión'}), 500

@app.route('/socios/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_socio():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        dni = request.form.get('dni')
        fono = request.form.get('fono')
        tipo = request.form.get('tipo')
        comentarios = request.form.get('comentarios')
        if not all([dni, fono, nombre, tipo, comentarios]):
            flash('Por favor, complete todos los campos.', 'danger')
            return render_template('crear_socio.html')
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(sqlconstants.INSERT_SOCIO, (nombre, fono, dni, comentarios, tipo, session['user_username']))
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
        active = request.form.get('active')
        try:
            cursor = connection.cursor()
            cursor.execute(sqlconstants.UPDATE_SOCIO, (nombre, fono, dni, comentarios, tipo, active, id))            
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
    pdf.cell(0, 8, f"E.T.Las Flores :: [{cod}] - [{usr}] -                                                                     {hora1}", 0, 1, 'R')
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
