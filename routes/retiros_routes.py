from flask import render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from mysql.connector import Error
import datetime
import sqlconstants
from utils.database import get_db_connection, get_nombre_padron

from .retiros import retiros_bp

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def get_usuarios_caja_grifero():
    """Obtiene lista de usuarios con rol CAJA o GRIFERO"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, fullname, roles FROM applicationuser WHERE roles IN ('CAJA', 'GRIFERO') AND status = 'ACTIVE' ORDER BY fullname")
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        return usuarios
    except Exception as e:
        print(f"Error obteniendo usuarios: {e}")
        return []


@retiros_bp.route('/retiros_socio', methods=['GET', 'POST'])
def retiros_socio():
    total = 0
    tipos = []
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    querA = sqlconstants.DROPLIST_APORTES_RET
    cursor.execute(querA)
    tipos = cursor.fetchall()
    padrones = []
    usr = session['user_username']
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
        query = sqlconstants.SELECT_RETIROS_1
        query = query.replace("$p1$", str(p1))
        query = query.replace("$p2$", str(p2))
        query = query.replace("$p3$", str(p3))
        query = query.replace("$p4$", str(p4))
        cursor.execute(query)
        retiros = cursor.fetchall()
        conn.close()
        for r0 in retiros:
            total += float(r0['mnt_retirado'])
        return render_template('retiros_socio.html', retiros=retiros, tipos=tipos, total=total, p1=p1, p2=p2, p3=p3, p4=p4, padrones=padrones)
    else:
        conn.close()           
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('retiros_socio.html', retiros=[], tipos=tipos, p1=px, p2=px, p3=0, p4='', total=total, padrones=padrones)


@retiros_bp.route('/retiros', methods=['GET', 'POST'])
def retiros():
    total = 0
    tipos = []
    usuarios_caja_grifero = get_usuarios_caja_grifero()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    querA = sqlconstants.DROPLIST_APORTES_RET
    cursor.execute(querA)
    tipos = cursor.fetchall()
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
        p4 = request.form.get('p4')
        query = sqlconstants.SELECT_RETIROS_1
        query = query.replace("$p1$", str(p1))
        query = query.replace("$p2$", str(p2))
        query = query.replace("$p3$", str(p3))
        query = query.replace("$p4$", str(p4))
        cursor.execute(query)
        retiros = cursor.fetchall()
        conn.close()
        for r0 in retiros:
            total += float(r0['mnt_retirado'])
        return render_template('retiros.html', retiros=retiros, tipos=tipos, total=total, p1=p1, p2=p2, p3=p3, p4=p4, usuarios_caja_grifero=usuarios_caja_grifero)
    else:
        conn.close()
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('retiros.html', retiros=[], tipos=tipos, p1=px, p2=px, p3=0, p4='', total=total, usuarios_caja_grifero=usuarios_caja_grifero)


@retiros_bp.route('/retiros/nuevo', methods=['GET', 'POST'])
def crear_retiro():
    conn = get_db_connection()   
    cursor = conn.cursor(dictionary=True)
    padrones = []
    usr = session['user_username']
    if (session['user_rol'] == "SOCIO"):
        quer1 = sqlconstants.SELECT_LISTA_PADRONES
        quer1 = quer1.replace("$usr$", usr)
        cursor.execute(quer1)
        padrones = cursor.fetchall()
    if request.method == 'POST':
        act = request.form['act']
        pad = request.form['pad']
        fec = request.form['fec']
        des = request.form['des']
        nom = ""
        lid = request.form.get('lid')
        if not all([fec, pad]):
            flash('Por favor, complete todos los campos con (*).', 'danger')
            return render_template('crear_retiro.html', padrones=padrones)
        if act == '-':
            try:
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
                                tipos=tipos, padrones=padrones)
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
                            return render_template('crear_retiro.html', padrones=padrones)
                query9 = sqlconstants.INS_RETIRO
                cursor.execute(query9, (pad, fec, tip, mnt, sld, des, act, usr))
                lid = cursor.lastrowid
                conn.commit()
                query = sqlconstants.SELECT_RETIROS_1
                query = query.replace("$p1$", fec)
                query = query.replace("$p2$", fec)
                query = query.replace("$p3$", pad)
                query = query.replace("$p4$", tip)
                cursor.execute(query)
                retiros = cursor.fetchall()
                querA = sqlconstants.DROPLIST_APORTES_RET
                cursor.execute(querA)
                tipos = cursor.fetchall()
                cursor.close()
                conn.commit()
                flash('Confirmacion de Solicitud del Retiro fue exitosa.', 'success')
                if (session['user_rol'] == "SOCIO"):
                    return render_template('retiros_socio.html', 
                        retiros=retiros, tipos=tipos, total=0, p1=fec, p2=fec, p3=pad, p4=tip, padrones=padrones)
                else:
                    return render_template('retiros.html', 
                        retiros=retiros, tipos=tipos, total=0, p1=fec, p2=fec, p3=pad, p4=tip)
            except Error as e:
                    if 'Duplicate entry' in str(e):
                        flash('Retiro existe.', 'danger')
                    else:
                        flash(f'Error al crear retiro: {str(e)}', 'danger')
                    conn.rollback()
    conn.close()
    return render_template('crear_retiro.html', act='-',but='Consultar', lid=0, padrones=padrones)


@retiros_bp.route('/retiros/aprobar/<int:retiro_id>', methods=['POST'])
def aprobar_retiro(retiro_id):
    total = 0
    p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
    p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
    p3 = request.form.get('p3')
    p4 = request.form.get('p4')
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
    return redirect(url_for('retiros.retiros', retiros=retiros, tipos=tipos, total=total, p1=p1, p2=p2, p3=p3, p4=p4))


@retiros_bp.route('/retiros/rechazar/<int:retiro_id>', methods=['POST'])
def rechazar_retiro(retiro_id):
    total = 0
    p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
    p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
    p3 = request.form.get('p3')
    p4 = request.form.get('p4')
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
    return redirect(url_for('retiros.retiros', retiros=retiros, tipos=tipos, total=total, p1=p1, p2=p2, p3=p3, p4=p4))


@retiros_bp.route('/api/retiros/<int:retiro_id>/cajero', methods=['POST'])
def actualizar_cajero_retiro(retiro_id):
    """Actualiza el cajero de un retiro"""
    try:
        data = request.get_json()
        cajero = data.get('cajero', '')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE a_retiros SET cajero=%s, modified=NOW() WHERE id=%s", (cajero, retiro_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Cajero actualizado correctamente'})
    except Error as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
