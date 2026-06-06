import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { ClipboardList, ShoppingCart, Scissors, PackageCheck, Package, Hammer } from 'lucide-react'
import CentroOperaciones from './CentroOperaciones'
import PedidosOnline from '../pedidos/PedidosOnline'
import PedidosFabricacion from '../fabricacion/PedidosFabricacion'
import StockPendienteFab from '../fabricacion/StockPendienteFab'
import Empaque from '../empaque/Empaque'
import Pendientes from '../pendientes/Pendientes'

// Pestañas (viñetas) de la ventana única de Operaciones
const TABS = [
  { id: 'resumen',     label: 'Resumen',      icon: ClipboardList, Comp: CentroOperaciones,  roles: ['administrador', 'vendedor', 'cajero'] },
  { id: 'web',         label: 'Pedidos Web',  icon: ShoppingCart,  Comp: PedidosOnline,      roles: ['administrador', 'vendedor'] },
  { id: 'fabricacion', label: 'Fabricación',  icon: Scissors,      Comp: PedidosFabricacion, roles: ['administrador', 'vendedor'] },
  { id: 'stockfab',    label: 'Stock Fab.',   icon: Hammer,        Comp: StockPendienteFab,  roles: ['administrador', 'vendedor'] },
  { id: 'empaque',     label: 'Empaque',      icon: PackageCheck,  Comp: Empaque,            roles: ['administrador', 'vendedor', 'cajero'] },
  { id: 'pendientes',  label: 'Pendientes',   icon: Package,       Comp: Pendientes,         roles: ['administrador', 'vendedor', 'cajero'] },
]

export default function Operaciones() {
  const { usuario } = useAuth()
  const [params, setParams] = useSearchParams()
  const rol = usuario?.rol

  const visibles = TABS.filter(t => t.roles.includes(rol))
  const activeId = params.get('tab') || 'resumen'
  const active = visibles.find(t => t.id === activeId) || visibles[0]
  const Active = active.Comp

  return (
    <div className="space-y-4">
      {/* Viñetas */}
      <div className="flex gap-1 border-b border-gray-200 overflow-x-auto">
        {visibles.map(t => (
          <button
            key={t.id}
            onClick={() => setParams({ tab: t.id })}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 whitespace-nowrap transition-colors ${
              active.id === t.id
                ? 'border-raloz-500 text-raloz-600 bg-raloz-50'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <t.icon size={15} /> {t.label}
          </button>
        ))}
      </div>

      {/* Contenido de la viñeta activa */}
      <div>
        <Active />
      </div>
    </div>
  )
}
