from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify
from functools import wraps
from mysql.connector import Error
from decimal import Decimal
import datetime
import os
import sqlconstants
from utils.database import get_db_connection, get_nombre_padron

from .recibos import recibos_bp

# Carpeta donde se guardan los PDF de los recibos generados
RECIBOS_DIR = 'recibos_'

# Titulo que se imprime en la cabecera del PDF segun la serie
TITULOS_SERIE = {
    '1': 'RECIBO DE INGRESOS',
    '2': 'Recibo Cot.x Padron',
    '3': 'RECIBO ACCESO Y CAPITAL',
    '4': 'RECIBO ATU COMBUSTIBLE',
    '5': 'Recibo Cobranza de Comb.',
    '6': 'RECIBO DE DESPACHO',
}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def _saldo_cobro_comb(connection, pad):
    """Saldo pendiente de combustible del padrón: ventas - cobros (serie 5, COBRO.COMB)."""
    try:
        cur = connection.cursor()
        cur.execute(sqlconstants.SALDO_COBRO_COMB, (pad, pad))
        row = cur.fetchone()
        cur.close()
        saldo = float(row[0]) if row and row[0] is not None else 0.0
        return round(saldo, 2)
    except Exception as e:
        print(f"Error al calcular saldo COBRO.COMB: {e}")
        return 0.0


def _generar_pdf_recibo(ser, num, pad, nom, fec, items, recibo_id=None):
    """Genera el PDF del recibo y devuelve solo el nombre del archivo (basename).

    Devuelve None si ocurre un error, para no interrumpir el registro del recibo.
    """
    try:
        from .reportes_routes import generar_recibo
        from utils.database import get_db_connection

        print(f"\n{'='*60}")
        print(f"[_generar_pdf_recibo] INICIO - recibo_id={recibo_id} (tipo: {type(recibo_id).__name__})")

        fecha_reg = datetime.datetime.now().strftime('%Y-%m-%d')
        titulo = TITULOS_SERIE.get(str(ser), 'RECIBO')

        # Obtener fecha de modificación del recibo si existe
        fecha_impresion = None

        if recibo_id:
            print(f"[_generar_pdf_recibo] recibo_id NO es None, intentando obtener de BD...")
            try:
                conn = get_db_connection()
                if conn:
                    print(f"[_generar_pdf_recibo] Conexión a BD exitosa")
                    cursor = conn.cursor(dictionary=True)
                    query = "SELECT id, modified FROM a_recibos WHERE id = %s"
                    print(f"[_generar_pdf_recibo] Ejecutando: {query} con id={recibo_id}")
                    cursor.execute(query, (recibo_id,))
                    result = cursor.fetchone()
                    print(f"[_generar_pdf_recibo] Query result: {result}")
                    if result:
                        fecha_impresion = result.get('modified')
                        print(f"[_generar_pdf_recibo] ✓ fecha_impresion obtenida: {fecha_impresion} (tipo: {type(fecha_impresion).__name__})")
                    else:
                        print(f"[_generar_pdf_recibo] ✗ No se encontró recibo con id={recibo_id}")
                    cursor.close()
                    conn.close()
                else:
                    print(f"[_generar_pdf_recibo] ✗ No se pudo conectar a BD")
            except Exception as e:
                print(f"[_generar_pdf_recibo] ✗ Error en BD: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[_generar_pdf_recibo] ✗ recibo_id es None, usando hora del sistema")

        print(f"[_generar_pdf_recibo] Pasando a generar_recibo: fecha_impresion={fecha_impresion}")
        ruta = generar_recibo(titulo, str(ser), num, pad, nom, fecha_reg, fec, items, fecha_impresion=fecha_impresion)
        print(f"[_generar_pdf_recibo] FIN - PDF generado")
        print(f"{'='*60}\n")
        return os.path.basename(ruta)
    except Exception as e:
        print(f"[_generar_pdf_recibo] ✗ EXCEPCIÓN: {e}")
        import traceback
        traceback.print_exc()
        return None


@recibos_bp.route('/pdf/<path:filename>')
@login_required
def ver_recibo_pdf(filename):
    """Sirve el PDF del recibo en linea (para visualizarlo/imprimirlo)."""
    ruta = os.path.abspath(os.path.join(RECIBOS_DIR, os.path.basename(filename)))
    if os.path.exists(ruta):
        return send_file(ruta, mimetype='application/pdf')
    flash('Recibo no encontrado.', 'danger')
    return redirect(url_for('recibos.crear_recibo_s2'))


