import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  LayoutDashboard, FileText, Search, CreditCard, Package,
  TrendingUp, Users, Wallet, BookOpen, Clock, UserCog,
  Menu, X, LogOut, ChevronDown
} from 'lucide-react'

const menuItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['administrador', 'vendedor', 'cajero'] },
  { path: '/facturacion', label: 'Nueva Venta', icon: FileText, roles: ['administrador', 'vendedor', 'cajero'] },
  { path: '/buscar', label: 'Buscar Facturas', icon: Search, roles: ['administrador', 'vendedor', 'cajero'] },
  { path: '/pagos', label: 'Pagos', icon: CreditCard, roles: ['administrador', 'vendedor', 'cajero'] },
  { path: '/stock', label: 'Inventario', icon: Package, roles: ['administrador', 'vendedor'] },
  { path: '/ventas', label: 'Hoja de Ventas', icon: TrendingUp, roles: ['administrador', 'vendedor'] },
  { path: '/clientes', label: 'Clientes', icon: Users, roles: ['administrador', 'vendedor', 'cajero'] },
  { path: '/gastos', label: 'Gastos', icon: Wallet, roles: ['administrador', 'cajero'] },
  { path: '/caja', label: 'Caja', icon: BookOpen, roles: ['administrador', 'cajero'] },
  { path: '/pendientes', label: 'Pendientes', icon: Clock, roles: ['administrador', 'vendedor'] },
  { path: '/usuarios', label: 'Usuarios', icon: UserCog, roles: ['administrador'] },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { usuario, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const filteredMenu = menuItems.filter(item => item.roles.includes(usuario?.rol))

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200
        transform transition-transform duration-200 ease-in-out
        lg:translate-x-0 lg:static lg:inset-auto
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-100">
          <div>
            <h1 className="text-xl font-bold text-raloz-700">RALOZ</h1>
            <p className="text-[10px] text-gray-400 -mt-1">COL SAS</p>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 140px)' }}>
          {filteredMenu.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-raloz-50 text-raloz-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="border-t border-gray-100 p-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-raloz-100 text-raloz-700 rounded-full flex items-center justify-center text-sm font-bold">
              {usuario?.usuario?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{usuario?.usuario}</p>
              <p className="text-xs text-gray-500 capitalize">{usuario?.rol}</p>
            </div>
            <button onClick={handleLogout} className="text-gray-400 hover:text-red-500 transition-colors" title="Cerrar sesión">
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
