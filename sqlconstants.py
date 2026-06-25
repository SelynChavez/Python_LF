REP0PCGE = "SELECT concat(elemento) d1, concat(cuenta) d2, concat(coalesce(nombre,'.')) d3,concat(id) d4 FROM av_plan_contable_general ORDER BY 1,2 LIMIT 9000"
REP_SS_APORTES = """
SELECT CONCAT('',serie,'-',LPAD(numero,4,'0')) d1,  dateDMY(fecha) d2,  dateDMY(giro) d3,
  if(fecha>giro,'ATRAZADO',if(fecha<giro,'ADELANTO','NORMAL')) d4,
  (SELECT CONCAT(p.id,':',p.placa,':',s.nombre) FROM a_padrones p, a_socios s WHERE p.socio=s.id AND v.padron=p.id) d6,
  concat(round((SELECT SUM(monto) FROM a_recibos_detalle d WHERE d.recibo=v.id),2),'') d7,
  v.active d8,  upper(substr(v.webuser,1,10)) d9,  concat(v.id) d10,  concat(v.padron) d11,  '0' d0, v.serie d12 
FROM a_recibos v 
WHERE serie>0 and v.fecha>=date('$p1$') and v.fecha<=date('$p2$') and (v.padron='$p3$' or '0'='$p3$') and (v.active='S') 
ORDER BY v.fecha, v.padron, v.id
"""
REP_S3_APORTES = """
SELECT CONCAT( 'RP0',serie,'-',LPAD(numero,6,'0')) d1,  dateDMY(fecha) d2,  dateDMY(giro) d3,
  if(fecha>giro,'ATRAZADO',if(fecha<giro,'ADELANTO','NORMAL')) d4,
  (SELECT CONCAT(p.id,':',p.placa,':',s.nombre) FROM a_padrones p, a_socios s WHERE p.socio=s.id AND v.padron=p.id) d6,
  concat(round((SELECT SUM(monto) FROM a_recibos_detalle d WHERE d.recibo=v.id),2),'') d7,
  v.active d8,  upper(substr(v.webuser,1,10)) d9,  concat(v.id) d10,  concat(v.padron) d11,  '0' d0 
FROM a_recibos v 
WHERE serie='$serie$' and v.fecha>=date('$p1$') and v.fecha<=date('$p2$') and (v.padron='$p3$' or '0'='$p3$') and (v.active='S') 
ORDER BY v.fecha, v.padron, v.id  
"""
REP_S2_APORTES = """
SELECT t01.*, concat(d7i,'') d7, concat(round(d7i,2),'') d13 FROM (
SELECT CONCAT((CASE WHEN serie='2' THEN 'BE0' ELSE 'RP0' END),serie,'-',LPAD(numero,6,'0')) d1,  dateDMY(fecha) d2,  dateDMY(giro) d3,
  if(fecha>giro,'ATRAZADO',if(fecha<giro,'ADELANTO','NORMAL')) d4,
  (SELECT CONCAT(p.id,':',p.placa,':',s.nombre) FROM a_padrones p, a_socios s WHERE p.socio=s.id AND v.padron=p.id) d6,
  round((SELECT SUM(monto) FROM a_recibos_detalle d WHERE d.recibo=v.id),2) d7i,
  v.active d8,  upper(substr(v.webuser,1,10)) d9,  concat(v.id) d10,  concat(v.padron) d11,  '0' d0  
FROM a_recibos v 
WHERE serie='$serie$' and v.fecha>=date('$p1$') and v.fecha<=date('$p2$') and (v.padron='$p3$' or '0'='$p3$') and (v.active='S') 
ORDER BY v.fecha, v.padron, v.id ) AS t01 
"""
REP1APORTES = """
SELECT CONCAT('RI0',serie,'-',LPAD(numero,6,'0')) d1,  dateDMY(fecha) d2,  dateDMY(giro) d3,
  if(fecha>giro,'ATRAZADO',if(fecha<giro,'ADELANTO','NORMAL')) d4,
  (SELECT CONCAT(p.id,':',p.placa,':',s.nombre) FROM a_padrones p, a_socios s WHERE p.socio=s.id AND v.padron=p.id) d6,
  concat(round((SELECT SUM(monto) FROM a_recibos_detalle d WHERE d.recibo=v.id),2),'') d7,
  v.active d8,  upper(substr(v.webuser,1,10)) d9,  concat(v.id) d10,  concat(v.padron) d11,  '0' d0 
FROM a_recibos v 
WHERE serie='1' and v.fecha>=date('$p1$') and v.fecha<=date('$p2$') and (v.padron='$p3$' or '0'='$p3$') and (v.active='S') 
ORDER BY v.fecha, v.padron, v.id  """
REP2APORTES = """
  SELECT 
    CONCAT('RI-',v.serie,'-',LPAD(v.numero,6,'0')) d1,
    dateDMY(v.giro) d2,
    IF(v.padron IS NULL,LPAD(v.socio,4,'0'),LPAD(v.padron,4,'0')) d3,
    (SELECT CONCAT(p.id,':',p.placa,':',s.nombre) FROM a_padrones p, a_socios s WHERE p.socio=s.id AND v.padron=p.id) d4,
    IF(fecha>giro,'ATRAZADO',IF(fecha<giro,'ADELANTADO','NORMAL')) d5,
    IFNULL(IF(v.serie='7',CONCAT(v.moneda,' T.C=',v.tc),'S/.'),'') d6,
    concat(round(IF(serie='7',IF(moneda='DOLARES',vd.monto*IFNULL(v.tc,1),vd.monto),IFNULL(vd.monto,0)),2),'') d7,
    vd.aporte d8
  FROM a_recibos_detalle vd, a_recibos v 
  WHERE v.serie in ('1') AND v.id=vd.recibo AND (v.fecha>='$p1$' AND v.fecha<='$p2$') AND 
    ((socio IS NOT NULL AND ('$p3$'='0' OR socio='$p3$')) OR (padron IS NOT NULL AND ('$p3$'='0' OR padron='$p3$'))) AND 
    ((vd.aporte = '$p4$') or 'TODOS'='$p4$') AND 
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
UPDATE_SOCIO = "UPDATE a_socios SET nombre=%s, fono=%s, dni=%s, comentarios=%s, tipo=%s, active=%s, email=%s, usuario=%s, modified=now() WHERE id=%s "
SELECT_SOCIO = "SELECT * FROM a_socios WHERE id = %s"
SEL_NM_SOCIO = "SELECT nombre FROM a_socios WHERE id = %s"
DELETE_SOCIO = "DELETE FROM a_socios WHERE id = %s"

LISTA_EMPLEADOS = "SELECT * FROM a_empleados ORDER BY modified DESC "
INSERT_EMPLEADO = "INSERT INTO a_empleados (nombre, fono, dni, email, cargo, direccion, afp, sueldo, active, modified, webuser) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'S', now(), %s)"
UPDATE_EMPLEADO = "UPDATE a_empleados SET nombre=%s, fono=%s, dni=%s, email=%s, cargo=%s, direccion=%s, afp=%s, sueldo=%s, active=%s,  modified=now() WHERE id=%s "
SELECT_EMPLEADO = "SELECT * FROM a_empleados WHERE id = %s"
SEL_NM_EMPLEADO = "SELECT nombre FROM a_empleados WHERE id = %s"
DELETE_EMPLEADO = "DELETE FROM a_empleados WHERE id = %s"

LISTA_PROVEEDORES = "SELECT * FROM a_proveedores ORDER BY modified DESC "
INSERT_PROVEEDOR = "INSERT INTO a_proveedores (nombre, ruc, contacto, cargo, fono, email, tipo, direccion, observaciones, active, modified, webuser) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'S', now(), %s)"
UPDATE_PROVEEDOR = "UPDATE a_proveedores SET nombre=%s, ruc=%s, contacto=%s, cargo=%s, fono=%s, email=%s, tipo=%s, direccion=%s, observaciones=%s, active=%s,webuser=%s, modified=now() WHERE id=%s "
SELECT_PROVEEDOR = "SELECT * FROM a_proveedores WHERE id = %s"
SEL_NM_PROVEEDOR = "SELECT nombre FROM a_proveedores WHERE id = %s"
DELETE_PROVEEDOR = "DELETE FROM a_proveedores WHERE id = %s"

LISTA_PADRONES = "SELECT p.*,(SELECT concat(s.nombre,' #',s.id) FROM a_socios s WHERE s.id=p.socio) nombresocio FROM a_padrones p ORDER BY p.modified DESC "
INSERT_PADRON = "INSERT INTO a_padrones (placa, socio, active, monto1, monto2, monto3, monto4, modified, webuser) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), %s)"
UPDATE_PADRON = "UPDATE a_padrones SET placa=%s, socio=%s, active=%s, monto1=%s, monto2=%s, monto3=%s, monto4=%s, modified=now() WHERE id=%s "
SELECT_PADRON = "SELECT p.*,(SELECT s.nombre FROM a_socios s WHERE s.id=p.socio) nombresocio FROM a_padrones p WHERE p.id = %s"
SEL_NM_PADRON = "SELECT placa FROM a_padrones WHERE id = %s"
DELETE_PADRON = "DELETE FROM a_padrones WHERE id = %s"
GET_NOMBRE_PADRON = "SELECT concat(p.id,':',p.placa,':',s.nombre) as n0 FROM a_padrones p, a_socios s WHERE p.id=%s and p.socio=s.id "

LISTA_TIPOS_APORTE = "SELECT t.*,concat('S00',atributo1) serie FROM a_tipos t WHERE t.tipo=%s ORDER BY t.modified DESC "
LISTA_TIPOS = "SELECT t.* FROM a_tipos t WHERE t.tipo=%s ORDER BY t.modified DESC "
INSERT_TIPO = "INSERT INTO a_tipos (tipo, codigo, descripcion, monto1, monto2, atributo1, atributo2, atributo3, atributo4, atributo5, modified, webuser) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), %s)"
UPDATE_TIPO = "UPDATE a_tipos SET codigo=%s, descripcion=%s, monto1=%s,monto2=%s,atributo1=%s,atributo2=%s,atributo3=%s,atributo4=%s,atributo5=%s, modified=now() WHERE id=%s "
SELECT_TIPO = "SELECT t.* FROM a_tipos t WHERE t.id = %s"
SEL_NM_TIPO = "SELECT tipo,codigo FROM a_tipos WHERE id = %s"
DELETE_TIPO = "DELETE FROM a_tipos WHERE id = %s"

DROPLIST_APORTES = "SELECT codigo d1,concat(codigo,':',descripcion) d2 FROM a_tipos WHERE tipo='APORTE' "
DROPLIST_APORTES_RET = "SELECT codigo d1,concat(codigo,':',descripcion) d2 FROM a_tipos WHERE tipo='APORTE' and atributo4='S' "
INSERT_LOGUSUARIO = "INSERT INTO logs_usuarios (usuario_id, accion, descripcion) VALUES (%s, %s, %s)"

DELETE_RECIBO_U = "DELETE FROM a_recibos WHERE serie=%s AND giro=%s AND padron=%s AND active != 'S' "
INSERT_CORREL_X = "INSERT INTO a_corrrec_$serie$ VALUES (null,'X',now())"
INSERT_RECIBO_X = "INSERT INTO a_recibos (serie, numero, fecha, giro, padron, comentarios, active, modified, webuser, igv) VALUES (%s, %s, now(), %s, %s, %s, %s, now(), %s, %s)"
UPDATE_RECIBO_X = "UPDATE a_recibos SET active='S' WHERE id='$recibo$'"
INSERT_DETREC_X = "INSERT INTO a_recibos_detalle (aporte, recibo, monto, prestamo, tipodeuda, modified, webuser) VALUES ('$apo$', '$rec$', '$mnt$', '$pre$', '$tip$', now(), '$usr$')"
INSERT_RECIBO_IMPORT = "INSERT INTO a_recibos (serie, numero, fecha, giro, padron, comentarios, active, modified, webuser, igv) VALUES (%s, %s, %s, %s, %s, %s, 'S', now(), %s, 'N')"
INSERT_DETREC_IMPORT = "INSERT INTO a_recibos_detalle (aporte, recibo, monto, prestamo, tipodeuda, modified, webuser) VALUES (%s, %s, %s, '0', '', now(), %s)"
SELECT_RECIBO_X = "SELECT r.*,nombPadronSocio(r.padron) nombre, concat(fecha) fec, concat(giro) gir FROM a_recibos r WHERE r.id='$pX$'"
SELECT_DETALLEX = "SELECT rd.*,tt.codigo,tt.descripcion FROM a_recibos_detalle rd, a_tipos tt WHERE recibo='$pX$' AND tt.tipo='APORTE' AND tt.codigo=rd.aporte ORDER BY rd.id"
DETALLE_SERIE_1 = """SELECT * FROM (SELECT t.codigo,t.descripcion,
  ROUND(COALESCE((CASE
      WHEN t.codigo='APAHORRO'  THEN p.monto2
      WHEN t.codigo='APAPORTE'  THEN p.monto3
      ELSE t.monto1
  END),0),2) monto, 0 prestamo, '' tipodeuda, t.id idx0, 1 serie
FROM a_tipos t left outer join a_padrones p on t.tipo='APORTE' and p.id='$pad$'
WHERE t.tipo='APORTE' and t.atributo1='1' and (t.codigo not in ('PRESTAMO'))
UNION ALL
SELECT t.codigo,t.descripcion,p.cuota monto,p.id prestamo,p.tipo_prestamo tipodeuda,t.id idx, 1 serie 
FROM a_prestamos p,a_tipos t 
WHERE p.padron='$pad$' and p.estado='aprobado' and t.tipo='APORTE' and t.codigo='PRESTAMO') as table1
WHERE ( (codigo in ('APAHORRO','APAPORTE') and monto > 0) OR codigo not in ('APAHORRO','APAPORTE') )
"""
DETALLE_SERIE_2x = """SELECT * FROM (SELECT t.codigo,t.descripcion,
  ROUND(COALESCE((CASE
      WHEN t.codigo='AP.SEGURO.X' THEN p.monto4
      ELSE t.monto1
  END),0),2) monto, 0 prestamo, '' tipodeuda, t.id idx0, 2 serie
FROM a_tipos t left outer join a_padrones p on t.tipo='APORTE' and p.id='$pad$'
WHERE t.tipo='APORTE' and t.atributo1='2' and (t.codigo not in ('PRESTAMO'))
UNION ALL
SELECT t.codigo,t.descripcion,p.cuota monto,p.id prestamo,p.tipo_prestamo tipodeuda,t.id idx, 2 serie 
FROM a_prestamos p,a_tipos t 
WHERE p.padron='$pad$' and p.estado='aprobado' and t.tipo='APORTE' and t.codigo='PRESTAMO') as table1
WHERE ( (codigo in ('AP.SEGURO.X') and monto > 0) OR codigo not in ('AP.SEGURO.X') )
"""

DETALLE_SERIE_3X = """ SELECT t.codigo,t.descripcion,
  ROUND(COALESCE((CASE
      WHEN t.codigo='AP.SEGURO.X' THEN p.monto4
      ELSE t.monto1
  END),0),2) monto, 0 prestamo, '' tipodeuda, t.id idx0
