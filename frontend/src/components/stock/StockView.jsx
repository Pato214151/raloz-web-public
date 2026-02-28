import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Package, AlertTriangle, Edit, Plus, X } from 'lucide-react'

const getStockStatus = (cantidad) => {
  if (cantidad === 0) return { label: 'Sin Stock', color: 'bg-red-100 text-red-700', icon: 'bg-red-500' }
  if (cantidad < 5) return { label: 'Bajo Stock', color: 'bg-yellow-100 text-yellow-700', icon: 'bg-yellow-500' }
  return { label: 'En Stock', color: 'bg-green-100 text-green-700', icon: 'bg-green-500' }
}

export default function StockView() {
  const [resumen, setResumen] = useState([])
  const [colegios, setColegios] = useState([])
  const [stock, setStock] = useState([])
  const [colegioId, setColegioId] = useState('')
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState(null)
  const [editCantidad, setEditCantidad] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)
  const [newStock, setNewStock] = useState({ producto_id: '', talla: '', cantidad: '' })

  useEffect(() => {
    loadResumen()
  }, [])

  useEffect(() => {
    if (colegioId) {
      loadStock(colegioId)
    }
  }, [colegioId])

  const loadResumen = async () => {
    try {
      const res = await api.get('/stock/resumen')
      setResumen(res.data.resumen || [])
      const colegiosRes = await api.get('/colegios')
      setColegios(colegiosRes.data.colegios || [])
    } catch (err) {
      toast.error('Error cargando stock')
    } finally {
      setLoading(false)
    }
  }

  const loadStock = async (id) => {
    try {
      const res = await api.get('/stock', { params: { colegio_id: id } })
      setStock(res.data.stock || [])
    } catch (err) {
      toast.error('Error cargando detalle')
    }
  }

  const updateCantidad = async (id) => {
    if (!editCantidad || editCantidad < 0) {
      toast.error('Cantidad inválida')
      return
    }
    try {
      await api.put(`/stock/${id}`, { cantidad: parseInt(editCantidad) })
      toast.success('Stock actualizado')
      setEditingId(null)
      loadStock(colegioId)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const deleteStock = async (id) => {
    if (!confirm('¿Eliminar este ítem de stock?')) return
    try {
      await api.delete(`/stock/${id}`)
      toast.success('Eliminado')
      loadStock(colegioId)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const addStock = async (e) => {
    e.preventDefault()
    if (!newStock.producto_id || !newStock.talla || !newStock.cantidad) {
      toast.error('Completa todos los campos')
      return
    }
    try {
      await api.post('/stock', {
        colegio_id: colegioId,
        producto_id: newStock.producto_id,
        talla_individual: newStock.talla,
        cantidad: parseInt(newStock.cantidad)
      })
      toast.success('Stock agregado')
      setShowAddForm(false)
      setNewStock({ producto_id: '', talla: '', cantidad: '' })
      loadStock(colegioId)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const totalUnidades = stock.reduce((sum, s) => sum + s.cantidad, 0)
  const bajoStock = stock.filter(s => s.cantidad > 0 && s.cantidad < 5).length
  const sinStock = stock.filter(s => s.cantidad === 0).length

  if (loading) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Inventario de Prendas</h2>

      {/* Resumen por Colegio */}
      <div className="space-y-4">
        <h3 className="font-semibold text-lg">Colegios</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {resumen.map(r => (
            <div
              key={r.id_colegio}
              onClick={() => setColegioId(r.id_colegio)}
              className={`card cursor-pointer hover:shadow-lg transition-all ${
                colegioId === r.id_colegio ? 'ring-2 ring-raloz-500 shadow-lg' : ''
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3 flex-1">
                  <div className="p-2 bg-raloz-100 rounded">
                    <Package className="text-raloz-600" size={20} />
                  </div>
                  <div>
                    <p className="font-semibold">{r.colegio}</p>
                    <p className="text-sm text-gray-600">{r.total_unidades} unidades</p>
                    <p className="text-xs text-gray-500">{r.total_items} items</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detalle de Stock */}
      {colegioId && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <h3 className="font-semibold text-lg">
              Stock de {colegios.find(c => c.id_colegio.toString() === colegioId.toString())?.nombre || 'Colegio'}
            </h3>
            <button
              onClick={() => setShowAddForm(true)}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Plus size={16} /> Agregar Stock
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card">
              <p className="text-xs text-gray-600 mb-1">Total Unidades</p>
              <p className="text-2xl font-bold text-blue-600">{totalUnidades}</p>
            </div>
            <div className="card">
              <p className="text-xs text-gray-600 mb-1">Bajo Stock</p>
              <p className="text-2xl font-bold text-yellow-600">{bajoStock}</p>
            </div>
            <div className="card">
              <p className="text-xs text-gray-600 mb-1">Sin Stock</p>
              <p className="text-2xl font-bold text-red-600">{sinStock}</p>
            </div>
          </div>

          {/* Tabla de Stock */}
          {stock.length === 0 ? (
            <div className="card text-center py-12">
              <Package className="mx-auto text-gray-300 mb-4" size={48} />
              <p className="text-gray-500">No hay items de stock</p>
            </div>
          ) : (
            <div className="card overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    <th className="px-4 py-3 text-left text-gray-600 font-medium">Producto</th>
                    <th className="px-4 py-3 text-left text-gray-600 font-medium">Talla</th>
                    <th className="px-4 py-3 text-right text-gray-600 font-medium">Cantidad</th>
                    <th className="px-4 py-3 text-center text-gray-600 font-medium">Estado</th>
                    <th className="px-4 py-3 text-center text-gray-600 font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {stock.map(s => {
                    const status = getStockStatus(s.cantidad)
                    return (
                      <tr key={s.id_stock} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-900">{s.producto_nombre || s.id_producto}</td>
                        <td className="px-4 py-3 text-gray-700">{s.talla_individual || '—'}</td>
                        <td className="px-4 py-3 text-right">
                          {editingId === s.id_stock ? (
                            <input
                              type="number"
                              value={editCantidad}
                              onChange={(e) => setEditCantidad(e.target.value)}
                              className="input w-20 text-right"
                              autoFocus
                              onBlur={() => {
                                if (editCantidad !== s.cantidad.toString()) {
                                  updateCantidad(s.id_stock)
                                } else {
                                  setEditingId(null)
                                }
                              }}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') updateCantidad(s.id_stock)
                                if (e.key === 'Escape') setEditingId(null)
                              }}
                            />
                          ) : (
                            <span
                              onClick={() => {
                                setEditingId(s.id_stock)
                                setEditCantidad(s.cantidad.toString())
                              }}
                              className="cursor-pointer font-semibold hover:text-raloz-600"
                            >
                              {s.cantidad}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${status.color}`}>
                            {status.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => deleteStock(s.id_stock)}
                            className="text-red-600 hover:text-red-800 p-1"
                            title="Eliminar"
                          >
                            <X size={14} />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Alertas de Stock Bajo */}
          {bajoStock > 0 && (
            <div className="card bg-yellow-50 border-yellow-200">
              <div className="flex items-start gap-3">
                <AlertTriangle className="text-yellow-600 mt-0.5" size={20} />
                <div>
                  <p className="font-semibold text-yellow-900">Stock Bajo</p>
                  <p className="text-sm text-yellow-800">{bajoStock} item(s) con cantidad menor a 5 unidades</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modal Agregar Stock */}
      {showAddForm && colegioId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md max-h-screen overflow-y-auto">
            <h3 className="text-lg font-bold mb-4">Agregar Stock</h3>
            <form onSubmit={addStock} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Producto *</label>
                <input
                  type="text"
                  required
                  value={newStock.producto_id}
                  onChange={e => setNewStock({...newStock, producto_id: e.target.value})}
                  className="input w-full"
                  placeholder="ID o nombre del producto"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Talla *</label>
                <input
                  type="text"
                  required
                  value={newStock.talla}
                  onChange={e => setNewStock({...newStock, talla: e.target.value})}
                  className="input w-full"
                  placeholder="Talla"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Cantidad *</label>
                <input
                  type="number"
                  required
                  min="1"
                  value={newStock.cantidad}
                  onChange={e => setNewStock({...newStock, cantidad: e.target.value})}
                  className="input w-full"
                  placeholder="0"
                />
              </div>

              <div className="flex gap-3 justify-end pt-4 border-t">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddForm(false)
                    setNewStock({ producto_id: '', talla: '', cantidad: '' })
                  }}
                  className="btn-secondary"
                >
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Agregar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
