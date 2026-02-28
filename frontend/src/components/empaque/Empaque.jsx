import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Package, Search, Check, X, ChevronDown } from 'lucide-react'

export default function Empaque() {
  const [facturaId, setFacturaId] = useState('')
  const [factura, setFactura] = useState(null)
  const [productos, setProductos] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedItems, setSelectedItems] = useState(new Set())
  const [expandedItems, setExpandedItems] = useState(new Set())

  const buscarFactura = async (e) => {
    e.preventDefault()
    if (!facturaId) {
      toast.error('Ingresa un número de factura')
      return
    }

    setLoading(true)
    try {
      const res = await api.get(`/facturas/${facturaId}`)
      setFactura(res.data.factura)
      const prodRes = await api.get(`/facturas/${facturaId}/productos`)
      setProductos(prodRes.data.productos || [])
      setSelectedItems(new Set())
      setExpandedItems(new Set())
    } catch (err) {
      toast.error('Factura no encontrada')
      setFactura(null)
      setProductos([])
    } finally {
      setLoading(false)
    }
  }

  const toggleItem = (id) => {
    const newSelected = new Set(selectedItems)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedItems(newSelected)
  }

  const toggleExpand = (id) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedItems(newExpanded)
  }

  const marcarCompletados = async () => {
    if (selectedItems.size === 0) {
      toast.error('Selecciona al menos un producto')
      return
    }
    try {
      await api.post('/empaque/marcar-completados', {
        factura_id: facturaId,
        producto_ids: Array.from(selectedItems)
      })
      toast.success(`${selectedItems.size} producto(s) marcados como empacados`)
      setSelectedItems(new Set())
      // Recargar productos
      const prodRes = await api.get(`/facturas/${facturaId}/productos`)
      setProductos(prodRes.data.productos || [])
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const marcarTodosCompletados = async () => {
    if (productos.length === 0) {
      toast.error('No hay productos')
      return
    }
    try {
      const allIds = productos.map(p => p.id_producto)
      await api.post('/empaque/marcar-completados', {
        factura_id: facturaId,
        producto_ids: allIds
      })
      toast.success('Todos los productos marcados como empacados')
      setSelectedItems(new Set())
      // Recargar productos
      const prodRes = await api.get(`/facturas/${facturaId}/productos`)
      setProductos(prodRes.data.productos || [])
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const limpiar = () => {
    setFacturaId('')
    setFactura(null)
    setProductos([])
    setSelectedItems(new Set())
    setExpandedItems(new Set())
  }

  const completados = productos.filter(p => p.estado_empaque === 'COMPLETADO').length
  const pendientes = productos.filter(p => p.estado_empaque === 'PENDIENTE').length

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Empaque de Facturas</h2>

      {/* Búsqueda */}
      <form onSubmit={buscarFactura} className="card">
        <div className="flex gap-3 flex-wrap">
          <div className="relative flex-1 min-w-64">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
            <input
              type="text"
              value={facturaId}
              onChange={(e) => setFacturaId(e.target.value)}
              placeholder="Número de factura"
              className="input pl-10 w-full"
            />
          </div>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Buscando...' : 'Buscar'}
          </button>
          {factura && (
            <button type="button" onClick={limpiar} className="btn-secondary">
              Limpiar
            </button>
          )}
        </div>
      </form>

      {/* Detalle de Factura */}
      {factura && (
        <div className="space-y-6">
          {/* Info Factura */}
          <div className="card">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-600">Factura</p>
                <p className="font-semibold">{factura.numero_factura}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Cliente</p>
                <p className="font-semibold">{factura.cliente_nombre}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Colegio</p>
                <p className="font-semibold">{factura.colegio_nombre}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Fecha</p>
                <p className="font-semibold">{factura.fecha}</p>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card">
              <p className="text-xs text-gray-600 mb-1">Total Productos</p>
              <p className="text-2xl font-bold text-gray-900">{productos.length}</p>
            </div>
            <div className="card">
              <p className="text-xs text-gray-600 mb-1">Completados</p>
              <p className="text-2xl font-bold text-green-600">{completados}</p>
            </div>
            <div className="card">
              <p className="text-xs text-gray-600 mb-1">Pendientes</p>
              <p className="text-2xl font-bold text-yellow-600">{pendientes}</p>
            </div>
          </div>

          {/* Acciones */}
          {pendientes > 0 && (
            <div className="card bg-blue-50 border-blue-200">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                  <p className="font-semibold text-blue-900">Seleccionados: {selectedItems.size}</p>
                  <p className="text-sm text-blue-700">Productos por empacar</p>
                </div>
                <div className="flex gap-2">
                  {selectedItems.size > 0 && (
                    <button
                      onClick={marcarCompletados}
                      className="btn-success flex items-center gap-2"
                    >
                      <Check size={16} /> Marcar como Empacados
                    </button>
                  )}
                  <button
                    onClick={marcarTodosCompletados}
                    className="btn-primary flex items-center gap-2"
                  >
                    <Check size={16} /> Empacar Todo
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Lista de Productos */}
          {productos.length === 0 ? (
            <div className="card text-center py-12">
              <Package className="mx-auto text-gray-300 mb-4" size={48} />
              <p className="text-gray-500">No hay productos en esta factura</p>
            </div>
          ) : (
            <div className="space-y-2">
              {productos.map(producto => (
                <div
                  key={producto.id_producto}
                  className={`card ${
                    producto.estado_empaque === 'COMPLETADO'
                      ? 'bg-green-50 border-green-100'
                      : ''
                  }`}
                >
                  <div className="space-y-3">
                    {/* Header */}
                    <div className="flex items-center gap-3">
                      {producto.estado_empaque === 'PENDIENTE' && (
                        <input
                          type="checkbox"
                          checked={selectedItems.has(producto.id_producto)}
                          onChange={() => toggleItem(producto.id_producto)}
                          className="w-5 h-5 cursor-pointer"
                        />
                      )}
                      {producto.estado_empaque === 'COMPLETADO' && (
                        <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center">
                          <Check size={14} className="text-white" />
                        </div>
                      )}

                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">{producto.nombre}</p>
                        <p className="text-sm text-gray-600">
                          {producto.talla_grupo || '—'} • Cantidad: {producto.cantidad}
                        </p>
                      </div>

                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        producto.estado_empaque === 'PENDIENTE'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-green-100 text-green-700'
                      }`}>
                        {producto.estado_empaque}
                      </span>

                      {producto.detalles && producto.detalles.length > 0 && (
                        <button
                          onClick={() => toggleExpand(producto.id_producto)}
                          className="text-gray-400 hover:text-gray-600 p-1"
                        >
                          <ChevronDown
                            size={16}
                            className={`transition-transform ${
                              expandedItems.has(producto.id_producto) ? 'rotate-180' : ''
                            }`}
                          />
                        </button>
                      )}
                    </div>

                    {/* Detalles expandidos */}
                    {expandedItems.has(producto.id_producto) && producto.detalles && (
                      <div className="pl-8 border-l-2 border-gray-200 space-y-1 pt-2">
                        {producto.detalles.map((det, idx) => (
                          <div key={idx} className="text-sm text-gray-600">
                            <p>Talla: {det.talla} • Cantidad: {det.cantidad}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Notas */}
                    {producto.notas && (
                      <div className="pl-8 text-sm bg-gray-50 p-2 rounded">
                        <p className="text-gray-600"><strong>Notas:</strong> {producto.notas}</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Estado inicial */}
      {!factura && (
        <div className="card text-center py-12">
          <Package className="mx-auto text-gray-300 mb-4" size={48} />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">Busca una Factura</h3>
          <p className="text-gray-500">Ingresa el número de factura para ver los productos que necesitan empaque</p>
        </div>
      )}
    </div>
  )
}

