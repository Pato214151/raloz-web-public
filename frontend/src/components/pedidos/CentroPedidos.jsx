import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import {
  ShoppingCart, Scissors, Package, Clock, RefreshCw, Search, CheckCircle,
  PackageCheck, Truck, FileText, Eye, XCircle, CreditCard, DollarSign,
  User, Phone, MapPin, AlertCircle,
} from 'lucide-react'

// ─── Formateo ───────────────────────────────────────────────────
const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')
const fmtFecha = (iso) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
}

// ─── Tabs del centro ────────────────────────────────────────────
const TABS = [
  { id: 'web',    label: 'Pedidos Web',    icon: ShoppingCart },
  { id: 'fab',    label: 'Fabricación',    icon: Scissors      },
  { id: 'empaque',label: 'Empaque',        icon: PackageCheck  },
  { id: 'pend',   label: 'Por Entregar',  icon: Truck         },
]

// ─── KPI Card del centro ────────────────────────────────────────
function CentroKPICard({ icon: Icon, label, value, color, onClick }) {
  const colorMap = {
    blue:   'bg-blue-50 text-blue-600',
    green:  'bg-emerald-50 text-emerald-600',
    amber:  'bg-amber-50 text-amber-600',
    red:    'bg-red-50 text-red-500',
    purple: 'bg-purple-50 text-purple-600',
    slate:  'bg-slate-100 text-slate-600',
  }
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-3 p-4 bg-white rounded-xl border border-gray-100 shadow-sm
                  hover:shadow-md hover:border-gray-200 transition-all cursor-pointer text-left w-full`}
    >
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${colorMap[color] || colorMap.blue}`}>
        <Icon size={18} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-gray-400 truncate">{label}</p>
        <p className="text-lg font-bold text-gray-900 leading-tight">{value}</p>
      </div>
    </button>
  )
}

