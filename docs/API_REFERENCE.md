# RALOZ Web Backend API Reference

## Base URL
```
http://localhost:5000/api
```

## Authentication
All endpoints require JWT token in Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

---

## PRECIOS API
**Base Path:** `/api/precios`

### List Prices
```http
GET /precios?colegio_id=5&producto_id=10&talla_grupo=6-8&page=1&per_page=20
```
**Auth:** Any authenticated user
**Params:**
- `colegio_id` (required): School ID
- `producto_id` (optional): Product ID
- `talla_grupo` (optional): Size group (6-8, 10-12, 14-16, S-M, L, XL)
- `page` (optional, default=1)
- `per_page` (optional, default=20, max=100)

**Response:** 200 OK
```json
{
  "precios": [
    {
      "id_precio": 1,
      "id_colegio": 5,
      "colegio_nombre": "Colegio A",
      "id_producto": 10,
      "producto_nombre": "Uniforme Niño",
      "talla_grupo": "6-8",
      "precio_unitario": 45000
    }
  ],
  "total": 150,
  "pages": 8,
  "page": 1
}
```

### Get Product Prices
```http
GET /precios/5/10
```
**Auth:** Any authenticated user

**Response:** 200 OK
```json
{
  "id_colegio": 5,
  "colegio_nombre": "Colegio A",
  "id_producto": 10,
  "producto_nombre": "Uniforme Niño",
  "precios": [
    {
      "talla_grupo": "6-8",
      "precio_unitario": 45000
    },
    {
      "talla_grupo": "10-12",
      "precio_unitario": 48000
    }
  ]
}
```

### Create/Update Price
```http
POST /precios
```
**Auth:** administrador only

**Request Body:**
```json
{
  "id_colegio": 5,
  "id_producto": 10,
  "talla_grupo": "6-8",
  "precio_unitario": 45000
}
```

**Response:** 201 Created or 200 OK

### Bulk Update Prices
```http
PUT /precios/bulk
```
**Auth:** administrador only

**Request Body:**
```json
{
  "precios": [
    {
      "id_colegio": 5,
      "id_producto": 10,
      "talla_grupo": "6-8",
      "precio_unitario": 45000
    },
    {
      "id_colegio": 5,
      "id_producto": 10,
      "talla_grupo": "10-12",
      "precio_unitario": 48000
    }
  ]
}
```

**Response:** 200 OK
```json
{
  "message": "Actualización en lote completada: 3 creados, 5 actualizados",
  "creados": 3,
  "actualizados": 5,
  "errores": [],
  "precios": [...]
}
```

### Delete Price
```http
DELETE /precios/1
```
**Auth:** administrador only

**Response:** 200 OK

---

## PENDIENTES API
**Base Path:** `/api/pendientes`

### List Pending Items
```http
GET /pendientes?estado=PENDIENTE&colegio_id=3&page=1&per_page=20
```
**Auth:** Any authenticated user
**Params:**
- `estado` (optional, default=PENDIENTE): PENDIENTE, ENTREGADO, CANCELADO
- `colegio_id` (optional): Filter by school
- `factura_id` (optional): Filter by invoice
- `page`, `per_page`: Pagination

**Response:** 200 OK
```json
{
  "pendientes": [
    {
      "id_pendiente": 1,
      "id_factura": 5,
      "numero_factura": "FAC-2026-000001",
      "id_colegio": 3,
      "colegio_nombre": "Colegio A",
      "producto_nombre": "Uniforme Niño",
      "talla": "8",
      "cantidad_faltante": 2,
      "estado": "PENDIENTE",
      "fecha_registro": "2026-02-28"
    }
  ],
  "total": 45,
  "pages": 3,
  "page": 1,
  "resumen": {
    "pendientes": 30,
    "entregados": 15,
    "cancelados": 0
  }
}
```

### Group Pending by School
```http
GET /pendientes/por-colegio?estado=PENDIENTE&ordenar=colegio
```
**Auth:** Any authenticated user
**Params:**
- `estado` (optional, default=PENDIENTE)
- `ordenar` (optional): colegio, fecha

**Response:** 200 OK
```json
{
  "pendientes_por_colegio": [
    {
      "id_colegio": 3,
      "colegio_nombre": "Colegio A",
      "total": 10,
      "items": [...]
    }
  ],
  "total_items": 45,
  "total_colegios": 8
}
```

### Pending Summary
```http
GET /pendientes/resumen
```
**Auth:** Any authenticated user

