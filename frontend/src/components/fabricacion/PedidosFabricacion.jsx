import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../context/AuthContext'
import { Scissors, Eye, CheckCircle, PackageCheck, Clock, RefreshCw, ChevronDown } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'https://raloz-web.onrender.com/api'

const ESTADOS = {
  en_produccion:      { label: 'En producción',       color: 'bg-yellow-100 text-yellow-800' },
  listo_para_entrega: { label: 'Listo para entrega',  color: 'bg-blue-100 text-blue-800'    },
  entregado:          { label: 'Entregado',            color: 'bg-green-100 text-green-800'  },
}

function BadgeEstado({ estado }) {
  const cfg = ESTADOS[estado] || { label: estado, color: 'bg-gray-100 text-gray-700' }
  return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.color}`}>{cfg.label}</span>
}

function formatCOP(n) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(n)
}

export default function PedidosFabricacion() {
  const { token } = useAuth()
  const [pedidos, setPedidos]       = useState([])
  const [total, setTotal]           = useState(0)
  const [loading, setLoading]       = useState(false)
  const [filtroEstado, setFiltro]   = useState('')
  const [detalle, setDetalle]       = useState(null)
  const [accionando, setAccionando] = useState(null)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const qs  = filtroEstado ? `?estado=${filtroEstado}&limit=100` : '?limit=100'
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

  const marcar = async (id, accion) => {
    setAccionando(id)
    try {
      await fetch(`${API}/tienda/admin/fabricacion/pedidos/${id}/${accion}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      await cargar()
      if (detalle?.id_pedido === id) setDetalle(null)
    } finally {
      setAccionando(null)
    }
  }

  const verDetalle = async (id) => {
    const res = await fetch(`${API}/tienda/admin/fabricacion/pedidos/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      const d = await res.json()
      setDetalle(d.pedido)
    }
  }

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
        <div className="flex items-center gap-2">
          {/* Filtro estado */}
          <div className="relative">
            <select
              value={filtroEstado}
              onChange={e => setFiltro(e.target.value)}
              className="appearance-none pl-3 pr-8 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              <option value="">Todos los estados</option>
              {Object.entries(ESTADOS).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          </div>
          <button onClick={cargar} disabled={loading}
            className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 text-gray-500">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['ID', 'Cliente', 'Colegio', 'Abono pagado', 'Saldo pend.', 'Fecha pedido', 'Fecha est.', 'Estado', 'Acciones'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading && (
                <tr><td colSpan={9} className="text-center py-10 text-gray-400">Cargando...</td></tr>
              )}
              {!loading && !pedidos.length && (
                <tr><td colSpan={9} className="text-center py-10 text-gray-400">Sin pedidos</td></tr>
              )}
              {pedidos.map(p => (
                <tr key={p.id_pedido} className="hover:bg-gray-50/50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">#{p.id_pedido}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{p.nombre_cliente}</p>
                    <p className="text-xs text-gray-500">{p.email_cliente}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{p.nombre_colegio}</td>
                  <td className="px-4 py-3 text-green-700 font-semibold">{formatCOP(p.abono_monto)}</td>
                  <td className="px-4 py-3 text-red-600 font-semibold">{formatCOP(p.saldo_pendiente)}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{p.fecha_pedido?.slice(0,10)}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{p.fecha_estimada}</td>
                  <td className="px-4 py-3"><BadgeEstado estado={p.estado} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <button onClick={() => verDetalle(p.id_pedido)}
                        className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500" title="Ver detalle">
                        <Eye size={15} />
                      </button>
                      {p.estado === 'en_produccion' && (
                        <button onClick={() => marcar(p.id_pedido, 'marcar-listo')}
                          disabled={accionando === p.id_pedido}
                          className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-600" title="Marcar listo">
                          <CheckCircle size={15} />
                        </button>
                      )}
                      {p.estado === 'listo_para_entrega' && (
                        <button onClick={() => marcar(p.id_pedido, 'marcar-entregado')}
                          disabled={accionando === p.id_pedido}
                          className="p-1.5 rounded-lg hover:bg-green-50 text-green-600" title="Marcar entregado">
                          <PackageCheck size={15} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal detalle */}
      {detalle && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setDetalle(null)}>
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-gray-900">Pedido #{detalle.id_pedido}</h3>
              <BadgeEstado estado={detalle.estado} />
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><p className="text-gray-500 text-xs">Cliente</p><p className="font-medium">{detalle.nombre_cliente}</p></div>
              <div><p className="text-gray-500 text-xs">Teléfono</p><p className="font-medium">{detalle.telefono_cliente}</p></div>
              <div><p className="text-gray-500 text-xs">Colegio</p><p className="font-medium">{detalle.nombre_colegio}</p></div>
              <div><p className="text-gray-500 text-xs">Fecha estimada</p><p className="font-medium flex items-center gap-1"><Clock size={13}/>{detalle.fecha_estimada}</p></div>
              <div><p className="text-gray-500 text-xs">Abono pagado</p><p className="font-bold text-green-700">{formatCOP(detalle.abono_monto)} ({detalle.abono_porcentaje}%)</p></div>
              <div><p className="text-gray-500 text-xs">Saldo pendiente</p><p className="font-bold text-red-600">{formatCOP(detalle.saldo_pendiente)}</p></div>
            </div>
            <div>
              <p className="text-xs text-gray-500 font-semibold uppercase mb-2">Productos</p>
              <div className="space-y-1.5">
                {detalle.items?.map((item, i) => (
                  <div key={i} className="flex justify-between text-sm bg-gray-50 rounded-lg px-3 py-2">
                    <span>{item.nombre} — Talla {item.talla} ×{item.cantidad}</span>
                    <span className="font-semibold">{formatCOP(item.subtotal)}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              {detalle.estado === 'en_produccion' && (
                <button onClick={() => marcar(detalle.id_pedido, 'marcar-listo')}
                  className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700">
                  <CheckCircle size={14} className="inline mr-1" /> Marcar listo para entrega
                </button>
              )}
              {detalle.estado === 'listo_para_entrega' && (
                <button onClick={() => marcar(detalle.id_pedido, 'marcar-entregado')}
                  className="flex-1 py-2 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700">
                  <PackageCheck size={14} className="inline mr-1" /> Marcar entregado
                </button>
              )}
              <button onClick={() => setDetalle(null)}
                className="px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
