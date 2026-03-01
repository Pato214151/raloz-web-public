import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Package, Search, Check, X, AlertTriangle, FileText, User, School, Calendar, DollarSign, Hash } from 'lucide-react'

export default function Empaque() {
  const [numeroFactura, setNumeroFactura] = useState('')
  const [factura, setFactura] = useState(null)
  const [detalles, setDetalles] = useState([])
  const [prendasExistentes, setPrendasExistentes] = useState([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [totalPendientesSistema, setTotalPendientesSistema] = useState(0)

  // Estado por cada detalle: { checked, cantidad, genero, observaciones }
  const [itemStates, setItemStates] = useState({})

  // Cargar total de pendientes del sistema al montar
  useEffect(() => {
    cargarTotalPendientes()
  }, [])

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Package className="text-blue-600" size={28} />
            Empaque - Registrar Pendientes
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Busca una factura, marca las prendas que quedaron debiendo y guárdalas como pendientes
          </p>
        </div>
        <div className="bg-orange-50 border border-orange-200 rounded-lg px-4 py-2">
          <p className="text-xs text-orange-600">Total pendientes en sistema</p>
          <p className="text-xl font-bold text-orange-700">{totalPendientesSistema} prendas</p>
        </div>
      </div>

      {/* Búsqueda */}
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
                placeholder="Ej: FAC-2026-000001"
                className="input-field pl-10 w-full"
              />
            </div>
          </div>
          <button type="submit" className="btn-primary h-10" disabled={loading}>
            {loading ? 'Buscando...' : 'Buscar Factura'}
          </button>
          {factura && (
            <button type="button" onClick={limpiar} className="btn-secondary h-10">
              Limpiar
            </button>
          )}
        </div>
      </form>

      {/* Detalle de Factura */}
      {factura && (
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
                  Todo Listo (Sin pendientes)
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Estado inicial */}
      {!factura && !loading && (
        <div className="card text-center py-16">
          <Package className="mx-auto text-gray-300 mb-4" size={56} />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">Busca una Factura</h3>
          <p className="text-gray-500 max-w-md mx-auto">
            Ingresa el número de factura para ver los productos. Podrás marcar las prendas que quedaron debiendo
            y registrarlas como pendientes automáticamente.
          </p>
        </div>
      )}
    </div>
  )
}
