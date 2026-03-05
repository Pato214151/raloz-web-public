import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Package, Search, Check, X, AlertTriangle, FileText, User, School, Calendar, DollarSign, Hash, Phone, Bell, Printer } from 'lucide-react'

export default function Empaque() {
  const [numeroFactura, setNumeroFactura] = useState('')
  const [factura, setFactura] = useState(null)
  const [detalles, setDetalles] = useState([])
  const [prendasExistentes, setPrendasExistentes] = useState([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [totalPendientesSistema, setTotalPendientesSistema] = useState(0)
  const [tab, setTab] = useState('registrar') // 'registrar' | 'listos'
  const [listosLlamar, setListosLlamar] = useState([])
  const [loadingListos, setLoadingListos] = useState(false)

  // Estado por cada detalle: { checked, cantidad, genero, observaciones }
  const [itemStates, setItemStates] = useState({})

  // Cargar total de pendientes del sistema al montar
  useEffect(() => {
    cargarTotalPendientes()
  }, [])

  useEffect(() => {
    if (tab === 'listos') cargarListosLlamar()
  }, [tab])

  const cargarListosLlamar = async () => {
    setLoadingListos(true)
    try {
      const res = await api.get('/empaque/listos-llamar')
      setListosLlamar(res.data)
    } catch {
      toast.error('Error cargando paquetes listos')
    } finally {
      setLoadingListos(false)
    }
  }

  const cargarTotalPendientes = async () => {
    try {
      const res = await api.get('/prendas?estado=PENDIENTE&per_page=1')
      setTotalPendientesSistema(res.data.total_pendientes || res.data.total || 0)
    } catch (err) {
      // silencioso
    }
  }

  const buscarFactura = async (e) => {
    e.preventDefault()
    if (!numeroFactura.trim()) {
      toast.error('Ingresa un número de factura')
      return
    }

    setLoading(true)
    try {
      // Usar el endpoint correcto de empaque
      const res = await api.get(`/empaque/factura/${numeroFactura.trim()}`)
      const data = res.data

      setFactura(data.factura)
      setDetalles(data.factura.detalles || [])
      setPrendasExistentes(data.prendas_pendientes || [])

      // Inicializar estados de cada item
      const states = {}
      ;(data.factura.detalles || []).forEach((det, idx) => {
        // Verificar si este item ya tiene prendas pendientes registradas
        const yaRegistrado = (data.prendas_pendientes || []).some(
          p => p.producto_nombre === det.producto_nombre && p.talla === det.talla && p.estado === 'PENDIENTE'
        )
        states[idx] = {
          checked: false,
          cantidad: det.cantidad,
          genero: data.factura.genero_estudiante || 'NIÑO',
          observaciones: '',
          yaRegistrado: yaRegistrado,
        }
      })
      setItemStates(states)
    } catch (err) {
      toast.error('Factura no encontrada. Verifica el número.')
      setFactura(null)
      setDetalles([])
      setPrendasExistentes([])
      setItemStates({})
    } finally {
      setLoading(false)
    }
  }

  const updateItemState = (idx, field, value) => {
    setItemStates(prev => ({
      ...prev,
      [idx]: { ...prev[idx], [field]: value }
    }))
  }

  const toggleItem = (idx) => {
    if (itemStates[idx]?.yaRegistrado) return
    updateItemState(idx, 'checked', !itemStates[idx]?.checked)
  }

  const selectedCount = Object.values(itemStates).filter(s => s.checked && !s.yaRegistrado).length
  const yaRegistradosCount = Object.values(itemStates).filter(s => s.yaRegistrado).length

  const guardarPendientes = async () => {
    const prendas = []

    Object.entries(itemStates).forEach(([idx, state]) => {
      if (state.checked && !state.yaRegistrado) {
        const det = detalles[parseInt(idx)]
        prendas.push({
          producto_nombre: det.producto_nombre,
          talla: det.talla,
          cantidad: state.cantidad,
          genero: state.genero,
          observaciones: state.observaciones,
        })
      }
    })

    if (prendas.length === 0) {
      toast.error('Selecciona al menos un producto para marcar como pendiente')
      return
    }

    setSaving(true)
    try {
      const res = await api.post('/empaque/registrar', {
        id_factura: factura.id_factura,
        prendas: prendas,
      })
      toast.success(`${res.data.prendas_registradas} prenda(s) registradas como pendientes`)

      // Recargar factura para actualizar estado
      const reloadRes = await api.get(`/empaque/factura/${numeroFactura.trim()}`)
      setFactura(reloadRes.data.factura)
      setDetalles(reloadRes.data.factura.detalles || [])
      setPrendasExistentes(reloadRes.data.prendas_pendientes || [])

      // Reinicializar estados
      const states = {}
      ;(reloadRes.data.factura.detalles || []).forEach((det, i) => {
        const yaRegistrado = (reloadRes.data.prendas_pendientes || []).some(
          p => p.producto_nombre === det.producto_nombre && p.talla === det.talla && p.estado === 'PENDIENTE'
        )
        states[i] = {
          checked: false,
          cantidad: det.cantidad,
          genero: reloadRes.data.factura.genero_estudiante || 'NIÑO',
          observaciones: '',
          yaRegistrado: yaRegistrado,
        }
      })
      setItemStates(states)

      cargarTotalPendientes()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al registrar pendientes')
    } finally {
      setSaving(false)
    }
  }

  const todoListo = async () => {
    if (!factura) return
    try {
      await api.post(`/empaque/todo-listo/${factura.id_factura}`)
      toast.success('Factura marcada como LISTA - sin pendientes')
      limpiar()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al marcar como lista')
    }
  }

  const marcarListoLlamar = async () => {
    if (!factura) return
    try {
      const res = await api.post(`/empaque/listo-llamar/${factura.id_factura}`)
      toast.success('¡Paquete listo para llamar al cliente!')
      imprimirTicket(res.data.factura)
      limpiar()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const imprimirTicket = (f) => {
    const w = window.open('', '_blank', 'width=400,height=300')
    const saldo = f.saldo_pendiente > 0
      ? `<p style="color:#dc2626;font-size:13px">Saldo pendiente: <b>$${Number(f.saldo_pendiente).toLocaleString('es-CO')}</b></p>`
      : '<p style="color:#16a34a;font-size:13px">✅ Factura pagada</p>'
    w.document.write(`<!DOCTYPE html><html><head><title>Ticket</title>
      <style>body{font-family:Arial,sans-serif;text-align:center;padding:20px;font-size:14px}
      .titulo{font-size:18px;font-weight:bold;color:#1e40af}
      .num{font-size:28px;font-weight:bold;color:#1e40af;margin:10px 0}
      .nombre{font-size:20px;font-weight:bold;margin:8px 0}
      hr{border:none;border-top:2px dashed #ccc;margin:12px 0}
      @media print{body{padding:10px}}</style></head>
      <body>
        <div class="titulo">📦 RALOZ COL SAS</div>
        <div>Paquete listo para entrega</div>
        <hr>
        <div class="num">${f.numero_factura}</div>
        <div class="nombre">${f.cliente_nombre}</div>
        ${f.cliente_telefono ? `<p style="font-size:16px">📞 ${f.cliente_telefono}</p>` : ''}
        ${f.colegio_nombre ? `<p style="color:#555">${f.colegio_nombre}</p>` : ''}
        ${saldo}
        <hr>
        <p style="font-size:11px;color:#999">${new Date().toLocaleString('es-CO')}</p>
        <script>window.onload=function(){window.print();window.close()}<\/script>
      </body></html>`)
    w.document.close()
  }

  const imprimirTicketManual = (f) => {
    imprimirTicket(f)
  }

  const limpiar = () => {
    setNumeroFactura('')
    setFactura(null)
    setDetalles([])
    setPrendasExistentes([])
    setItemStates({})
  }

  const formatMoney = (val) => {
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(val || 0)
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Package className="text-blue-600" size={28} />
            Empaque
          </h2>
        </div>
        <div className="bg-orange-50 border border-orange-200 rounded-lg px-4 py-2">
          <p className="text-xs text-orange-600">Pendientes en sistema</p>
          <p className="text-xl font-bold text-orange-700">{totalPendientesSistema} prendas</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setTab('registrar')}
          className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            tab === 'registrar' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Registrar pendientes
        </button>
        <button
          onClick={() => setTab('listos')}
          className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
            tab === 'listos' ? 'border-green-600 text-green-600' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Bell size={14} /> Listos para llamar
          {listosLlamar.length > 0 && (
            <span className="bg-green-500 text-white text-xs rounded-full px-1.5 py-0.5">{listosLlamar.length}</span>
          )}
        </button>
      </div>

      {/* ─── TAB: Listos para llamar ─── */}
      {tab === 'listos' && (
        <div className="space-y-3">
          {loadingListos ? (
            <div className="flex justify-center py-10"><div className="animate-spin h-8 w-8 border-b-2 border-green-600 rounded-full" /></div>
          ) : listosLlamar.length === 0 ? (
            <div className="card text-center py-14">
              <Bell className="mx-auto text-gray-300 mb-3" size={40} />
              <p className="text-gray-500">No hay paquetes listos para llamar</p>
              <p className="text-xs text-gray-400 mt-1">Cuando un paquete esté listo, aparecerá aquí</p>
            </div>
          ) : (
            listosLlamar.map(f => (
              <div key={f.id_factura} className="card flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <Package size={18} className="text-green-600" />
                  </div>
                  <div>
                    <p className="font-bold text-gray-900">{f.cliente_nombre}</p>
                    {f.cliente_telefono && (
                      <p className="text-sm text-gray-500 flex items-center gap-1">
                        <Phone size={12} /> {f.cliente_telefono}
                      </p>
                    )}
                    <p className="text-xs text-gray-400">{f.numero_factura} · {f.colegio_nombre}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {f.saldo_pendiente > 0 && (
                    <span className="text-xs bg-red-50 text-red-600 border border-red-200 px-2 py-1 rounded-full">
                      Debe ${Number(f.saldo_pendiente).toLocaleString('es-CO')}
                    </span>
                  )}
                  <button
                    onClick={() => imprimirTicketManual(f)}
                    className="btn-secondary text-sm flex items-center gap-1.5"
                  >
                    <Printer size={14} /> Imprimir
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ─── TAB: Registrar pendientes ─── */}
      {/* Búsqueda */}
      {tab === 'registrar' && (
        <form onSubmit={buscarFactura} className="card">
          <div className="flex gap-3 flex-wrap items-end">
            <div className="flex-1 min-w-64">
              <label className="block text-sm font-medium text-gray-700 mb-1">Número de Factura</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
                <input
                  type="text"
                  value={numeroFactura}
                  onChange={(e) => setNumeroFactura(e.target.value)}
                  placeholder="Ej: FAC-2026-000001 o R-981"
                  className="input-field pl-10 w-full"
                />
              </div>
            </div>
            <button type="submit" className="btn-primary h-10" disabled={loading}>
              {loading ? 'Buscando...' : 'Buscar'}
            </button>
            {factura && (
              <button type="button" onClick={limpiar} className="btn-secondary h-10">
                Limpiar
              </button>
            )}
          </div>
        </form>
      )}

      {/* Detalle de Factura */}
      {tab === 'registrar' && factura && (
        <div className="space-y-4">
          {/* Info Factura */}
          <div className="card bg-blue-50 border-blue-200">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="flex items-center gap-2">
                <FileText size={16} className="text-blue-600" />
                <div>
                  <p className="text-xs text-blue-600">Factura</p>
                  <p className="font-bold text-blue-900">{factura.numero_factura}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <User size={16} className="text-blue-600" />
                <div>
                  <p className="text-xs text-blue-600">Cliente</p>
                  <p className="font-semibold text-blue-900">{factura.cliente_nombre}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <School size={16} className="text-blue-600" />
                <div>
                  <p className="text-xs text-blue-600">Colegio</p>
                  <p className="font-semibold text-blue-900">{factura.colegio_nombre}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Calendar size={16} className="text-blue-600" />
                <div>
                  <p className="text-xs text-blue-600">Fecha</p>
                  <p className="font-semibold text-blue-900">{factura.fecha_factura}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <DollarSign size={16} className="text-blue-600" />
                <div>
                  <p className="text-xs text-blue-600">Total</p>
                  <p className="font-bold text-blue-900">{formatMoney(factura.total)}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Prendas ya registradas como pendientes */}
          {prendasExistentes.length > 0 && (
            <div className="card bg-yellow-50 border-yellow-200">
              <p className="font-semibold text-yellow-800 mb-2 flex items-center gap-2">
                <AlertTriangle size={16} />
                Prendas ya registradas como pendientes ({prendasExistentes.length})
              </p>
              <div className="space-y-1">
                {prendasExistentes.map((p, i) => (
                  <div key={i} className="text-sm text-yellow-700 flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs ${p.estado === 'PENDIENTE' ? 'bg-yellow-200' : 'bg-green-200 text-green-700'}`}>
                      {p.estado}
                    </span>
                    <span>{p.producto_nombre} - Talla {p.talla} x{p.cantidad}</span>
                    {p.genero && <span className="text-yellow-600">({p.genero})</span>}
                    {p.observaciones && <span className="italic text-yellow-600">- {p.observaciones}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tabla de productos de la factura */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-gray-900">Productos de la Factura ({detalles.length})</h3>
              <p className="text-sm text-gray-500">
                Marca las prendas que quedaron debiendo
              </p>
            </div>

            {detalles.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No hay productos en esta factura</p>
            ) : (
              <div className="space-y-3">
                {detalles.map((det, idx) => {
                  const state = itemStates[idx] || {}
                  const isYaRegistrado = state.yaRegistrado

                  return (
                    <div
                      key={idx}
                      className={`border rounded-lg p-4 transition-all ${
                        isYaRegistrado
                          ? 'bg-gray-100 border-gray-300 opacity-60'
                          : state.checked
                          ? 'bg-red-50 border-red-300 ring-2 ring-red-200'
                          : 'bg-white border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      {/* Fila principal: checkbox + info producto */}
                      <div className="flex items-center gap-4">
                        <input
                          type="checkbox"
                          checked={state.checked || false}
                          onChange={() => toggleItem(idx)}
                          disabled={isYaRegistrado}
                          className="w-5 h-5 cursor-pointer rounded border-gray-300 text-red-600 focus:ring-red-500"
                        />
                        <div className="flex-1 grid grid-cols-2 md:grid-cols-5 gap-3 items-center">
                          <div className="md:col-span-2">
                            <p className="font-semibold text-gray-900">{det.producto_nombre}</p>
                            {isYaRegistrado && (
                              <span className="text-xs text-yellow-600 font-medium">Ya en pendientes</span>
                            )}
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Talla</p>
                            <p className="font-medium">{det.talla}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Cantidad</p>
                            <p className="font-medium">{det.cantidad}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Precio Unit.</p>
                            <p className="font-medium">{formatMoney(det.precio_unitario)}</p>
                          </div>
                        </div>
                      </div>

                      {/* Campos adicionales cuando está marcado */}
                      {state.checked && !isYaRegistrado && (
                        <div className="mt-3 pt-3 border-t border-red-200 grid grid-cols-1 md:grid-cols-4 gap-3">
                          {/* Cantidad pendiente */}
                          <div>
                            <label className="block text-xs font-medium text-red-700 mb-1">
                              Cant. debiendo
                            </label>
                            <input
                              type="number"
                              min="1"
                              max={det.cantidad}
                              value={state.cantidad}
                              onChange={(e) => updateItemState(idx, 'cantidad', Math.min(Math.max(1, parseInt(e.target.value) || 1), det.cantidad))}
                              className="input-field w-full text-center"
                            />
                          </div>
                          {/* Género */}
                          <div>
                            <label className="block text-xs font-medium text-red-700 mb-1">
                              Género
                            </label>
                            <div className="flex gap-2">
                              <button
                                type="button"
                                onClick={() => updateItemState(idx, 'genero', 'NIÑO')}
                                className={`flex-1 py-2 px-3 rounded text-sm font-medium transition-colors ${
                                  state.genero === 'NIÑO'
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                              >
                                Niño
                              </button>
                              <button
                                type="button"
                                onClick={() => updateItemState(idx, 'genero', 'NIÑA')}
                                className={`flex-1 py-2 px-3 rounded text-sm font-medium transition-colors ${
                                  state.genero === 'NIÑA'
                                    ? 'bg-pink-600 text-white'
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                              >
                                Niña
                              </button>
                            </div>
                          </div>
                          {/* Observaciones */}
                          <div className="md:col-span-2">
                            <label className="block text-xs font-medium text-red-700 mb-1">
                              Observaciones
                            </label>
                            <input
                              type="text"
                              value={state.observaciones}
                              onChange={(e) => updateItemState(idx, 'observaciones', e.target.value)}
                              placeholder="Ej: largo de S, sin bolsillo..."
                              className="input-field w-full"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Resumen y acciones */}
          <div className="card bg-gray-50 border-gray-200">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="space-y-1">
                <p className="text-sm text-gray-600">
                  Seleccionados para pendientes: <span className="font-bold text-red-600">{selectedCount}</span>
                </p>
                {yaRegistradosCount > 0 && (
                  <p className="text-sm text-yellow-600">
                    Ya en pendientes: {yaRegistradosCount}
                  </p>
                )}
              </div>
              <div className="flex gap-3 flex-wrap">
                {selectedCount > 0 && (
                  <button
                    onClick={guardarPendientes}
                    disabled={saving}
                    className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-6 rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50"
                  >
                    <AlertTriangle size={16} />
                    {saving ? 'Guardando...' : `Guardar ${selectedCount} Pendiente(s)`}
                  </button>
                )}
                <button
                  onClick={todoListo}
                  className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-6 rounded-lg flex items-center gap-2 transition-colors"
                >
                  <Check size={16} />
                  Todo listo
                </button>
                <button
                  onClick={marcarListoLlamar}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg flex items-center gap-2 transition-colors"
                >
                  <Bell size={16} />
                  Listo para llamar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Estado inicial (solo en tab registrar) */}
      {tab === 'registrar' && !factura && !loading && (
        <div className="card text-center py-16">
          <Package className="mx-auto text-gray-300 mb-4" size={56} />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">Busca una Factura</h3>
          <p className="text-gray-500 max-w-md mx-auto">
            Ingresa el número de factura. Puedes registrar pendientes o marcar el paquete como listo para llamar.
          </p>
        </div>
      )}
    </div>
  )
}