**Response:** 200 OK
```json
{
  "resumen": {
    "total_pendientes": 30,
    "total_entregados": 45,
    "total_cancelados": 2
  },
  "por_colegio": [
    {
      "id_colegio": 3,
      "pendientes": 5,
      "entregados": 10,
      "cancelados": 0
    }
  ]
}
```

### Mark as Delivered
```http
POST /pendientes/1/entregar
```
**Auth:** administrador, vendedor

**Optional Body:**
```json
{
  "observaciones": "Se entregó en persona"
}
```

**Response:** 200 OK

### Batch Deliver
```http
POST /pendientes/entregar-lote
```
**Auth:** administrador, vendedor

**Request Body:**
```json
{
  "ids": [1, 2, 3, 4, 5],
  "observaciones": "Entrega a granel"
}
```

**Response:** 200 OK
```json
{
  "message": "3 pendientes marcados como entregados",
  "entregas_exitosas": 3,
  "entregas_fallidas": 0,
  "errores": []
}
```

---

## EMPAQUE API
**Base Path:** `/api/empaque`

### Get Invoice for Review
```http
GET /empaque/factura/FAC-2026-000001
```
**Auth:** Any authenticated user

**Response:** 200 OK
```json
{
  "factura": {
    "id_factura": 5,
    "numero_factura": "FAC-2026-000001",
    "cliente_nombre": "Juan Pérez",
    "colegio_nombre": "Colegio A",
    "total": 150000,
    "estado": "PAGADA",
    "estado_entrega": "POR_ENTREGAR",
    "detalles": [
      {
        "producto_nombre": "Uniforme Niño",
        "talla": "8",
        "cantidad": 2,
        "precio_unitario": 45000,
        "subtotal": 90000
      }
    ]
  },
  "prendas_pendientes": []
}
```

### Register Pending Garments
```http
POST /empaque/registrar
```
**Auth:** administrador, vendedor

**Request Body:**
```json
{
  "id_factura": 5,
  "prendas": [
    {
      "producto_nombre": "Uniforme Niño",
      "talla": "8",
      "cantidad": 1,
      "observaciones": "Sin costuras"
    },
    {
      "producto_nombre": "Uniforme Niño",
      "talla": "10",
      "cantidad": 1,
      "observaciones": "Falta dobladillo"
    }
  ]
}
```

**Response:** 201 Created
```json
{
  "message": "2 prendas registradas",
  "prendas_registradas": 2,
  "prendas": [...]
}
```

### Mark Invoice Ready
```http
POST /empaque/todo-listo/5
```
**Auth:** administrador, vendedor

**Optional Body:**
```json
{
  "observaciones": "Todas las prendas listas"
}
```

**Response:** 200 OK
```json
{
  "message": "Factura marcada como lista para empaque",
  "factura": {
    "id_factura": 5,
    "numero_factura": "FAC-2026-000001",
    "estado_entrega": "LISTO_EMPAQUE"
  }
}
```

---

## VENTAS API
**Base Path:** `/api/ventas`

### Daily Sales Sheet
```http
GET /ventas/hoja?fecha=2026-02-28
```
**Auth:** Any authenticated user
**Params:**
- `fecha` (optional, default=today, format=YYYY-MM-DD)

**Response:** 200 OK
```json
{
  "fecha": "2026-02-28",
  "resumen": {
    "total_facturas": 10,
    "total_ventas": 1500000,
    "total_cobrado": 1300000,
    "total_gastos": 150000,
    "utilidad": 1150000,
    "saldo_pendiente": 200000
  },
  "facturas": [
    {
      "numero_factura": "FAC-2026-000001",
      "cliente_nombre": "Juan Pérez",
      "colegio_nombre": "Colegio A",
      "total": 150000,
      "estado": "PAGADA",
      "metodo_pago": "EFECTIVO"
    }
  ],
  "pagos": [
    {
      "numero_factura": "FAC-2026-000001",
      "valor": 150000,
      "metodo": "EFECTIVO"
    }
  ],
  "gastos": [
    {
      "descripcion": "Combustible",
      "valor": 50000,
      "categoria": "TRANSPORTE"
    }
  ]
}
```

### Payment Method Summary
```http
GET /ventas/resumen-metodos?fecha_desde=2026-02-01&fecha_hasta=2026-02-28&colegio_id=3
```
**Auth:** Any authenticated user
**Params:**
- `fecha_desde` (required, format=YYYY-MM-DD)
- `fecha_hasta` (required, format=YYYY-MM-DD)
- `colegio_id` (optional)

