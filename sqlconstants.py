REP1APORTES = """
  SELECT
    CONCAT('0',serie,'-',LPAD(id,6,'0')) d1,
    dateDMY(fecha) d2,
    dateDMY(giro) d3,
    if(fecha>giro,'ATRAZADO',if(fecha<giro,'ADELANTO','NORMAL')) d4,
    (SELECT CONCAT(p.id,':',p.placa,':',s.nombre) FROM a_padrones p, a_socios s WHERE p.socio=s.id AND v.padron=p.id) d6,
    concat(round((SELECT SUM(monto) FROM a_recibos_detalle d WHERE d.recibo=v.id),2),'') d7,
    v.active d8,
    upper(substr(v.webuser,1,10)) d9,
    concat(v.id) d10,
    '0' d0 
    FROM a_recibos v 
    WHERE serie='1' and v.fecha>=date('$p1$') and v.fecha<=date('$p2$') and 
        (v.padron='$p3$' or '0'='$p3$') and 
        (v.active='S') 
    ORDER BY v.fecha, v.padron, v.id 
    LIMIT 1000
    """
REP2APORTES = """
  SELECT 
    CONCAT('0',v.serie,'-',LPAD(v.id,6,'0')) d1,
    dateDMY(v.giro) d2,
    IF(v.padron IS NULL,LPAD(v.socio,4,'0'),LPAD(v.padron,4,'0')) d3,
    (SELECT CONCAT(p.id,':',p.placa,':',s.nombre) FROM a_padrones p, a_socios s WHERE p.socio=s.id AND v.padron=p.id) d4,
    IF(fecha>giro,'ATRAZADO',IF(fecha<giro,'ADELANTADO','NORMAL')) d5,
    IFNULL(IF(v.serie='7',CONCAT(v.moneda,' T.C=',v.tc),v.comentarios),'') d6,
    concat(round(IF(serie='7',IF(moneda='DOLARES',vd.monto*IFNULL(v.tc,1),vd.monto),IFNULL(vd.monto,0)),2),'') d7
  FROM a_recibos_detalle vd, a_recibos v 
  WHERE v.serie in ('1') AND v.id=vd.recibo AND (v.fecha>='$p1$' AND v.fecha<='$p2$') AND 
    ((socio IS NOT NULL AND ('$p3$'='0' OR socio='$p3$')) OR (padron IS NOT NULL AND ('$p3$'='0' OR padron='$p3$'))) AND 
    (vd.aporte = '$p4$') AND 
    (v.active='S') 
   ORDER BY 2, 1 DESC
"""

QRY1USUARIOS = """
  SELECT id, username, fullname, email, roles, 
          DATE_FORMAT(modified, '%%d/%%m/%%Y %%H:%%i') as modified, 
          status 
  FROM applicationuser 
  WHERE username LIKE %s OR fullname LIKE %s OR email LIKE %s
  ORDER BY modified DESC
"""
LISTA_USUARIOS = "SELECT * FROM applicationuser ORDER BY modified DESC "
INSERT_USUARIO = "INSERT INTO applicationuser (username, password, fullname, email, roles, status, modified) VALUES (%s, %s, %s, %s, %s, 'ACTIVE', now())"
UPDAT1_USUARIO = "UPDATE applicationuser SET username = %s, fullname = %s, email = %s, roles = %s, status = %s, password = %s WHERE id = %s "
UPDAT2_USUARIO = "UPDATE applicationuser SET username = %s, fullname = %s, email = %s, roles = %s, status = %s WHERE id = %s "
SELECT_USUARIO = "SELECT * FROM applicationuser WHERE id = %s"
SEL_NM_USUARIO = "SELECT username FROM applicationuser WHERE id = %s"
DELETE_USUARIO = "DELETE FROM applicationuser WHERE id = %s"

