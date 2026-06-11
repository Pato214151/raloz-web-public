import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import {
  ShoppingCart, CheckCircle, XCircle, Clock, Download,
  RefreshCw, Eye, CreditCard, Package, Truck, FileText, Mail,
} from 'lucide-react'

const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')
const fmtFecha = (iso) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
}

const ESTADOS_PAGO = {
  pendiente: { label: 'Pendiente', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  pagado:    { label: 'Pagado',    color: 'bg-green-100 text-green-800',  icon: CheckCircle },
  fallido:   { label: 'Fallido',   color: 'bg-red-100 text-red-800',     icon: XCircle },
  cancelado: { label: 'Cancelado', color: 'bg-gray-100 text-gray-700',   icon: XCircle },
}

const ESTADOS_ENTREGA = {
  POR_ENTREGAR: { label: 'Por entregar', color: 'bg-blue-100 text-blue-700',   icon: '📦' },
  EMPACADO:     { label: 'Empacado',     color: 'bg-purple-100 text-purple-700', icon: '🎁' },
  ENTREGADO:    { label: 'Entregado',    color: 'bg-green-100 text-green-700', icon: '✅' },
}

export default function PedidosOnline() {
  const [pedidos, setPedidos]       = useState([])
  const [total, setTotal]           = useState(0)
  const [loading, setLoading]       = useState(false)
  const [filtroEstado, setFiltro]   = useState('activos')
  const [seleccionado, setSelected] = useState(null)
  const [descargando, setDesc]      = useState(null)
  const [marcando, setMarcando]     = useState(null)
  const [generando, setGenerando]   = useState(null)
  const [actualizando, setActual]   = useState(null)
  const [enviando, setEnviando]     = useState(null)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const params = filtroEstado === 'activos'
        ? { vista: 'activos' }
        : (filtroEstado ? { estado: filtroEstado } : {})
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

  const generarFactura = async (pedido) => {
    setGenerando(pedido.id_pedido)
    try {
      const res = await api.post(`/tienda/admin/pedidos/${pedido.id_pedido}/generar-factura`)
      toast.success(`Factura ${res.data.factura_numero} generada ✅`)
      cargar()
      if (seleccionado?.id_pedido === pedido.id_pedido) {
        const det = await api.get(`/tienda/admin/pedidos/${pedido.id_pedido}`)
        setSelected(det.data.pedido)
      }
    } catch (err) {
      toast.error(err?.response?.data?.error || 'Error generando factura')
    } finally {
      setGenerando(null)
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

  const reenviarEmail = async (pedido) => {
    setEnviando(pedido.id_pedido)
    try {
      const res = await api.post(`/tienda/admin/pedidos/${pedido.id_pedido}/reenviar-email`)
      toast.success(res.data.mensaje || 'Email enviado ✅')
    } catch (err) {
      toast.error(err?.response?.data?.error || 'Error enviando email')
    } finally {
      setEnviando(null)
    }
  }

  const actualizarEntrega = async (pedido, nuevoEstado) => {
    setActual(pedido.id_pedido)
    try {
      await api.post(`/tienda/admin/pedidos/${pedido.id_pedido}/actualizar-entrega`, {
        estado_entrega: nuevoEstado,
      })
      const labels = { EMPACADO: '🎁 Marcado como empacado', ENTREGADO: '✅ Marcado como entregado' }
      toast.success(labels[nuevoEstado] || 'Estado actualizado')
      cargar()
      if (seleccionado?.id_pedido === pedido.id_pedido) {
        const det = await api.get(`/tienda/admin/pedidos/${pedido.id_pedido}`)
        setSelected(det.data.pedido)
      }
    } catch (err) {
      toast.error(err?.response?.data?.error || 'Error actualizando estado')
    } finally {
      setActual(null)
    }
  }

  const BadgePago = ({ estado }) => {
    const cfg  = ESTADOS_PAGO[estado] || ESTADOS_PAGO.pendiente
    const Icon = cfg.icon
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
        <Icon size={12} /> {cfg.label}
      </span>
    )
  }

  const BadgeEntrega = ({ estado }) => {
    if (!estado) return null
    const cfg = ESTADOS_ENTREGA[estado] || ESTADOS_ENTREGA.POR_ENTREGAR
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
        {cfg.icon} {cfg.label}
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
        {[['activos', 'Por atender'], ['', 'Todos'], ['pendiente', 'Pendientes'], ['pagado', 'Pagados'], ['fallido', 'Fallidos']].map(([val, lab]) => (
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
        <div className="text-center py-12 text-gray-400">{filtroEstado === 'activos' ? '🎉 No hay pedidos por atender — ¡todo al día!' : `Sin pedidos${filtroEstado ? ` con estado "${filtroEstado}"` : ''}.`}</div>
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
                <th className="text-center px-4 py-3 text-gray-600 font-medium">Pago</th>
                <th className="text-center px-4 py-3 text-gray-600 font-medium">Entrega</th>
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
                  <td className="px-4 py-3 text-right">
                    <span className="font-semibold text-gray-800">{fmt(p.total_orden || p.total)}</span>
                    {p.tiene_fabricacion && (
                      <span className="ml-1 text-xs text-orange-600" title="Incluye fabricación">🏭</span>
                    )}
                    {p.abono_porcentaje === 50 && (
                      <div className="text-xs text-amber-600 font-normal">Cobrado: {fmt(p.total)}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center"><BadgePago estado={p.estado} /></td>
                  <td className="px-4 py-3 text-center">
                    {p.estado === 'pagado' && <BadgeEntrega estado={p.estado_entrega} />}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1.5">
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
                      {p.estado === 'pagado' && !p.id_factura && (
                        <button onClick={() => generarFactura(p)} title="Generar factura"
                          disabled={generando === p.id_pedido}
                          className="p-1.5 rounded hover:bg-yellow-50 text-yellow-600 disabled:opacity-40">
                          <FileText size={15} className={generando === p.id_pedido ? 'animate-pulse' : ''} />
                        </button>
                      )}
                      {p.estado === 'pagado' && p.id_factura && (
                        <button onClick={() => descargarPDF(p)} title="Descargar factura PDF"
                          disabled={descargando === p.id_pedido}
                          className="p-1.5 rounded hover:bg-green-50 text-green-600 disabled:opacity-40">
                          <Download size={15} className={descargando === p.id_pedido ? 'animate-bounce' : ''} />
                        </button>
                      )}
                      {p.estado === 'pagado' && p.estado_entrega === 'POR_ENTREGAR' && p.id_factura && (
                        <button onClick={() => actualizarEntrega(p, 'EMPACADO')} title="Marcar empacado"
                          disabled={actualizando === p.id_pedido}
                          className="p-1.5 rounded hover:bg-purple-50 text-purple-600 disabled:opacity-40">
                          <Package size={15} />
                        </button>
                      )}
                      {p.estado === 'pagado' && p.estado_entrega === 'EMPACADO' && (
                        <button onClick={() => actualizarEntrega(p, 'ENTREGADO')} title="Marcar entregado"
                          disabled={actualizando === p.id_pedido}
                          className="p-1.5 rounded hover:bg-green-50 text-green-700 disabled:opacity-40">
                          <Truck size={15} />
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
                {seleccionado.direccion_envio && (
                  <p><span className="text-gray-500">Dirección:</span> {seleccionado.direccion_envio}</p>
                )}
                {seleccionado.factura_numero && (
                  <p><span className="text-gray-500">Factura:</span> <span className="font-mono font-semibold">{seleccionado.factura_numero}</span></p>
                )}
                {seleccionado.tiene_fabricacion && (
                  <div className="mt-2 pt-2 border-t border-orange-200 flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-orange-200 text-orange-800">
                      🏭 Incluye fabricación
                    </span>
                    <span className="text-xs text-gray-500">Ver en pestaña Fabricación</span>
                  </div>
                )}
              </div>

              {/* Estado de entrega */}
              {seleccionado.estado === 'pagado' && seleccionado.estado_entrega && (
                <div className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                  <span className="text-sm text-gray-600 font-medium">Estado de entrega</span>
                  <BadgeEntrega estado={seleccionado.estado_entrega} />
                </div>
              )}

              {/* Items */}
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">Productos</p>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-500 border-b">
                      <th className="text-left pb-1">Producto</th>
                      <th className="text-center pb-1">Talla</th>
                      <th className="text-center pb-1">Cant.</th>
                      <th className="text-center pb-1">Tipo</th>
                      <th className="text-right pb-1">Subtotal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(seleccionado.items || []).map((item, i) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="py-1.5 text-gray-800">{item.nombre}</td>
                        <td className="py-1.5 text-center text-gray-600">{item.talla}</td>
                        <td className="py-1.5 text-center text-gray-600">{item.cantidad}</td>
                        <td className="py-1.5 text-center">
                          {item.tipo_pedido === 'fabricacion' ? (
                            <span className="text-xs text-orange-700 bg-orange-50 px-1.5 py-0.5 rounded">🏭 Fab.</span>
                          ) : item.tipo_pedido === 'mixto' ? (
                            <span className="text-xs text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded">Mixto</span>
                          ) : (
                            <span className="text-xs text-green-700 bg-green-50 px-1.5 py-0.5 rounded">Stock</span>
                          )}
                        </td>
                        <td className="py-1.5 text-right font-medium">{fmt(item.subtotal)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Total + estado pago */}
              <div className="pt-2 border-t border-gray-100 space-y-1">
                <div className="flex items-center justify-between">
                  <BadgePago estado={seleccionado.estado} />
                  <span className="text-lg font-bold text-orange-600">
                    {fmt(seleccionado.total_orden || seleccionado.total)}
                  </span>
                </div>
                {seleccionado.abono_porcentaje === 50 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs space-y-0.5">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Total pedido</span>
                      <span className="font-semibold">{fmt(seleccionado.total_orden)}</span>
                    </div>
                    <div className="flex justify-between text-amber-700">
                      <span>Cobrado ahora (50%)</span>
                      <span className="font-semibold">{fmt(seleccionado.total)}</span>
                    </div>
                    <div className="flex justify-between text-red-600">
                      <span>Saldo pendiente</span>
                      <span className="font-semibold">{fmt((seleccionado.total_orden || 0) - (seleccionado.total || 0))}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Acciones */}
              <div className="space-y-2">
                {seleccionado.estado === 'pendiente' && (
                  <button onClick={() => marcarPagado(seleccionado)}
                    disabled={marcando === seleccionado.id_pedido}
                    className="w-full flex items-center justify-center gap-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                    <CreditCard size={16} />
                    {marcando === seleccionado.id_pedido ? 'Procesando...' : '✓ Marcar como pagado manualmente'}
                  </button>
                )}

                {seleccionado.estado === 'pagado' && !seleccionado.id_factura && (
                  <button onClick={() => generarFactura(seleccionado)}
                    disabled={generando === seleccionado.id_pedido}
                    className="w-full flex items-center justify-center gap-2 py-2 bg-yellow-500 hover:bg-yellow-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                    <FileText size={16} />
                    {generando === seleccionado.id_pedido ? 'Generando...' : '📄 Generar Factura'}
                  </button>
                )}

                {seleccionado.estado === 'pagado' && seleccionado.id_factura && (
                  <div className="flex gap-2">
                    <button onClick={() => descargarPDF(seleccionado)}
                      disabled={descargando === seleccionado.id_pedido}
                      className="flex-1 flex items-center justify-center gap-2 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                      <Download size={16} />
                      {descargando === seleccionado.id_pedido ? 'Generando...' : 'Descargar PDF'}
                    </button>
                    <button onClick={() => reenviarEmail(seleccionado)}
                      disabled={enviando === seleccionado.id_pedido}
                      title="Reenviar email de confirmación al cliente"
                      className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                      <Mail size={16} />
                      {enviando === seleccionado.id_pedido ? '...' : 'Email'}
                    </button>
                  </div>
                )}

                {seleccionado.estado === 'pagado' && seleccionado.estado_entrega === 'POR_ENTREGAR' && seleccionado.id_factura && (
                  <button onClick={() => actualizarEntrega(seleccionado, 'EMPACADO')}
                    disabled={actualizando === seleccionado.id_pedido}
                    className="w-full flex items-center justify-center gap-2 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                    <Package size={16} />
                    {actualizando === seleccionado.id_pedido ? 'Actualizando...' : '🎁 Marcar como Empacado'}
                  </button>
                )}

                {seleccionado.estado === 'pagado' && seleccionado.estado_entrega === 'EMPACADO' && (
                  <button onClick={() => actualizarEntrega(seleccionado, 'ENTREGADO')}
                    disabled={actualizando === seleccionado.id_pedido}
                    className="w-full flex items-center justify-center gap-2 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                    <Truck size={16} />
                    {actualizando === seleccionado.id_pedido ? 'Actualizando...' : '🚚 Marcar como Entregado'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
