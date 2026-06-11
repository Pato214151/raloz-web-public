/**
 * Tipos de dominio compartidos — RALOZ COL SAS.
 *
 * Reflejan las formas que devuelve el backend (los `to_dict()` de los modelos
 * Flask). Punto de partida de la migración gradual a TypeScript: los archivos
 * que se vayan convirtiendo a .ts/.tsx pueden importar estos tipos para tener
 * autocompletado y verificación. Ampliar a medida que se tipen más pantallas.
 */

export type Rol = 'administrador' | 'vendedor' | 'cajero';

export interface Usuario {
  id_usuario: number;
  usuario: string;
  email: string;
  rol: Rol;
  activo: boolean;
  avatar_url?: string | null;
}

export interface Colegio {
  id_colegio: number;
  nombre: string;
  ciudad?: string | null;
  activo?: boolean;
}

export interface Producto {
  id_producto: number;
  codigo?: string | null;
  nombre: string;
  tipo?: string | null;
  activo?: boolean;
}

export interface Stock {
  id_stock: number;
  id_colegio: number;
  id_producto: number;
  talla_individual: string;
  cantidad: number;
}

/** Estado de entrega de una factura/pedido (flujo logístico). */
export type EstadoEntrega = 'POR_ENTREGAR' | 'EMPACADO' | 'ENTREGADO';

/** Estado de cobro de una factura. */
export type EstadoFactura = 'PAGADA' | 'ABONO' | 'ANULADA';

export interface FacturaDetalle {
  id_producto: number;
  talla_individual: string;
  cantidad: number;
  precio_unitario: number;
  total_linea: number;
}

export interface Factura {
  id_factura: number;
  numero_factura: string;
  id_colegio?: number | null;
  cliente_nombre?: string;
  cliente_telefono?: string;
  cliente_email?: string;
  total: number;
  total_abonado?: number;
  saldo_pendiente?: number;
  estado: EstadoFactura;
  estado_entrega: EstadoEntrega;
  fecha_factura?: string;
}

/** Estado de un pedido de la tienda online. */
export type EstadoPedidoWeb =
  | 'pendiente'
  | 'pagado'
  | 'fallido'
  | 'cancelado'
  | 'reembolsado';

export interface PedidoWeb {
  id_pedido: number;
  referencia: string;
  nombre_cliente: string;
  email_cliente: string;
  telefono_cliente?: string;
  nombre_colegio?: string;
  total: number;
  total_orden?: number;
  estado: EstadoPedidoWeb;
  tiene_fabricacion?: boolean;
  id_factura?: number | null;
  estado_entrega?: EstadoEntrega | null;
  factura_numero?: string | null;
}

/** Sobre genérico paginado que usan varios endpoints de listado. */
export interface ListaPaginada<T> {
  total: number;
  limit?: number;
  offset?: number;
  [key: string]: T[] | number | undefined;
}