// ─── Badges de estado ────────────────────────────────────────────
function Badge({ children, className }) {
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${className}`}>{children}</span>
}

// ══════════════════════════════════════════════════════════════════
// TAB: PEDIDOS WEB
// ══════════════════════════════════════════════════════════════════
function TabWeb() {
  const [pedidos, setPedidos] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtroEstado, setFiltroEstado] = useState('activos')
  const [seleccionado, setSeleccionado] = useState(null)
  const [marcando, setMarcando] = useState(null)
  const [actualizando, setActualizando] = useState(null)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const params = filtroEstado === 'activos' ? { vista: 'activos' } : (filtroEstado ? { estado: filtroEstado } : {})
      const res = await api.get('/tienda/admin/pedidos', { params })
      setPedidos(res.data.pedidos || [])
    } catch { toast.error('Error cargando pedidos') }
    finally { setLoading(false) }
  }, [filtroEstado])

  useEffect(() => { cargar() }, [cargar])

  const verDetalle = async (id) => {
    try {
      const res = await api.get(`/tienda/admin/pedidos/${id}`)
      setSeleccionado(res.data.pedido)
    } catch { toast.error('Error cargando detalle') }
  }

  const marcarPagado = async (pedido) => {
    if (!window.confirm(`¿Marcar ${pedido.referencia} como PAGADO manualmente?`)) return
    setMarcando(pedido.id_pedido)
    try {
      const res = await api.post(`/tienda/admin/pedidos/${pedido.id_pedido}/marcar-pagado`)
      toast.success(res.data.factura_numero ? `✅ Factura: ${res.data.factura_numero}` : 'Pagado')
      cargar()
    } catch { toast.error('Error') }
    finally { setMarcando(null) }
  }

  const cambiarEntrega = async (pedido, estado) => {
    setActualizando(pedido.id_pedido)
    try {
      await api.post(`/tienda/admin/pedidos/${pedido.id_pedido}/estado-entrega`, { estado_entrega: estado })
      toast.success('Estado actualizado')
      cargar()
      if (seleccionado?.id_pedido === pedido.id_pedido) verDetalle(pedido.id_pedido)
    } catch { toast.error('Error actualizando estado') }
    finally { setActualizando(null) }
  }

  const ESTADOS_PAGO = {
    pendiente: { label: 'Pendiente', color: 'bg-yellow-100 text-yellow-800' },
    pagado:    { label: 'Pagado',    color: 'bg-green-100 text-green-800' },
    fallido:   { label: 'Fallido',   color: 'bg-red-100 text-red-800' },
  }

  return (
    <div className="space-y-4">
      {/* Filtros */}
      <div className="flex items-center gap-2 flex-wrap">
        {['activos', 'pendiente', 'pagado', 'fallido'].map(f => (
          <button key={f} onClick={() => setFiltroEstado(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filtroEstado === f
                ? 'bg-slate-800 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}>
            {f === 'activos' ? 'Activos' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
        <button onClick={cargar} className="ml-auto p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Tabla */}
      {loading ? (
        <div className="space-y-2 animate-pulse">
          {[...Array(4)].map((_, i) => <div key={i} className="h-14 bg-gray-100 rounded-xl" />)}
        </div>
      ) : pedidos.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400 gap-3">
          <ShoppingCart size={36} className="opacity-30" />
          <p className="text-sm font-medium">No hay pedidos {filtroEstado !== 'activos' ? filtroEstado : 'activos'}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {pedidos.map(p => {
            const ep = ESTADOS_PAGO[p.wompi_status] || ESTADOS_PAGO.pendiente
            const ee = p.estado_entrega || 'POR_ENTREGAR'
            return (
              <div key={p.id_pedido} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-gray-900 text-sm">{p.referencia}</span>
                      <span className={`${ep.color} px-2 py-0.5 rounded-full text-xs font-medium`}>{ep.label}</span>
                      {ee !== 'ENTREGADO' && ee !== 'ENTREGADA' && (
                        <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full text-xs font-medium">{ee.replace('_', ' ')}</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1 truncate">
                      {p.nombre_cliente} · {p.telefono_cliente}
                    </p>
                    <p className="text-xs text-gray-400">{fmtFecha(p.fecha_creacion)}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-bold text-gray-900">{fmt(p.total)}</p>
                    <p className="text-xs text-gray-400">{p.metodo_pago || '—'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-50">
                  <button onClick={() => verDetalle(p.id_pedido)}
                    className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium">
                    <Eye size={12} /> Ver
                  </button>
                  {p.wompi_status === 'pendiente' && (
                    <button onClick={() => marcarPagado(p)}
                      disabled={marcando === p.id_pedido}
                      className="flex items-center gap-1 text-xs text-green-600 hover:text-green-800 font-medium disabled:opacity-50">
                      <CreditCard size={12} /> Marcar Pagado
                    </button>
                  )}
                  {p.wompi_status === 'pagado' && ee !== 'ENTREGADO' && ee !== 'ENTREGADA' && (
                    <button onClick={() => cambiarEntrega(p, 'EMPACADO')}
                      disabled={actualizando === p.id_pedido}
                      className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-800 font-medium disabled:opacity-50">
                      <PackageCheck size={12} /> Marcar Empacado
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Modal detalle */}
      {seleccionado && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setSeleccionado(null)}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[85vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-gray-900">{seleccionado.referencia}</h3>
                <p className="text-xs text-gray-400">{fmtFecha(seleccionado.fecha_creacion)}</p>
              </div>
              <button onClick={() => setSeleccionado(null)} className="p-2 text-gray-400 hover:text-gray-700 rounded-lg hover:bg-gray-100">
                <XCircle size={18} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-400 mb-1">Cliente</p>
                  <p className="font-medium text-gray-900">{seleccionado.nombre_cliente}</p>
                  <p className="text-xs text-gray-500">{seleccionado.telefono_cliente}</p>
                  {seleccionado.direccion_envio && <p className="text-xs text-gray-400 mt-1">{seleccionado.direccion_envio}</p>}
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-400 mb-1">Total</p>
                  <p className="text-xl font-bold text-gray-900">{fmt(seleccionado.total)}</p>
                  <p className="text-xs text-gray-400">{seleccionado.metodo_pago || '—'} · {seleccionado.wompi_status}</p>
                </div>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase mb-2">Items</p>
                {(() => {
                  try {
                    const items = JSON.parse(seleccionado.items_json || '[]')
                    return items.map((item, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                        <div>
                          <p className="text-sm font-medium text-gray-800">{item.nombre}</p>
                          <p className="text-xs text-gray-400">Talla {item.talla} · x{item.cantidad}</p>
                        </div>
                        <p className="text-sm font-semibold text-gray-700">{fmt(item.subtotal || item.precio_unitario * item.cantidad)}</p>
                      </div>
                    ))
                  } catch { return <p className="text-sm text-gray-400">Sin items</p> }
                })()}
              </div>
              {seleccionado.observaciones && (
                <div className="bg-amber-50 rounded-lg p-3">
                  <p className="text-xs font-medium text-amber-700">Observaciones</p>
                  <p className="text-sm text-amber-800">{seleccionado.observaciones}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════
// TAB: FABRICACIÓN
// ══════════════════════════════════════════════════════════════════
function TabFab() {
  const [pedidos, setPedidos] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtroEstado, setFiltroEstado] = useState('todos')

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const params = filtroEstado !== 'todos' ? { estado: filtroEstado } : {}
      const res = await api.get('/tienda/admin/fabricacion/pedidos', { params })
      setPedidos(res.data.pedidos || [])
    } catch { toast.error('Error') }
    finally { setLoading(false) }
  }, [filtroEstado])

  useEffect(() => { cargar() }, [cargar])

  const cambiarEstado = async (id, nuevoEstado) => {
    try {
      await api.post(`/tienda/admin/fabricacion/pedidos/${id}/estado`, { estado: nuevoEstado })
      toast.success('Estado actualizado')
      cargar()
    } catch { toast.error('Error') }
  }

  const ESTADOS_FAB = {
    en_produccion:      { label: 'En producción',      color: 'bg-yellow-100 text-yellow-800' },
    listo_para_entrega: { label: 'Listo para entrega', color: 'bg-blue-100 text-blue-800' },
    entregado:          { label: 'Entregado',           color: 'bg-green-100 text-green-800' },
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        {['todos', 'en_produccion', 'listo_para_entrega', 'entregado'].map(f => (
          <button key={f} onClick={() => setFiltroEstado(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filtroEstado === f ? 'bg-amber-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}>
            {f === 'todos' ? 'Todos' : ESTADOS_FAB[f]?.label || f}
          </button>
        ))}
        <button onClick={cargar} className="ml-auto p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {loading ? (
        <div className="space-y-2 animate-pulse">
          {[...Array(3)].map((_, i) => <div key={i} className="h-16 bg-gray-100 rounded-xl" />)}
        </div>
      ) : pedidos.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400 gap-3">
          <Scissors size={36} className="opacity-30" />
          <p className="text-sm font-medium">No hay pedidos de fabricación</p>
        </div>
      ) : (
        <div className="space-y-2">
          {pedidos.map(p => {
            const ef = ESTADOS_FAB[p.estado] || ESTADOS_FAB.en_produccion
            return (
              <div key={p.id_pedido} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-gray-900 text-sm">{p.referencia || `#${p.id_pedido}`}</span>
                      <span className={`${ef.color} px-2 py-0.5 rounded-full text-xs font-medium`}>{ef.label}</span>
                      {p.tipo_pedido !== 'normal' && (
                        <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full text-xs font-medium">
                          {p.tipo_pedido}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1 truncate">{p.nombre_cliente} · {p.telefono_cliente}</p>
                    <p className="text-xs text-gray-400">{fmtFecha(p.fecha_pago || p.fecha_creacion)}</p>
                  </div>
                  <div className="text-right shrink-0">
                    {p.saldo_pendiente > 0 && (
                      <p className="text-xs text-red-500 font-medium">Saldo: {fmt(p.saldo_pendiente)}</p>
                    )}
                    {p.total && <p className="text-sm font-bold text-gray-900">{fmt(p.total)}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-50">
                  {p.estado === 'en_produccion' && (
                    <button onClick={() => cambiarEstado(p.id_pedido, 'listo_para_entrega')}
                      className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium">
                      <CheckCircle size={12} /> Marcar Listo
                    </button>
                  )}
                  {p.estado === 'listo_para_entrega' && (
                    <button onClick={() => cambiarEstado(p.id_pedido, 'entregado')}
                      className="flex items-center gap-1 text-xs text-green-600 hover:text-green-800 font-medium">
                      <Truck size={12} /> Marcar Entregado
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════
// TAB: EMPAQUE
// ══════════════════════════════════════════════════════════════════
function TabEmpaque() {
  const [numeroFactura, setNumeroFactura] = useState('')
  const [factura, setFactura] = useState(null)
  const [loading, setLoading] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [itemStates, setItemStates] = useState({})
  const [savingMsg, setSavingMsg] = useState('')

  const ESTADOS_DETALLE = ['POR_ENTREGAR', 'EMPACADO', 'ENTREGADO']

  const buscarFactura = async (e) => {
    e?.preventDefault()
    if (!numeroFactura.trim()) return
    setLoading(true)
    try {
      const res = await api.get(`/empaque/factura/${encodeURIComponent(numeroFactura.trim())}`)
      setFactura(res.data)
      setItemStates({})
    } catch { toast.error('Factura no encontrada') }
    finally { setLoading(false) }
  }

  const marcarItem = async (itemId, nuevoEstado) => {
    setGuardando(true)
    try {
      await api.post(`/empaque/factura/${factura.id_factura}/item/${itemId}/estado`, { estado: nuevoEstado })
      setFactura(prev => ({
        ...prev,
        detalles: prev.detalles.map(d => d.id_detalle === itemId ? { ...d, estado_entrega: nuevoEstado } : d),
      }))
      toast.success('Estado actualizado')
    } catch { toast.error('Error') }
    finally { setGuardando(false) }
  }

  return (
    <div className="space-y-4">
      {/* Buscador */}
      <form onSubmit={buscarFactura} className="flex gap-2">
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={numeroFactura}
            onChange={e => setNumeroFactura(e.target.value)}
            placeholder="Buscar por número de factura..."
            className="w-full pl-9 pr-4 py-2.5 text-sm border border-gray-200 rounded-xl
                       focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-none"
          />
        </div>
        <button type="submit" disabled={loading}
          className="px-4 py-2.5 bg-slate-800 text-white text-sm font-medium rounded-xl hover:bg-slate-700 disabled:opacity-50 transition-colors">
          {loading ? 'Buscando…' : 'Buscar'}
        </button>
      </form>

      {!factura ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400 gap-3">
          <Package size={36} className="opacity-30" />
          <p className="text-sm font-medium">Ingresa un número de factura para buscar</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
            <div>
              <p className="font-bold text-gray-900">{factura.numero_factura}</p>
              <p className="text-xs text-gray-400">{factura.cliente_nombre} · {fmt(factura.total)}</p>
            </div>
            <span className="text-xs text-gray-400 bg-white border border-gray-200 px-2 py-1 rounded-lg">
              {factura.estado_entrega || 'Sin estado'}
            </span>
          </div>
          <div className="divide-y divide-gray-50">
            {(factura.detalles || []).map(item => {
              const ee = item.estado_entrega || 'POR_ENTREGAR'
              const siguiente = ESTADOS_DETALLE[ESTADOS_DETALLE.indexOf(ee) + 1]
              return (
                <div key={item.id_detalle} className="p-4 flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-800 truncate">{item.producto_nombre}</p>
                    <p className="text-xs text-gray-400">{item.talla} · x{item.cantidad}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      ee === 'ENTREGADO' ? 'bg-green-100 text-green-700' :
                      ee === 'EMPACADO' ? 'bg-purple-100 text-purple-700' :
                      'bg-blue-50 text-blue-700'
                    }`}>{ee.replace('_', ' ')}</span>
                    {siguiente && (
                      <button onClick={() => marcarItem(item.id_detalle, siguiente)}
                        disabled={guardando}
                        className="text-xs text-blue-600 hover:text-blue-800 font-medium disabled:opacity-50 whitespace-nowrap">
                        → {siguiente.replace('_', ' ')}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════
// TAB: POR ENTREGAR
// ══════════════════════════════════════════════════════════════════
function TabPendientes() {
  const [prendas, setPrendas] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtro, setFiltro] = useState('PENDIENTE')
  const [buscar, setBuscar] = useState('')

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const params = { estado: filtro }
      if (buscar) params.buscar = buscar
      const res = await api.get('/prendas', { params })
      setPrendas(res.data.prendas || [])
    } catch { toast.error('Error') }
    finally { setLoading(false) }
  }, [filtro, buscar])

  useEffect(() => { cargar() }, [cargar])

  const marcarEntregado = async (id) => {
    try {
      await api.post(`/prendas/${id}/entregar`)
      toast.success('Marcado como entregado')
      cargar()
    } catch { toast.error('Error') }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        {['PENDIENTE', 'ENTREGADO'].map(f => (
          <button key={f} onClick={() => setFiltro(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filtro === f ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}>
            {f === 'PENDIENTE' ? 'Por entregar' : 'Entregados'}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input value={buscar} onChange={e => setBuscar(e.target.value)}
              placeholder="Buscar..."
              className="pl-8 pr-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:ring-1 focus:ring-amber-500 outline-none w-36" />
          </div>
          <button onClick={cargar} className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-2 animate-pulse">
          {[...Array(4)].map((_, i) => <div key={i} className="h-14 bg-gray-100 rounded-xl" />)}
        </div>
      ) : prendas.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400 gap-3">
          <Clock size={36} className="opacity-30" />
          <p className="text-sm font-medium">No hay prendas {filtro === 'PENDIENTE' ? 'por entregar' : 'entregadas'}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {prendas.map(p => (
            <div key={p.id_detalle} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex items-center justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-gray-900 truncate">{p.producto_nombre}</p>
                <p className="text-xs text-gray-400">{p.talla} · {p.cantidad} unidades · {p.colegio_nombre || '—'}</p>
                {p.numero_factura && <p className="text-xs text-gray-400">Fac. {p.numero_factura}</p>}
              </div>
              {filtro === 'PENDIENTE' && (
                <button onClick={() => marcarEntregado(p.id_detalle)}
                  className="flex items-center gap-1 text-xs text-teal-600 hover:text-teal-800 font-medium whitespace-nowrap shrink-0">
                  <CheckCircle size={12} /> Entregar
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════
// MAIN: Centro de Pedidos
// ══════════════════════════════════════════════════════════════════
export default function CentroPedidos() {
  const [tab, setTab] = useState('web')
  const [totales, setTotales] = useState({ web: 0, fab: 0, empaque: 0, pend: 0 })
  const [loadingTotales, setLoadingTotales] = useState(true)

  useEffect(() => {
    const cargarTotales = async () => {
      setLoadingTotales(true)
      try {
        const [web, fab, pend] = await Promise.all([
          api.get('/tienda/admin/pedidos', { params: { vista: 'activos' } }).catch(() => ({ data: { total: 0 } })),
          api.get('/tienda/admin/fabricacion/pedidos').catch(() => ({ data: { pedidos: [] } })),
          api.get('/prendas', { params: { estado: 'PENDIENTE', per_page: 1 } }).catch(() => ({ data: { total_pendientes: 0 } })),
        ])
        const enProd = (fab.data.pedidos || []).filter(p => p.estado === 'en_produccion').length
        setTotales({
          web: web.data.total || 0,
          fab: enProd,
          empaque: (fab.data.pedidos || []).filter(p => p.estado === 'listo_para_entrega').length,
          pend: pend.data.total_pendientes || pend.data.total || 0,
        })
      } catch { /* silencioso */ }
      finally { setLoadingTotales(false) }
    }
    cargarTotales()
  }, [])

  return (
    <div className="space-y-5">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <CentroKPICard
          icon={ShoppingCart} label="Pedidos Web" value={loadingTotales ? '…' : totales.web}
          color="blue" onClick={() => setTab('web')}
        />
        <CentroKPICard
          icon={Scissors} label="En producción" value={loadingTotales ? '…' : totales.fab}
          color="amber" onClick={() => setTab('fab')}
        />
        <CentroKPICard
          icon={PackageCheck} label="Listos empacar" value={loadingTotales ? '…' : totales.empaque}
          color="purple" onClick={() => setTab('empaque')}
        />
        <CentroKPICard
          icon={Truck} label="Por entregar" value={loadingTotales ? '…' : totales.pend}
          color="green" onClick={() => setTab('pend')}
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-1 -mb-px">
          {TABS.map(t => (
            <button key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                tab === t.id
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <t.icon size={14} />
              {t.label}
              {!loadingTotales && totales[t.id] > 0 && (
                <span className={`text-[10px] font-bold rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center ${
                  tab === t.id ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-500'
                }`}>
                  {totales[t.id]}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Contenido del tab activo */}
      {tab === 'web' && <TabWeb />}
      {tab === 'fab' && <TabFab />}
      {tab === 'empaque' && <TabEmpaque />}
      {tab === 'pend' && <TabPendientes />}
    </div>
  )
}
