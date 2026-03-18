import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { ShoppingCart, CheckCircle, XCircle, Clock, Download, RefreshCw, Eye, CreditCard } from 'lucide-react'

const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')
const fmtFecha = (iso) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
}

const ESTADOS = {
  pendiente: { label: 'Pendiente', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  pagado:    { label: 'Pagado',    color: 'bg-green-100 text-green-800',  icon: CheckCircle },
  fallido:   { label: 'Fallido',   color: 'bg-red-100 text-red-800',     icon: XCircle },
  cancelado: { label: 'Cancelado', color: 'bg-gray-100 text-gray-700',   icon: XCircle },
}

export default function PedidosOnline() {
  const [pedidos, setPedidos]       = useState([])
  const [total, setTotal]           = useState(0)
  const [loading, setLoading]       = useState(false)
  const [filtroEstado, setFiltro]   = useState('')
  const [seleccionado, setSelected] = useState(null)
  const [descargando, setDesc]      = useState(null)
  const [marcando, setMarcando]     = useState(null)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const params = filtroEstado ? { estado: filtroEstado } : {}
      const res = await api.get('/tienda/admin/pedidos', { params })
      setPedidos(res.data.pedidos || [])
      setTotal(res.data.total || 0)
    } catch {
      toast.error('Error cargando pedidos online')
    } finally {
      setLoading(false)
    }
  }, [filtroEstado])

  useEffect(() => { cargar() }, [cargar])

  const verDetalle = async (id) => {
    try {
      const res = await api.get(`/tienda/admin/pedidos/${id}`)
      setSelected(res.data.pedido)
    } catch {
      toast.error('Error cargando detalle')
    }
  }

  const marcarPagado = async (pedido) => {
    if (!window.confirm(`¿Marcar el pedido ${pedido.referencia} como PAGADO manualmente?\nEsto generará la factura y descontará el stock.`)) return
    setMarcando(pedido.id_pedido)
    try {
      const res = await api.post(`/tienda/admin/pedidos/${pedido.id_pedido}/marcar-pagado`)
      if (res.data.factura_numero) {
        toast.success(`✅ Pagado. Factura: ${res.data.factura_numero}`)
      } else if (res.data.error_factura) {
        toast.error(`Pedido pagado pero falló la factura: ${res.data.error_factura}`)
      } else {
        toast.success('Pedido marcado como pagado')
      }
      cargar()
      if (seleccionado?.id_pedido === pedido.id_pedido) setSelected(res.data.pedido)
    } catch (err) {
      toast.error(err?.response?.data?.error || 'No se pudo marcar como pagado')
    } finally {
      setMarcando(null)
    }
  }

  const descargarPDF = async (pedido) => {
    setDesc(pedido.id_pedido)
    try {
      const res = await api.get(`/tienda/admin/pedidos/${pedido.id_pedido}/factura.pdf`, {
        responseType: 'blob',
      })
      const url  = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href     = url
      link.download = `Factura-${pedido.referencia}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('No hay factura para este pedido aún')
    } finally {
      setDesc(null)
    }
  }

  const BadgeEstado = ({ estado }) => {
    const cfg  = ESTADOS[estado] || ESTADOS.pendiente
    const Icon = cfg.icon
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
        <Icon size={12} /> {cfg.label}
      </span>
    )
  }

  return (
    <div className="p-4 max-w-6xl mx-auto">
      {/* Cabecera */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ShoppingCart className="text-orange-500" size={22} />
          <h1 className="text-xl font-bold text-gray-800">Pedidos Online</h1>
          <span className="text-sm text-gray-500">({total} en total)</span>
        </div>
        <button onClick={cargar} disabled={loading}
          className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-sm text-gray-700">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Actualizar
        </button>
      </div>

      {/* Filtros por estado */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {[['', 'Todos'], ['pendiente', 'Pendientes'], ['pagado', 'Pagados'], ['fallido', 'Fallidos']].map(([val, lab]) => (
          <button key={val} onClick={() => setFiltro(val)}
            className={`px-3 py-1 rounded-full text-sm border transition-colors ${
              filtroEstado === val
                ? 'bg-orange-500 text-white border-orange-500'
                : 'bg-white text-gray-600 border-gray-300 hover:border-orange-400'
            }`}>
            {lab}
          </button>
        ))}
      </div>

      {/* Tabla */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Cargando pedidos...</div>
      ) : pedidos.length === 0 ? (
        <div className="text-center py-12 text-gray-400">Sin pedidos{filtroEstado ? ` con estado "${filtroEstado}"` : ''}.</div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Referencia</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Fecha</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Cliente</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Colegio</th>
                <th className="text-right px-4 py-3 text-gray-600 font-medium">Total</th>
                <th className="text-center px-4 py-3 text-gray-600 font-medium">Estado</th>
                <th className="text-center px-4 py-3 text-gray-600 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {pedidos.map(p => (
                <tr key={p.id_pedido} className="hover:bg-orange-50/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{p.referencia}</td>
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{fmtFecha(p.fecha_creacion)}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-800">{p.nombre_cliente}</div>
                    <div className="text-xs text-gray-500">{p.email_cliente}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{p.nombre_colegio || '—'}</td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-800">{fmt(p.total)}</td>
                  <td className="px-4 py-3 text-center"><BadgeEstado estado={p.estado} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-2">
                      <button onClick={() => verDetalle(p.id_pedido)} title="Ver detalle"
                        className="p-1.5 rounded hover:bg-blue-50 text-blue-500">
                        <Eye size={15} />
                      </button>
                      {p.estado === 'pendiente' && (
                        <button onClick={() => marcarPagado(p)} title="Marcar como pagado manualmente"
                          disabled={marcando === p.id_pedido}
                          className="p-1.5 rounded hover:bg-green-50 text-green-600 disabled:opacity-40">
                          <CreditCard size={15} className={marcando === p.id_pedido ? 'animate-pulse' : ''} />
                        </button>
                      )}
                      {p.estado === 'pagado' && (
                        <button onClick={() => descargarPDF(p)} title="Descargar factura PDF"
                          disabled={descargando === p.id_pedido}
                          className="p-1.5 rounded hover:bg-green-50 text-green-600 disabled:opacity-40">
                          <Download size={15} className={descargando === p.id_pedido ? 'animate-bounce' : ''} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal de detalle */}
      {seleccionado && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h2 className="font-bold text-gray-800">Pedido {seleccionado.referencia}</h2>
                <p className="text-xs text-gray-500">{fmtFecha(seleccionado.fecha_creacion)}</p>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl leading-none">×</button>
            </div>

            <div className="p-5 space-y-4">
              {/* Cliente */}
              <div className="bg-orange-50 rounded-lg p-3 text-sm space-y-1">
                <p><span className="text-gray-500">Cliente:</span> <strong>{seleccionado.nombre_cliente}</strong></p>
                <p><span className="text-gray-500">Email:</span> {seleccionado.email_cliente}</p>
                <p><span className="text-gray-500">Teléfono:</span> {seleccionado.telefono_cliente || '—'}</p>
                <p><span className="text-gray-500">Colegio:</span> {seleccionado.nombre_colegio || '—'}</p>
              </div>

              {/* Items */}
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">Productos</p>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-500 border-b">
                      <th className="text-left pb-1">Producto</th>
                      <th className="text-center pb-1">Talla</th>
                      <th className="text-center pb-1">Cant.</th>
                      <th className="text-right pb-1">Precio</th>
                      <th className="text-right pb-1">Subtotal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(seleccionado.items || []).map((item, i) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="py-1.5 text-gray-800">{item.nombre}</td>
                        <td className="py-1.5 text-center text-gray-600">{item.talla}</td>
                        <td className="py-1.5 text-center text-gray-600">{item.cantidad}</td>
                        <td className="py-1.5 text-right text-gray-600">{fmt(item.precio_unitario)}</td>
                        <td className="py-1.5 text-right font-medium">{fmt(item.subtotal)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Total + estado */}
              <div className="flex items-center justify-between pt-2 border-t border-gray-100">
                <BadgeEstado estado={seleccionado.estado} />
                <span className="text-lg font-bold text-orange-600">{fmt(seleccionado.total)}</span>
              </div>

              {/* Botón marcar pagado */}
              {seleccionado.estado === 'pendiente' && (
                <button onClick={() => marcarPagado(seleccionado)}
                  disabled={marcando === seleccionado.id_pedido}
                  className="w-full flex items-center justify-center gap-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                  <CreditCard size={16} />
                  {marcando === seleccionado.id_pedido ? 'Procesando...' : '✓ Marcar como pagado manualmente'}
                </button>
              )}
              {/* Botón PDF */}
              {seleccionado.estado === 'pagado' && (
                <button onClick={() => descargarPDF(seleccionado)}
                  disabled={descargando === seleccionado.id_pedido}
                  className="w-full flex items-center justify-center gap-2 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                  <Download size={16} />
                  {descargando === seleccionado.id_pedido ? 'Generando PDF...' : 'Descargar Factura PDF'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
