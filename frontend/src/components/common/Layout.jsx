import { useState, useEffect } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import {
  LayoutDashboard, FileText, Search, Package, TrendingUp, Users, Wallet,
  BookOpen, UserCog, Menu, X, LogOut, ChevronDown, BarChart3, AlertCircle,
  DollarSign, Settings, ClipboardList, Hammer, CreditCard, PackageCheck,
  ShoppingCart, Scissors, Truck, Activity, ChevronRight,   MessageCircle, CalendarClock, MessageSquare,
  Clock, Inbox, ListTodo, PackageX, Megaphone, Zap, Home,
} from 'lucide-react'

// ─── Barra inferior (solo móvil): accesos directos a lo más usado ──
const bottomNavItems = [
  { path: '/',            label: 'Inicio', icon: Home,          roles: ['administrador', 'vendedor', 'cajero'] },
  { path: '/vender',      label: 'Vender', icon: ShoppingCart,  roles: ['administrador', 'vendedor', 'cajero'] },
  { path: '/stock',       label: 'Stock',  icon: Activity,      roles: ['administrador', 'vendedor']           },
  { path: '/whatsapp',    label: 'Chat',   icon: MessageCircle, roles: ['administrador', 'vendedor', 'cajero'] },
  { path: '/caja',        label: 'Caja',   icon: BookOpen,      roles: ['administrador', 'cajero']             },
]

// ─── Grupos de navegación reorganizados ─────────────────────────
const menuGroups = [
  {
    groupId: 'dashboard',
    label: 'Inicio',
    items: [
      { path: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['administrador', 'vendedor', 'cajero'] },
    ],
  },
  {
    groupId: 'ventas',
    label: 'Ventas',
    items: [
      { path: '/vender',      label: 'Nueva Venta',     icon: ShoppingCart, roles: ['administrador', 'vendedor', 'cajero'] },
      { path: '/buscar',      label: 'Buscar Facturas', icon: Search,       roles: ['administrador', 'vendedor', 'cajero'] },
      { path: '/pagos',       label: 'Registrar Pago',  icon: CreditCard,   roles: ['administrador', 'cajero']            },
      { path: '/cuentas',     label: 'Por Cobrar',      icon: AlertCircle,  roles: ['administrador', 'vendedor']          },
      { path: '/clientes',    label: 'Clientes',        icon: Users,        roles: ['administrador', 'vendedor', 'cajero'] },
    ],
  },
  {
    // Una sola entrada: la pantalla Operaciones ya junta Pedidos Web,
    // Fabricación, Stock Fab, Empaque y Por Entregar en pestañas.
    groupId: 'pedidos',
    label: 'Pedidos y Entregas',
    items: [
      { path: '/operaciones', label: 'Pedidos y Entregas', icon: ClipboardList, roles: ['administrador', 'vendedor', 'cajero'] },
    ],
  },
  {
    groupId: 'inventario',
    label: 'Inventario',
    items: [
      { path: '/stock',               label: 'Stock Actual',        icon: Activity,   roles: ['administrador', 'vendedor'] },
      { path: '/precios',             label: 'Precios Colegios',    icon: DollarSign, roles: ['administrador']             },
      { path: '/ordenes-produccion',  label: 'Órdenes de Producción', icon: Scissors, roles: ['administrador']           },
    ],
  },
  {
    groupId: 'finanzas',
    label: 'Dinero',
    items: [
      { path: '/caja',      label: 'Caja',           icon: BookOpen,   roles: ['administrador', 'cajero']   },
      { path: '/gastos',    label: 'Gastos',         icon: Wallet,     roles: ['administrador', 'cajero']   },
      { path: '/reportes',  label: 'Reportes',       icon: BarChart3,  roles: ['administrador']             },
      { path: '/ventas',    label: 'Hoja de Ventas', icon: TrendingUp, roles: ['administrador', 'vendedor'] },
    ],
  },
  {
    groupId: 'comunicacion',
    label: 'Comunicación',
    items: [
      { path: '/whatsapp', label: 'WhatsApp', icon: MessageCircle, roles: ['administrador', 'vendedor', 'cajero'] },
      { path: '/citas',    label: 'Citas',    icon: CalendarClock, roles: ['administrador', 'vendedor', 'cajero'] },
      { path: '/leads',    label: 'Leads',    icon: MessageSquare, roles: ['administrador', 'vendedor']           },
      { path: '/avisos',   label: 'Avisos',   icon: Megaphone,     roles: ['administrador']                       },
    ],
  },
  {
    groupId: 'tienda',
    label: 'Tienda online',
    items: [
      { path: '/publicaciones',  label: 'Publicaciones',  icon: Megaphone, roles: ['administrador'] },
      { path: '/automatizacion', label: 'Automatización', icon: Zap,       roles: ['administrador'] },
    ],
  },
  {
    groupId: 'ajustes',
    label: 'Ajustes',
    items: [
      { path: '/configuracion', label: 'Colegios', icon: Settings, roles: ['administrador']                        },
      { path: '/usuarios',      label: 'Usuarios', icon: UserCog,  roles: ['administrador']                        },
      { path: '/tareas',        label: 'Tareas',   icon: ListTodo, roles: ['administrador', 'vendedor', 'cajero'] },
    ],
  },
]