FROM a_tipos t left outer join a_padrones p on t.tipo='APORTE' and p.id='$pad$'
WHERE t.atributo1='$serie$'   """


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
SELECT f.id, f.nombre as fuel_name, f.nombre as fuel_type,
    f.stock_actual stock_available, f.stock_minimo stock_min,
    ROUND(CASE WHEN f.stock_minimo > 0 THEN (f.stock_actual / f.stock_minimo) * 100 ELSE 100 END, 2) as percentage,
    CASE
      WHEN f.stock_minimo > 0 AND f.stock_actual <= f.stock_minimo THEN 'CRITICO'
      WHEN f.stock_minimo > 0 AND f.stock_actual <= f.stock_minimo * 1.5 THEN 'BAJO'
      ELSE 'NORMAL'
    END as status
FROM a_combustible f
WHERE f.id IN (
    SELECT DISTINCT m.tipo_combustible
    FROM a_ventas_comb v JOIN a_maquinas m ON v.maquina = m.id
)
ORDER BY f.stock_actual ASC
"""
LISTA_TURNOS_MAQUINA_COMB = '''
    SELECT id, maquina machine_id,turno shift_code,nombre shift_name,fecha shift_date,lectura_inicial initial_reading,lectura_final final_reading,
           galones_vendidos gallons_sold,total_precio total_price,modified recorded_at,operador_id,webuser,notas notes
    FROM a_ventas_comb WHERE maquina = %s AND DATE(fecha) = CURDATE() ORDER BY fecha DESC
'''
LISTA_MAQUINAS_X_TURNOS = """
SELECT m.id, m.numero machine_number, m.ubicacion, tipo_combustible fuel_type_id, m.lectura_inicial initial_reading,
       m.lectura_actual current_reading, capacidad_stock stock_capacity,
       f.stock_actual stock_available, f.stock_minimo stock_min,
       estado status, m.modified created_at, f.nombre as fuel_name
FROM a_maquinas m LEFT JOIN a_combustible f ON m.tipo_combustible = f.id ORDER BY m.numero
"""
STOCK_POR_MAQUINA = """
SELECT m.id, m.numero machine_number, f.nombre fuel_name,
       f.stock_actual stock_available, m.capacidad_stock stock_capacity,
       ROUND(CASE WHEN m.capacidad_stock > 0 THEN (f.stock_actual / m.capacidad_stock) * 100 ELSE 0 END, 2) percentage,
       CASE
         WHEN f.stock_minimo > 0 AND f.stock_actual <= f.stock_minimo THEN 'CRITICO'
         WHEN f.stock_minimo > 0 AND f.stock_actual <= f.stock_minimo * 1.5 THEN 'BAJO'
         ELSE 'NORMAL'
       END status
FROM a_maquinas m LEFT JOIN a_combustible f ON m.tipo_combustible = f.id
ORDER BY m.numero
"""
INSERT_VTAS_COMBUSTIBLE = '''
INSERT INTO a_ventas_comb (maquina,turno,nombre,fecha,lectura_inicial,lectura_final,galones_vendidos,total_precio,webuser)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
'''
LISTA_VENTAS_X_USUARIO = '''
SELECT v.id, v.turno, v.nombre, v.fecha, v.lectura_inicial, v.lectura_final,
       v.galones_vendidos, v.total_precio, v.modified,
       m.numero AS machine_number, m.ubicacion
FROM a_ventas_comb v
LEFT JOIN a_maquinas m ON v.maquina = m.id
WHERE v.webuser = %s
ORDER BY v.fecha DESC, v.id DESC
LIMIT %s OFFSET %s
'''
COUNT_VENTAS_X_USUARIO = "SELECT COUNT(*) AS total FROM a_ventas_comb WHERE webuser = %s"
LISTA_VENTAS_TODAS = '''
SELECT v.id, v.turno, v.nombre, v.fecha, v.lectura_inicial, v.lectura_final,
       v.galones_vendidos, v.total_precio, v.modified, v.webuser,
       m.numero AS machine_number, m.ubicacion
FROM a_ventas_comb v
LEFT JOIN a_maquinas m ON v.maquina = m.id
ORDER BY v.fecha DESC, v.id DESC
LIMIT 10
'''
COUNT_VENTAS_TODAS = "SELECT COUNT(*) AS total FROM a_ventas_comb"
UPDATE_VTAS_COMB_MAQUINAS = "UPDATE a_maquinas SET lectura_actual = %s WHERE id = %s"
UPDATE_STOCK_COMBUSTIBLE_VTA = "UPDATE a_combustible SET stock_actual = stock_actual - %s WHERE id = %s"
LISTA_MAQUINAS = '''
SELECT m.id, m.numero machine_number, ubicacion, tipo_combustible fuel_type_id, m.lectura_inicial initial_reading, m.lectura_actual current_reading,
        capacidad_stock stock_capacity, f.stock_actual stock_available, f.stock_minimo stock_min, estado status, m.modified created_at,
        f.nombre as fuel_name, f.precio_unitario unit_price,
        COALESCE(SUM(s.galones_vendidos), 0) as total_gallons_today, f.stock_actual as current_stock
FROM a_maquinas m
LEFT JOIN a_combustible f ON m.tipo_combustible = f.id
LEFT JOIN a_ventas_comb s ON m.id = s.maquina AND DATE(s.fecha) = CURDATE()
GROUP BY m.id
'''
DEL_1_COMBUSTIBLE = 'DELETE FROM a_combustible WHERE id = %s'
UPD_1_COMBUSTIBLE = "UPDATE a_combustible SET nombre = %s, descripcion = %s, precio_compra = %s, precio_unitario = %s, stock_actual = %s, stock_minimo = %s, modified = NOW() WHERE id = %s"
INS_1_COMBUSTIBLE = 'INSERT INTO a_combustible (nombre, descripcion, precio_compra, precio_unitario, stock_actual, stock_minimo, modified) VALUES (%s, %s, %s, %s, %s, %s, NOW())'
SELECT_1_COMBUSTIBLE = 'SELECT * FROM a_combustible WHERE id = %s'
LISTA_COMBUSTIBLE_TODOS = "SELECT id,nombre name, descripcion description,precio_compra purchase_price,precio_promedio average_price,precio_unitario unit_price,stock_actual current_stock,stock_minimo min_stock FROM a_combustible"
INS_MAQUINAS = "INSERT INTO a_maquinas (numero,tipo_combustible,lectura_inicial,capacidad_stock,disponible_stock,ubicacion) VALUES (%s, %s, %s, %s, %s, %s)"
SEL_COMBUSTIBLE = "SELECT id,nombre name,descripcion,precio_compra purchase_price,precio_promedio average_price,precio_unitario unit_price,stock_actual current_stock,stock_minimo min_stock,modified FROM a_combustible ORDER BY nombre"
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
UPD_PRESTAMO_CUOTA_ESTADO = "UPDATE a_prestamos SET cuota=%s, estado=%s WHERE id=%s"
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
LISTA_CTAS_CONTABLES = "SELECT * FROM a_pcge WHERE (cuenta like '$p1$%' OR nombre like '%$p1$%' OR entidad like '%$p1$%') ORDER BY cuenta LIMIT 100"
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

