import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../context/AuthContext'
import {
  Scissors, CheckCircle, PackageCheck, RefreshCw, ChevronDown, ChevronUp,
  MessageCircle, DollarSign, MapPin, Phone, Mail, Calendar, Search,
  Factory, Box, Wrench,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'https://raloz-web.onrender.com/api'

const ESTADOS = {
  en_produccion:      { label: 'En producción',      color: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
  listo_para_entrega: { label: 'Listo para entrega', color: 'bg-blue-100 text-blue-800 border-blue-200'       },
  entregado:          { label: 'Entregado',           color: 'bg-green-100 text-green-800 border-green-200'   },
}

const COLEGIOS = { 1: 'Marillac', 2: 'Adventista', 3: 'Manyanet' }

function fmt(n) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(n || 0)
}

function BadgeEstado({ estado }) {
  const cfg = ESTADOS[estado] || { label: estado, color: 'bg-gray-100 text-gray-700 border-gray-200' }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

function BadgeTipo({ tipo }) {
  if (tipo === 'fabricacion') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700 border border-orange-200">
        <Wrench size={10} /> Fabricar
      </span>
    )
  }
  if (tipo === 'mixto') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700 border border-purple-200">
        <Wrench size={10} /> Mixto
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 border border-green-200">
      <Box size={10} /> Stock
    </span>
  )
}

