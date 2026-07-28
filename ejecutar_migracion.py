#!/usr/bin/env python3
"""
Script para ejecutar migraciones SQL en la base de datos.
"""

import mysql.connector
from config import Config
import os

def ejecutar_migracion():
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
            port=Config.MYSQL_PORT
        )

        cursor = connection.cursor()

        # Leer y ejecutar el archivo de migración
        ruta_migracion = '/Users/selynchavez/Documents/GitHub/Python_LF/migrations/001_alter_facturacion_sustento.sql'

        with open(ruta_migracion, 'r') as archivo:
            sql = archivo.read()

        print("Ejecutando migración:")
        print(sql)
        print("\n" + "="*60)

        cursor.execute(sql)
        connection.commit()

        print("✅ Migración ejecutada exitosamente")
        print("La columna 'sustento' ha sido cambiada de BLOB a LONGBLOB")

        cursor.close()
        connection.close()

    except mysql.connector.Error as err:
        print(f"❌ Error en la base de datos: {err}")
    except FileNotFoundError:
        print(f"❌ Archivo de migración no encontrado")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    ejecutar_migracion()
