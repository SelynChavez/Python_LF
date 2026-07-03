-- Crear tabla a_compras_comb_detalles si no existe
CREATE TABLE IF NOT EXISTS a_compras_comb_detalles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    factura_id INT NOT NULL,
    producto VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255),
    cantidad DECIMAL(10, 2) NOT NULL,
    uom VARCHAR(20),
    precio DECIMAL(12, 4) NOT NULL,
    subtotal DECIMAL(12, 4) NOT NULL,
    webuser VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (factura_id) REFERENCES a_compras_comb(id) ON DELETE CASCADE
);
