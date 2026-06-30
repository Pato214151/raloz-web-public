-- Migración: agregar columna prioridad a tabla tareas
-- Ejecutar UNA SOLA VEZ antes de iniciar el backend con la nueva versión

ALTER TABLE tareas
ADD COLUMN IF NOT EXISTS prioridad VARCHAR(10) DEFAULT 'MEDIA';

-- Actualizar tareas existentes que queden en NULL
UPDATE tareas SET prioridad = 'MEDIA' WHERE prioridad IS NULL;
