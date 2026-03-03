import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { DollarSign, Plus, Edit, X } from 'lucide-react'

const formatMoney = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

export default function Precios() {
  const [colegios, setColegios] = useState([])
  const [productos, setProductos] = useState([])
  const [precios, setPrecios] = useState([])
  const [colegioId, setColegioId] = useState('')
  const [productoId, setProductoId] = useState('')
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState(null)
  const [editPrecio, setEditPrecio] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [newPrecio, setNewPrecio] = useState({
    colegio_id: '',
    producto_id: '',
    talla_grupo: '',
    precio_unitario: ''
  })

  useEffect(() => {
    loadColegiosYProductos()
  }, [])

  useEffect(() => {
    if (colegioId && productoId) {
      loadPrecios(colegioId, productoId)
    }
  }, [colegioId, productoId])

  const loadColegiosYProductos = async () => {
    try {
      const [colegiosRes, productosRes] = await Promise.all([
        api.get('/colegios'),
        api.get('/productos')
      ])
      setColegios(colegiosRes.data.colegios || [])
      setProductos(productosRes.data.productos || [])
    } catch (err) {
      toast.error('Error cargando datos')
    } finally {
      setLoading(false)
    }
  }

  const loadPrecios = async (colId, prodId) => {
    try {
      const res = await api.get('/precios', {
        params: { colegio_id: colId, producto_id: prodId }
      })
      setPrecios(res.data.precios || [])
    } catch (err) {
      toast.error('Error cargando precios')
    }
  }

  const updatePrecio = async (id) => {
    if (!editPrecio || editPrecio <= 0) {
      toast.error('Precio inválido')
      return
    }
    try {
      await api.put(`/precios/${id}`, { precio_unitario: parseFloat(editPrecio) })
      toast.success('Precio actualizado')
      setEditingId(null)
      loadPrecios(colegioId, productoId)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const deletePrecio = async (id) => {
    if (!confirm('¿Eliminar este precio?')) return
    try {
      await api.delete(`/precios/${id}`)
      toast.success('Precio eliminado')
      loadPrecios(colegioId, productoId)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const addPrecio = async (e) => {
    e.preventDefault()
    if (!newPrecio.colegio_id || !newPrecio.producto_id || !newPrecio.talla_grupo || !newPrecio.precio_unitario) {
      toast.error('Completa todos los campos')
      return
    }
    try {
      await api.post('/precios', {
        ...newPrecio,
        colegio_id: parseInt(newPrecio.colegio_id),
        producto_id: parseInt(newPrecio.producto_id),
        precio_unitario: parseFloat(newPrecio.precio_unitario)
      })
      toast.success('Precio agregado')
      setShowForm(false)
      setNewPrecio({ colegio_id: '', producto_id: '', talla_grupo: '', precio_unitario: '' })
      loadPrecios(colegioId, productoId)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  if (loading) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Precios de Prendas</h2>

      {/* Selectores */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Colegio *</label>
            <select
              value={colegioId}
              onChange={(e) => {
                setColegioId(e.target.value)
                setProductoId('')
                setPrecios([])
              }}
              className="input-field w-full"
            >
              <option value="">Seleccionar colegio</option>
              {colegios.map(c => (
                <option key={c.id_colegio} value={c.id_colegio}>{c.nombre}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Producto *</label>
            <select
              value={productoId}
              onChange={(e) => {
                setProductoId(e.target.value)
                setPrecios([])
              }}
              disabled={!colegioId}
              className="input-field w-full disabled:bg-gray-100"
            >
              <option value="">Seleccionar producto</option>
              {productos.map(p => (
                <option key={p.id_producto} value={p.id_producto}>{p.nombre}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Tabla de Precios */}
      {colegioId && productoId ? (
        <>
          <div className="flex items-center justify-between flex-wrap gap-4">
            <h3 className="font-semibold text-lg">
              Precios: {colegios.find(c => c.id_colegio.toString() === colegioId.toString())?.nombre} - {productos.find(p => p.id_producto.toString() === productoId.toString())?.nombre}
            </h3>
            <button
              onClick={() => {
                setNewPrecio({
                  colegio_id: colegioId,
                  producto_id: productoId,
                  talla_grupo: '',
                  precio_unitario: ''
                })
                setShowForm(true)
              }}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Plus size={16} /> Agregar Precio
            </button>
          </div>

          {precios.length === 0 ? (
            <div className="card text-center py-12">
              <DollarSign className="mx-auto text-gray-300 mb-4" size={48} />
              <p className="text-gray-500">No hay precios registrados para esta combinación</p>
            </div>
          ) : (
            <div className="card overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    <th className="px-4 py-3 text-left text-gray-600 font-medium">Talla/Grupo</th>
                    <th className="px-4 py-3 text-right text-gray-600 font-medium">Precio Unitario</th>
                    <th className="px-4 py-3 text-center text-gray-600 font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {precios.map(p => (
                    <tr key={p.id_precio} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{p.talla_grupo}</td>
                      <td className="px-4 py-3 text-right">
                        {editingId === p.id_precio ? (
                          <input
                            type="number"
                            value={editPrecio}
                            onChange={(e) => setEditPrecio(e.target.value)}
                            className="input-field w-32 text-right"
                            autoFocus
                            onBlur={() => {
                              if (editPrecio !== p.precio_unitario.toString()) {
                                updatePrecio(p.id_precio)
                              } else {
                                setEditingId(null)
                              }
                            }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') updatePrecio(p.id_precio)
                              if (e.key === 'Escape') setEditingId(null)
                            }}
                          />
                        ) : (
                          <span
                            onClick={() => {
                              setEditingId(p.id_precio)
                              setEditPrecio(p.precio_unitario.toString())
                            }}
                            className="cursor-pointer font-semibold text-green-600 hover:text-green-800"
                          >
                            {formatMoney(p.precio_unitario)}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => deletePrecio(p.id_precio)}
                          className="text-red-600 hover:text-red-800 p-1"
                          title="Eliminar"
                        >
                          <X size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : (
        <div className="card text-center py-12">
          <DollarSign className="mx-auto text-gray-300 mb-4" size={48} />
          <p className="text-gray-500">Selecciona un colegio y producto para ver precios</p>
        </div>
      )}

      {/* Modal Agregar Precio */}
      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md max-h-screen overflow-y-auto">
            <h3 className="text-lg font-bold mb-4">Agregar Precio</h3>
            <form onSubmit={addPrecio} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Colegio *</label>
                <select
                  value={newPrecio.colegio_id}
                  onChange={e => setNewPrecio({...newPrecio, colegio_id: e.target.value})}
                  className="input-field w-full"
                  required
                >
                  <option value="">Seleccionar colegio</option>
                  {colegios.map(c => (
                    <option key={c.id_colegio} value={c.id_colegio}>{c.nombre}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Producto *</label>
                <select
                  value={newPrecio.producto_id}
                  onChange={e => setNewPrecio({...newPrecio, producto_id: e.target.value})}
                  className="input-field w-full"
                  required
                >
                  <option value="">Seleccionar producto</option>
                  {productos.map(p => (
                    <option key={p.id_producto} value={p.id_producto}>{p.nombre}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Talla/Grupo *</label>
                <input
                  type="text"
                  required
                  value={newPrecio.talla_grupo}
                  onChange={e => setNewPrecio({...newPrecio, talla_grupo: e.target.value})}
                  className="input-field w-full"
                  placeholder="Ej: 4-6, M, Grande"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Precio Unitario *</label>
                <input
                  type="number"
                  required
                  min="0.01"
                  step="0.01"
                  value={newPrecio.precio_unitario}
                  onChange={e => setNewPrecio({...newPrecio, precio_unitario: e.target.value})}
                  className="input-field w-full"
                  placeholder="0.00"
                />
              </div>

              <div className="flex gap-3 justify-end pt-4 border-t">
                <button
                  type="button"
                  onClick={() => {
                    setShowForm(false)
                    setNewPrecio({ colegio_id: '', producto_id: '', talla_grupo: '', precio_unitario: '' })
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
