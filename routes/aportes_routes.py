from flask import render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from flask import current_app
from mysql.connector import Error
import datetime
import sqlconstants
from utils.database import get_db_connection, get_nombre_padron

from .aportes import aportes_bp

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


def get_usuarios_para_recibos():
    """Obtiene usuarios: CAJA, ADMIN (solo AFIESTAS), GRIFERO"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, username, fullname, roles FROM applicationuser
            WHERE status = 'ACTIVE' AND (
                roles = 'CAJA' OR
                roles = 'GRIFERO' OR
                (roles = 'ADMIN' AND username = 'AFIESTAS')
            )
            ORDER BY fullname
        """)
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        return usuarios
    except Exception as e:
        print(f"Error obteniendo usuarios: {e}")
        return []


SERIE_COLORS = {
    '3': 'rgb(245, 247, 241)',
    '4': 'rgb(243, 215, 235)',
    '5': '#dce8f7',
    '6': '#f9eac9',
}


@aportes_bp.route('/anular_recibo', methods=['POST'])
@login_required
@admin_required
def anular_recibo():
    """Anula un recibo (active='N'). Revierte los saldos de prestamos afectados.

    Recibe JSON {id: <id_recibo>} y devuelve JSON {success: bool, error?: str}.
    """
    data = request.get_json(silent=True) or {}
    lid = data.get('id')
    if not lid:
        return jsonify({'success': False, 'error': 'No se indicó el recibo a anular.'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sqlconstants.SEL_RECIBO_BY_ID, (lid,))
        recibo = cursor.fetchone()
        if not recibo:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Recibo no encontrado.'}), 404
        if recibo['active'] != 'S':
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'El recibo ya está anulado.'}), 400

        # Revertir el saldo pendiente de los préstamos afectados por el detalle.
        cursor.execute(
            "SELECT prestamo, monto FROM a_recibos_detalle WHERE recibo=%s AND prestamo > 0",
            (lid,))
        detalles = cursor.fetchall()

        upd = connection.cursor()
        for d in detalles:
            upd.execute(
                "UPDATE a_prestamos SET saldo_pendiente = saldo_pendiente + %s WHERE id=%s",
                (d['monto'], d['prestamo']))

        upd.execute("UPDATE a_recibos SET active='N', modified=now() WHERE id=%s", (lid,))
        connection.commit()
        cursor.close()
        upd.close()
        connection.close()
        return jsonify({'success': True})
    except Error as e:
        connection.rollback()
        try:
            connection.close()
        except Exception:
            pass
        return jsonify({'success': False, 'error': str(e)})