QRY1SOCIOS = """
  SELECT id, nombre, dni, tipo, fono, DATE_FORMAT(modified, '%%d/%%m/%%Y %%H:%%i') as modified, active 
  FROM a_socios
  WHERE nombre LIKE %s OR dni LIKE %s OR tipo LIKE %s
  ORDER BY modified DESC
"""
LISTA_SOCIOS = "SELECT * FROM a_socios ORDER BY modified DESC "
INSERT_SOCIO = "INSERT INTO a_socios (nombre, fono, dni, comentarios, tipo, active, modified, webuser) VALUES (%s, %s, %s, %s, %s, 'S', now(), %s)"
UPDATE_SOCIO = "UPDATE a_socios SET nombre=%s, fono=%s, dni=%s, comentarios=%s, tipo=%s, active=%s, modified=now() WHERE id=%s "
SELECT_SOCIO = "SELECT * FROM a_socios WHERE id = %s"
SEL_NM_SOCIO = "SELECT nombre FROM a_socios WHERE id = %s"
DELETE_SOCIO = "DELETE FROM a_socios WHERE id = %s"

QRY1PADRONES = """
  SELECT id, placa, socio, active, monto1, DATE_FORMAT(modified, '%%d/%%m/%%Y %%H:%%i') as modified,
  (SELECT s.nombre FROM a_socios s WHERE s.id=p.socio) nombresocio 
  FROM a_padrones p
  WHERE placa LIKE %s OR socio LIKE %s 
  ORDER BY p.modified DESC
"""
LISTA_PADRONES = "SELECT p.*,(SELECT s.nombre FROM a_socios s WHERE s.id=p.socio) nombresocio FROM a_padrones p ORDER BY p.modified DESC "
INSERT_PADRON = "INSERT INTO a_padrones (placa, socio, active, monto1, monto2, monto3, monto4, modified, webuser) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), %s)"
UPDATE_PADRON = "UPDATE a_padrones SET placa=%s, socio=%s, active=%s, monto1=%s, monto2=%s, monto3=%s, monto4=%s, modified=now() WHERE id=%s "
SELECT_PADRON = "SELECT p.*,(SELECT s.nombre FROM a_socios s WHERE s.id=p.socio) nombresocio FROM a_padrones p WHERE p.id = %s"
SEL_NM_PADRON = "SELECT placa FROM a_padrones WHERE id = %s"
DELETE_PADRON = "DELETE FROM a_padrones WHERE id = %s"
GET_NOMBRE_PADRON = "SELECT concat(p.id,':',p.placa,':',s.nombre) as n0 FROM a_padrones p, a_socios s WHERE p.id=%s and p.socio=s.id "


DROPLIST_APORTES = "SELECT codigo d1,concat(codigo,':',descripcion) d2 FROM nlf_tipos WHERE tipo='APORTE' "
INSERT_LOGUSUARIO = "INSERT INTO logs_usuarios (usuario_id, accion, descripcion) VALUES (%s, %s, %s)"

INSERT_RECIBO_1 = "INSERT INTO a_recibos (serie, fecha, giro, padron, comentarios, active, modified, webuser) VALUES ('1', now(), %s, %s, %s, %s, now(), %s)"
UPDATE_RECIBO_1 = "UPDATE a_recibos SET active='S' WHERE id='$recibo$'"
INSERT_DETREC_1 = "INSERT INTO a_recibos_detalle (aporte, recibo, monto, prestamo, tipodeuda, modified, webuser) VALUES ('$apo$', '$rec$', '$mnt$', '$pre$', '$tip$', now(), '$usr$')"
DETALLE_SERIE_1 = """
  SELECT t.codigo,t.descripcion,
  (CASE
      WHEN t.codigo='APCAPITAL'   THEN p.monto1
      WHEN t.codigo='APAHORRO'    THEN p.monto2
      WHEN t.codigo='APAPORTE'    THEN p.monto3
      WHEN t.codigo='APSEGURO'    THEN p.monto4
      ELSE t.monto1
  END) monto, 0 prestamo, '' tipodeuda, t.id idx0
  FROM a_tipos t left outer join a_padrones p on t.tipo='APORTE' and p.id='$pad$'
  WHERE t.tipo='APORTE' and t.atributo2='I' and (t.codigo not in ('DEUDA','INICIAL'))
"""
