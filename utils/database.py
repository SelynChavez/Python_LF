from flask import current_app
from mysql.connector import Error
import hashlib


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


def get_nombre_padron(pad):
    nombre_default = ''
    connection1 = get_db_connection()
    if connection1:
        cursor = connection1.cursor(dictionary=True)
        import sqlconstants
        cursor.execute(sqlconstants.GET_NOMBRE_PADRON, (pad,))
        reg0 = cursor.fetchone()
        if reg0:
            nombre_default = reg0['n0']
        cursor.close()
        connection1.close()
    return nombre_default