@aportes_bp.route('/actualizar_usuario_recibo', methods=['POST'])
@login_required
def actualizar_usuario_recibo():
    """Actualiza el usuario (webuser) y fecha de giro de un recibo"""
    try:
        data = request.get_json()
        recibo_id = data.get('recibo_id')
        usuario = data.get('usuario', '')
        fecha_giro = data.get('fecha_giro', '')

        if not recibo_id:
            return jsonify({'success': False, 'error': 'No se indicó el recibo'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        if fecha_giro:
            cursor.execute("UPDATE a_recibos SET webuser=%s, giro=%s, modified=NOW() WHERE id=%s", (usuario, fecha_giro, recibo_id))
        else:
            cursor.execute("UPDATE a_recibos SET webuser=%s, modified=NOW() WHERE id=%s", (usuario, recibo_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Recibo actualizado correctamente'})
    except Error as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@aportes_bp.route('/aportes_series', methods=['GET', 'POST'])
@login_required
def aportes_series():
    total = 0
    line0 = 0
    recs = []
    serie = '3'
    color = SERIE_COLORS['3']
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
        serie = request.form.get('serie', '3')
        color = SERIE_COLORS.get(serie, SERIE_COLORS['3'])
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = sqlconstants.REP_S2_APORTES
            query = query.replace("$serie$", serie)
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
                total += float(reg['d7']) if reg['d7'] else 0
            return render_template('aportes_series.html', recibos=recibos, total=total, p1=p1, p2=p2, p3=p3, serie=serie, color=color)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard.menurecibos'))
    else:
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('aportes_series.html', p1=px, p2=px, p3=0, recibos=recs, total=total, serie=serie, color=color)


@aportes_bp.route('/aportes_s6', methods=['GET', 'POST'])
@login_required
def aportes_s6():
    total = 0
    line0 = 0
    recs = []
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = sqlconstants.REP_S2_APORTES
            query = query.replace("$serie$", '6')
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
                total += float(reg['d7']) if reg['d7'] else 0
            return render_template('aportes_s6.html', recibos=recibos, total=total, p1=p1, p2=p2, p3=p3)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard.menurecibos'))
    else:
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('aportes_s6.html', p1=px, p2=px, p3=0, recibos=recs, total=total)


@aportes_bp.route('/aportes_s5', methods=['GET', 'POST'])
@login_required
def aportes_s5():
    total = 0
    line0 = 0
    recs = []
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = sqlconstants.REP_S2_APORTES
            query = query.replace("$serie$", '5')
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
                total += float(reg['d7']) if reg['d7'] else 0
            return render_template('aportes_s5.html', recibos=recibos, total=total, p1=p1, p2=p2, p3=p3)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard.menurecibos'))
    else:
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('aportes_s5.html', p1=px, p2=px, p3=0, recibos=recs, total=total)


@aportes_bp.route('/aportes_s4', methods=['GET', 'POST'])
@login_required
def aportes_s4():
    total = 0
    line0 = 0
    recs = []
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = sqlconstants.REP_S2_APORTES
            query = query.replace("$serie$", '4')
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
                total += float(reg['d7']) if reg['d7'] else 0
            return render_template('aportes_s4.html', recibos=recibos, total=total, p1=p1, p2=p2, p3=p3)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard.menurecibos'))
    else:
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('aportes_s4.html', p1=px, p2=px, p3=0, recibos=recs, total=total)


@aportes_bp.route('/aportes_s3', methods=['GET', 'POST'])
@login_required
def aportes_s3():
    total = 0
    line0 = 0
    recs = []
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = sqlconstants.REP_S2_APORTES
            query = query.replace("$serie$", '3')
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
                total += float(reg['d7']) if reg['d7'] else 0
            return render_template('aportes_s3.html', recibos=recibos, total=total, p1=p1, p2=p2, p3=p3)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard.menurecibos'))
    else:
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('aportes_s3.html', p1=px, p2=px, p3=0, recibos=recs, total=total)


@aportes_bp.route('/aportes_s2', methods=['GET', 'POST'])
@login_required
def aportes_s2():
    total = 0
    subtotal = 0
    line0 = 0
    recs = []
    usuarios = get_usuarios_para_recibos()

    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = sqlconstants.REP_S2_APORTES
            query = query.replace("$serie$", '2')
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
                subtotal += float(reg['d7']) if reg['d7'] else 0
                total += round(float(reg['d13']),2) if reg['d13'] else 0
            return render_template('aportes_s2.html', recibos=recibos, total=total, subtotal=subtotal, p1=p1, p2=p2, p3=p3, usuarios=usuarios)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard.menurecibos'))
    else:
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('aportes_s2.html', p1=px, p2=px, p3=0, recibos=recs, total=total, subtotal=0)


@aportes_bp.route('/aportes_s2/importar', methods=['POST'])
@login_required
def importar_s2():
    import csv, io
    APORTE = 'AP.ESPECIAL'
    WEBUSER = 'AFIESTAS'
    COMENTARIO = '**Importado'
    SERIE = '2'

    archivo = request.files.get('csv_file')
    if not archivo or archivo.filename == '':
        flash('Debe seleccionar un archivo CSV.', 'danger')
        return redirect(url_for('aportes.aportes_s2'))

    raw = archivo.read()
    try:
        contenido = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        contenido = raw.decode('latin-1')

    lector = csv.reader(io.StringIO(contenido), delimiter=';')
    filas = [f for f in lector if any((c or '').strip() for c in f)]
    if filas and 'PAD' in (filas[0][0] or '').upper():
        filas = filas[1:]  # descartar encabezado

    connection = get_db_connection()
    if not connection:
        flash('Error de conexión a la base de datos.', 'danger')
        return redirect(url_for('aportes.aportes_s2'))

    def parse_fecha(valor):
        for fmt in ('%d/%m/%Y', '%d/%m/%y'):
            try:
                return datetime.datetime.strptime(valor, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        raise ValueError(f"fecha inválida '{valor}'")

    creados = 0
    errores = []
    cursor = connection.cursor()
    for idx, fila in enumerate(filas, start=1):
        if len(fila) < 6:
            errores.append(f'Fila {idx}: formato inválido (se esperan 6 columnas).')
            continue
        padron = (fila[0] or '').strip()
        importe = (fila[4] or '').strip().replace(',', '')
        fecha_str = (fila[3] or '').strip()
        giro_str = (fila[5] or '').strip()
        try:
            padron_id = int(padron)
            monto = float(importe)
            fecha = parse_fecha(fecha_str)
            giro = parse_fecha(giro_str)
        except (ValueError, TypeError) as e:
            errores.append(f'Fila {idx} (padron {padron}): datos inválidos ({e}).')
            continue
        try:
            quer0 = sqlconstants.INSERT_CORREL_X.replace('$serie$', SERIE)
            cursor.execute(quer0)
            numero = cursor.lastrowid
            cursor.execute(sqlconstants.INSERT_RECIBO_IMPORT,
                           (SERIE, numero, fecha, giro, padron_id, COMENTARIO, WEBUSER))
            recibo_id = cursor.lastrowid
            cursor.execute(sqlconstants.INSERT_DETREC_IMPORT,
                           (APORTE, recibo_id, monto, WEBUSER))
            connection.commit()
            creados += 1
        except Error as e:
            connection.rollback()
            if 'Duplicate entry' in str(e):
                errores.append(f'Fila {idx} (padron {padron}): ya existe una boleta para esa fecha de giro.')
            else:
                errores.append(f'Fila {idx} (padron {padron}): {str(e)}')
    cursor.close()
    connection.close()

    if creados:
        flash(f'{creados} boleta(s) importada(s) correctamente.', 'success')
    if errores:
        for err in errores[:20]:
            flash(err, 'warning')
        if len(errores) > 20:
            flash(f'... y {len(errores) - 20} error(es) más.', 'warning')
    if not creados and not errores:
        flash('El archivo no contenía filas para importar.', 'warning')
    return redirect(url_for('aportes.aportes_s2'))


@aportes_bp.route('/aportes', methods=['GET', 'POST'])
@login_required
@admin_required
def aportes():
    total = 0
    line0 = 0
    recs = []
    if request.method == 'POST':
        p1 = request.form.get('p1', datetime.datetime.now().strftime('%Y-%m-%d'))
        p2 = request.form.get('p2', datetime.datetime.now().strftime('%Y-%m-%d'))
        p3 = request.form.get('p3')
        sr = request.form.get('sr')
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
                total += float(reg['d7']) if reg['d7'] else 0
            return render_template('aportes.html', recibos=recibos, total=total, p1=p1, p2=p2, p3=p3, sr=sr)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard.menurecibos'))
    else:
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('aportes.html', p1=px, p2=px, p3=0, recibos=recs, total=total)


@aportes_bp.route('/aportes_socio', methods=['GET', 'POST'])
@login_required
def aportes_socio():
    total = 0
    line0 = 0
    recs = []
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    usr = session['user_username']
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
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = sqlconstants.REP_SS_APORTES
            query = query.replace("$serie$", '0')
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
                total += round(float(reg['d7']),2) if reg['d7'] else 0
            return render_template('aportes_socio.html', recibos=recibos, total=total, p1=p1, p2=p2, p3=p3, padrones=padrones)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard.dashboard'))
    else:
        connection.close()
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('aportes_socio.html', p1=px, p2=px, p3=0, recibos=recs, total=total, padrones=padrones)