SELECT_LISTA_PADRONES = "SELECT concat(p.id) id, p.placa, p.socio FROM a_padrones p, a_socios s WHERE p.socio = s.id and s.usuario = '$usr$'"

LISTA_PRODUCTOS = "SELECT * FROM a_productos ORDER BY id DESC"
SELECT_1_PRODUCTO = 'SELECT * FROM a_productos WHERE id = %s'
INSERT_PRODUCTO = 'INSERT INTO a_productos (nombre, tipo, precio_unitario, stock_actual, stock_minimo, active, observaciones, modified, webuser) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)'
UPDATE_PRODUCTO = 'UPDATE a_productos SET nombre = %s,tipo = %s,precio_unitario = %s,stock_actual = %s,stock_minimo = %s,active = %s,observaciones = %s,modified = NOW(),webuser = %s WHERE id = %s'
DELETE_PRODUCTO = 'DELETE FROM a_productos WHERE id = %s'

UPD_SALIDA_ANULADO = "UPDATE a_salidas SET estado = 'ANULADO', modified = CURRENT_TIMESTAMP WHERE id = %s"
SEL_SALIDA_ARCHIVO = "SELECT archivo FROM a_salidas WHERE id = %s"
UPD_SALIDA_ARCHIVO = "UPDATE a_salidas SET archivo = %s, modified = CURRENT_TIMESTAMP WHERE id = %s"
SELECT_1_SALIDA = "SELECT * FROM a_salidas WHERE id = %s"
SELECT_1_INGRESO = "SELECT * FROM a_ingresos WHERE id = %s"
LISTA_INGRESOS = "SELECT * FROM a_ingresos WHERE DATE(fecha_solicitud) BETWEEN %s AND %s AND estado in ('PENDIENTE','CONFIRMADO') ORDER BY fecha_solicitud DESC, id DESC"
LISTA_SALIDAS = "SELECT * FROM a_salidas WHERE DATE(fecha_solicitud) BETWEEN %s AND %s AND estado in ('PENDIENTE','CONFIRMADO') ORDER BY fecha_solicitud DESC, id DESC"
LISTA_TIPO_SALIDAS = "SELECT codigo,concat(descripcion,' [',codigo,']') descripcion FROM a_tipos WHERE tipo = 'SALIDA' ORDER BY 2"
LISTA_TIPO_INGRESOS = "SELECT codigo, CONCAT(descripcion, ' [', codigo, ']') as descripcion FROM a_tipos WHERE tipo = 'INGRESO' ORDER BY 2"
LISTA_DISCT_TIPO_SALIDAS = "SELECT DISTINCT codigo,descripcion nombre FROM a_tipos WHERE tipo = 'SALIDA' ORDER BY descripcion"
LISTA_FILTRO_SALIDAS = "SELECT s.*, DATE_FORMAT(fecha_solicitud, '%d/%m/%Y') fecha FROM a_salidas s WHERE fecha_solicitud BETWEEN %s AND %s "
LISTA_2_PADRONES = "SELECT id, nombPadronSocio(p.id) nombre, placa FROM a_padrones p ORDER BY nombre"
LISTA_3_PADRONES = "SELECT id, nombre, placa FROM a_padrones ORDER BY nombre"
LISTA_2_SOCIOS = "SELECT id, nombre, dni FROM a_socios ORDER BY nombre"
LISTA_3_SOCIOS = "SELECT id, concat(id,': ',nombre) nombre, dni FROM a_socios ORDER BY nombre"
LISTA_2_EMPLEADOS = "SELECT id, nombre, dni FROM a_empleados WHERE active = 'S' ORDER BY nombre"
LISTA_3_EMPLEADOS = "SELECT id, concat(id,': ',nombre) nombre, dni FROM a_empleados WHERE active = 'S' ORDER BY nombre"
LISTA_2_PROVEEDORES = "SELECT id, nombre, ruc FROM a_proveedores ORDER BY nombre"
LISTA_3_PROVEEDORES = "SELECT id, concat(id,': ',nombre) nombre, ruc FROM a_proveedores WHERE active='S' ORDER BY nombre"
LISTA_2_TERCEROS = "SELECT id, descripcion, codigo, atributo1, descripcion nombre FROM a_tipos WHERE tipo = 'TERCERO' ORDER BY 1"
LISTA_3_TERCEROS = "SELECT id, descripcion, atributo1, descripcion nombre FROM a_tipos WHERE tipo = 'TERCERO' ORDER BY 2"
LISTA_4_TERCEROS = "SELECT concat(codigo,': ',descripcion) descripcion FROM a_tipos WHERE tipo = 'TERCERO' ORDER BY 1"
UPD_9_SALIDAS = """UPDATE a_salidas
SET fecha_solicitud = %s,
    tipo_salida = %s,
    tipo_beneficiario = %s,
    beneficiario = %s,
    beneficiario_nombre = %s,
    monto = %s,
    observaciones = %s,
    tipo_doc = %s,
    numero_doc = %s,
    periodo = %s,
    modified = CURRENT_TIMESTAMP,
    webuser = %s,
    estado = 'CONFIRMADO'
WHERE id = %s """
INS_9_SALIDAS = """ 
INSERT INTO a_salidas 
(fecha_solicitud, tipo_salida, tipo_beneficiario, beneficiario,beneficiario_nombre, monto, estado, observaciones, tipo_doc, numero_doc, periodo, webuser)
VALUES (%s, %s, %s, %s, %s, %s, 'PENDIENTE', %s, %s, %s, %s, %s)
"""
UPD_9_INGRESOS = """UPDATE a_ingresos
SET fecha_solicitud = %s,
    tipo_ingreso = %s,
    tipo_tercero = %s,
    tercero = %s,
    monto = %s,
    observaciones = %s,
    tipo_doc = %s,
    numero_doc = %s,
    periodo = %s,
    estado = 'CONFIRMADO',
    modified = CURRENT_TIMESTAMP,
    webuser = %s
WHERE id = %s """
INS_9_INGRESOS = """
INSERT INTO a_ingresos
(fecha_solicitud, tipo_ingreso, tipo_tercero, tercero, monto, estado, observaciones, tipo_doc, numero_doc, periodo, webuser)
VALUES (%s, %s, %s, %s, %s, 'PENDIENTE', %s, %s, %s, %s, %s)
"""

