import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  LayoutDashboard, FileText, Search, Package,
  TrendingUp, Users, Wallet, BookOpen, UserCog,
  Menu, X, LogOut, ChevronDown, BarChart3, AlertCircle, DollarSign, Settings, ClipboardList, Hammer
} from 'lucide-react'

const menuGroups = [
  {
    groupId: 'dashboard',
    label: 'DASHBOARD',
    icon: '📊',
    items: [
      { path: '/', label: 'Inicio', icon: LayoutDashboard, roles: ['administrador', 'vendedor', 'cajero'] },
    ]
  },
  {
    groupId: 'ventas',
    label: 'VENTAS',
    icon: '🛒',
    items: [
      { path: '/facturacion', label: 'Nueva Venta', icon: FileText, roles: ['administrador', 'vendedor', 'cajero'] },
      { path: '/buscar', label: 'Buscar Facturas', icon: Search, roles: ['administrador', 'vendedor', 'cajero'] },
      { path: '/ventas', label: 'Hoja de Ventas', icon: TrendingUp, roles: ['administrador', 'vendedor'] },
      { path: '/cuentas', label: 'Cuentas por Cobrar', icon: AlertCircle, roles: ['administrador', 'vendedor'] },
    ]
  },
  {
    groupId: 'inventario',
    label: 'INVENTARIO',
    icon: '📦',
    items: [
      { path: '/stock', label: 'Stock Actual', icon: Package, roles: ['administrador', 'vendedor'] },
      { path: '/fabricacion/stock', label: 'Stock Pendiente', icon: Hammer, roles: ['administrador', 'vendedor'] },
      { path: '/precios', label: 'Precios por Colegio', icon: DollarSign, roles: ['administrador'] },
    ]
  },
  {
    groupId: 'fabricacion',
    label: 'FABRICACIÓN',
    icon: '⚙️',
    items: [
      { path: '/fabricacion', label: 'Pedidos de Fabricación', icon: BarChart3, roles: ['administrador', 'vendedor'] },
      { path: '/pedidos-online', label: 'Órdenes de Producción', icon: ClipboardList, roles: ['administrador', 'vendedor'] },
    ]
  },
  {
    groupId: 'finanzas',
    label: 'FINANZAS',
    icon: '💰',
    items: [
      { path: '/gastos', label: 'Gastos', icon: Wallet, roles: ['administrador', 'cajero'] },
      { path: '/caja', label: 'Caja', icon: BookOpen, roles: ['administrador', 'cajero'] },
      { path: '/reportes', label: 'Reportes', icon: BarChart3, roles: ['administrador'] },
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
    groupId: 'configuracion',
    label: 'CONFIGURACIÓN',
    icon: '🔧',
    items: [
      { path: '/usuarios', label: 'Usuarios', icon: UserCog, roles: ['administrador'] },
      { path: '/configuracion', label: 'Colegios', icon: Settings, roles: ['administrador'] },
      { path: '/tareas', label: 'Tareas / Pendientes', icon: ClipboardList, roles: ['administrador', 'vendedor', 'cajero'] },
    ]
  },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [expandedGroups, setExpandedGroups] = useState(
    menuGroups.reduce((acc, group) => ({...acc, [group.groupId]: true}), {})
  )
  const { usuario, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const toggleGroup = (groupId) => {
    setExpandedGroups(prev => ({...prev, [groupId]: !prev[groupId]}))
  }

  // Filter groups and items based on user role
  const filteredGroups = menuGroups
    .map(group => ({
      ...group,
      items: group.items.filter(item => item.roles.includes(usuario?.rol))
    }))
    .filter(group => group.items.length > 0)

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64
        transform transition-transform duration-200 ease-in-out
        lg:translate-x-0 lg:static lg:inset-auto
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        bg-slate-900 border-r border-slate-800 flex flex-col
      `}>
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-white">RALOZ</h1>
            <p className="text-[10px] text-gray-400 -mt-1">COL SAS</p>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-gray-400 hover:text-gray-300">
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 140px)' }}>
          {filteredGroups.map(group => (
            <div key={group.groupId} className="mb-6">
              {/* Group Header */}
              <button
                onClick={() => toggleGroup(group.groupId)}
                className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-300 transition-colors mb-2"
              >
                <span className="flex items-center gap-2">
                  <span>{group.icon}</span>
                  {group.label}
                </span>
                <ChevronDown
                  size={16}
                  className={`transition-transform duration-200 ${
                    expandedGroups[group.groupId] ? 'rotate-180' : ''
                  }`}
                />
              </button>

              {/* Group Items */}
              <div
                className={`overflow-hidden transition-all duration-200 ${
                  expandedGroups[group.groupId] ? 'max-h-96' : 'max-h-0'
                }`}
              >
                <div className="space-y-1">
                  {group.items.map(item => (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.path === '/'}
                      onClick={() => setSidebarOpen(false)}
                      className={({ isActive }) =>
                        `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                          isActive
                            ? 'bg-slate-800 text-amber-400 border-l-2 border-amber-400 pl-3.5'
                            : 'text-gray-300 hover:bg-slate-800 hover:text-gray-100'
                        }`
                      }
                    >
                      <item.icon size={16} />
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </nav>

        {/* User */}
        <div className="border-t border-slate-800 p-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-amber-500 text-slate-900 rounded-full flex items-center justify-center text-sm font-bold">
              {usuario?.usuario?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{usuario?.usuario}</p>
              <p className="text-xs text-gray-400 capitalize">{usuario?.rol}</p>
            </div>
            <button onClick={handleLogout} className="text-gray-400 hover:text-red-400 transition-colors" title="Cerrar sesión">
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      {/* Overlay móvil */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center px-4 lg:px-6 shrink-0">
          <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-gray-600 mr-4">
            <Menu size={24} />
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400 hidden sm:block">v1.0.0-beta</span>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-auto p-4 lg:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
