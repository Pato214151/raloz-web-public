import { Activity, DollarSign, Scissors, History, ClipboardCheck } from 'lucide-react'
import Hub from '../common/Hub'
import StockView from '../stock/StockView'
import Movimientos from '../stock/Movimientos'
import ConteoFisico from '../stock/ConteoFisico'
import Precios from '../precios/Precios'
import OrdenesProduccion from '../ordenes-produccion/OrdenesProduccion'

// 📦 Catálogo: inventario, conteo físico, movimientos (kardex), precios y producción.
// Nota: la creación de productos/colegios vive por ahora en Configuración.
export default function CatalogoHub() {
  return (
    <Hub tabs={[
      { id: 'inventario',  label: 'Inventario',    icon: Activity,       element: <StockView />, roles: ['administrador', 'vendedor'] },
      { id: 'conteo',      label: 'Conteo físico', icon: ClipboardCheck, element: <ConteoFisico />, roles: ['administrador'] },
      { id: 'movimientos', label: 'Movimientos',   icon: History,        element: <Movimientos />, roles: ['administrador', 'vendedor'] },
      { id: 'precios',     label: 'Precios',       icon: DollarSign,     element: <Precios />,   roles: ['administrador'] },
      { id: 'produccion',  label: 'Producción',    icon: Scissors,       element: <OrdenesProduccion />, roles: ['administrador'] },
    ]} />
  )
}