# Compras de Combustible
LISTA_COMPRAS_COMB = """SELECT c.id, c.ruc, COALESCE(p.nombre, c.ruc) nombre_proveedor, c.fecha, c.numero, c.tipo, c.total, c.moneda, c.webuser, c.created_at FROM a_compras_comb c LEFT JOIN a_proveedores p ON c.ruc = p.ruc ORDER BY c.id DESC LIMIT 200"""
INS_COMPRA_COMB = "INSERT INTO a_compras_comb (ruc, fecha, numero, subtotal, igv, descuentos, adicionales, total, moneda, tipo, observaciones, webuser) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
INS_COMPRA_COMB_DET = "INSERT INTO a_compras_comb_detalles (factura_id, producto, descripcion, cantidad, uom, precio, subtotal, webuser) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
UPD_COMB_STOCK_COMPRA = """UPDATE a_combustible SET precio_promedio = CASE WHEN (stock_actual + %s) > 0 THEN ((stock_actual * COALESCE(precio_promedio, precio_unitario)) + (%s * %s)) / (stock_actual + %s) ELSE %s END, stock_actual = stock_actual + %s WHERE nombre = %s"""
UPD_MAQUINA_STOCK_COMPRA = "UPDATE a_maquinas SET disponible_stock = disponible_stock + %s WHERE id = %s"
SEL_PROVEEDOR_POR_RUC = "SELECT id, nombre, ruc FROM a_proveedores WHERE ruc = %s AND active = 'S' LIMIT 1"
LISTA_COMB_PARA_COMPRA = "SELECT id, nombre, precio_compra FROM a_combustible ORDER BY nombre"
LISTA_MAQUINAS_COMPRA = "SELECT m.id, m.numero machine_number, COALESCE(c.nombre,'') fuel_name FROM a_maquinas m LEFT JOIN a_combustible c ON m.tipo_combustible = c.id ORDER BY m.numero"

