from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from functools import wraps
from flask import current_app
from mysql.connector import Error
import sqlconstants
import datetime
from .auth import bp as auth_bp

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

def hash_password(password):
    return password.encode()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
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
                session['login_time'] = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                connection = get_db_connection()
                if connection:
                    cursor = connection.cursor()
                    cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (user['id'], 'login', 'Inicio de sesión exitoso'))
                    connection.commit()
                    cursor.close()
                    connection.close()
                flash(f'Bienvenido, {user["fullname"]}!', 'success')
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('Usuario o contraseña incorrectos.', 'danger')
        else:
            flash('Error de conexión a la base de datos.', 'danger')
    return render_template('login.html')


@auth_bp.route('/cambiar-contrasena', methods=['GET', 'POST'])
@login_required
def cambiar_contrasena():
    if request.method == 'GET':
        return render_template('cambiar_contrasena.html')

    if request.method == 'POST':
        password_actual = request.form.get('password_actual')
        password_nuevo = request.form.get('password_nuevo')
        password_confirmar = request.form.get('password_confirmar')

        if not password_actual or not password_nuevo or not password_confirmar:
            flash('Por favor, complete todos los campos.', 'danger')
            return render_template('cambiar_contrasena.html')

        if len(password_nuevo) < 6:
            flash('La contraseña debe tener mínimo 6 caracteres.', 'danger')
            return render_template('cambiar_contrasena.html')

        if password_nuevo != password_confirmar:
            flash('Las contraseñas nuevas no coinciden.', 'danger')
            return render_template('cambiar_contrasena.html')

        connection = get_db_connection()
        if not connection:
            flash('Error de conexión a la base de datos.', 'danger')
            return render_template('cambiar_contrasena.html')

        cursor = connection.cursor(dictionary=True)
        try:
            hashed_password_actual = hash_password(password_actual)
            query = "SELECT * FROM applicationuser WHERE id = %s AND password = %s"
            cursor.execute(query, (session['user_id'], hashed_password_actual))
            user = cursor.fetchone()

            if not user:
                flash('Contraseña actual incorrecta.', 'danger')
                cursor.close()
                connection.close()
                return render_template('cambiar_contrasena.html')

            hashed_password_nuevo = hash_password(password_nuevo)
            update_query = "UPDATE applicationuser SET password = %s WHERE id = %s"
            cursor.execute(update_query, (hashed_password_nuevo, session['user_id']))
            connection.commit()

            cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'cambio_contrasena', 'Cambio de contraseña exitoso'))
            connection.commit()

            flash('Contraseña cambiada correctamente.', 'success')
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard.dashboard'))
        except Error as err:
            connection.rollback()
            flash(f'Error al cambiar la contraseña: {err}', 'danger')
            cursor.close()
            connection.close()
            return render_template('cambiar_contrasena.html')


@auth_bp.route('/logout')
def logout():
    if 'user_id' in session:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute(sqlconstants.INSERT_LOGUSUARIO, (session['user_id'], 'logout', 'Cierre de sesión'))
            connection.commit()
            cursor.close()
            connection.close()
    session.clear()
    flash('Ha cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))
