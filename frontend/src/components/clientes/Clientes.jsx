import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Users, Plus, Search, Edit, X, Eye, ArrowRight } from 'lucide-react'

const formatMoney = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

export default function Clientes() {
  const [clientes, setClientes] = useState([])
  const [buscar, setBuscar] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [selectedCliente, setSelectedCliente] = useState(null)
  const [colegios, setColegios] = useState([])
  const [historialCompras, setHistorialCompras] = useState([])
  const [form, setForm] = useState({
    nombre: '',
    telefono: '',
    email: '',
    tipo_documento: 'CC',
    numero_documento: '',
    direccion: '',
    id_colegio: '',
    notas: ''
  })

  useEffect(() => {
    loadColegios()
    loadClientes()
  }, [])

  const loadColegios = async () => {
    try {
      const res = await api.get('/colegios')
      setColegios(res.data.colegios || [])
    } catch (err) {
      console.error('Error cargando colegios:', err)
    }
  }

  const loadClientes = async (q = '') => {
    setLoading(true)
    try {
      const res = await api.get('/clientes', { params: { buscar: q, per_page: 100 } })
      setClientes(res.data.clientes || [])
    } catch {
      toast.error('Error cargando clientes')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    loadClientes(buscar)
  }

  const openForm = (cliente = null) => {
    if (cliente) {
      setEditingId(cliente.id_cliente)
      setForm({
        nombre: cliente.nombre || '',
        telefono: cliente.telefono || '',
        email: cliente.email || '',
        tipo_documento: cliente.tipo_documento || 'CC',
        numero_documento: cliente.numero_documento || '',
        direccion: cliente.direccion || '',
        id_colegio: cliente.id_colegio || '',
        notas: cliente.notas || ''
      })
    } else {
      setEditingId(null)
      setForm({
        nombre: '',
        telefono: '',
        email: '',
        tipo_documento: 'CC',
        numero_documento: '',
        direccion: '',
        id_colegio: '',
        notas: ''
      })
    }
    setShowForm(true)
  }

  const closeForm = () => {
    setShowForm(false)
    setEditingId(null)
  }

  const guardarCliente = async (e) => {
    e.preventDefault()
    try {
      if (editingId) {
        await api.put(`/clientes/${editingId}`, form)
        toast.success('Cliente actualizado')
      } else {
        await api.post('/clientes', form)
        toast.success('Cliente creado')
      }
      closeForm()
      loadClientes()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error guardando cliente')
    }
  }

  const verDetalle = async (cliente) => {
    setSelectedCliente(cliente)
    setShowDetail(true)
    try {
      const res = await api.get(`/clientes/${cliente.id_cliente}/historial`)
      setHistorialCompras(res.data.facturas || [])
    } catch {
      toast.error('Error cargando historial')
    }
  }

  const eliminarCliente = async (id, nombre) => {
    if (!confirm(`¿Eliminar cliente "${nombre}"?`)) return
    try {
      await api.delete(`/clientes/${id}`)
      toast.success('Cliente eliminado')
      loadClientes()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error eliminando cliente')
    }
  }

  if (loading && clientes.length === 0) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-bold text-gray-900">Clientes</h2>
        <button onClick={() => openForm()} className="btn-primary flex items-center gap-2">
          <Plus size={18} /> Nuevo Cliente
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <p className="text-sm text-gray-600">Total Clientes</p>
          <p className="text-3xl font-bold text-raloz-600">{clientes.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-600">Activos</p>
          <p className="text-3xl font-bold text-green-600">{clientes.filter(c => c.estado !== 'INACTIVO').length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-600">Con Colegio</p>
          <p className="text-3xl font-bold text-blue-600">{clientes.filter(c => c.id_colegio).length}</p>
        </div>
      </div>

      {/* Búsqueda */}
      <form onSubmit={handleSearch} className="card flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-64">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
          <input
            type="text"
            value={buscar}
            onChange={(e) => setBuscar(e.target.value)}
            placeholder="Buscar por nombre, teléfono, documento, email..."
            className="input pl-10 w-full"
          />
        </div>
        <button type="submit" className="btn-primary">Buscar</button>
      </form>

      {/* Tabla de Clientes */}
      {clientes.length === 0 ? (
        <div className="card text-center py-12">
          <Users className="mx-auto text-gray-300 mb-4" size={48} />
          <p className="text-gray-500">No hay clientes registrados</p>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Nombre</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Documento</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Teléfono</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Email</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Colegio</th>
                <th className="px-4 py-3 text-center text-gray-600 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {clientes.map(c => (
                <tr key={c.id_cliente} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{c.nombre}</td>
                  <td className="px-4 py-3 text-gray-700">{c.numero_documento || '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{c.telefono || '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{c.email || '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{c.colegio_nombre || '—'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button
                        onClick={() => verDetalle(c)}
                        className="text-blue-600 hover:text-blue-800 p-1"
                        title="Ver detalles"
                      >
                        <Eye size={14} />
                      </button>
                      <button
                        onClick={() => openForm(c)}
                        className="text-amber-600 hover:text-amber-800 p-1"
                        title="Editar"
                      >
                        <Edit size={14} />
                      </button>
                      <button
                        onClick={() => eliminarCliente(c.id_cliente, c.nombre)}
                        className="text-red-600 hover:text-red-800 p-1"
                        title="Eliminar"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal Crear/Editar */}
      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-screen overflow-y-auto">
            <h3 className="text-lg font-bold mb-4">
              {editingId ? 'Editar Cliente' : 'Nuevo Cliente'}
            </h3>
            <form onSubmit={guardarCliente} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Nombre *</label>
                  <input
                    type="text"
                    required
                    value={form.nombre}
                    onChange={e => setForm({...form, nombre: e.target.value})}
                    className="input w-full"
                    placeholder="Nombre completo"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Tipo Documento</label>
                  <select
                    value={form.tipo_documento}
                    onChange={e => setForm({...form, tipo_documento: e.target.value})}
                    className="input w-full"
                  >
                    <option value="CC">Cédula Ciudadanía</option>
                    <option value="CE">Cédula Extranjería</option>
                    <option value="NIT">NIT</option>
                    <option value="PASAPORTE">Pasaporte</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Número Documento</label>
                  <input
                    type="text"
                    value={form.numero_documento}
                    onChange={e => setForm({...form, numero_documento: e.target.value})}
                    className="input w-full"
                    placeholder="Número de documento"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Teléfono</label>
                  <input
                    type="tel"
                    value={form.telefono}
                    onChange={e => setForm({...form, telefono: e.target.value})}
                    className="input w-full"
                    placeholder="Teléfono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={e => setForm({...form, email: e.target.value})}
                  className="input w-full"
                  placeholder="Email"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Dirección</label>
                <input
                  type="text"
                  value={form.direccion}
                  onChange={e => setForm({...form, direccion: e.target.value})}
                  className="input w-full"
                  placeholder="Dirección"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Colegio</label>
                <select
                  value={form.id_colegio}
                  onChange={e => setForm({...form, id_colegio: e.target.value})}
                  className="input w-full"
                >
                  <option value="">Seleccionar colegio</option>
                  {colegios.map(c => (
                    <option key={c.id_colegio} value={c.id_colegio}>{c.nombre}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Notas</label>
                <textarea
                  value={form.notas}
                  onChange={e => setForm({...form, notas: e.target.value})}
                  className="input w-full"
                  rows={2}
                  placeholder="Notas adicionales"
                />
              </div>

              <div className="flex gap-3 justify-end pt-4 border-t">
                <button type="button" onClick={closeForm} className="btn-secondary">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  {editingId ? 'Actualizar' : 'Crear'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Detalle */}
      {showDetail && selectedCliente && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-screen overflow-y-auto">
            <h3 className="text-lg font-bold mb-4">Detalles de Cliente</h3>

            {/* Info Cliente */}
            <div className="grid grid-cols-2 gap-4 mb-6 pb-6 border-b">
              <div>
                <p className="text-xs text-gray-600">Nombre</p>
                <p className="font-semibold">{selectedCliente.nombre}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Documento</p>
                <p className="font-semibold">{selectedCliente.numero_documento || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Teléfono</p>
                <p className="font-semibold">{selectedCliente.telefono || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Email</p>
                <p className="font-semibold text-sm">{selectedCliente.email || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Dirección</p>
                <p className="font-semibold">{selectedCliente.direccion || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Colegio</p>
                <p className="font-semibold">{selectedCliente.colegio_nombre || '—'}</p>
              </div>
            </div>

            {/* Historial */}
            <h4 className="font-semibold mb-3">Historial de Compras</h4>
            {historialCompras.length === 0 ? (
              <p className="text-gray-500 text-sm mb-4">Sin compras registradas</p>
            ) : (
              <div className="space-y-2 mb-4">
                {historialCompras.map(f => (
                  <div key={f.id_factura} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <div>
                      <p className="font-medium">Factura #{f.numero_factura}</p>
                      <p className="text-xs text-gray-600">{f.fecha}</p>
                    </div>
                    <p className="font-semibold text-green-600">{formatMoney(f.total)}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-3 justify-end pt-4 border-t">
              <button onClick={() => setShowDetail(false)} className="btn-secondary">
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
