import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-muy-segura-para-desarrollo'
    
    # Configuración MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or '161.132.40.175'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'b2p8'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'b2p8i'
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE') or 'b2p'
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)