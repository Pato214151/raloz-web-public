/** Centro de Finanzas: reportes, caja, gastos y hoja de ventas en pestañas. */

import { BarChart3, BookOpen, Wallet, TrendingUp } from 'lucide-react'
import Hub from '../common/Hub'
import Reportes from '../reportes/Reportes'
import Caja from '../caja/Caja'
import Gastos from '../gastos/Gastos'
import Ventas from '../ventas/Ventas'

// 💵 Finanzas: caja, gastos y reportes sobre los datos reales de ventas.
export default function FinanzasHub() {
  return (
    <Hub tabs={[
      { id: 'reportes', label: 'Reportes', icon: BarChart3,  element: <Reportes />, roles: ['administrador'] },
      { id: 'caja',     label: 'Caja',     icon: BookOpen,   element: <Caja />,     roles: ['administrador', 'cajero'] },
      { id: 'gastos',   label: 'Gastos',   icon: Wallet,     element: <Gastos />,   roles: ['administrador', 'cajero'] },
      { id: 'ventas',   label: 'Hoja de ventas', icon: TrendingUp, element: <Ventas />, roles: ['administrador', 'vendedor'] },
    ]} />
  )
}