**Response:** 200 OK
```json
{
  "fecha_desde": "2026-02-01",
  "fecha_hasta": "2026-02-28",
  "resumen_general": {
    "total_cobrado": 1500000,
    "total_pendiente": 300000,
    "total_anulado": 50000
  },
  "por_metodo": [
    {
      "metodo": "EFECTIVO",
      "total": 800000,
      "cantidad": 5,
      "porcentaje": 53.3
    },
    {
      "metodo": "NEQUI",
      "total": 500000,
      "cantidad": 8,
      "porcentaje": 33.3
    }
  ],
  "por_colegio": [
    {
      "id_colegio": 3,
      "colegio_nombre": "Colegio A",
      "total_cobrado": 600000,
      "total_pendiente": 150000,
      "efectivo": 400000,
      "nequi": 200000,
      "daviplata": 0,
      "bancolombia": 0,
      "transferencia": 0
    }
  ]
}
```

---

## REPORTES API ENHANCEMENTS
**Base Path:** `/api/reportes`

### Accounting Report
```http
GET /reportes/cuentas?fecha_desde=2026-02-01&fecha_hasta=2026-02-28&colegio_id=3
```
**Auth:** Any authenticated user

**Response:** 200 OK
```json
{
  "fecha_desde": "2026-02-01",
  "fecha_hasta": "2026-02-28",
  "resumen": {
    "total_ingresos": 1500000,
    "total_gastos": 150000,
    "utilidad_bruta": 1350000,
    "total_cobrado": 1300000,
    "total_pendiente": 200000,
    "utilidad_neta": 1150000
  },
  "detalles_ingresos": {
    "facturas": 1500000,
    "cantidad_facturas": 10,
    "ticket_promedio": 150000
  },
  "detalles_egresos": {
    "gastos": 150000,
    "cantidad_gastos": 5
  },
  "por_colegio": [
    {
      "id_colegio": 3,
      "colegio_nombre": "Colegio A",
      "ingresos": 600000,
      "gastos": 50000,
      "utilidad": 550000,
      "cobrado": 500000,
      "pendiente": 100000
    }
  ]
}
```

### Sales by School
```http
GET /reportes/ventas-por-colegio?fecha_desde=2026-02-01&fecha_hasta=2026-02-28&ordenar=ventas
```
**Auth:** Any authenticated user
**Params:**
- `fecha_desde` (required)
- `fecha_hasta` (required)
- `ordenar` (optional): ventas, facturas, nombre

**Response:** 200 OK
```json
{
  "fecha_desde": "2026-02-01",
  "fecha_hasta": "2026-02-28",
  "resumen_general": {
    "total_ventas": 1500000,
    "total_facturas": 15,
    "cantidad_colegios": 8
  },
  "por_colegio": [
    {
      "id_colegio": 3,
      "colegio_nombre": "Colegio A",
      "total_ventas": 600000,
      "cantidad_facturas": 6,
      "ticket_promedio": 100000,
      "total_cobrado": 500000,
      "saldo_pendiente": 100000,
      "estado_cobro": "PARCIAL"
    }
  ]
}
```

---

## SIZE REFERENCE

### Valid Individual Sizes (for Stock)
- Children: 4, 6, 8, 10, 12, 14, 16
- Adult: S, M, L, XL

### Valid Grouped Sizes (for Pricing)
- 4, 6-8, 10-12, 14-16, S-M, L, XL

### Automatic Conversion
- 4 → 4
- 6, 8 → 6-8
- 10, 12 → 10-12
- 14, 16 → 14-16
- S, M → S-M
- L → L
- XL → XL

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 500 | Server Error |

---

## Payment Methods
- EFECTIVO
- NEQUI
- DAVIPLATA
- BANCOLOMBIA
- TRANSFERENCIA

---

## Invoice States
- PENDIENTE: Awaiting payment
- PAGADA: Fully paid
- ANULADA: Cancelled

---

## Delivery States
- POR_ENTREGAR: Pending delivery
- LISTO_EMPAQUE: Ready for packaging
- ENTREGADO: Delivered

---

## Error Response Format

All errors follow this format:
```json
{
  "error": "Descriptive error message",
  "code": "optional_error_code"
}
```

---

## Rate Limiting

API is rate limited to 200 requests per minute per IP.

---

## Version
API Version: 1.0.0-beta
