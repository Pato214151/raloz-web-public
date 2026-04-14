import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  LayoutDashboard, FileText, Search, Package, TrendingUp, Users, Wallet,
  BookOpen, UserCog, Menu, X, LogOut, ChevronDown, BarChart3, AlertCircle,
  DollarSign, Settings, ClipboardList, Hammer, CreditCard, PackageCheck,
  ShoppingCart, Scissors, Truck,
} from 'lucide-react'

const menuGroups = [
  {
    groupId: 'dashboard',
    label: 'INICIO',
    icon: '📊',
    items: [
      { path: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['administrador', 'vendedor', 'cajero'] },
    ]
  },
  {
    groupId: 'ventas',
    label: 'VENTAS',
    icon: '🛒',
    items: [
      { path: '/facturacion',  label: 'Nueva Venta',        icon: FileText,    roles: ['administrador', 'vendedor', 'cajero'] },
      { path: '/buscar',       label: 'Buscar Facturas',    icon: Search,      roles: ['administrador', 'vendedor', 'cajero'] },
      { path: '/pagos',        label: 'Registrar Pago',     icon: CreditCard,  roles: ['administrador', 'cajero'] },
      { path: '/ventas',       label: 'Hoja de Ventas',     icon: TrendingUp,  roles: ['administrador', 'vendedor'] },
      { path: '/cuentas',      label: 'Cuentas por Cobrar', icon: AlertCircle, roles: ['administrador', 'vendedor'] },
    ]
  },
  {
    groupId: 'pedidos',
    label: 'PEDIDOS',
    icon: '📬',
    items: [
      { path: '/pedidos-online', label: 'Pedidos Online',       icon: ShoppingCart, roles: ['administrador', 'vendedor'] },
      { path: '/fabricacion',    label: 'Fabricación',          icon: Scissors,     roles: ['administrador', 'vendedor'] },
      { path: '/fabricacion/stock', label: 'Stock Fabricación', icon: Hammer,       roles: ['administrador', 'vendedor'] },
    ]
  },
  {
    groupId: 'entregas',
    label: 'ENTREGAS',
    icon: '🚚',
    items: [
      { path: '/pendientes', label: 'Prendas Pendientes', icon: Package,      roles: ['administrador', 'vendedor', 'cajero'] },
      { path: '/empaque',    label: 'Empaque',            icon: PackageCheck, roles: ['administrador', 'vendedor', 'cajero'] },
    ]
  },
  {
    groupId: 'inventario',
    label: 'INVENTARIO',
    icon: '📦',
    items: [
      { path: '/stock',   label: 'Stock Actual',      icon: Package,    roles: ['administrador', 'vendedor'] },
      { path: '/precios', label: 'Precios Colegios',  icon: DollarSign, roles: ['administrador'] },
    ]
  },
  {
    groupId: 'finanzas',
    label: 'FINANZAS',
    icon: '💰',
    items: [
      { path: '/gastos',   label: 'Gastos',    icon: Wallet,   roles: ['administrador', 'cajero'] },
      { path: '/caja',     label: 'Caja',      icon: BookOpen, roles: ['administrador', 'cajero'] },
      { path: '/reportes', label: 'Reportes',  icon: BarChart3, roles: ['administrador'] },
    ]
  },
  {
    groupId: 'clientes',
    label: 'CLIENTES',
    icon: '👥',
    items: [
      { path: '/clientes', label: 'Listado de Clientes', icon: Users, roles: ['administrador', 'vendedor', 'cajero'] },
    ]
  },
  {
    groupId: 'config',
    label: 'CONFIGURACIÓN',
    icon: '🔧',
    items: [
      { path: '/usuarios',      label: 'Usuarios',    icon: UserCog,      roles: ['administrador'] },
      { path: '/configuracion', label: 'Colegios',    icon: Settings,     roles: ['administrador'] },
      { path: '/tareas',        label: 'Tareas',      icon: ClipboardList, roles: ['administrador', 'vendedor', 'cajero'] },
    ]
  },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [expandedGroups, setExpandedGroups] = useState(
    menuGroups.reduce((acc, g) => ({ ...acc, [g.groupId]: true }), {})
  )
  const { usuario, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }
  const toggleGroup = (id) => setExpandedGroups(prev => ({ ...prev, [id]: !prev[id] }))

  const filteredGroups = menuGroups
    .map(g => ({ ...g, items: g.items.filter(i => i.roles.includes(usuario?.rol)) }))
    .filter(g => g.items.length > 0)

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-60
        transform transition-transform duration-200 ease-in-out
        lg:translate-x-0 lg:static lg:inset-auto
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        bg-slate-900 border-r border-slate-800 flex flex-col
      `}>
        {/* Logo */}
        <div className="flex items-center justify-between h-14 px-5 border-b border-slate-800 shrink-0">
          <div>
            <h1 className="text-lg font-bold text-white tracking-wide">RALOZ</h1>
            <p className="text-[9px] text-amber-400 -mt-0.5 font-medium tracking-widest">COL SAS · POS</p>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-gray-400 hover:text-gray-300">
            <X size={18} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 overflow-y-auto space-y-1">
          {filteredGroups.map(group => (
            <div key={group.groupId} className="mb-1">
              <button
                onClick={() => toggleGroup(group.groupId)}
                className="w-full flex items-center justify-between px-2 py-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-widest hover:text-slate-400 transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <span className="text-xs">{group.icon}</span>
                  {group.label}
                </span>
                <ChevronDown
                  size={12}
                  className={`transition-transform duration-200 ${expandedGroups[group.groupId] ? 'rotate-180' : ''}`}
                />
              </button>

              <div className={`overflow-hidden transition-all duration-200 ${expandedGroups[group.groupId] ? 'max-h-96' : 'max-h-0'}`}>
                <div className="space-y-0.5 mt-0.5">
                  {group.items.map(item => (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.path === '/'}
                      onClick={() => setSidebarOpen(false)}
                      className={({ isActive }) =>
                        `flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all ${
                          isActive
                            ? 'bg-amber-500/15 text-amber-400 border-l-2 border-amber-400 pl-2.5'
                            : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                        }`
                      }
                    >
                      <item.icon size={14} />
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </nav>

        {/* User footer */}
        <div className="border-t border-slate-800 p-3 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-amber-500 text-slate-900 rounded-full flex items-center justify-center text-xs font-bold shrink-0">
              {usuario?.usuario?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-white truncate">{usuario?.usuario}</p>
              <p className="text-[10px] text-slate-400 capitalize">{usuario?.rol}</p>
            </div>
            <button onClick={handleLogout} className="text-slate-500 hover:text-red-400 transition-colors" title="Cerrar sesión">
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* Overlay móvil */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-12 bg-white border-b border-gray-200 flex items-center px-4 shrink-0">
          <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-gray-600 mr-3">
            <Menu size={20} />
          </button>
          <div className="flex-1" />
          <span className="text-[11px] text-gray-400">v1.0</span>
        </header>

        <div className="flex-1 overflow-auto p-4 lg:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
