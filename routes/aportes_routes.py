from flask import render_template, request, redirect, url_for, flash, session
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


SERIE_COLORS = {
    '3': 'rgb(245, 247, 241)',
    '4': 'rgb(243, 215, 235)',
    '5': '#dce8f7',
    '6': '#f9eac9',
}

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
                total += float(reg['d7'])
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
                total += float(reg['d7'])
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
                total += float(reg['d7'])
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
                total += float(reg['d7'])
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
                total += float(reg['d7'])
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
    totaligv = 0
    subtotal = 0
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
                subtotal += float(reg['d7'])
                totaligv += round(float(reg['d12']),1)
                total += round(float(reg['d13']),2)
            return render_template('aportes_s2.html', recibos=recibos, total=total, totaligv=totaligv, subtotal=subtotal, p1=p1, p2=p2, p3=p3)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard.menurecibos'))
    else:
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('aportes_s2.html', p1=px, p2=px, p3=0, recibos=recs, total=total, subtotal=0, totaligv=0)


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
                total += float(reg['d7'])
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
                total += round(float(reg['d7']),2)
            return render_template('aportes_socio.html', recibos=recibos, total=total, p1=p1, p2=p2, p3=p3, padrones=padrones)
        else:
            flash('Error de conexión a la base de datos.', 'danger')
            return redirect(url_for('dashboard.dashboard'))
    else:
        connection.close()
        px = datetime.datetime.now().strftime('%Y-%m-%d')
        flash('Listo para consultar.', 'success')
        return render_template('aportes_socio.html', p1=px, p2=px, p3=0, recibos=recs, total=total, padrones=padrones)
