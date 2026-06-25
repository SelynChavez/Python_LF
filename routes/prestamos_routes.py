from flask import render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from mysql.connector import Error
import datetime
import sqlconstants
from utils.database import get_db_connection, get_nombre_padron

from .prestamos import prestamos_bp

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@prestamos_bp.route('/prestamos', methods=['GET', 'POST'])
def prestamos():
    total = 0
    totsp = 0
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
        p4 = request.form.get('p4')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = sqlconstants.SELECT_PRESTAMOS_1
        query = query.replace("$p1$", str(p1))
        query = query.replace("$p2$", str(p2))
        query = query.replace("$p3$", str(p3))
        query = query.replace("$p4$", str(p4))
        cursor.execute(query)
        prestamos = cursor.fetchall()
        for r0 in prestamos:
            total += float(r0['mnt_aprobado'])
            totsp += float(r0['sld_pendiente'])
        conn.close()
        return render_template('prestamos.html', prestamos=prestamos, total=total, totsp=totsp, p1=p1, p2=p2, p3=p3, p4=p4)
    else:
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('prestamos.html', prestamos=[],p1=px, p2=px, p3=0, p4='off', total=0, totsp=0)


@prestamos_bp.route('/prestamos_socio', methods=['GET', 'POST'])
def prestamos_socio():
    total = 0
    totsp = 0
    usr = session['user_username']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    padrones = []
    if (session['user_rol'] == "SOCIO"):
        quer1 = sqlconstants.SELECT_LISTA_PADRONES
        quer1 = quer1.replace("$usr$", usr)
        cursor.execute(quer1)
        padrones = cursor.fetchall()
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
        p4 = request.form.get('p4')
        query = sqlconstants.SELECT_PRESTAMOS_1
        query = query.replace("$p1$", str(p1))
        query = query.replace("$p2$", str(p2))
        query = query.replace("$p3$", str(p3))
        query = query.replace("$p4$", str(p4))
        cursor.execute(query)
        prestamos = cursor.fetchall()
        for r0 in prestamos:
            total += float(r0['mnt_aprobado'])
            totsp += float(r0['sld_pendiente'])
        conn.close()
        return render_template('prestamos_socio.html', prestamos=prestamos, total=total, totsp=totsp, p1=p1, p2=p2, p3=p3, p4=p4,padrones=padrones)
    else:
        conn.close()
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('prestamos_socio.html', prestamos=[],p1=px, p2=px, p3=0, p4='off', total=0, totsp=0, padrones=padrones)


@prestamos_bp.route('/prestamos/nuevo', methods=['GET', 'POST'])
def crear_prestamo():
    conn = get_db_connection()    
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sqlconstants.DROPLIST_DEUDAS)
    tipos = cursor.fetchall()
    usr = session['user_username']
    padrones = []
    if (session['user_rol'] == "SOCIO"):
        quer1 = sqlconstants.SELECT_LISTA_PADRONES
        quer1 = quer1.replace("$usr$", usr)
        cursor.execute(quer1)
        padrones = cursor.fetchall()
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
                cursor.execute(sqlconstants.INS_PRESTAMO, (pad, fec, tip, mnt, des, cuo, gar, 'pendiente'))
                lid = cursor.lastrowid
                conn.commit()
                act = "evaluacion"
                conn.close()
                nom = get_nombre_padron(pad)
                flash('Préstamo solicitado exitosamente', 'success')
                return render_template('crear_prestamo.html',
                                act=act, fec=fec, pad=pad, des=des, mnt=mnt, cuo=cuo, 
                                tip=tip, gar=gar, but='.', lid=lid, nom = nom,
                                tipos=tipos, padrones=padrones)
            except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Prestamo existe.', 'danger')
                    else:
                        flash(f'Error al crear prestamo: {str(e)}', 'danger')
                    conn.rollback()
        if act == 'evaluacion':
            try:
                nom = request.form.get('nom')
                usr = session['user_username']
                query9 = sqlconstants.ACT_PRESTAMO
                query9 = query9.replace("$lid$",lid)
                query9 = query9.replace("$usr$",usr)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query9)
                conn.commit()
                flash('Solicitud del Préstamo fue puesto en evalucacion por el solicitante.', 'success')
                return render_template('prestamos.html', prestamos=[], total=0, totsp=0, p1=fec, p2=fec, p3=pad, p4="off", padrones=padrones)
            except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Prestamo existe.', 'danger')
                    else:
                        flash(f'Error al crear prestamo: {str(e)}', 'danger')
                    conn.rollback()
    cursor.close()
    conn.close()
    return render_template('crear_prestamo.html', act='-',but='Registrar', tipos=tipos, padrones=padrones)


@prestamos_bp.route('/prestamos/aprobar/<int:prestamo_id>', methods=['POST'])
def aprobar_prestamo(prestamo_id):
    total = 0
    p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
    p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
    p3 = request.form.get('p3')
    p4 = request.form.get('p4')
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
    return redirect(url_for('prestamos.prestamos', prestamos=prestamos, total=total, p1=p1, p2=p2, p3=p3, p4=p4))


@prestamos_bp.route('/prestamos/rechazar/<int:prestamo_id>', methods=['POST'])
def rechazar_prestamo(prestamo_id):
    total = 0
    p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
    p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
    p3 = request.form.get('p3')
    p4 = request.form.get('p4')
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
    return redirect(url_for('prestamos.prestamos', prestamos=prestamos, total=total, p1=p1, p2=p2, p3=p3, p4=p4))


@prestamos_bp.route('/api/prestamos/<int:prestamo_id>/actualizar', methods=['POST'])
def actualizar_prestamo(prestamo_id):
    try:
        data = request.get_json()
        cuota = data.get('cuota')
        estado = data.get('estado')

        if cuota is None:
            return jsonify({'success': False, 'error': 'La cuota es requerida'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        if estado and estado.strip():
            cursor.execute(sqlconstants.UPD_PRESTAMO_CUOTA_ESTADO, (cuota, estado, prestamo_id))
        else:
            cursor.execute(sqlconstants.UPD_PRESTAMO_CUOTA, (cuota, prestamo_id))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Préstamo actualizado correctamente'})
    except Error as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