# ===== Ventas de Combustible por Padron =====
CREATE_VENTAS_COMB_PADRON = """
CREATE TABLE IF NOT EXISTS a_ventas_comb_padron (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATE NOT NULL,
    padron INT NOT NULL,
    monto DECIMAL(12,2) NOT NULL,
    observacion VARCHAR(255) DEFAULT NULL,
    forma_pago VARCHAR(10) NOT NULL DEFAULT 'Contado',
    webuser VARCHAR(50) NOT NULL,
    created DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_vcp_webuser (webuser),
    INDEX idx_vcp_fecha (fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""
# Migración idempotente: agrega la columna forma_pago si la tabla ya existía sin ella.
COLCHECK_VCP_FORMA_PAGO = """
SELECT COUNT(*) AS c FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'a_ventas_comb_padron' AND COLUMN_NAME = 'forma_pago'
"""
ALTER_VCP_ADD_FORMA_PAGO = "ALTER TABLE a_ventas_comb_padron ADD COLUMN forma_pago VARCHAR(10) NOT NULL DEFAULT 'Contado' AFTER observacion"
INSERT_VENTA_COMB_PADRON = "INSERT INTO a_ventas_comb_padron (fecha, padron, monto, observacion, forma_pago, webuser) VALUES (%s, %s, %s, %s, %s, %s)"
LISTA_VENTAS_COMB_PADRON_USR = """
SELECT v.id, v.fecha, v.padron, nombPadronSocio(v.padron) nombre, v.monto, v.observacion, v.forma_pago, v.webuser, v.created
FROM a_ventas_comb_padron v WHERE v.webuser = %s ORDER BY v.fecha DESC, v.id DESC
"""
LISTA_VENTAS_COMB_PADRON_ALL = """
SELECT v.id, v.fecha, v.padron, nombPadronSocio(v.padron) nombre, v.monto, v.observacion, v.forma_pago, v.webuser, v.created
FROM a_ventas_comb_padron v ORDER BY v.fecha DESC, v.id DESC
"""
SELECT_VENTA_COMB_PADRON = "SELECT id, webuser FROM a_ventas_comb_padron WHERE id = %s"
DELETE_VENTA_COMB_PADRON = "DELETE FROM a_ventas_comb_padron WHERE id = %s"
LISTA_USUARIOS_ACTIVOS = "SELECT username, fullname, roles FROM applicationuser WHERE status = 'ACTIVE' ORDER BY fullname"

# Saldo pendiente de combustible de un padrón (para Recibo Cobranza de Comb. - Serie 5):
#   ventas de combustible a CREDITO (a_ventas_comb_padron) - total cobrado (aporte COBRO.COMB en recibos serie 5 activos)
SALDO_COBRO_COMB = """
SELECT
  COALESCE((SELECT SUM(monto) FROM a_ventas_comb_padron WHERE padron = %s AND forma_pago = 'Credito'), 0) -
  COALESCE((SELECT SUM(rd.monto) FROM a_recibos r
            JOIN a_recibos_detalle rd ON rd.recibo = r.id
            WHERE r.serie = '5' AND r.active = 'S' AND r.padron = %s AND rd.aporte = 'COBRO.COMB'), 0) AS saldo
