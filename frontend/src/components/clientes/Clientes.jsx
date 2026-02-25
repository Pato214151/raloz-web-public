import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Users, Plus, Search } from 'lucide-react'

export default function Clientes() {
  const [clientes, setClientes] = useState([])
  const [buscar, setBuscar] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ nombre: '', telefono: '', email: '', tipo_documento: 'CC', numero_documento: '' })

  useEffect(() => { loadClientes() }, [])

  const loadClientes = async (q = '') => {
    setLoading(true)
    try {
      const res = await api.get('/clientes', { params: { buscar: q, per_page: 50 } })
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

  const crearCliente = async (e) => {
    e.preventDefault()
    try {
      await api.post('/clientes', form)
      toast.success('Cliente creado')
      setShowForm(false)
      setForm({ nombre: '', telefono: '', email: '', tipo_documento: 'CC', numero_documento: '' })
      loadClientes()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error creando cliente')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Clientes</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
          <Plus size={18} /> Nuevo Cliente
        </button>
      </div>

      {showForm && (
        <form onSubmit={crearCliente} className="card space-y-4">
          <h3 className="font-semibold">Nuevo Cliente</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input value={form.nombre} onChange={e => setForm({...form, nombre: e.target.value})} className="input-field" placeholder="Nombre" required />
            <input value={form.telefono} onChange={e => setForm({...form, telefono: e.target.value})} className="input-field" placeholder="Teléfono" />
            <input value={form.email} onChange={e => setForm({...form, email: e.target.value})} className="input-field" placeholder="Email" type="email" />
          </div>
          <div className="flex gap-3">
            <button type="submit" className="btn-success">Guardar</button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancelar</button>
          </div>
        </form>
      )}

      <form onSubmit={handleSearch} className="flex gap-3">
        <input value={buscar} onChange={e => setBuscar(e.target.value)} className="input-field flex-1" placeholder="Buscar por nombre, teléfono, documento..." />
        <button type="submit" className="btn-primary"><Search size={18} /></button>
      </form>

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-gray-200">
              <th className="text-left py-2 px-3 text-gray-600">Nombre</th>
              <th className="text-left py-2 px-3 text-gray-600">Teléfono</th>
              <th className="text-left py-2 px-3 text-gray-600">Email</th>
              <th className="text-left py-2 px-3 text-gray-600">Colegio</th>
            </tr></thead>
            <tbody>
              {clientes.map(c => (
                <tr key={c.id_cliente} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-2 px-3 font-medium">{c.nombre}</td>
                  <td className="py-2 px-3">{c.telefono || '—'}</td>
                  <td className="py-2 px-3">{c.email || '—'}</td>
                  <td className="py-2 px-3">{c.colegio_nombre || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
