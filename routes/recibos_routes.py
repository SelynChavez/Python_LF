from flask import render_template, request, redirect, url_for, flash, session
from functools import wraps
from mysql.connector import Error
from decimal import Decimal
import datetime
import sqlconstants
from utils.database import get_db_connection, get_nombre_padron

from .recibos import recibos_bp

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@recibos_bp.route('/crear_s6', methods=['GET', 'POST'])
@login_required
def crear_recibo_s6():
    if request.method == 'POST':
        act = request.form.get('act')
        fec = request.form.get('fec')
        pad = request.form.get('pad')
        com = request.form.get('com')
        lid = request.form.get('lid')
        num = request.form.get('num')
        ser = '6'
        nom = ""
        if not all([fec, pad]):
            flash('Por favor, complete todos los campos con (*).', 'danger')
            return render_template('crear_recibo_s6.html')
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            consulta = sqlconstants.DETALLE_SERIE_2
            consulta = consulta.replace("$serie$", ser)
            consulta = consulta.replace("$pad$", pad)
            cursor.execute(consulta)
            items = cursor.fetchall()
            cursor.close()
            if act == '-':
                try:
                    curs0r = connection.cursor()
                    quer0 = sqlconstants.INSERT_CORREL_X
                    quer0 = quer0.replace("$serie$", ser)
                    curs0r.execute(quer0)
                    num = curs0r.lastrowid
                    curs0r.close()

                    cursor = connection.cursor()
                    query = sqlconstants.INSERT_RECIBO_X
                    cursor.execute(query, (ser, num, fec, pad, com, act, session['user_username'], 'N')) 
                    lid = cursor.lastrowid
                    connection.commit()
                    act = '*'
                    nom = get_nombre_padron(pad)
                    connection.close()
                    flash('Continuar con detalles.', 'success')
                    return render_template('crear_recibo_s6.html', act=act, fec=fec, pad=pad, com=com, nom=nom, but='Registrar', items=items, lid=lid, num=num)
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('1.El recibo serie/fecha/padron ya existe.', 'danger')
                    else:
                        flash(f'2.Error al crear recibo: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            if act == '*':
                try:
                    lin = 0
                    total = 0
                    nom = request.form.get('nom')
                    cursor = connection.cursor()
                    for i0 in items:
                        lin += 1
                        mnt = request.form.get(i0['codigo'])
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        if mnt and mnt0 > 0:
                            i0['monto'] = Decimal(mnt0)
                            query = sqlconstants.INSERT_DETREC_X
                            query = query.replace("$apo$", i0['codigo'])
                            query = query.replace("$rec$", lid)
                            query = query.replace("$mnt$", mnt)
                            query = query.replace("$pre$", '0')
                            query = query.replace("$tip$", '')
                            query = query.replace("$usr$", session['user_username'])
                            cursor = connection.cursor()
                            cursor.execute(query)
                    query9 = sqlconstants.UPDATE_RECIBO_X
                    query9 = query9.replace("$recibo$",lid)
                    cursor.execute(query9)
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Recibo registrado.', 'success')
                    return render_template('crear_recibo_s6.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar')
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('El recibo serie/fecha/padron ya existe.', 'danger')
                    else:
                        flash(f'Error al crear recibo: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
        else:
            flash('Error de conexión a la base de datos.', 'danger')
    return render_template('crear_recibo_s6.html', act='-',but='Continuar')


@recibos_bp.route('/crear_s5', methods=['GET', 'POST'])
@login_required
def crear_recibo_s5():
    if request.method == 'POST':
        act = request.form.get('act')
        fec = request.form.get('fec')
        pad = request.form.get('pad')
        com = request.form.get('com')
        lid = request.form.get('lid')
        num = request.form.get('num')
        ser = '5'
        nom = ""
        if not all([fec, pad]):
            flash('Por favor, complete todos los campos con (*).', 'danger')
            return render_template('crear_recibo_s5.html')
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            consulta = sqlconstants.DETALLE_SERIE_2
            consulta = consulta.replace("$serie$", ser)
            consulta = consulta.replace("$pad$", pad)
            cursor.execute(consulta)
            items = cursor.fetchall()
            cursor.close()
            if act == '-':
                try:
                    curs0r = connection.cursor()
                    quer0 = sqlconstants.INSERT_CORREL_X
                    quer0 = quer0.replace("$serie$", ser)
                    curs0r.execute(quer0)
                    num = curs0r.lastrowid
                    curs0r.close()
                    cursor = connection.cursor()
                    query = sqlconstants.INSERT_RECIBO_X
                    cursor.execute(query, (ser, num, fec, pad, com, act, session['user_username'], 'N')) 
                    lid = cursor.lastrowid
                    connection.commit()
                    act = '*'
                    nom = get_nombre_padron(pad)
                    connection.close()
                    flash('Continuar con detalles.', 'success')
                    return render_template('crear_recibo_s5.html', act=act, fec=fec, pad=pad, com=com, nom=nom, but='Registrar', items=items, lid=lid, num=num)
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('1.El recibo serie/fecha/padron ya existe.', 'danger')
                    else:
                        flash(f'2.Error al crear recibo: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            if act == '*':
                try:
                    lin = 0
                    total = 0
                    nom = request.form.get('nom')
                    cursor = connection.cursor()
                    for i0 in items:
                        lin += 1
                        mnt = request.form.get(i0['codigo'])
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        if mnt and mnt0 > 0:
                            i0['monto'] = Decimal(mnt0)
                            query = sqlconstants.INSERT_DETREC_X
                            query = query.replace("$apo$", i0['codigo'])
                            query = query.replace("$rec$", lid)
                            query = query.replace("$mnt$", mnt)
                            query = query.replace("$pre$", '0')
                            query = query.replace("$tip$", '')
                            query = query.replace("$usr$", session['user_username'])
                            cursor = connection.cursor()
                            cursor.execute(query)
                    query9 = sqlconstants.UPDATE_RECIBO_X
                    query9 = query9.replace("$recibo$",lid)
                    cursor.execute(query9)
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Recibo registrado.', 'success')
                    return render_template('crear_recibo_s5.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar')
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('El recibo serie/fecha/padron ya existe.', 'danger')
                    else:
                        flash(f'Error al crear recibo: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
        else:
            flash('Error de conexión a la base de datos.', 'danger')
    return render_template('crear_recibo_s5.html', act='-',but='Continuar')


@recibos_bp.route('/crear_s4', methods=['GET', 'POST'])
@login_required
def crear_recibo_s4():
    if request.method == 'POST':
        act = request.form.get('act')
        fec = request.form.get('fec')
        pad = request.form.get('pad')
        com = request.form.get('com')
        lid = request.form.get('lid')
        num = request.form.get('num')
        ser = '4'
        nom = ""
        if not all([fec, pad]):
            flash('Por favor, complete todos los campos con (*).', 'danger')
            return render_template('crear_recibo_s4.html')
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            consulta = sqlconstants.DETALLE_SERIE_2
            consulta = consulta.replace("$serie$", ser)
            consulta = consulta.replace("$pad$", pad)
            cursor.execute(consulta)
            items = cursor.fetchall()
            cursor.close()
            if act == '-':
                try:
                    curs0r = connection.cursor()
                    quer0 = sqlconstants.INSERT_CORREL_X
                    quer0 = quer0.replace("$serie$", ser)
                    curs0r.execute(quer0)
                    num = curs0r.lastrowid
                    curs0r.close()

                    cursor = connection.cursor()
                    query = sqlconstants.INSERT_RECIBO_X
                    cursor.execute(query, (ser, num, fec, pad, com, act, session['user_username'], 'N')) 
                    lid = cursor.lastrowid
                    connection.commit()
                    act = '*'
                    nom = get_nombre_padron(pad)
                    connection.close()
                    flash('Continuar con detalles.', 'success')
                    return render_template('crear_recibo_s4.html', act=act, fec=fec, pad=pad, com=com, nom=nom, but='Registrar', items=items, lid=lid, num=num)
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('1.El recibo serie/fecha/padron ya existe', 'danger')
                    else:
                        flash(f'2.Error al crear recibo: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            if act == '*':
                try:
                    lin = 0
                    total = 0
                    nom = request.form.get('nom')
                    cursor = connection.cursor()
                    for i0 in items:
                        lin += 1
                        mnt = request.form.get(i0['codigo'])
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        if mnt and mnt0 > 0:
                            i0['monto'] = Decimal(mnt0)
                            query = sqlconstants.INSERT_DETREC_X
                            query = query.replace("$apo$", i0['codigo'])
                            query = query.replace("$rec$", lid)
                            query = query.replace("$mnt$", mnt)
                            query = query.replace("$pre$", '0')
                            query = query.replace("$tip$", '')
                            query = query.replace("$usr$", session['user_username'])
                            cursor = connection.cursor()
                            cursor.execute(query)
                    query9 = sqlconstants.UPDATE_RECIBO_X
                    query9 = query9.replace("$recibo$",lid)
                    cursor.execute(query9)
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Recibo registrado.', 'success')
                    return render_template('crear_recibo_s4.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar')
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('El recibo serie/fecha/padron ya existe.', 'danger')
                    else:
                        flash(f'Error al crear recibo(2): {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
        else:
            flash('Error de conexión a la base de datos.', 'danger')
    return render_template('crear_recibo_s4.html', act='-',but='Continuar')


@recibos_bp.route('/crear_s3', methods=['GET', 'POST'])
@login_required
def crear_recibo_s3():
    if request.method == 'POST':
        act = request.form.get('act')
        fec = request.form.get('fec')
        pad = request.form.get('pad')
        com = request.form.get('com')
        lid = request.form.get('lid')
        num = request.form.get('num')
        ser = '3'
        nom = ""
        if not all([fec, pad]):
            flash('Por favor, complete todos los campos con (*).', 'danger')
            return render_template('crear_recibo_s3.html')
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            consulta = sqlconstants.DETALLE_SERIE_2
            consulta = consulta.replace("$serie$", ser)
            consulta = consulta.replace("$pad$", pad)
            cursor.execute(consulta)
            items = cursor.fetchall()
            cursor.close()
            if act == '-':
                try:
                    curs0r = connection.cursor()
                    quer0 = sqlconstants.INSERT_CORREL_X
                    quer0 = quer0.replace("$serie$", ser)
                    curs0r.execute(quer0)
                    num = curs0r.lastrowid
                    curs0r.close()

                    cursor = connection.cursor()
                    query = sqlconstants.INSERT_RECIBO_X
                    cursor.execute(query, (ser, num, fec, pad, com, act, session['user_username'], 'N')) 
                    lid = cursor.lastrowid
                    connection.commit()
                    act = '*'
                    nom = get_nombre_padron(pad)
                    connection.close()
                    flash('Continuar con detalles.', 'success')
                    return render_template('crear_recibo_s3.html', act=act, fec=fec, pad=pad, com=com, nom=nom, but='Registrar', items=items, lid=lid, num=num)
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('1.El recibo serie/fecha/padron ya existe', 'danger')
                    else:
                        flash(f'2.Error al crear recibo: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            if act == '*':
                try:
                    lin = 0
                    total = 0
                    nom = request.form.get('nom')
                    cursor = connection.cursor()
                    for i0 in items:
                        lin += 1
                        mnt = request.form.get(i0['codigo'])
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        if mnt and mnt0 > 0:
                            i0['monto'] = Decimal(mnt0)
                            query = sqlconstants.INSERT_DETREC_X
                            query = query.replace("$apo$", i0['codigo'])
                            query = query.replace("$rec$", lid)
                            query = query.replace("$mnt$", mnt)
                            query = query.replace("$pre$", '0')
                            query = query.replace("$tip$", '')
                            query = query.replace("$usr$", session['user_username'])
                            cursor = connection.cursor()
                            cursor.execute(query)
                    query9 = sqlconstants.UPDATE_RECIBO_X
                    query9 = query9.replace("$recibo$",lid)
                    cursor.execute(query9)
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Recibo registrado.', 'success')
                    return render_template('crear_recibo_s3.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar')
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('El recibo serie/fecha/padron ya existe.', 'danger')
                    else:
                        flash(f'Error al crear recibo: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
        else:
            flash('Error de conexión a la base de datos.', 'danger')
    return render_template('crear_recibo_s3.html', act='-',but='Continuar')


@recibos_bp.route('/crear_s2', methods=['GET', 'POST'])
@login_required
def crear_recibo_s2():
    if request.method == 'POST':
        act = request.form.get('act')
        fec = request.form.get('fec')
        pad = request.form.get('pad')
        com = request.form.get('com')
        lid = request.form.get('lid')
        num = request.form.get('num')
        ser = '2'
        nom = ""
        if not all([fec, pad]):
            flash('Por favor, complete todos los campos con (*).', 'danger')
            return render_template('crear_recibo_s2.html')
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            consulta = sqlconstants.DETALLE_SERIE_2
            consulta = consulta.replace("$serie$", ser)
            consulta = consulta.replace("$pad$", pad)
            cursor.execute(consulta)
            items = cursor.fetchall()
            cursor.close()
            if act == '-':
                try:
                    curs0r = connection.cursor()
                    quer0 = sqlconstants.INSERT_CORREL_X
                    quer0 = quer0.replace("$serie$", ser)
                    curs0r.execute(quer0)
                    num = curs0r.lastrowid
                    curs0r.close()
                    cursor = connection.cursor()
                    query = sqlconstants.INSERT_RECIBO_X
                    cursor.execute(query, (ser, num, fec, pad, com, act, session['user_username'], 'S')) 
                    lid = cursor.lastrowid
                    connection.commit()
                    act = '*'
                    nom = get_nombre_padron(pad)
                    connection.close()
                    flash('Continuar ingresando montos del detalle.', 'success')
                    return render_template('crear_recibo_s2.html', act=act, fec=fec, pad=pad, com=com, nom=nom, but='Registrar', items=items, lid=lid, num=num)
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('1.El recibo serie/fecha/padron ya existe.', 'danger')
                    else:
                        flash(f'2.Error al crear recibo(29): {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            if act == '*':
                try:
                    lin = 0
                    total = 0
                    nom = request.form.get('nom')
                    cursor = connection.cursor()
                    for i0 in items:
                        lin += 1
                        mnt = request.form.get(i0['codigo'])
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        if mnt and mnt0 > 0:
                            i0['monto'] = Decimal(mnt0)
                            query = sqlconstants.INSERT_DETREC_X
                            query = query.replace("$apo$", i0['codigo'])
                            query = query.replace("$rec$", lid)
                            query = query.replace("$mnt$", mnt)
                            query = query.replace("$pre$", '0')
                            query = query.replace("$tip$", '')
                            query = query.replace("$usr$", session['user_username'])
                            cursor = connection.cursor()
                            cursor.execute(query)
                    query9 = sqlconstants.UPDATE_RECIBO_X
                    query9 = query9.replace("$recibo$",lid)
                    cursor.execute(query9)
                    connection.commit()
                    cursor.close()
                    connection.close()
                    flash('Recibo registrado.', 'success')
                    return render_template('crear_recibo_s2.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar')
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('El recibo serie/fecha/padron ya existe', 'danger')
                    else:
                        flash(f'Error al crear socio: {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
        else:
            flash('Error de conexión a la base de datos.', 'danger')
    return render_template('crear_recibo_s2.html', act='-',but='Continuar')


@recibos_bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear_recibo():
    if request.method == 'POST':
        act = request.form.get('act')
        fec = request.form.get('fec')
        pad = request.form.get('pad')
        com = request.form.get('com')
        lid = request.form.get('lid')
        num = request.form.get('num')
        ser = '1'
        nom = ""
        if not all([fec, pad]):
            flash('Por favor, complete todos los campos con (*).', 'danger')
            return render_template('crear_recibo.html')
        connection = get_db_connection()
        if act == '-':
            if connection:
                try:
                    curs0r = connection.cursor()
                    quer0 = sqlconstants.INSERT_CORREL_X
                    quer0 = quer0.replace("$serie$", ser)
                    curs0r.execute(quer0)
                    num = curs0r.lastrowid
                    curs0r.close()
                    cursor = connection.cursor()
                    querd = sqlconstants.DELETE_RECIBO_U
                    cursor.execute(querd, (ser, fec, pad ))
                    query = sqlconstants.INSERT_RECIBO_X
                    cursor.execute(query, (ser, num, fec, pad, com, act, session['user_username'], 'N')) 
                    lid = cursor.lastrowid
                    connection.commit()
                    act = '*'
                    cursor = connection.cursor(dictionary=True)
                    consulta = sqlconstants.DETALLE_SERIE_1
                    consulta = consulta.replace("$pad$", pad)
                    cursor.execute(consulta)
                    items = cursor.fetchall()
                    cursor.close()
                    nom = get_nombre_padron(pad)
                    connection.close()
                    flash('Continuar con detalles.', 'success')
                    return render_template('crear_recibo.html', ser=ser, act=act, fec=fec, pad=pad, com=com, nom=nom, but='Registrar', items=items, lid=lid, num=num)
                except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('El recibo serie/fecha/padron ya existe.', 'danger')
                    else:
                        flash(f'Error al crear recibo(1): {str(e)}', 'danger')
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
                    deu = 0
                    nom = request.form.get('nom')
                    cursor = connection.cursor(dictionary=True)
                    consulta = sqlconstants.DETALLE_SERIE_1
                    consulta = consulta.replace("$pad$", pad)
                    cursor.execute(consulta)
                    items = cursor.fetchall()
                    for i0 in items:
                        lin += 1
                        mnt = request.form.get(i0['codigo'])
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        if mnt and mnt0 > 0:
                            i0['monto'] = Decimal(mnt0)
                            query = sqlconstants.INSERT_DETREC_X
                            query = query.replace("$apo$", i0['codigo'])
                            query = query.replace("$rec$", lid)
                            query = query.replace("$mnt$", mnt)
                            query = query.replace("$pre$", str(i0['prestamo']))
                            query = query.replace("$tip$", str(i0['tipodeuda']))
                            query = query.replace("$usr$", session['user_username'])
                            cursor = connection.cursor()
                            cursor.execute(query)
                            deu = i0['prestamo']
                            if deu > 0:
                                quer0 = "UPDATE a_prestamos SET saldo_pendiente=saldo_pendiente-$mnt$ WHERE id='$pre$'"
                                quer0 = quer0.replace("$pre$", str(deu))
                                quer0 = quer0.replace("$mnt$", str(mnt))
                                cursor.execute(quer0)
                    query9 = sqlconstants.UPDATE_RECIBO_X
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
                        flash('El recibo serie/fecha/padron ya existe.', 'danger')
                    else:
                        flash(f'Error al crear recibo(14): {str(e)}', 'danger')
                    connection.rollback()
                    cursor.close()
                    connection.close()
            else:
                flash('Error de conexión a la base de datos.', 'danger')
    return render_template('crear_recibo.html', act='-',but='Continuar')