"""

# Reporte de saldos de deuda de combustible por padrón (misma lógica que SALDO_COBRO_COMB).
REP_SALDOS_COMB = """
SELECT pad.padron,
       nombPadronSocio(pad.padron) nombre,
       ROUND(COALESCE(v.ventas, 0), 2) ventas,
       ROUND(COALESCE(c.cobrado, 0), 2) cobrado,
       ROUND(COALESCE(v.ventas, 0) - COALESCE(c.cobrado, 0), 2) saldo
FROM (
    SELECT padron FROM a_ventas_comb_padron WHERE forma_pago = 'Credito'
    UNION
    SELECT r.padron FROM a_recibos r JOIN a_recibos_detalle rd ON rd.recibo = r.id
    WHERE r.serie = '5' AND r.active = 'S' AND rd.aporte = 'COBRO.COMB'
) pad
LEFT JOIN (SELECT padron, SUM(monto) ventas FROM a_ventas_comb_padron
           WHERE forma_pago = 'Credito' GROUP BY padron) v ON v.padron = pad.padron
LEFT JOIN (SELECT r.padron, SUM(rd.monto) cobrado FROM a_recibos r
           JOIN a_recibos_detalle rd ON rd.recibo = r.id
           WHERE r.serie = '5' AND r.active = 'S' AND rd.aporte = 'COBRO.COMB' GROUP BY r.padron) c ON c.padron = pad.padron