// Mapeo ruta → título para el header dinámico
const PAGE_TITLES = {
  '/':                      'Dashboard',
  '/facturacion':           'Nueva Venta (clásica)',
  '/vender':                'Nueva Venta',
  '/buscar':                'Buscar Facturas',
  '/pagos':                 'Registrar Pago',
  '/ventas':                'Hoja de Ventas',
  '/cuentas':              'Cuentas por Cobrar',
  '/clientes':              'Clientes',
  '/whatsapp':              'WhatsApp',
  '/escribir-cliente':      'Escribir a cliente',
  '/leads':                'Leads',
  '/citas':                'Citas',
  '/pedidos-online':        'Centro de Pedidos',
  '/fabricacion':           'Fabricación',
  '/fabricacion/stock':     'Stock Fabricación',
  '/pendientes':            'Por Entregar',
  '/empaque':               'Empaque',
  '/stock':                 'Stock Actual',
  '/publicaciones':         'Publicaciones',
  '/automatizacion':        'Automatización',
  '/avisos':                'Avisos',
  '/precios':               'Precios Colegios',
  '/ordenes-produccion':    'Órdenes de Producción',
  '/gastos':                'Gastos',
  '/caja':                  'Caja',
  '/reportes':              'Reportes',
  '/usuarios':              'Usuarios',
  '/configuracion':          'Configuración',
  '/tareas':                'Tareas',
  '/operaciones':           'Pedidos y Entregas',
}