@recibos_bp.route('/imprimir/<path:filename>')
@login_required
def imprimir_recibo(filename):
    """Pagina que carga el PDF y lanza el dialogo de impresion del navegador."""
    return render_template('imprimir_recibo.html', filename=os.path.basename(filename))


@recibos_bp.route('/regenerar_pdf/<int:recibo_id>')
@login_required
def regenerar_pdf_recibo(recibo_id):
    """Regenera el PDF de un recibo con la fecha correcta del campo modified."""
    print(f"\n{'='*60}")
    print(f"[regenerar_pdf_recibo] INICIO - recibo_id={recibo_id}")

    conn = get_db_connection()
    if not conn:
        print(f"[regenerar_pdf_recibo] ✗ Error: No se pudo conectar a BD")
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('recibos.crear_recibo_s2'))

    print(f"[regenerar_pdf_recibo] ✓ Conexión exitosa")
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT r.id, r.serie, r.numero, r.padron, r.fecha, r.modified,
                   (SELECT CONCAT(p.id, ':', p.placa, ':', s.nombre)
                    FROM a_padrones p, a_socios s
                    WHERE p.socio=s.id AND r.padron=p.id) as nombre_padron
            FROM a_recibos r
            WHERE r.id = %s
        """, (recibo_id,))
        recibo = cursor.fetchone()
        print(f"[regenerar_pdf_recibo] Query recibo: {recibo}")

        if not recibo:
            print(f"[regenerar_pdf_recibo] ✗ Recibo no encontrado")
            flash('Recibo no encontrado', 'danger')
            return redirect(url_for('recibos.crear_recibo_s2'))

        print(f"[regenerar_pdf_recibo] ✓ Recibo encontrado: id={recibo['id']}, modified={recibo['modified']}")

        # Obtener detalles del recibo
        cursor.execute("""
            SELECT d.aporte as codigo, t.descripcion, d.monto
            FROM a_recibos_detalle d
            LEFT JOIN a_tipos t ON t.codigo = d.aporte AND t.tipo = 'APORTE'
            WHERE d.recibo = %s
            ORDER BY d.id
        """, (recibo_id,))
        items = cursor.fetchall()

        # Convertir items al formato esperado
        items_formateados = []
        for item in items:
            items_formateados.append({
                'codigo': item['codigo'] or '',
                'descripcion': item['descripcion'] or '',
                'monto': float(item['monto']) if item['monto'] else 0
            })

        # Regenerar PDF con la fecha correcta
        from .reportes_routes import generar_recibo
        nombre_padron = recibo['nombre_padron'] if recibo['nombre_padron'] else ''
        titulo = TITULOS_SERIE.get(str(recibo['serie']), 'RECIBO')

        # Convertir la fecha de modificación para pasarla al PDF
        fecha_impresion = recibo['modified']
        print(f"[regenerar_pdf_recibo] Usando fecha_impresion={fecha_impresion} (tipo: {type(fecha_impresion).__name__})")

        # Generar el PDF en una ubicación temporal
        pdf_file = generar_recibo(
            titulo,
            str(recibo['serie']),
            recibo['numero'],
            recibo['padron'],
            nombre_padron,
            recibo['fecha'].strftime('%Y-%m-%d'),
            recibo['fecha'].strftime('%Y-%m-%d'),
            items_formateados,
            fecha_impresion=fecha_impresion
        )

        print(f"[regenerar_pdf_recibo] ✓ PDF generado: {pdf_file}")
        print(f"[regenerar_pdf_recibo] FIN")
        print(f"{'='*60}\n")
        return send_file(pdf_file, mimetype='application/pdf', as_attachment=False)

    except Exception as e:
        print(f"[regenerar_pdf_recibo] ✗ EXCEPCIÓN: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        flash(f'Error al regenerar PDF: {str(e)}', 'danger')
        return redirect(url_for('recibos.crear_recibo_s2'))
    finally:
        cursor.close()
        conn.close()


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
            consulta = sqlconstants.DETALLE_SERIE_3X
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
                    for idx, i0 in enumerate(items):
                        lin += 1
                        mnt = request.form.get(f"monto_{idx}")
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        i0['monto'] = Decimal(str(mnt0))
                        if mnt and mnt0 > 0:
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
                    print(f"\n>>> ANTES de llamar _generar_pdf_recibo: lid={lid}, ser={ser}, num={num}")
                    pdf_file = _generar_pdf_recibo(ser, num, pad, nom, fec, items, recibo_id=lid)
                    print(f"<<< DESPUES de llamar _generar_pdf_recibo: pdf_file={pdf_file}\n")
                    flash('Recibo registrado.', 'success')
                    return render_template('crear_recibo_s6.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar', pdf_file=pdf_file)
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
    return render_template('crear_recibo_s6.html', act='-', fec=datetime.datetime.now().strftime('%Y-%m-%d'), pad=0, com='', nom='', but='Continuar')


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
            consulta = sqlconstants.DETALLE_SERIE_3X
            consulta = consulta.replace("$serie$", ser)
            consulta = consulta.replace("$pad$", pad)
            cursor.execute(consulta)
            items = cursor.fetchall()
            cursor.close()
            # Saldo pendiente de combustible del padrón; se precarga en el aporte COBRO.COMB.
            saldo_comb = _saldo_cobro_comb(connection, pad)
            for it in items:
                if it['codigo'] == 'COBRO.COMB':
                    it['monto'] = saldo_comb
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
                    return render_template('crear_recibo_s5.html', act=act, fec=fec, pad=pad, com=com, nom=nom, but='Registrar', items=items, lid=lid, num=num, saldo=saldo_comb)
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
                    for idx, i0 in enumerate(items):
                        lin += 1
                        mnt = request.form.get(f"monto_{idx}")
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        i0['monto'] = Decimal(str(mnt0))
                        if mnt and mnt0 > 0:
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
                    print(f"\n>>> ANTES de llamar _generar_pdf_recibo: lid={lid}, ser={ser}, num={num}")
                    pdf_file = _generar_pdf_recibo(ser, num, pad, nom, fec, items, recibo_id=lid)
                    print(f"<<< DESPUES de llamar _generar_pdf_recibo: pdf_file={pdf_file}\n")
                    flash('Recibo registrado.', 'success')
                    return render_template('crear_recibo_s5.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar', pdf_file=pdf_file)
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
    return render_template('crear_recibo_s5.html', act='-', fec=datetime.datetime.now().strftime('%Y-%m-%d'), pad=0, com='', nom='', but='Continuar')


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
            consulta = sqlconstants.DETALLE_SERIE_3X
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
                    for idx, i0 in enumerate(items):
                        lin += 1
                        mnt = request.form.get(f"monto_{idx}")
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        i0['monto'] = Decimal(str(mnt0))
                        if mnt and mnt0 > 0:
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
                    print(f"\n>>> ANTES de llamar _generar_pdf_recibo: lid={lid}, ser={ser}, num={num}")
                    pdf_file = _generar_pdf_recibo(ser, num, pad, nom, fec, items, recibo_id=lid)
                    print(f"<<< DESPUES de llamar _generar_pdf_recibo: pdf_file={pdf_file}\n")
                    flash('Recibo registrado.', 'success')
                    return render_template('crear_recibo_s4.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar', pdf_file=pdf_file)
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
    return render_template('crear_recibo_s4.html', act='-', fec=datetime.datetime.now().strftime('%Y-%m-%d'), pad=0, com='', nom='', but='Continuar')


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
            consulta = sqlconstants.DETALLE_SERIE_3X
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
                    for idx, i0 in enumerate(items):
                        lin += 1
                        mnt = request.form.get(f"monto_{idx}")
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        i0['monto'] = Decimal(str(mnt0))
                        if mnt and mnt0 > 0:
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
                    print(f"\n>>> ANTES de llamar _generar_pdf_recibo: lid={lid}, ser={ser}, num={num}")
                    pdf_file = _generar_pdf_recibo(ser, num, pad, nom, fec, items, recibo_id=lid)
                    print(f"<<< DESPUES de llamar _generar_pdf_recibo: pdf_file={pdf_file}\n")
                    flash('Recibo registrado.', 'success')
                    return render_template('crear_recibo_s3.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar', pdf_file=pdf_file)
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
    return render_template('crear_recibo_s3.html', act='-', fec=datetime.datetime.now().strftime('%Y-%m-%d'), pad=0, com='', nom='', but='Continuar')


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
            consulta = sqlconstants.DETALLE_SERIE_2x
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
                    for idx, i0 in enumerate(items):
                        lin += 1
                        mnt = request.form.get(f"monto_{idx}")
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        i0['monto'] = Decimal(str(mnt0))
                        if mnt and mnt0 > 0:
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
                                # invocar al SP para q ponga como "pagado" el prestamo si el saldo pendiente es 0 
                                quer6 = "CALL b2p.actPrestamoFinal($deu$)"
                                quer6 = quer6.replace("$deu$", str(deu))
                                cursor.execute(quer6)

                    query9 = sqlconstants.UPDATE_RECIBO_X
                    query9 = query9.replace("$recibo$",lid)
                    cursor.execute(query9)
                    connection.commit()
                    cursor.close()
                    connection.close()
                    print(f"\n>>> ANTES de llamar _generar_pdf_recibo: lid={lid}, ser={ser}, num={num}")
                    pdf_file = _generar_pdf_recibo(ser, num, pad, nom, fec, items, recibo_id=lid)
                    print(f"<<< DESPUES de llamar _generar_pdf_recibo: pdf_file={pdf_file}\n")
                    flash('Recibo registrado.', 'success')
                    return render_template('crear_recibo_s2.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar', pdf_file=pdf_file)
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
    return render_template('crear_recibo_s2.html', act='-', fec=datetime.datetime.now().strftime('%Y-%m-%d'), pad=0, com='', nom='', but='Continuar')


@recibos_bp.route('/verificar_recibo_s2', methods=['POST'])
@login_required
def verificar_recibo_s2():
    fecha = request.form.get('fecha')
    padron = request.form.get('padron')

    if not fecha or not padron:
        return jsonify({'existe': False})

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT id, active FROM a_recibos WHERE serie = '2' AND DATE(giro) = %s AND padron = %s"
        cursor.execute(query, (fecha, padron))
        resultado = cursor.fetchone()
        cursor.close()
        connection.close()

        if resultado:
            # Si existe y está activo (girado)
            if resultado.get('active') == 'S':
                return jsonify({'existe': True})
            else:
                return jsonify({'existe': False})
        else:
            return jsonify({'existe': False})
    else:
        return jsonify({'existe': False, 'error': 'Conexión fallida'})


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
                    for idx, i0 in enumerate(items):
                        lin += 1
                        mnt = request.form.get(f"monto_{idx}")
                        if (not mnt):
                            mnt = "0"
                        mnt0 = float(mnt)
                        i0['monto'] = Decimal(str(mnt0))
                        if mnt and mnt0 > 0:
                            query = sqlconstants.INSERT_DETREC_X
                            query = query.replace("$apo$", i0['codigo'])
                            query = query.replace("$rec$", lid)
                            query = query.replace("$mnt$", mnt)
#                            query = query.replace("$pre$", str(i0['prestamo']))
#                            query = query.replace("$tip$", str(i0['tipodeuda']))
                            query = query.replace("$pre$", '0')
                            query = query.replace("$tip$", '')
                            query = query.replace("$usr$", session['user_username'])
                            cursor = connection.cursor()
                            cursor.execute(query)
#                            deu = i0['prestamo']
#                            if deu > 0:
#                                quer0 = "UPDATE a_prestamos SET saldo_pendiente=saldo_pendiente-$mnt$ WHERE id='$pre$'"
#                                quer0 = quer0.replace("$pre$", str(deu))
#                                quer0 = quer0.replace("$mnt$", str(mnt))
#                                cursor.execute(quer0)
                    query9 = sqlconstants.UPDATE_RECIBO_X
                    query9 = query9.replace("$recibo$",lid)
                    cursor = connection.cursor()
                    cursor.execute(query9)
                    connection.commit()
                    cursor.close()

                    # Obtener items nuevamente con los montos editados desde la BD
                    conn_refresh = get_db_connection()
                    if conn_refresh:
                        cursor_refresh = conn_refresh.cursor(dictionary=True)
                        query_refresh = sqlconstants.SELECT_DETALLEX
                        query_refresh = query_refresh.replace("$pX$", lid)
                        cursor_refresh.execute(query_refresh)
                        items = cursor_refresh.fetchall()
                        cursor_refresh.close()
                        conn_refresh.close()

                    connection.close()
                    print(f"\n>>> ANTES de llamar _generar_pdf_recibo: lid={lid}, ser={ser}, num={num}")
                    pdf_file = _generar_pdf_recibo(ser, num, pad, nom, fec, items, recibo_id=lid)
                    print(f"<<< DESPUES de llamar _generar_pdf_recibo: pdf_file={pdf_file}\n")
                    flash('Recibo registrado.', 'success')
                    return render_template('crear_recibo.html', act='-', fec=fec, pad=0, com='', nom='', but='Continuar', pdf_file=pdf_file)
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
    return render_template('crear_recibo.html', act='-', fec=datetime.datetime.now().strftime('%Y-%m-%d'), pad=0, com='', nom='', but='Continuar')