// ────────────────────────────────────────────────────────────
// Modal: Registrar pago de saldo
// ────────────────────────────────────────────────────────────
function ModalSaldo({ pedido, token, onClose, onDone }) {
  const [monto, setMonto]   = useState(String(Math.round(pedido.saldo_pendiente)))
  const [metodo, setMetodo] = useState('efectivo')
  const [loading, setLoad]  = useState(false)
  const [error, setError]   = useState('')

  const confirmar = async () => {
    const val = parseFloat(monto)
    if (!val || val <= 0) { setError('Ingresa un monto válido'); return }
    setLoad(true); setError('')
    try {
      const res = await fetch(`${API}/tienda/admin/fabricacion/pedidos/${pedido.id_pedido}/registrar-saldo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ monto: val, metodo }),
      })
      const d = await res.json()
      if (!res.ok) { setError(d.error || 'Error al registrar'); return }
      onDone(d.pedido)
    } catch {
      setError('Error de conexión')
    } finally {
      setLoad(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-2">
          <DollarSign size={18} className="text-green-600" />
          <h3 className="text-lg font-bold text-gray-900">Registrar pago de saldo</h3>
        </div>

        <div className="bg-gray-50 rounded-xl p-3 text-sm space-y-1">
          <p className="text-gray-500">Cliente: <strong className="text-gray-800">{pedido.nombre_cliente}</strong></p>
          <p className="text-gray-500">Saldo total: <strong className="text-red-600">{fmt(pedido.saldo_pendiente)}</strong></p>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Monto recibido</label>
            <input
              type="number"
              value={monto}
              onChange={e => setMonto(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Método de pago</label>
            <select
              value={metodo}
              onChange={e => setMetodo(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="efectivo">Efectivo</option>
              <option value="transferencia">Transferencia / Nequi / Daviplata</option>
              <option value="mercadopago">MercadoPago</option>
              <option value="tarjeta">Tarjeta</option>
            </select>
          </div>
        </div>

        {error && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

        <div className="flex gap-2 pt-1">
          <button onClick={confirmar} disabled={loading}
            className="flex-1 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-xl text-sm font-semibold disabled:opacity-50 transition-colors">
            {loading ? 'Registrando...' : '✓ Confirmar pago'}
          </button>
          <button onClick={onClose}
            className="px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 transition-colors">
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// Card expandible por pedido
// ────────────────────────────────────────────────────────────
function PedidoCard({ pedido: initialPed, token, onRefresh }) {
  const [ped, setPed]         = useState(initialPed)
  const [abierto, setAbierto] = useState(false)
  const [accion, setAccion]   = useState(null)    // id de acción en curso
  const [fechaEdit, setFecha] = useState(ped.fecha_estimada || '')
  const [editFecha, setEdit]  = useState(false)
  const [modalSaldo, setSaldo] = useState(false)

  useEffect(() => { setPed(initialPed); setFecha(initialPed.fecha_estimada || '') }, [initialPed])

  const call = async (ruta, extra = {}) => {
    setAccion(ruta)
    try {
      const res = await fetch(`${API}/tienda/admin/fabricacion/pedidos/${ped.id_pedido}/${ruta}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        ...extra,
      })
      const d = await res.json()
      if (d.pedido) setPed(d.pedido)
      else onRefresh()
    } finally {
      setAccion(null)
    }
  }

  const guardarFecha = async () => {
    if (!fechaEdit) return
    setAccion('fecha')
    try {
      await fetch(`${API}/tienda/admin/fabricacion/pedidos/${ped.id_pedido}/actualizar-fecha`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ fecha_estimada: fechaEdit }),
      })
      setPed(p => ({ ...p, fecha_estimada: fechaEdit }))
      setEdit(false)
    } finally {
      setAccion(null)
    }
  }

  const notificarWhatsApp = async () => {
    const tel  = (ped.telefono_cliente || '').replace(/\D/g, '')
    const saldo = ped.saldo_pendiente || 0
    const msg  = saldo > 0
      ? `Hola ${ped.nombre_cliente}, su pedido RALOZ #${ped.id_pedido} está listo para entrega esta semana. Debe cancelar el saldo de ${fmt(saldo)} para coordinar la entrega. ¡Contáctenos para confirmar! 🎒`
      : `Hola ${ped.nombre_cliente}, su pedido RALOZ #${ped.id_pedido} está listo para entrega esta semana. Todo está pagado, coordinaremos la entrega pronto. 🎒`
    window.open(`https://wa.me/57${tel}?text=${encodeURIComponent(msg)}`, '_blank')
    await call('marcar-notificado', {})
    setPed(p => ({ ...p, notificado: true }))
  }

  const estadoCfg = ESTADOS[ped.estado] || ESTADOS.en_produccion

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      {/* Cabecera del card — siempre visible */}
      <div
        className="flex items-start gap-3 p-4 cursor-pointer hover:bg-gray-50/60 transition-colors select-none"
        onClick={() => setAbierto(v => !v)}
      >
        {/* Ícono estado */}
        <div className={`mt-0.5 w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          ped.estado === 'entregado' ? 'bg-green-100' :
          ped.estado === 'listo_para_entrega' ? 'bg-blue-100' : 'bg-yellow-100'
        }`}>
          {ped.estado === 'entregado' ? <PackageCheck size={16} className="text-green-600" /> :
           ped.estado === 'listo_para_entrega' ? <CheckCircle size={16} className="text-blue-600" /> :
           <Factory size={16} className="text-yellow-600" />}
        </div>

        {/* Info principal */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="font-mono text-xs text-gray-400">#{ped.id_pedido}</span>
            <BadgeEstado estado={ped.estado} />
            {ped.notificado && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-teal-100 text-teal-700">
                <MessageCircle size={10} /> Notificado
              </span>
            )}
          </div>
          <p className="font-semibold text-gray-900 text-sm truncate">{ped.nombre_cliente}</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {ped.nombre_colegio} · {ped.fecha_pedido?.slice(0, 10)}
          </p>
        </div>

        {/* Saldo/abono + chevron */}
        <div className="text-right flex-shrink-0">
          <p className="text-xs text-gray-500">Abono</p>
          <p className="font-semibold text-green-700 text-sm">{fmt(ped.abono_monto)}</p>
          {ped.saldo_pendiente > 0 && (
            <>
              <p className="text-xs text-gray-500 mt-0.5">Saldo</p>
              <p className="font-semibold text-red-600 text-sm">{fmt(ped.saldo_pendiente)}</p>
            </>
          )}
        </div>
        <div className="flex-shrink-0 text-gray-400 mt-1">
          {abierto ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {/* Contenido expandido */}
      {abierto && (
        <div className="border-t border-gray-100 px-4 pb-4 pt-3 space-y-4">
          {/* Datos del cliente */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="flex items-start gap-2">
              <Phone size={13} className="text-gray-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs text-gray-400">Teléfono</p>
                <a href={`tel:${ped.telefono_cliente}`} className="text-gray-800 hover:text-blue-600">{ped.telefono_cliente || '—'}</a>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Mail size={13} className="text-gray-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs text-gray-400">Email</p>
                <p className="text-gray-800 text-xs truncate">{ped.email_cliente || '—'}</p>
              </div>
            </div>
            {ped.direccion_envio && (
              <div className="col-span-2 flex items-start gap-2">
                <MapPin size={13} className="text-gray-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs text-gray-400">Dirección de entrega</p>
                  <p className="text-gray-800">{ped.direccion_envio}</p>
                </div>
              </div>
            )}
          </div>

          {/* Tabla de items */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Prendas del pedido</p>
            <div className="rounded-xl border border-gray-100 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Prenda</th>
                    <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500">Talla</th>
                    <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500">Cant.</th>
                    <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500">Tipo</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">Subtotal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {(ped.items || []).map((item, i) => (
                    <tr key={i} className="hover:bg-gray-50/50">
                      <td className="px-3 py-2 text-gray-800">{item.nombre}</td>
                      <td className="px-3 py-2 text-center text-gray-600 font-mono">{item.talla}</td>
                      <td className="px-3 py-2 text-center text-gray-600">×{item.cantidad}</td>
                      <td className="px-3 py-2 text-center">
                        <BadgeTipo tipo={item.tipo_pedido} />
                      </td>
                      <td className="px-3 py-2 text-right font-medium text-gray-800">{fmt(item.subtotal)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Resumen financiero */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-gray-50 rounded-xl p-3 text-center">
              <p className="text-xs text-gray-500 mb-1">Total orden</p>
              <p className="font-bold text-gray-900">{fmt(ped.total_orden)}</p>
            </div>
            <div className="bg-green-50 rounded-xl p-3 text-center">
              <p className="text-xs text-gray-500 mb-1">Abono pagado</p>
              <p className="font-bold text-green-700">{fmt(ped.abono_monto)}</p>
              <p className="text-xs text-gray-400">{ped.abono_porcentaje}%</p>
            </div>
            <div className={`rounded-xl p-3 text-center ${ped.saldo_pendiente > 0 ? 'bg-red-50' : 'bg-green-50'}`}>
              <p className="text-xs text-gray-500 mb-1">Saldo pend.</p>
              <p className={`font-bold ${ped.saldo_pendiente > 0 ? 'text-red-600' : 'text-green-700'}`}>
                {ped.saldo_pendiente > 0 ? fmt(ped.saldo_pendiente) : '✓ Saldado'}
              </p>
            </div>
          </div>

          {/* Fecha estimada */}
          <div className="flex items-center gap-3">
            <Calendar size={14} className="text-gray-400 flex-shrink-0" />
            <div className="flex-1 flex items-center gap-2">
              <p className="text-xs text-gray-500">Fecha estimada:</p>
              {editFecha ? (
                <>
                  <input
                    type="date"
                    value={fechaEdit}
                    onChange={e => setFecha(e.target.value)}
                    className="border border-gray-300 rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-amber-500"
                  />
                  <button onClick={guardarFecha} disabled={accion === 'fecha'}
                    className="px-3 py-1 bg-amber-500 text-white rounded-lg text-xs font-semibold hover:bg-amber-600 disabled:opacity-50">
                    {accion === 'fecha' ? '...' : 'Guardar'}
                  </button>
                  <button onClick={() => setEdit(false)} className="text-xs text-gray-500 hover:text-gray-700">Cancelar</button>
                </>
              ) : (
                <>
                  <span className="text-sm font-medium text-gray-800">{ped.fecha_estimada || '—'}</span>
                  {ped.estado !== 'entregado' && (
                    <button onClick={() => setEdit(true)}
                      className="text-xs text-amber-600 hover:text-amber-700 hover:underline">
                      Editar
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Botones de acción */}
          {ped.estado !== 'entregado' && (
            <div className="flex flex-wrap gap-2 pt-1 border-t border-gray-100">
              {ped.estado === 'en_produccion' && (
                <button
                  onClick={() => call('marcar-listo')}
                  disabled={accion === 'marcar-listo'}
                  className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold disabled:opacity-50 transition-colors"
                >
                  <CheckCircle size={14} />
                  {accion === 'marcar-listo' ? 'Procesando...' : 'Marcar listo para entrega'}
                </button>
              )}

              {ped.estado === 'listo_para_entrega' && (
                <>
                  <button
                    onClick={notificarWhatsApp}
                    disabled={accion === 'marcar-notificado'}
                    className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 ${
                      ped.notificado
                        ? 'bg-teal-50 text-teal-700 border border-teal-200 hover:bg-teal-100'
                        : 'bg-green-500 hover:bg-green-600 text-white'
                    }`}
                  >
                    <MessageCircle size={14} />
                    {ped.notificado ? '✓ Notificar de nuevo' : 'Notificar por WhatsApp'}
                  </button>

                  {ped.saldo_pendiente > 0 && (
                    <button
                      onClick={() => setSaldo(true)}
                      className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-sm font-semibold transition-colors"
                    >
                      <DollarSign size={14} /> Registrar pago saldo
                    </button>
                  )}

                  <button
                    onClick={() => call('marcar-entregado')}
                    disabled={accion === 'marcar-entregado'}
                    className="flex items-center gap-1.5 px-4 py-2 bg-gray-800 hover:bg-gray-900 text-white rounded-xl text-sm font-semibold disabled:opacity-50 transition-colors"
                  >
                    <PackageCheck size={14} />
                    {accion === 'marcar-entregado' ? 'Procesando...' : 'Marcar entregado'}
                  </button>
                </>
              )}
            </div>
          )}

          {ped.estado === 'entregado' && (
            <div className="flex items-center gap-2 text-green-600 text-sm">
              <PackageCheck size={16} /> Pedido entregado al cliente
            </div>
          )}
        </div>
      )}

      {/* Modal saldo */}
      {modalSaldo && (
        <ModalSaldo
          pedido={ped}
          token={token}
          onClose={() => setSaldo(false)}
          onDone={updated => { setPed(updated); setSaldo(false) }}
        />
      )}
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// Componente principal
// ────────────────────────────────────────────────────────────
export default function PedidosFabricacion() {
  const { token } = useAuth()
  const [pedidos, setPedidos]     = useState([])
  const [total, setTotal]         = useState(0)
  const [loading, setLoading]     = useState(false)
  const [filtroEstado, setFiltro] = useState('')
  const [filtroColegio, setColegio] = useState('')
  const [busqueda, setBusqueda]   = useState('')

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const qs = filtroEstado ? `?estado=${filtroEstado}&limit=100` : '?limit=100'
      const res = await fetch(`${API}/tienda/admin/fabricacion/pedidos${qs}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const d = await res.json()
        setPedidos(d.pedidos || [])
        setTotal(d.total || 0)
      }
    } finally {
      setLoading(false)
    }
  }, [token, filtroEstado])

  useEffect(() => { cargar() }, [cargar])

  // Filtros locales
  const pedidosFiltrados = pedidos.filter(p => {
    if (filtroColegio && String(p.id_colegio) !== filtroColegio) return false
    if (busqueda) {
      const q = busqueda.toLowerCase()
      return (p.nombre_cliente || '').toLowerCase().includes(q)
        || String(p.id_pedido).includes(q)
        || (p.email_cliente || '').toLowerCase().includes(q)
    }
    return true
  })

  // Contadores por estado
  const contadores = pedidos.reduce((acc, p) => {
    acc[p.estado] = (acc[p.estado] || 0) + 1
    return acc
  }, {})

  return (
    <div className="space-y-4">
      {/* Cabecera */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Scissors size={20} className="text-amber-700" /> Pedidos en Fabricación
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} pedidos en total</p>
        </div>
        <button onClick={cargar} disabled={loading}
          className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 text-gray-500 transition-colors">
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Resumen rápido */}
      <div className="grid grid-cols-3 gap-3">
        {Object.entries(ESTADOS).map(([key, cfg]) => (
          <button key={key}
            onClick={() => setFiltro(filtroEstado === key ? '' : key)}
            className={`rounded-xl p-3 text-left border transition-all ${
              filtroEstado === key ? 'ring-2 ring-amber-400 border-amber-300' : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <p className="text-2xl font-bold text-gray-900">{contadores[key] || 0}</p>
            <p className="text-xs text-gray-500 mt-0.5">{cfg.label}</p>
          </button>
        ))}
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-2">
        {/* Búsqueda */}
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={busqueda}
            onChange={e => setBusqueda(e.target.value)}
            placeholder="Buscar por nombre, ID..."
            className="w-full pl-8 pr-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-500"
          />
        </div>

        {/* Colegio */}
        <div className="relative">
          <select
            value={filtroColegio}
            onChange={e => setColegio(e.target.value)}
            className="appearance-none pl-3 pr-8 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <option value="">Todos los colegios</option>
            {Object.entries(COLEGIOS).map(([id, nombre]) => (
              <option key={id} value={id}>{nombre}</option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {/* Lista de cards */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">Cargando pedidos...</div>
      ) : pedidosFiltrados.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          {busqueda || filtroColegio || filtroEstado ? 'Sin resultados para los filtros aplicados' : 'Sin pedidos de fabricación'}
        </div>
      ) : (
        <div className="space-y-3">
          {pedidosFiltrados.map(p => (
            <PedidoCard key={p.id_pedido} pedido={p} token={token} onRefresh={cargar} />
          ))}
        </div>
      )}
    </div>
  )
}