ORDER BY saldo DESC, pad.padron
"""

# Reportes flexibles con múltiples series y tipos de fecha
REP_FLEX_RECIBOS_PADRON = """
SELECT CONCAT(
  CASE
    WHEN v.serie='1' THEN 'RI'
    WHEN v.serie='2' THEN 'BE'
    ELSE 'RP'
  END,
  v.serie,'-',LPAD(v.numero,4,'0')) d1,
  dateDMY(v.fecha) d2,
  dateDMY(v.giro) d3,
  IF(v.fecha>v.giro,'ATRAZADO',IF(v.fecha<v.giro,'ADELANTO','NORMAL')) d4,
  (SELECT CONCAT(p.id,':',p.placa,':',s.nombre) FROM a_padrones p, a_socios s WHERE p.socio=s.id AND v.padron=p.id) d6,
  CONCAT(ROUND((SELECT SUM(monto) FROM a_recibos_detalle d WHERE d.recibo=v.id),2),'') d7,
  v.active d8,
  UPPER(SUBSTR(v.webuser,1,10)) d9,
  CONCAT(v.id) d10,
  CONCAT(v.padron) d11,
  '0' d0,
  v.serie d12
FROM a_recibos v
WHERE v.serie IN ($serie$)
  AND (CASE WHEN '$tipo_fecha$'='giro' THEN v.giro ELSE v.fecha END) >= date('$p1$')
  AND (CASE WHEN '$tipo_fecha$'='giro' THEN v.giro ELSE v.fecha END) <= date('$p2$')
  AND (v.padron='$p3$' OR '0'='$p3$')
  AND (v.webuser='$p5$' OR '0'='$p5$')
  AND v.active='S'
