import { ShoppingCart, Search, AlertCircle, CreditCard } from 'lucide-react'
import Hub from '../common/Hub'
import Vender from '../facturacion/Vender'
import BuscarFacturas from '../facturacion/BuscarFacturas'
import CuentasPorCobrar from '../reportes/CuentasPorCobrar'
import Pagos from '../pagos/Pagos'

// 💰 Centro de Ventas: nueva venta, facturas, por cobrar y pagos en un solo lugar.
export default function VentasHub() {
  return (
    <Hub tabs={[
      { id: 'nueva',     label: 'Nueva venta',    icon: ShoppingCart, element: <Vender /> },
      { id: 'todas',     label: 'Facturas',       icon: Search,       element: <BuscarFacturas /> },
      { id: 'porcobrar', label: 'Por cobrar',     icon: AlertCircle,  element: <CuentasPorCobrar />, roles: ['administrador', 'vendedor'] },
      { id: 'pago',      label: 'Registrar pago', icon: CreditCard,   element: <Pagos />,           roles: ['administrador', 'cajero'] },
    ]} />
  )
}
