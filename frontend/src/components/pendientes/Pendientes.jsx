import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Clock, Check, Search, Plus, Package, X } from 'lucide-react'

export default function Pendientes() {
  const [prendas, setPrendas] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtro, setFiltro] = useState('PENDIENTE')
  const [buscar, setBuscar] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [nuevaPrenda, setNuevaPrenda] = useState({
    id_factura: '', producto_nombre: '', talla: '', cantidad: 1, genero: 'NIÑO', observaciones: ''
  })

  useEffect(() => { loadPrendas() }, [filtro])

  const loadPrendas = async () => {
    try {
      const params = {}
      if (filtro) params.estado = filtro
      if (buscar) params.buscar = buscar
      const res = await api.get('/prendas', { params })
      setPrendas(res.data.prendas || [])
    } catch {
      toast.error('Error cargando pendientes')
    } finally {
      setLoading(false)
    }
  }

  const handleBuscar = (e) => {
    e.preventDefault()
    setLoading(true)
    loadPrendas()
  }

  const entregar = async (id) => {
    if (!confirm('¿Marcar como entregado?')) return
    try {
      await api.post(`/prendas/${id}/entregar`)
      toast.success('Marcado como entregado')
      loadPrendas()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const crearPrenda = async (e) => {
    e.preventDefault()
    try {
      await api.post('/prendas', nuevaPrenda)
      toast.success('Prenda pendiente creada')
      setShowModal(false)
      setNuevaPrenda({ id_factura: '', producto_nombre: '', talla: '', cantidad: 1, genero: 'NIÑO', observaciones: '' })
      loadPrendas()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error creando prenda')
    }
  }

  const eliminar = async (id) => {
    if (!confirm('¿Eliminar esta prenda pendiente?')) return
    try {
      await api.delete(`/prendas/${id}`)
      toast.success('Eliminado')
      loadPrendas()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const pendientesCount = prendas.filter(p => p.estado === 'PENDIENTE').length
  const entregadosCount = prendas.filter(p => p.estado === 'ENTREGADO').length

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Prendas Pendientes</h2>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Nueva Prenda
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card bg-yellow-50 border-yellow-200">
          <div className="flex items-center gap-3">
            <Clock className="text-yellow-600" size={24} />
            <div>
              <p className="text-sm text-yellow-600">Pendientes</p>
              <p className="text-2xl font-bold text-yellow-700">{filtro === 'PENDIENTE' ? prendas.length : pendientesCount}</p>
            </div>
          </div>
        </div>
        <div className="card bg-green-50 border-green-200">
          <div className="flex items-center gap-3">
            <Check className="text-green-600" size={24} />
            <div>
              <p className="text-sm text-green-600">Entregados</p>
              <p className="text-2xl font-bold text-green-700">{filtro === 'ENTREGADO' ? prendas.length : entregadosCount}</p>
            </div>
          </div>
        </div>
        <div className="card bg-blue-50 border-blue-200">
          <div className="flex items-center gap-3">
            <Package className="text-blue-600" size={24} />
            <div>
              <p className="text-sm text-blue-600">Total</p>
              <p className="text-2xl font-bold text-blue-700">{prendas.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="card">
        <div className="flex flex-col md:flex-row gap-4">
          <form onSubmit={handleBuscar} className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
              <input
                type="text"
                value={buscar}
                onChange={(e) => setBuscar(e.target.value)}
                placeholder="Buscar por cliente, producto, factura..."
                className="input pl-10 w-full"
              />
            </div>
            <button type="submit" className="btn-primary">Buscar</button>
          </form>
          <div className="flex gap-2">
            {['PENDIENTE', 'ENTREGADO', ''].map((estado) => (
              <button
                key={estado}
                onClick={() => { setFiltro(estado); setLoading(true) }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filtro === estado ? 'bg-raloz-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {estado === '' ? 'Todos' : estado === 'PENDIENTE' ? 'Pendientes' : 'Entregados'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Lista */}
      {prendas.length === 0 ? (
        <div className="card text-center py-12">
          <Package className="mx-auto text-gray-300 mb-4" size={48} />
          <p className="text-gray-500">No hay prendas {filtro === 'PENDIENTE' ? 'pendientes' : filtro === 'ENTREGADO' ? 'entregadas' : ''}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {prendas.map(p => (
            <div key={p.id_pendiente} className={`card flex items-center justify-between ${
              p.estado === 'ENTREGADO' ? 'bg-green-50 border-green-100' : ''
            }`}>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-gray-900">{p.producto_nombre}</p>
                  {p.talla && <span className="text-xs bg-gray-200 text-gray-700 px-2 py-0.5 rounded">Talla {p.talla}</span>}
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    p.genero === 'NIÑA' ? 'bg-pink-100 text-pink-700' : 'bg-blue-100 text-blue-700'
                  }`}>{p.genero}</span>
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                    p.estado === 'PENDIENTE' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
                  }`}>{p.estado}</span>
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  Cliente: {p.cliente_nombre} • Factura: {p.numero_factura} • Colegio: {p.colegio_nombre}
                </p>
                <p className="text-xs text-gray-400">
                  Cant: {p.cantidad} • Registrado: {p.fecha_registro}
                  {p.fecha_entrega && ` • Entregado: ${p.fecha_entrega}`}
                  {p.observaciones && ` • ${p.observaciones}`}
                </p>
              </div>
              <div className="flex gap-2">
                {p.estado === 'PENDIENTE' && (
                  <button onClick={() => entregar(p.id_pendiente)} className="btn-success flex items-center gap-1 text-sm">
                    <Check size={14} /> Entregar
                  </button>
                )}
                <button onClick={() => eliminar(p.id_pendiente)} className="text-red-500 hover:text-red-700 p-2">
                  <X size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Crear Prenda */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-bold mb-4">Nueva Prenda Pendiente</h3>
            <form onSubmit={crearPrenda} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">ID Factura *</label>
                <input type="number" required value={nuevaPrenda.id_factura}
                  onChange={e => setNuevaPrenda({...nuevaPrenda, id_factura: e.target.value})}
                  className="input w-full" placeholder="Número de ID de factura" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Producto *</label>
                <input type="text" required value={nuevaPrenda.producto_nombre}
                  onChange={e => setNuevaPrenda({...nuevaPrenda, producto_nombre: e.target.value})}
                  className="input w-full" placeholder="Nombre del producto" />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Talla</label>
                  <input type="text" value={nuevaPrenda.talla}
                    onChange={e => setNuevaPrenda({...nuevaPrenda, talla: e.target.value})}
                    className="input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Cantidad *</label>
                  <input type="number" min="1" required value={nuevaPrenda.cantidad}
                    onChange={e => setNuevaPrenda({...nuevaPrenda, cantidad: parseInt(e.target.value)})}
                    className="input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Género</label>
                  <select value={nuevaPrenda.genero}
                    onChange={e => setNuevaPrenda({...nuevaPrenda, genero: e.target.value})}
                    className="input w-full">
                    <option value="NIÑO">NIÑO</option>
                    <option value="NIÑA">NIÑA</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Observaciones</label>
                <textarea value={nuevaPrenda.observaciones}
                  onChange={e => setNuevaPrenda({...nuevaPrenda, observaciones: e.target.value})}
                  className="input w-full" rows={2} />
              </div>
              <div className="flex gap-3 justify-end">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">Cancelar</button>
                <button type="submit" className="btn-primary">Crear</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
