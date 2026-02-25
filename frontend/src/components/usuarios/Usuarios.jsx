import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { UserCog, Plus, Shield, Eye } from 'lucide-react'

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState([])
  const [selected, setSelected] = useState(null)
  const [actividad, setActividad] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ usuario: '', password: '', email: '', rol: 'vendedor' })

  useEffect(() => { loadUsuarios() }, [])

  const loadUsuarios = async () => {
    try {
      const res = await api.get('/usuarios')
      setUsuarios(res.data.usuarios || [])
    } catch {
      toast.error('Error cargando usuarios')
    }
  }

  const verActividad = async (id) => {
    setSelected(id)
    try {
      const res = await api.get(`/usuarios/${id}/actividad`)
      setActividad(res.data)
    } catch {
      toast.error('Error cargando actividad')
    }
  }

  const crearUsuario = async (e) => {
    e.preventDefault()
    try {
      await api.post('/usuarios', form)
      toast.success('Usuario creado')
      setShowForm(false)
      setForm({ usuario: '', password: '', email: '', rol: 'vendedor' })
      loadUsuarios()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const toggleUsuario = async (id) => {
    try {
      await api.post(`/usuarios/${id}/toggle`)
      toast.success('Estado actualizado')
      loadUsuarios()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Gestión de Usuarios</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2"><Plus size={18} /> Nuevo</button>
      </div>

      {showForm && (
        <form onSubmit={crearUsuario} className="card space-y-4">
          <h3 className="font-semibold">Crear Usuario</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <input value={form.usuario} onChange={e => setForm({...form, usuario: e.target.value})} className="input-field" placeholder="Usuario" required />
            <input type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} className="input-field" placeholder="Contraseña" required />
            <input value={form.email} onChange={e => setForm({...form, email: e.target.value})} className="input-field" placeholder="Email" type="email" />
            <select value={form.rol} onChange={e => setForm({...form, rol: e.target.value})} className="input-field">
              <option value="vendedor">Vendedor</option>
              <option value="cajero">Cajero</option>
              <option value="administrador">Administrador</option>
            </select>
          </div>
          <div className="flex gap-3">
            <button type="submit" className="btn-success">Crear</button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancelar</button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Lista */}
        <div className="space-y-2">
          {usuarios.map(u => (
            <div key={u.id_usuario} className={`card flex items-center justify-between cursor-pointer hover:shadow-md ${selected === u.id_usuario ? 'ring-2 ring-raloz-500' : ''}`}
              onClick={() => verActividad(u.id_usuario)}>
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${u.activo ? 'bg-raloz-100 text-raloz-700' : 'bg-gray-200 text-gray-500'}`}>
                  {u.usuario.charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-medium">{u.usuario}</p>
                  <p className="text-xs text-gray-500 capitalize">{u.rol} {!u.activo && '• Inactivo'}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={(e) => { e.stopPropagation(); toggleUsuario(u.id_usuario) }}
                  className={`text-xs px-2 py-1 rounded ${u.activo ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
                  {u.activo ? 'Desactivar' : 'Activar'}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Actividad */}
        {actividad && (
          <div className="card sticky top-4">
            <h3 className="text-lg font-semibold mb-4">Actividad de {actividad.usuario.usuario}</h3>

            <div className="grid grid-cols-2 gap-3 mb-6">
              <div className="bg-blue-50 p-3 rounded-lg">
                <p className="text-xs text-blue-600">Hoy</p>
                <p className="font-bold">{fmt(actividad.kpis.hoy.total)}</p>
                <p className="text-xs text-gray-500">{actividad.kpis.hoy.facturas} facturas</p>
              </div>
              <div className="bg-green-50 p-3 rounded-lg">
                <p className="text-xs text-green-600">Esta Semana</p>
                <p className="font-bold">{fmt(actividad.kpis.semana.total)}</p>
                <p className="text-xs text-gray-500">{actividad.kpis.semana.facturas} facturas</p>
              </div>
              <div className="bg-purple-50 p-3 rounded-lg">
                <p className="text-xs text-purple-600">Este Mes</p>
                <p className="font-bold">{fmt(actividad.kpis.mes.total)}</p>
                <p className="text-xs text-gray-500">{actividad.kpis.mes.facturas} facturas</p>
              </div>
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="text-xs text-gray-600">Ayer</p>
                <p className="font-bold">{fmt(actividad.kpis.ayer.total)}</p>
                <p className="text-xs text-gray-500">{actividad.kpis.ayer.facturas} facturas</p>
              </div>
            </div>

            <h4 className="text-sm font-semibold text-gray-700 mb-2">Últimas Facturas</h4>
            <div className="space-y-1 max-h-60 overflow-y-auto">
              {actividad.ultimas_facturas.map(f => (
                <div key={f.id_factura} className="flex justify-between text-sm py-1 border-b border-gray-50">
                  <span className="text-gray-600">{f.numero_factura} • {f.fecha_factura}</span>
                  <span className="font-medium">{fmt(f.total)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
