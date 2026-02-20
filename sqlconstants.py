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
    concat(v.padron) d11,
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

LISTA_SOCIOS = "SELECT * FROM a_socios ORDER BY modified DESC "
INSERT_SOCIO = "INSERT INTO a_socios (nombre, fono, dni, comentarios, tipo, email, active, modified, webuser) VALUES (%s, %s, %s, %s, %s, %s, 'S', now(), %s)"
UPDATE_SOCIO = "UPDATE a_socios SET nombre=%s, fono=%s, dni=%s, comentarios=%s, tipo=%s, active=%s, email=%s, modified=now() WHERE id=%s "
SELECT_SOCIO = "SELECT * FROM a_socios WHERE id = %s"
SEL_NM_SOCIO = "SELECT nombre FROM a_socios WHERE id = %s"
DELETE_SOCIO = "DELETE FROM a_socios WHERE id = %s"

LISTA_PADRONES = "SELECT p.*,(SELECT s.nombre FROM a_socios s WHERE s.id=p.socio) nombresocio FROM a_padrones p ORDER BY p.modified DESC "
INSERT_PADRON = "INSERT INTO a_padrones (placa, socio, active, monto1, monto2, monto3, monto4, modified, webuser) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), %s)"
UPDATE_PADRON = "UPDATE a_padrones SET placa=%s, socio=%s, active=%s, monto1=%s, monto2=%s, monto3=%s, monto4=%s, modified=now() WHERE id=%s "
SELECT_PADRON = "SELECT p.*,(SELECT s.nombre FROM a_socios s WHERE s.id=p.socio) nombresocio FROM a_padrones p WHERE p.id = %s"
SEL_NM_PADRON = "SELECT placa FROM a_padrones WHERE id = %s"
DELETE_PADRON = "DELETE FROM a_padrones WHERE id = %s"
GET_NOMBRE_PADRON = "SELECT concat(p.id,':',p.placa,':',s.nombre) as n0 FROM a_padrones p, a_socios s WHERE p.id=%s and p.socio=s.id "

LISTA_TIPOS = "SELECT t.*,concat('S00',atributo1) serie FROM a_tipos t WHERE t.tipo=%s ORDER BY t.modified DESC "
INSERT_TIPO = "INSERT INTO a_tipos (tipo, codigo, descripcion, monto1, monto2, atributo1, atributo2, atributo3, atributo4, atributo5, modified, webuser) VALUES (%s, %s, %s, '0','0','','','','','', now(), %s)"
UPDATE_TIPO = "UPDATE a_tipos SET codigo=%s, descripcion=%s, monto1=%s,monto2=%s,atributo1=%s,atributo2=%s,atributo3=%s,atributo4=%s,atributo5=%s, modified=now() WHERE id=%s "
SELECT_TIPO = "SELECT t.* FROM a_tipos t WHERE t.id = %s"
SEL_NM_TIPO = "SELECT tipo,codigo FROM a_tipos WHERE id = %s"
DELETE_TIPO = "DELETE FROM a_tipos WHERE id = %s"

DROPLIST_APORTES = "SELECT codigo d1,concat(codigo,':',descripcion) d2 FROM nlf_tipos WHERE tipo='APORTE' "
INSERT_LOGUSUARIO = "INSERT INTO logs_usuarios (usuario_id, accion, descripcion) VALUES (%s, %s, %s)"

