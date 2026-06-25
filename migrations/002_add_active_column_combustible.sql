-- Migración: Agregar columna 'active' a la tabla a_combustible
-- Fecha: 2024-06-24
-- Descripción: Agrega la columna 'active' para marcar combustibles como activos o inactivos

ALTER TABLE a_combustible
ADD COLUMN IF NOT EXISTS active VARCHAR(1) DEFAULT 'S'
AFTER precio_promedio;

-- Mensaje de confirmación
SELECT 'Migración completada: Columna active agregada a a_combustible' AS status;
