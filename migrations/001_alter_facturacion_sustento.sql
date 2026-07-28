-- Cambiar columna 'sustento' de BLOB a LONGBLOB en la tabla 'a_facturacion_sys'
ALTER TABLE a_facturacion_sys MODIFY COLUMN sustento LONGBLOB;