ORDER BY v.fecha, v.padron, v.id
"""

REP_FLEX_RECIBOS_APORTES = """
SELECT
  CONCAT('RI-',v.serie,'-',LPAD(v.numero,6,'0')) d1,
  dateDMY(CASE WHEN '$tipo_fecha$'='giro' THEN v.giro ELSE v.fecha END) d2,
  IF(v.padron IS NULL,LPAD(v.socio,4,'0'),LPAD(v.padron,4,'0')) d3,
  (SELECT CONCAT(p.id,':',p.placa,':',s.nombre) FROM a_padrones p, a_socios s WHERE p.socio=s.id AND v.padron=p.id) d4,
  IF(v.fecha>v.giro,'ATRAZADO',IF(v.fecha<v.giro,'ADELANTADO','NORMAL')) d5,
  IFNULL(IF(v.serie='7',CONCAT(v.moneda,' T.C=',v.tc),'S/.'),'') d6,
  CONCAT(ROUND(IF(v.serie='7',IF(v.moneda='DOLARES',vd.monto*IFNULL(v.tc,1),vd.monto),IFNULL(vd.monto,0)),2),'') d7,
  vd.aporte d8
FROM a_recibos_detalle vd, a_recibos v
WHERE v.serie IN ($serie$)
  AND v.id=vd.recibo
  AND (CASE WHEN '$tipo_fecha$'='giro' THEN v.giro ELSE v.fecha END) >= date('$p1$')
  AND (CASE WHEN '$tipo_fecha$'='giro' THEN v.giro ELSE v.fecha END) <= date('$p2$')
  AND ((v.socio IS NOT NULL AND ('$p3$'='0' OR v.socio='$p3$')) OR (v.padron IS NOT NULL AND ('$p3$'='0' OR v.padron='$p3$')))
  AND ((vd.aporte = '$p4$') OR 'TODOS'='$p4$')
  AND v.active='S'
ORDER BY d2 DESC, d1 DESC
"""

REP_VENTAS_COMB = """
SELECT
  v.id,
  v.fecha,
  v.padron,
  COALESCE(nombPadronSocio(v.padron), CONCAT('Padron #', v.padron)) nombre_padron,
  v.monto,
  v.forma_pago,
  v.observacion,
  v.webuser,
  v.created
FROM a_ventas_comb_padron v
WHERE v.fecha >= date('$p1$')
  AND v.fecha <= date('$p2$')
  AND (v.padron = '$p3$' OR '0' = '$p3$')
  AND (v.forma_pago = '$p4$' OR 'TODOS' = '$p4$')
  AND (v.webuser = '$p5$' OR '$p5$' = '0')
ORDER BY v.fecha DESC, v.padron, v.id

"""

REP_VENTAS_COMB_TOTAL_DIA = """
SELECT
  v.fecha,
  COALESCE(v.forma_pago, 'TOTAL') forma_pago,
  ROUND(SUM(v.monto), 2) total_monto,
  COUNT(*) cantidad
FROM a_ventas_comb_padron v
WHERE v.fecha >= date('$p1$')
  AND v.fecha <= date('$p2$')
  AND (v.padron = '$p3$' OR '0' = '$p3$')
  AND (v.forma_pago = '$p4$' OR 'TODOS' = '$p4$')
  AND (v.webuser = '$p5$' OR '$p5$' = '0')
GROUP BY v.fecha, v.forma_pago
ORDER BY v.fecha DESC, v.forma_pago
"""

REP_VENTAS_COMB_MAQUINA = """
SELECT
  m.numero machine_number,
  v.nombre,
  m.ubicacion local,
  v.fecha,
  v.lectura_inicial,
  v.lectura_final,
  v.galones_vendidos,
  v.total_precio,
  v.webuser,
  m.id machine_id
FROM a_ventas_comb v
LEFT JOIN a_maquinas m ON v.maquina = m.id
WHERE v.fecha >= date('$p1$')
  AND v.fecha <= date('$p2$')
  AND (v.maquina = '$p3$' OR '0' = '$p3$')
  AND (v.webuser = '$p5$' OR '0' = '$p5$')
ORDER BY m.numero, v.fecha DESC, v.id DESC
"""

# Tabla de precios históricos de compra de combustible
CREATE_PRECIOS_HISTORICOS_COMB = """
CREATE TABLE IF NOT EXISTS a_precios_historicos_comb (
    id INT AUTO_INCREMENT PRIMARY KEY,
    producto_nombre VARCHAR(100) NOT NULL,
    fecha_compra DATE NOT NULL,
    precio_unitario DECIMAL(10,5) NOT NULL,
    cantidad DECIMAL(12,2) NOT NULL,
    moneda VARCHAR(10) DEFAULT 'PEN',
    factura_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_producto (producto_nombre),
    INDEX idx_fecha (fecha_compra),
    FOREIGN KEY (factura_id) REFERENCES a_compras_comb(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

INS_PRECIO_HISTORICO_COMB = """
INSERT INTO a_precios_historicos_comb (producto_nombre, fecha_compra, precio_unitario, cantidad, moneda, factura_id)
VALUES (%s, %s, %s, %s, %s, %s)
"""

GET_PRECIO_PROMEDIO_COMB = """
SELECT 
    producto_nombre,
    SUM(cantidad) as total_cantidad,
    ROUND(SUM(precio_unitario * cantidad) / SUM(cantidad), 5) as precio_promedio,
    COUNT(*) as total_compras,
    MAX(fecha_compra) as ultima_compra
FROM a_precios_historicos_comb
WHERE producto_nombre = %s AND moneda = %s
GROUP BY producto_nombre, moneda
"""


# Agregar columna estado a compras_comb si no existe
ALTER_COMPRAS_COMB_ADD_ESTADO = """
ALTER TABLE a_compras_comb
ADD COLUMN IF NOT EXISTS estado VARCHAR(20) DEFAULT 'ACTIVO'
AFTER tipo
"""

