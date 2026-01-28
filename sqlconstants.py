REP1APORTES = """
  SELECT
    CONCAT('0',serie,'-',LPAD(numero,6,'0')) d1,
    dateDMY(fecha) d2,
    dateDMY(giro) d3,
    if(fecha>giro,'ATRAZADO',if(fecha<giro,'ADELANTO','NORMAL')) d4,
    (select substr(i.completo,1,35) from v_nlf_sociopadron i where i.id=v.padron) d6,
    concat(round((SELECT SUM(monto) FROM nlf_recibos_detalle d WHERE d.recibo=v.id),2),'') d7,
    v.active d8,
    upper(substr(v.webuser,1,10)) d9,
    concat(v.id) d10,
    '0' d0 
    FROM nlf_recibos v 
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
    (select substr(i.completo,1,35) from v_nlf_sociopadron i where i.id=v.padron) d4,
    IF(fecha>giro,'ATRAZADO',IF(fecha<giro,'ADELANTADO','NORMAL')) d5,
    IFNULL(IF(v.serie='7',CONCAT(v.moneda,' T.C=',v.tc),v.comentarios),'') d6,
    concat(round(IF(serie='7',IF(moneda='DOLARES',vd.monto*IFNULL(v.tc,1),vd.monto),IFNULL(vd.monto,0)),2),'') d7
  FROM nlf_recibos_detalle vd, nlf_recibos v 
  WHERE v.id=vd.recibo AND 
    (v.fecha>='$p1$' AND v.fecha<='$p2$') AND 
    ((socio IS NOT NULL AND ('$p3$'='0' OR socio='$p3$')) OR (padron IS NOT NULL AND ('$p3$'='0' OR padron='$p3$'))) AND 
    (vd.aporte = '$p4$') AND 
    (v.active='S') 
   ORDER BY 2, 1 DESC
"""