INSERT_RECIBO_1 = "INSERT INTO a_recibos (serie, fecha, giro, padron, comentarios, active, modified, webuser) VALUES ('1', now(), %s, %s, %s, %s, now(), %s)"
UPDATE_RECIBO_1 = "UPDATE a_recibos SET active='S' WHERE id='$recibo$'"
INSERT_DETREC_1 = "INSERT INTO a_recibos_detalle (aporte, recibo, monto, prestamo, tipodeuda, modified, webuser) VALUES ('$apo$', '$rec$', '$mnt$', '$pre$', '$tip$', now(), '$usr$')"
SELECT_RECIBO_1 = "SELECT r.*,nombPadronSocio(r.padron) nombre, concat(fecha) fec, concat(giro) gir FROM a_recibos r WHERE r.id='$pX$'"
SELECT_DETALLE1 = "SELECT rd.*,tt.codigo,tt.descripcion FROM a_recibos_detalle rd, a_tipos tt WHERE recibo='$pX$' AND tt.tipo='APORTE' AND tt.codigo=rd.aporte ORDER BY rd.id"
DETALLE_SERIE_1 = """
SELECT t.codigo,t.descripcion,
  COALESCE((CASE
      WHEN t.codigo='CP.TRABAJO' THEN p.monto1
      WHEN t.codigo='APAHORRO'   THEN p.monto2
      WHEN t.codigo='APAPORTE'   THEN p.monto3
      ELSE t.monto1
  END),0) monto, 0 prestamo, '' tipodeuda, t.id idx0
FROM a_tipos t left outer join a_padrones p on t.tipo='APORTE' and p.id='$pad$'
WHERE t.tipo='APORTE' and t.atributo1='1' and (t.codigo not in ('PRESTAMO','INICIAL'))
UNION ALL
SELECT t.codigo,t.descripcion,p.cuota monto,p.id prestamo,p.tipo_prestamo tipodeuda,t.id idx 
FROM a_prestamos p,a_tipos t 
WHERE p.padron='$pad$' and p.estado='aprobado' and t.tipo='APORTE' and t.codigo='PRESTAMO'
"""
DASHB_COMB_TOTAL_HOY = """
SELECT COALESCE(SUM(galones_vendidos), 0) as total_gallons,
       COALESCE(SUM(total_precio), 0) as total_revenue,
       COUNT(DISTINCT maquina) as active_machines
FROM a_ventas_comb WHERE DATE(fecha) = CURDATE()
"""
DASHB_COMB_TURNOS_HOY = """
SELECT nombre as shift_name, SUM(galones_vendidos) as gallons, SUM(total_precio) as revenue
FROM a_ventas_comb WHERE DATE(fecha) = CURDATE() GROUP BY nombre, turno
ORDER BY FIELD(turno, 'TURNO_1', 'TURNO_2', 'TURNO_3')
"""
DASHB_COMB_TOP_MAQUINAS = '''
SELECT m.id, m.numero machine_number, f.nombre fuel_type, COALESCE(SUM(s.galones_vendidos), 0) gallons, 
       COALESCE(SUM(s.total_precio), 0) revenue
FROM a_maquinas m
  LEFT JOIN a_combustible f ON m.tipo_combustible = f.id
  LEFT JOIN a_ventas_comb s ON m.id = s.maquina AND DATE(s.fecha) = CURDATE()
GROUP BY m.id
ORDER BY gallons DESC
LIMIT 5
'''
DASHB_COMB_STOCK_CRITICO = """
SELECT m.id, m.numero as machine_number, f.nombre as fuel_type, f.nombre as fuel_name, m.disponible_stock stock_available,
    m.capacidad_stock stock_capacity, ROUND((m.disponible_stock/ m.capacidad_stock) * 100, 2) as percentage,
    CASE 
      WHEN (m.disponible_stock / m.capacidad_stock) < 0.2 THEN 'CRITICO'
      WHEN (m.disponible_stock / m.capacidad_stock) < 0.4 THEN 'BAJO'
      ELSE 'NORMAL'
    END as status
FROM a_maquinas m LEFT JOIN a_combustible f ON m.tipo_combustible = f.id ORDER BY percentage ASC
"""
LISTA_TURNOS_MAQUINA_COMB = '''
    SELECT id, maquina machine_id,turno shift_code,nombre shift_name,fecha shift_date,lectura_inicial initial_reading,lectura_final final_reading,
           galones_vendidos gallons_sold,total_precio total_price,modified recorded_at,operador_id,webuser,notas notes
    FROM a_ventas_comb WHERE maquina = %s AND DATE(fecha) = CURDATE() ORDER BY fecha DESC
'''
LISTA_MAQUINAS_X_TURNOS = """
SELECT m.id, m.numero machine_number, tipo_combustible fuel_type_id, m.lectura_inicial initial_reading, 
       m.lectura_actual current_reading, capacidad_stock stock_capacity, disponible_stock stock_available, 
       estado status, m.modified created_at, f.nombre as fuel_name 
FROM a_maquinas m LEFT JOIN a_combustible f ON m.tipo_combustible = f.id ORDER BY m.numero
"""
INSERT_VTAS_COMBUSTIBLE = '''
INSERT INTO a_ventas_comb (maquina,turno,nombre,fecha,lectura_inicial,lectura_final,galones_vendidos,total_precio)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
'''
UPDATE_VTAS_COMB_MAQUINAS = "UPDATE a_maquinas SET disponible_stock = disponible_stock - %s, lectura_actual = %s WHERE id = %s"
LISTA_MAQUINAS = '''
SELECT m.id, m.numero machine_number, tipo_combustible fuel_type_id, m.lectura_inicial initial_reading, m.lectura_actual current_reading, 
        capacidad_stock stock_capacity, disponible_stock stock_available, estado status, m.modified created_at,
        f.nombre as fuel_name, f.precio_unitario unit_price, 
        COALESCE(SUM(s.galones_vendidos), 0) as total_gallons_today, m.disponible_stock as current_stock
FROM a_maquinas m
LEFT JOIN a_combustible f ON m.tipo_combustible = f.id
LEFT JOIN a_ventas_comb s ON m.id = s.maquina AND DATE(s.fecha) = CURDATE()
GROUP BY m.id
'''
LISTA_COMBUSTIBLE_TODOS = "SELECT id,nombre name, descripcion description,precio_unitario unit_price,stock_actual current_stock,stock_minimo min_stock FROM a_combustible"
INS_MAQUINAS = "INSERT INTO a_maquinas (numero,tipo_combustible,lectura_inicial,capacidad_stock,disponible_stock) VALUES (%s, %s, %s, %s, %s)"
SEL_COMBUSTIBLE = "SELECT id,nombre name,descripcion,precio_unitario unit_price,stock_actual current_stock,stock_minimo min_stock,modified FROM a_combustible ORDER BY nombre"
SEL_1_MAQUINA = """
SELECT m.id, m.numero machine_number, tipo_combustible fuel_type_id, m.lectura_inicial initial_reading, m.lectura_actual current_reading, 
        capacidad_stock stock_capacity, disponible_stock stock_available, estado status, m.modified created_at, f.nombre as fuel_name, f.precio_unitario unit_price
FROM a_maquinas m 
LEFT JOIN a_combustible f ON m.tipo_combustible = f.id 
WHERE m.id = %s
"""
INS_VENTAS_COMB = "INSERT INTO a_ventas_comb (maquina,turno,nombre,fecha,lectura_inicial,lectura_final,galones_vendidos,total_precio) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
UPD_MAQUINAS_VTAS_COMB = "UPDATE a_maquinas SET disponible_stock = disponible_stock - %s, lectura_actual = %s WHERE id = %s"
UPD_COMBUSTIBLE_CTAS_COMB = "UPDATE a_combustible SET stock_actual = stock_actual - %s WHERE id = %s"
PRECIO_U_COMB = "SELECT precio_unitario unit_price FROM a_combustible WHERE id = %s"
INS_PRESTAMO = "INSERT INTO a_prestamos (padron,fecha_solicitud,tipo_prestamo,monto_solicitado,saldo_pendiente,descripcion,cuota,garantia_aporte,estado) VALUES (%s, %s, %s, %s, 0, %s, %s, %s, %s)"
ACT_PRESTAMO = "UPDATE a_prestamos SET estado='pendiente',modified=now(),webuser='$usr$' WHERE id='$lid$' "
APR_PRESTAMO = "UPDATE a_prestamos SET estado='aprobado',fecha_aprobacion=curdate(),monto_aprobado=monto_solicitado,saldo_pendiente=monto_solicitado WHERE id = %s"
RCH_PRESTAMO = "UPDATE a_prestamos SET estado='rechazado' WHERE id = %s"
DROPLIST_DEUDAS = "SELECT tp.* FROM a_tipos tp WHERE tp.tipo='DEUDA' "
DROPLIST_APORTES_SALDO_X_PADRON = "SELECT aporte codigo,descripcion,aportado,retirado,(aportado-retirado) saldo FROM av_total_aportes_x_padron WHERE padron='$pad$' and aporte in (select codigo from a_tipos where tipo='APORTE' and atributo4='S') ORDER by 1"
SELECT_PRESTAMOS_1 = """
SELECT p.*, pr.placa, s.nombre, tp.descripcion as tipo_nombre, coalesce(p.monto_aprobado,0) mnt_aprobado, coalesce(saldo_pendiente,0) sld_pendiente
FROM a_prestamos p
  JOIN a_padrones pr ON p.padron = pr.id
  JOIN a_socios s ON pr.socio = s.id
  JOIN a_tipos tp ON tp.tipo='DEUDA' and p.tipo_prestamo = tp.codigo
WHERE (p.fecha_solicitud>=date('$p1$') AND p.fecha_solicitud<=date('$p2$')) AND
      (p.padron='$p3$' OR '$p3$'='0') AND (('$p4$'='on' AND estado='aprobado') OR ('$p4$'!='on'))
ORDER BY p.id DESC, p.fecha_solicitud DESC
"""
SELECT_RETIROS_1 = """
SELECT r.*, pr.placa, s.nombre, coalesce(r.monto_retirado,0) as mnt_retirado 
FROM a_retiros r 
  JOIN a_padrones pr ON r.padron = pr.id 
  JOIN a_socios s ON pr.socio = s.id 
WHERE (r.fecha_solicitud>=date('$p1$') AND r.fecha_solicitud<=date('$p2$')) AND
      (r.padron='$p3$' OR '$p3$'='0') AND ('$p4$'='' OR r.tipo_aporte='$p4$')
ORDER BY r.fecha_retiro DESC
"""
LISTA_CTAS_CONTABLES = "SELECT * FROM a_pcge WHERE (cuenta like '%$p1$%' OR nombre like '%$p1$%' OR entidad like '%$p1$%') ORDER BY cuenta LIMIT 50"
INS_RETIRO = "INSERT INTO a_retiros (padron,socio,fecha_solicitud,tipo_aporte,monto_solicitado,saldo_final_dia,monto_retirado,descripcion,estado,modified,webuser) VALUES (%s, 0, %s, %s, %s, %s, 0, %s, %s, now(), %s)"
APR_RETIRO = "UPDATE a_retiros SET estado='aprobado',monto_retirado=monto_solicitado,fecha_retiro=curdate() WHERE id = %s"
RCH_RETIRO = "UPDATE a_retiros SET estado='rechazado',monto_retirado=0 WHERE id = %s"
DASHB_PRRET_SOCIOS = "SELECT COALESCE(COUNT(distinct p.socio )) as total FROM a_recibos_detalle rd, a_recibos r, a_padrones p WHERE r.id = rd.recibo and r.active='S' and date(r.fecha)>=DATE_ADD(now(), INTERVAL -30 DAY) and rd.monto>0 and p.id=r.padron"
DASHB_PRRET_RETIROS = "SELECT COALESCE(SUM(monto_retirado), 0) as total FROM a_retiros r WHERE estado='aprobado' and date(r.fecha_retiro)=curdate()"
DASHB_PRRET_APORTES = "SELECT COALESCE(SUM(monto), 0) as total FROM a_recibos_detalle rd, a_recibos r WHERE r.id = rd.recibo and r.active='S' and date(r.fecha)=curdate()"
DASHB_PRRET_PRESTAMOS = "SELECT COALESCE(SUM(monto_aprobado), 0) as total FROM a_prestamos WHERE estado='aprobado' and date(fecha_aprobacion)=curdate()"
DASHB_PRRET_PRESTAMOS_ESTADO = "SELECT estado, COUNT(*) as cantidad, COALESCE(SUM(CASE WHEN estado='aprobado' THEN monto_aprobado ELSE monto_solicitado END), 0) as total FROM a_prestamos GROUP BY estado"
DASHB_PRRET_PRESTAMOS_TIPOS = "SELECT tp.descripcion, COUNT(*) as cantidad, COALESCE(SUM(p.saldo_pendiente), 0) as total FROM a_prestamos p JOIN a_tipos tp ON tp.tipo='DEUDA' AND p.tipo_prestamo = tp.codigo WHERE p.estado IN ('pendiente', 'aprobado') GROUP BY tp.descripcion"
DASHB_PRRET_PAD_MAY_APORTES = "select placa,nombre,sum(aportado) aportado from av_total_aportes_x_padron group by placa,nombre order by 3 desc limit 6"
DASHB_PRRET_MOVS_RET_PREST = """
(SELECT 'Préstamo' as tipo, pr.placa, p.monto_solicitado as monto, p.estado, p.fecha_solicitud as fecha FROM a_prestamos p JOIN a_padrones pr ON p.padron = pr.id and estado='aprobado' ORDER BY p.id DESC LIMIT 3)
UNION ALL
(SELECT 'Retiro' as tipo,   pr.placa, r.monto_solicitado as monto, r.estado, r.fecha_solicitud as fecha FROM a_retiros   r JOIN a_padrones pr ON r.padron = pr.id and estado='aprobado' ORDER BY r.id DESC LIMIT 3)
ORDER BY fecha DESC
LIMIT 10
"""
UPDATE_CUENTA_CONTABLE = "UPDATE a_pcge SET elemento=%s, cuenta=%s, nombre=%s, dinamico=%s, entidad=%s, codigo=%s, auxiliar=%s, observaciones=%s WHERE id=%s "
SELECT_CUENTA_CONTABLE = "SELECT t.* FROM a_pcge t WHERE t.id = %s"
SEL_NM_CUENTA_CONTABLE = "SELECT nombre FROM a_pcge WHERE id = %s"
DELETE_CUENTA_CONTABLE = "DELETE FROM a_pcge WHERE id = %s"
