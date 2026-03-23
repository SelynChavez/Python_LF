from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, make_response
import mysql.connector
from mysql.connector import Error
import os
from config import Config
import sqlconstants
from werkzeug.utils import secure_filename
from io import BytesIO
import base64
import datetime
from decimal import Decimal
from time import time
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

app = Flask(__name__)
app.config.from_object(Config)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_password(password):
    return password.encode()

# Registrar Blueprints
from routes import (
    auth_bp, contabilidad_bp, configuracion_bp, 
    reportes_bp, io_cash_bp, combustibles_bp,
    productos_bp, dashboard_bp, aportes_bp,
    prestamos_bp, retiros_bp, recibos_bp
)

app.register_blueprint(auth_bp)
app.register_blueprint(contabilidad_bp)
app.register_blueprint(configuracion_bp)
app.register_blueprint(reportes_bp)
app.register_blueprint(io_cash_bp)
app.register_blueprint(combustibles_bp)
app.register_blueprint(productos_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(aportes_bp)
app.register_blueprint(prestamos_bp)
app.register_blueprint(retiros_bp)
app.register_blueprint(recibos_bp)

# ==================== RUTAS DE API ====================
@app.route('/api/usuarios')
def api_usuarios():
    from utils.database import get_db_connection
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
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

@app.route('/api/padron/<int:padron_id>/saldo')
def api_padron_saldo(padron_id):
    from utils.database import get_db_connection
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT monto0 FROM a_padrones WHERE id = %s", (padron_id,))
        result = cursor.fetchone()
    conn.close()    
    if result:
        return jsonify({'saldo': float(result['monto0'])})
    return jsonify({'error': 'Padrón no encontrado'}), 404

# ==================== RUTA RAÍZ ====================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('auth.login'))

@app.route('/imprimir_recibo/<int:l_id>', methods=['GET', 'POST'])
def imprimir_recibo(l_id):
    from routes.reportes_routes import generar_recibo
    from utils.database import get_db_connection
    
    lid = str(l_id)
    if request.method == 'GET':
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            queryHead = sqlconstants.SELECT_RECIBO_X
            queryHead = queryHead.replace("$pX$", lid)
            cursor.execute(queryHead)
            recibo = cursor.fetchone()
            fec = recibo['fecha']
            date_format = '%Y-%m-%d'
            date_obj = datetime.datetime.strptime(recibo['fec'], date_format)
            fec = date_obj.strftime('%d-%m-%Y')
            date_obj = datetime.datetime.strptime(recibo['gir'], date_format)
            gir = date_obj.strftime('%d-%m-%Y')
            consulta = sqlconstants.SELECT_DETALLEX
            consulta = consulta.replace("$pX$", lid)
            cursor.execute(consulta)
            items = cursor.fetchall()
            titulo = 'RECIBO DE PAGO'
            if (recibo['serie']=='1'):
                titulo = 'RECIBO DE INGRESO'
            if (recibo['serie']=='2'):
                titulo = 'BOLETA ELECTRONICA'
            archivo = generar_recibo(titulo, recibo['serie'], recibo['numero'], recibo['padron'], recibo['nombre'], fec, gir, items)
            print(f"Recibo guardado en: {os.path.abspath(archivo)}")
            try:
                with open(archivo, 'rb') as archivobin:
                    pdf_buffer = archivobin.read()
                    pdf_base64 = base64.b64encode(pdf_buffer).decode('utf-8')
                    return render_template('mostrar_pdf.html', pdf_data=pdf_base64, cod='Recibo')    
            except FileNotFoundError:
                print("El archivo no existe.")
    return render_template('menurecibos.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
