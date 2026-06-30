-- Migración: crear tablas de Caja Diaria y Movimientos
-- Ejecutar UNA SOLA VEZ en el SQL Editor de Supabase

-- Tabla principal de caja diaria
CREATE TABLE IF NOT EXISTS caja_diaria (
    id_caja        SERIAL PRIMARY KEY,
    fecha_apertura TIMESTAMP NOT NULL,
    fecha_cierre   TIMESTAMP,
    usuario_apertura VARCHAR(100) NOT NULL,
    usuario_cierre   VARCHAR(100),
    monto_inicial  FLOAT DEFAULT 0,
    total_ventas   FLOAT DEFAULT 0,
    total_gastos   FLOAT DEFAULT 0,
    monto_esperado FLOAT DEFAULT 0,
    monto_real     FLOAT DEFAULT 0,
    diferencia     FLOAT DEFAULT 0,
    estado         VARCHAR(20) DEFAULT 'ABIERTA',
    observaciones  TEXT
);

-- Tabla de movimientos de caja
CREATE TABLE IF NOT EXISTS movimientos_caja (
    id_movimiento SERIAL PRIMARY KEY,
    id_caja       INTEGER NOT NULL REFERENCES caja_diaria(id_caja),
    tipo          VARCHAR(50) NOT NULL,
    concepto      VARCHAR(500),
    valor         FLOAT NOT NULL,
    metodo_pago   VARCHAR(50),
    referencia    VARCHAR(200),
    usuario       VARCHAR(100) NOT NULL,
    fecha_hora    TIMESTAMP DEFAULT NOW()
);

-- Índice para búsquedas por caja
CREATE INDEX IF NOT EXISTS idx_movimientos_caja ON movimientos_caja(id_caja);