// Grupos que arrancan colapsados por defecto
const DEFAULT_COLLAPSED = ['inventario', 'finanzas', 'comunicacion', 'tienda', 'ajustes']

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [expandedGroups, setExpandedGroups] = useState(
    menuGroups.reduce((acc, g) => ({
      ...acc,
      [g.groupId]: !DEFAULT_COLLAPSED.includes(g.groupId),
    }), {})
  )
  const { usuario, logout } = useAuth()
  const navigate  = useNavigate()
  const location  = useLocation()

  // Badge de pedidos online nuevos (pagados, aún sin procesar). Refresca cada 45 s.
  const [nuevosPedidos, setNuevosPedidos] = useState(0)
  const puedeVerPedidos = ['administrador', 'vendedor'].includes(usuario?.rol)
  useEffect(() => {
    if (!puedeVerPedidos) return
    let activo = true
    const cargar = async () => {
      try {
        const res = await api.get('/tienda/admin/pedidos/conteo-nuevos')
        if (activo) setNuevosPedidos(res.data?.nuevos || 0)
      } catch { /* silencioso */ }
    }
    cargar()
    const id = setInterval(cargar, 45000)
    return () => { activo = false; clearInterval(id) }
  }, [puedeVerPedidos])

  // Badge de WhatsApp: mensajes de clientes sin leer. Refresca cada 25 s.
  const [waNoLeidos, setWaNoLeidos] = useState(0)
  useEffect(() => {
    let activo = true
    const cargar = async () => {
      try {
        const res = await api.get('/wa/no-leidos')
        if (activo) setWaNoLeidos(res.data?.no_leidos || 0)
      } catch { /* silencioso */ }
    }
    cargar()
    const id = setInterval(cargar, 25000)
    return () => { activo = false; clearInterval(id) }
  }, [])

  // Badge de citas pendientes. Refresca cada 30 s.
  const [citasPend, setCitasPend] = useState(0)
  useEffect(() => {
    let activo = true
    const cargar = async () => {
      try {
        const res = await api.get('/citas/pendientes/conteo')
        if (activo) setCitasPend(res.data?.pendientes || 0)
      } catch { /* silencioso */ }
    }
    cargar()
    const id = setInterval(cargar, 30000)
    return () => { activo = false; clearInterval(id) }
  }, [])

  // Badge de leads pendientes (canal web + WhatsApp). Refresca cada 45 s.
  const [leadsPend, setLeadsPend] = useState(0)
  const puedeVerLeads = ['administrador', 'vendedor'].includes(usuario?.rol)
  useEffect(() => {
    if (!puedeVerLeads) return
    let activo = true
    const cargar = async () => {
      try {
        const res = await api.get('/leads/resumen')
        if (activo) setLeadsPend(res.data?.pendientes || 0)
      } catch { /* silencioso */ }
    }
    cargar()
    const id = setInterval(cargar, 45000)
    return () => { activo = false; clearInterval(id) }
  }, [puedeVerLeads])

  const handleLogout = () => { logout(); navigate('/login') }
  const toggleGroup  = (id) => setExpandedGroups(prev => ({ ...prev, [id]: !prev[id] }))

  const filteredGroups = menuGroups
    .map(g => ({ ...g, items: g.items.filter(i => i.roles.includes(usuario?.rol)) }))
    .filter(g => g.items.length > 0)

  const pageTitle = PAGE_TITLES[location.pathname] ?? 'RALOZ'

  const rolLabel = {
    administrador: 'Administrador',
    vendedor:      'Vendedor',
    cajero:        'Cajero',
  }[usuario?.rol] ?? usuario?.rol

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">

      {/* ── Sidebar ────────────────────────────────────────────── */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64
        transform transition-transform duration-200 ease-in-out
        lg:translate-x-0 lg:static lg:inset-auto
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        bg-slate-900 flex flex-col
      `}>

        {/* Logo */}
        <div className="flex items-center justify-between h-14 px-5 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-amber-400 rounded-md flex items-center justify-center shrink-0">
              <span className="text-slate-900 font-black text-xs leading-none">R</span>
            </div>
            <div>
              <p className="text-white font-bold text-sm leading-tight tracking-wide">RALOZ COL</p>
              <p className="text-amber-400/70 text-[9px] font-semibold tracking-widest leading-tight">SISTEMA POS</p>
            </div>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-slate-500 hover:text-slate-300 transition-colors">
            <X size={17} />
          </button>
        </div>

        {/* Navegación */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-0.5 scrollbar-thin">
          {filteredGroups.map((group, gi) => (
            <div key={group.groupId} className={gi > 0 ? 'pt-1' : ''}>

              {/* Cabecera del grupo */}
              {group.groupId !== 'dashboard' ? (
                <button
                  onClick={() => toggleGroup(group.groupId)}
                  className="w-full flex items-center justify-between px-2 py-1.5 mb-0.5 rounded-md
                             text-[10px] font-bold text-slate-500 uppercase tracking-widest
                             hover:text-slate-400 hover:bg-slate-800/50 transition-all"
                >
                  <span>{group.label}</span>
                  <ChevronDown
                    size={11}
                    className={`transition-transform duration-200 ${expandedGroups[group.groupId] ? 'rotate-180' : ''}`}
                  />
                </button>
              ) : null}

              {/* Items del grupo */}
              <div className={`overflow-hidden transition-all duration-200 ${
                group.groupId === 'dashboard' || expandedGroups[group.groupId] ? 'max-h-screen' : 'max-h-0'
              }`}>
                <div className="space-y-0.5">
                  {group.items.map(item => (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.path === '/'}
                      onClick={() => setSidebarOpen(false)}
                      className={({ isActive }) =>
                        `flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all ${
                          isActive
                            ? 'bg-amber-400/12 text-amber-300 ring-1 ring-amber-400/20'
                            : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                        }`
                      }
                    >
                      {({ isActive }) => {
                        const showPedidosBadge = item.path === '/pedidos-online' && nuevosPedidos > 0
                        const showWaBadge = item.path === '/whatsapp' && waNoLeidos > 0
                        const showCitasBadge = item.path === '/citas' && citasPend > 0
                        const showLeadsBadge = item.path === '/leads' && leadsPend > 0
                        return (
                          <>
                            <item.icon size={14} className={isActive ? 'text-amber-400' : ''} />
                            <span className="truncate">{item.label}</span>
                            {showPedidosBadge ? (
                              <span className="ml-auto bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center shrink-0 animate-pulse">
                                {nuevosPedidos > 99 ? '99+' : nuevosPedidos}
                              </span>
                            ) : showWaBadge ? (
                              <span className="ml-auto bg-green-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center shrink-0 animate-pulse">
                                {waNoLeidos > 99 ? '99+' : waNoLeidos}
                              </span>
                            ) : showLeadsBadge ? (
                              <span className="ml-auto bg-rose-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center shrink-0 animate-pulse">
                                {leadsPend > 99 ? '99+' : leadsPend}
                              </span>
                            ) : showCitasBadge ? (
                              <span className="ml-auto bg-amber-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center shrink-0">
                                {citasPend > 99 ? '99+' : citasPend}
                              </span>
                            ) : isActive ? (
                              <div className="ml-auto w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                            ) : null}
                          </>
                        )
                      }}
                    </NavLink>
                  ))}
                </div>
              </div>

              {/* Separador entre grupos (excepto el último) */}
              {gi < filteredGroups.length - 1 && group.groupId !== 'dashboard' && (
                <div className="mt-2 border-t border-slate-800/60" />
              )}
            </div>
          ))}
        </nav>

        {/* Footer usuario */}
        <div className="border-t border-slate-800 p-3 shrink-0">
          <div className="flex items-center gap-2.5 px-1">
            <div className="w-8 h-8 bg-amber-400 text-slate-900 rounded-lg flex items-center justify-center text-xs font-black shrink-0">
              {usuario?.usuario?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-white truncate leading-tight">{usuario?.usuario}</p>
              <p className="text-[10px] text-slate-400 leading-tight">{rolLabel}</p>
            </div>
            <button
              onClick={handleLogout}
              title="Cerrar sesión"
              className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-slate-800 rounded-md transition-all"
            >
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </aside>

      {/* Overlay móvil */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── Área principal ─────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden min-w-0">

        {/* Header */}
        <header className="h-13 bg-white border-b border-gray-200 flex items-center px-4 lg:px-6 gap-3 shrink-0" style={{ height: '52px' }}>
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-1.5 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-all"
          >
            <Menu size={18} />
          </button>

          {/* Marca (solo móvil) */}
          <div className="lg:hidden w-6 h-6 bg-amber-400 rounded-md flex items-center justify-center shrink-0">
            <span className="text-slate-900 font-black text-[11px] leading-none">R</span>
          </div>

          {/* Título dinámico */}
          <div className="flex items-center gap-2 min-w-0">
            <h1 className="text-sm font-semibold text-gray-900 truncate">{pageTitle}</h1>
          </div>

          <div className="flex-1" />

          {/* Info usuario en el header (solo desktop) */}
          <div className="hidden lg:flex items-center gap-2 text-xs text-gray-400">
            <div className="w-6 h-6 bg-amber-100 text-amber-700 rounded-md flex items-center justify-center font-bold text-[10px] shrink-0">
              {usuario?.usuario?.charAt(0).toUpperCase()}
            </div>
            <span className="font-medium text-gray-600 truncate max-w-[120px]">{usuario?.usuario}</span>
            <span className="text-gray-300">·</span>
            <span className="text-gray-400 capitalize">{rolLabel}</span>
          </div>
        </header>

        {/* Contenido */}
        <div className="flex-1 overflow-auto">
          <div className="p-4 pb-24 lg:p-6 lg:pb-6 max-w-screen-2xl mx-auto">
            <Outlet />
          </div>
        </div>
      </main>

      {/* ── Barra inferior de navegación (solo móvil) ──────────────── */}
      <nav
        className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t border-gray-200
                   flex items-stretch justify-around px-1"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        {bottomNavItems
          .filter(i => i.roles.includes(usuario?.rol))
          .map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex-1 flex flex-col items-center justify-center gap-0.5 py-2 rounded-lg transition-colors ${
                  isActive ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <div className="relative">
                    <item.icon size={22} strokeWidth={isActive ? 2.4 : 2} />
                    {item.path === '/whatsapp' && waNoLeidos > 0 && (
                      <span className="absolute -top-1.5 -right-2 bg-green-500 text-white text-[9px] font-bold rounded-full min-w-[15px] h-[15px] px-1 flex items-center justify-center">
                        {waNoLeidos > 9 ? '9+' : waNoLeidos}
                      </span>
                    )}
                  </div>
                  <span className={`text-[10px] leading-none ${isActive ? 'font-bold' : 'font-medium'}`}>{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
      </nav>
    </div>
  )
}
