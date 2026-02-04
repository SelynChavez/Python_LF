REP1APORTES = """
  SELECT
    CONCAT('0',serie,'-',LPAD(numero,6,'0')) d1,
    dateDMY(fecha) d2,
    dateDMY(giro) d3,
    if(fecha>giro,'ATRAZADO',if(fecha<giro,'ADELANTO','NORMAL')) d4,
    (SELECT CONCAT(p.id,':',p.placa,':',s.nombre) FROM a_padrones p, a_socios s WHERE p.socio=a.id AND v.padron=p.id) d6,
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
    CONCAT('0',v.serie,'-',LPAD(v.numero,6,'0')) d1,
    dateDMY(v.giro) d2,
    IF(v.padron IS NULL,LPAD(v.socio,4,'0'),LPAD(v.padron,4,'0')) d3,
    (SELECT CONCAT(p.id,':',p.placa,':',s.nombre) FROM a_padrones p, a_socios s WHERE p.socio=a.id AND v.padron=p.id) d4,
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
DROPLIST_APORTES = "SELECT codigo d1,concat(codigo,':',descripcion) d2 FROM nlf_tipos WHERE tipo='APORTE' "
LISTA_USUARIOS = "SELECT * FROM applicationuser ORDER BY modified DESC "
LISTA_SOCIOS = "SELECT * FROM a_socios ORDER BY modified DESC "
QRY1USUARIOS = """
  SELECT id, username, fullname, email, roles, 
          DATE_FORMAT(modified, '%%d/%%m/%%Y %%H:%%i') as modified, 
          status 
  FROM applicationuser 
  WHERE username LIKE %s OR fullname LIKE %s OR email LIKE %s
  ORDER BY modified DESC
"""
QRY1SOCIOS = """
  SELECT id, nombre, dni, tipo, fono, DATE_FORMAT(modified, '%%d/%%m/%%Y %%H:%%i') as modified, active 
  FROM a_socios
  WHERE nombre LIKE %s OR dni LIKE %s OR tipo LIKE %s
  ORDER BY modified DESC
"""

INSERT_LOGUSUARIO = "INSERT INTO logs_usuarios (usuario_id, accion, descripcion) VALUES (%s, %s, %s)"
REP1APORTES_F2 = """
  SELECT
    CONCAT('0',serie,'-',LPAD(v.`number`,6,'0')) d1,
    dateDMY(dated) d2,
    dateDMY(effective) d3,
    if(dated>effective,'ATRAZADO',if(dated<effective,'ADELANTO','NORMAL')) d4,
    -- (select substr(i.completo,1,35) from v_nlf_sociopadron i where i.id=v.padron) d6,
    concat(round((SELECT SUM(amount) FROM f2_recibos_detalle d WHERE d.voucher=v.id),2),'') d7,
    v.active d8,
    upper(substr(v.webuser,1,10)) d9,
    concat(v.id) d10,
    '0' d0 
    FROM f2_recibos v 
    WHERE serie='1' and v.dated>=date('$p1$') and v.dated<=date('$p2$') and 
        (v.instance='$p3$' or '0'='$p3$') and 
        (v.active='S') 
    ORDER BY v.dated, v.instance, v.id 
    LIMIT 1000
    """