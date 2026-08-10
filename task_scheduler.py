from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

scheduler = BackgroundScheduler()
logger = logging.getLogger(__name__)


def ejecutar_tarea_programada(tarea_id):
    """Ejecuta una tarea programada y registra el resultado"""
    from app import app
    from utils.database import get_db_connection
    import sqlconstants

    with app.app_context():
        connection = get_db_connection()
        if not connection:
            logger.error(f"No se pudo conectar a la BD para tarea {tarea_id}")
            return

        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(sqlconstants.OBTENER_PROGRAMA_TAREA, (tarea_id,))
            tarea = cursor.fetchone()

            if not tarea:
                logger.warning(f"Tarea {tarea_id} no encontrada")
                return

            if tarea['activo'] != 'S':
                logger.info(f"Tarea {tarea_id} inactiva, saltando")
                return

            # Ejecutar tarea
            inicio = datetime.now()
            estado = 'EXITOSO'
            registros_afectados = 0
            mensaje_error = None

            try:
                task_cursor = connection.cursor()
                task_cursor.execute(tarea['sql_query'])
                registros_afectados = task_cursor.rowcount
                connection.commit()
                task_cursor.close()
                logger.info(f"Tarea {tarea_id} ejecutada: {registros_afectados} registros afectados")
            except Exception as e:
                estado = 'ERROR'
                mensaje_error = str(e)
                connection.rollback()
                logger.error(f"Error en tarea {tarea_id}: {mensaje_error}")

            # Registrar ejecución
            fin = datetime.now()
            duracion_segundos = int((fin - inicio).total_seconds())

            try:
                reg_cursor = connection.cursor()
                reg_cursor.execute("""
                    INSERT INTO a_ejecuciones_tareas
                    (tarea_id, fecha_inicio, fecha_fin, duracion_segundos, estado, registros_afectados, mensaje_error)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (tarea_id, inicio, fin, duracion_segundos, estado, registros_afectados, mensaje_error))
                connection.commit()
                reg_cursor.close()
            except Exception as e:
                logger.error(f"Error al registrar ejecución de tarea {tarea_id}: {str(e)}")

        except Exception as e:
            logger.error(f"Error procesando tarea {tarea_id}: {str(e)}")
        finally:
            cursor.close()
            connection.close()


def agendar_tarea(tarea):
    """Agrega una tarea al scheduler basado en su configuración"""
    tarea_id = tarea['id']
    hora = tarea['hora_ejecucion']
    dias = tarea['dias_semana']

    if not hora:
        logger.warning(f"Tarea {tarea_id} sin hora de ejecución, no se agenda")
        return

    # Remover job anterior si existe
    try:
        scheduler.remove_job(f"tarea_{tarea_id}")
    except:
        pass

    try:
        # Convertir hora a horas y minutos
        hora_parts = str(hora).split(':')
        hour = int(hora_parts[0])
        minute = int(hora_parts[1]) if len(hora_parts) > 1 else 0

        # Configurar trigger según los días
        if dias and dias.strip():
            # Días específicos: "Lun,Mar,Mié,Jue,Vie"
            dias_abbr = {
                'Lun': 'mon', 'Mon': 'mon',
                'Mar': 'tue', 'Martes': 'tue',
                'Mié': 'wed', 'Miércoles': 'wed',
                'Jue': 'thu', 'Jueves': 'thu',
                'Vie': 'fri', 'Viernes': 'fri',
                'Sáb': 'sat', 'Sábado': 'sat',
                'Dom': 'sun', 'Domingo': 'sun'
            }

            dias_lista = [d.strip() for d in dias.split(',')]
            dias_cron = []
            for dia in dias_lista:
                dias_cron.append(dias_abbr.get(dia, dia.lower()))

            trigger = CronTrigger(
                day_of_week=','.join(dias_cron),
                hour=hour,
                minute=minute
            )
            logger.info(f"Tarea {tarea_id}: {','.join(dias_cron)} a las {hour:02d}:{minute:02d}")
        else:
            # Todos los días
            trigger = CronTrigger(hour=hour, minute=minute)
            logger.info(f"Tarea {tarea_id}: Todos los días a las {hour:02d}:{minute:02d}")

        scheduler.add_job(
            ejecutar_tarea_programada,
            trigger=trigger,
            args=[tarea_id],
            id=f"tarea_{tarea_id}",
            name=f"Tarea: {tarea['nombre']}",
            replace_existing=True
        )
    except Exception as e:
        logger.error(f"Error agendando tarea {tarea_id}: {str(e)}")


def cargar_tareas_al_iniciar(app):
    """Carga todas las tareas activas al iniciar la aplicación"""
    from utils.database import get_db_connection
    import sqlconstants

    with app.app_context():
        connection = get_db_connection()
        if not connection:
            logger.error("No se pudo conectar a la BD para cargar tareas")
            return

        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM a_programas_tareas WHERE activo = 'S'")
            tareas = cursor.fetchall()
            logger.info(f"Cargando {len(tareas)} tareas activas")
            for tarea in tareas:
                agendar_tarea(tarea)
        except Exception as e:
            logger.error(f"Error cargando tareas: {str(e)}")
        finally:
            cursor.close()
            connection.close()


def iniciar_scheduler(app):
    """Inicia el scheduler de fondo"""
    if not scheduler.running:
        scheduler.start()
        cargar_tareas_al_iniciar(app)
        logger.info("Task Scheduler iniciado")
