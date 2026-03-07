import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Settings, School, Package, CreditCard, Plus, Edit, ToggleLeft, ToggleRight, X, Save, Users, KeyRound, Building2, Eye, EyeOff } from 'lucide-react'

const TABS = [
  { id: 'colegios', label: 'Colegios', icon: School, color: 'blue' },
  { id: 'productos', label: 'Productos', icon: Package, color: 'green' },
  { id: 'metodos', label: 'Métodos de Pago', icon: CreditCard, color: 'red' },
  { id: 'usuarios', label: 'Usuarios', icon: Users, color: 'purple' },
  { id: 'empresa', label: 'Empresa', icon: Building2, color: 'indigo' },
]

const EMPRESA_DEFAULT = { nombre: 'RALOZ COL SAS', nit: '', direccion: '', telefono: '', ciudad: '', email: '' }

function cargarEmpresa() {
  try { return JSON.parse(localStorage.getItem('raloz_empresa') || 'null') || EMPRESA_DEFAULT } catch { return EMPRESA_DEFAULT }
}
function guardarEmpresaLS(data) {
  localStorage.setItem('raloz_empresa', JSON.stringify(data))
}

const ROL_BADGE = {
  administrador: 'bg-purple-100 text-purple-700',
  vendedor: 'bg-blue-100 text-blue-700',
  cajero: 'bg-yellow-100 text-yellow-700',
}

const TIPOS_PRODUCTO = ['uniforme_niño', 'uniforme_niña', 'edu_fisica', 'accesorio', 'medias']

export default function Configuracion() {
  const [tab, setTab] = useState('colegios')

  // ── Colegios ──
  const [colegios, setColegios] = useState([])
  const [colForm, setColForm] = useState({ nombre: '', ciudad: '' })
  const [editingCol, setEditingCol] = useState(null)
  const [showColForm, setShowColForm] = useState(false)

  // ── Productos ──
  const [productos, setProductos] = useState([])
  const [prodForm, setProdForm] = useState({ codigo: '', nombre: '', tipo: 'uniforme_niño' })
  const [editingProd, setEditingProd] = useState(null)
  const [showProdForm, setShowProdForm] = useState(false)

  // ── Métodos de Pago ──
  const [metodos, setMetodos] = useState([])
  const [metForm, setMetForm] = useState({ nombre: '' })
  const [showMetForm, setShowMetForm] = useState(false)

  // ── Usuarios ──
  const [usuarios, setUsuarios] = useState([])
  const [userForm, setUserForm] = useState({ usuario: '', password: '', rol: 'vendedor', email: '' })
  const [showUserForm, setShowUserForm] = useState(false)
  const [pwdModal, setPwdModal] = useState(null)
  const [nuevaPwd, setNuevaPwd] = useState('')

  // ── Empresa ──
  const [empresaForm, setEmpresaForm] = useState(cargarEmpresa)
  const [empresaSaved, setEmpresaSaved] = useState(false)

  // ── Visibilidad contraseñas ──
  const [showPwdCreate, setShowPwdCreate] = useState(false)
  const [showPwdChange, setShowPwdChange] = useState(false)

  useEffect(() => {
    loadColegios()
    loadProductos()
    loadMetodos()
    loadUsuarios()
  }, [])

  // ════════════════════ COLEGIOS ════════════════════
  const loadColegios = async () => {
    try {
      const res = await api.get('/colegios', { params: { activos: 'all' } })
      setColegios(res.data.colegios || [])
    } catch { toast.error('Error cargando colegios') }
  }

  const guardarColegio = async (e) => {
    e.preventDefault()
    if (!colForm.nombre.trim()) return toast.error('Nombre requerido')
    try {
      if (editingCol) {
        await api.put(`/colegios/${editingCol}`, colForm)
        toast.success('Colegio actualizado')
      } else {
        await api.post('/colegios', colForm)
        toast.success('Colegio creado')
      }
      setShowColForm(false)
      setEditingCol(null)
      setColForm({ nombre: '', ciudad: '' })
      loadColegios()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const toggleColegio = async (col) => {
    try {
      await api.put(`/colegios/${col.id_colegio}`, { activo: !col.activo })
      toast.success(col.activo ? 'Colegio desactivado' : 'Colegio activado')
      loadColegios()
    } catch { toast.error('Error') }
  }

  const editarColegio = (col) => {
    setEditingCol(col.id_colegio)
    setColForm({ nombre: col.nombre, ciudad: col.ciudad || '' })
    setShowColForm(true)
  }

  // ════════════════════ PRODUCTOS ════════════════════
  const loadProductos = async () => {
    try {
      const res = await api.get('/productos', { params: { activos: 'all' } })
      setProductos(res.data.productos || [])
    } catch { toast.error('Error cargando productos') }
  }

  const guardarProducto = async (e) => {
    e.preventDefault()
    if (!prodForm.nombre.trim()) return toast.error('Nombre requerido')
    try {
      if (editingProd) {
        await api.put(`/productos/${editingProd}`, prodForm)
        toast.success('Producto actualizado')
      } else {
        await api.post('/productos', prodForm)
        toast.success('Producto creado')
      }
      setShowProdForm(false)
      setEditingProd(null)
      setProdForm({ codigo: '', nombre: '', tipo: 'uniforme_niño' })
      loadProductos()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const toggleProducto = async (prod) => {
    try {
      await api.put(`/productos/${prod.id_producto}`, { activo: !prod.activo })
      toast.success(prod.activo ? 'Producto desactivado' : 'Producto activado')
      loadProductos()
    } catch { toast.error('Error') }
  }

  const editarProducto = (prod) => {
    setEditingProd(prod.id_producto)
    setProdForm({ codigo: prod.codigo || '', nombre: prod.nombre, tipo: prod.tipo || 'uniforme_niño' })
    setShowProdForm(true)
  }

  // ════════════════════ MÉTODOS DE PAGO ════════════════════
  const loadMetodos = async () => {
    try {
      const res = await api.get('/metodos-pago', { params: { activos: 'all' } })
      setMetodos(res.data.metodos || [])
    } catch { toast.error('Error cargando métodos') }
  }

  const guardarMetodo = async (e) => {
    e.preventDefault()
    if (!metForm.nombre.trim()) return toast.error('Nombre requerido')
    try {
      await api.post('/metodos-pago', { nombre: metForm.nombre })
      toast.success('Método creado')
      setShowMetForm(false)
      setMetForm({ nombre: '' })
      loadMetodos()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const toggleMetodo = async (met) => {
    try {
      await api.put(`/metodos-pago/${met.id_metodo}`, { activo: !met.activo })
      toast.success(met.activo ? 'Método desactivado' : 'Método activado')
      loadMetodos()
    } catch { toast.error('Error') }
  }

  // ════════════════════ USUARIOS ════════════════════
  const loadUsuarios = async () => {
    try {
      const res = await api.get('/usuarios')
      setUsuarios(res.data.usuarios || [])
    } catch { toast.error('Error cargando usuarios') }
  }

  const crearUsuario = async (e) => {
    e.preventDefault()
    if (!userForm.usuario.trim() || !userForm.password.trim()) return toast.error('Usuario y contraseña requeridos')
    try {
      await api.post('/usuarios', userForm)
      toast.success('Usuario creado')
      setShowUserForm(false)
      setUserForm({ usuario: '', password: '', rol: 'vendedor', email: '' })
      loadUsuarios()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error creando usuario')
    }
  }

  const toggleUsuario = async (u) => {
    try {
      await api.post(`/usuarios/${u.id_usuario}/toggle`)
      toast.success(u.activo ? 'Usuario desactivado' : 'Usuario activado')
      loadUsuarios()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const cambiarPassword = async (e) => {
    e.preventDefault()
    if (!nuevaPwd || nuevaPwd.length < 6) return toast.error('Mínimo 6 caracteres')
    try {
      await api.post(`/usuarios/${pwdModal.id_usuario}/password`, { password: nuevaPwd })
      toast.success('Contraseña actualizada')
      setPwdModal(null)
      setNuevaPwd('')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  // ════════════════════ RENDER ════════════════════
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Settings className="text-gray-600" size={24} />
          <h1 className="text-2xl font-bold text-gray-800">Configuración del Sistema</h1>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 pb-0">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
              tab === t.id
                ? `border-${t.color}-500 text-${t.color}-600 bg-${t.color}-50`
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <t.icon size={16} />
            {t.label}
          </button>
        ))}
      </div>

      {/* ══════════ TAB COLEGIOS ══════════ */}
      {tab === 'colegios' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-700 flex items-center gap-2">
              <School size={18} className="text-blue-500" /> Gestionar Colegios
              <span className="text-xs bg-blue-100 text-blue-600 px-2 py-0.5 rounded-full ml-2">{colegios.length}</span>
            </h2>
            <button onClick={() => { setEditingCol(null); setColForm({ nombre: '', ciudad: '' }); setShowColForm(true) }}
              className="flex items-center gap-1 bg-blue-500 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-blue-600">
              <Plus size={14} /> Agregar
            </button>
          </div>

          {/* Form Modal */}
          {showColForm && (
            <div className="p-4 bg-blue-50 border-b border-blue-100">
              <form onSubmit={guardarColegio} className="flex items-end gap-3">
                <div className="flex-1">
                  <label className="text-xs text-gray-500 mb-1 block">Nombre *</label>
                  <input value={colForm.nombre} onChange={e => setColForm({...colForm, nombre: e.target.value})}
                    className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Nombre del colegio" autoFocus />
                </div>
                <div className="w-48">
                  <label className="text-xs text-gray-500 mb-1 block">Ciudad</label>
                  <input value={colForm.ciudad} onChange={e => setColForm({...colForm, ciudad: e.target.value})}
                    className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Ciudad" />
                </div>
                <button type="submit" className="flex items-center gap-1 bg-blue-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-600">
                  <Save size={14} /> {editingCol ? 'Actualizar' : 'Guardar'}
                </button>
                <button type="button" onClick={() => { setShowColForm(false); setEditingCol(null) }}
                  className="text-gray-400 hover:text-gray-600 p-2">
                  <X size={18} />
                </button>
              </form>
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="text-left px-4 py-3">ID</th>
                  <th className="text-left px-4 py-3">Nombre</th>
                  <th className="text-left px-4 py-3">Ciudad</th>
                  <th className="text-center px-4 py-3">Estado</th>
                  <th className="text-center px-4 py-3">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {colegios.map(col => (
                  <tr key={col.id_colegio} className={`hover:bg-gray-50 ${!col.activo ? 'opacity-50' : ''}`}>
                    <td className="px-4 py-3 text-gray-400">{col.id_colegio}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{col.nombre}</td>
                    <td className="px-4 py-3 text-gray-600">{col.ciudad || '-'}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        col.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>{col.activo ? 'ACTIVO' : 'INACTIVO'}</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button onClick={() => editarColegio(col)} className="text-blue-500 hover:text-blue-700" title="Editar">
                          <Edit size={15} />
                        </button>
                        <button onClick={() => toggleColegio(col)}
                          className={col.activo ? 'text-orange-500 hover:text-orange-700' : 'text-green-500 hover:text-green-700'}
                          title={col.activo ? 'Desactivar' : 'Activar'}>
                          {col.activo ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {colegios.length === 0 && (
                  <tr><td colSpan={5} className="text-center py-8 text-gray-400">No hay colegios registrados</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ══════════ TAB PRODUCTOS ══════════ */}
      {tab === 'productos' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-700 flex items-center gap-2">
              <Package size={18} className="text-green-500" /> Gestionar Productos
              <span className="text-xs bg-green-100 text-green-600 px-2 py-0.5 rounded-full ml-2">{productos.length}</span>
            </h2>
            <button onClick={() => { setEditingProd(null); setProdForm({ codigo: '', nombre: '', tipo: 'uniforme_niño' }); setShowProdForm(true) }}
              className="flex items-center gap-1 bg-green-500 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-green-600">
              <Plus size={14} /> Agregar
            </button>
          </div>

          {/* Form */}
          {showProdForm && (
            <div className="p-4 bg-green-50 border-b border-green-100">
              <form onSubmit={guardarProducto} className="flex items-end gap-3 flex-wrap">
                <div className="w-32">
                  <label className="text-xs text-gray-500 mb-1 block">Código</label>
                  <input value={prodForm.codigo} onChange={e => setProdForm({...prodForm, codigo: e.target.value})}
                    className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="COD" />
                </div>
                <div className="flex-1 min-w-[200px]">
                  <label className="text-xs text-gray-500 mb-1 block">Nombre *</label>
                  <input value={prodForm.nombre} onChange={e => setProdForm({...prodForm, nombre: e.target.value})}
                    className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Nombre del producto" autoFocus />
                </div>
                <div className="w-48">
                  <label className="text-xs text-gray-500 mb-1 block">Tipo</label>
                  <select value={prodForm.tipo} onChange={e => setProdForm({...prodForm, tipo: e.target.value})}
                    className="w-full border rounded-lg px-3 py-2 text-sm bg-white">
                    {TIPOS_PRODUCTO.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                  </select>
                </div>
                <button type="submit" className="flex items-center gap-1 bg-green-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-600">
                  <Save size={14} /> {editingProd ? 'Actualizar' : 'Guardar'}
                </button>
                <button type="button" onClick={() => { setShowProdForm(false); setEditingProd(null) }}
                  className="text-gray-400 hover:text-gray-600 p-2">
                  <X size={18} />
                </button>
              </form>
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="text-left px-4 py-3">ID</th>
                  <th className="text-left px-4 py-3">Código</th>
                  <th className="text-left px-4 py-3">Nombre</th>
                  <th className="text-left px-4 py-3">Tipo</th>
                  <th className="text-center px-4 py-3">Estado</th>
                  <th className="text-center px-4 py-3">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {productos.map(prod => (
                  <tr key={prod.id_producto} className={`hover:bg-gray-50 ${!prod.activo ? 'opacity-50' : ''}`}>
                    <td className="px-4 py-3 text-gray-400">{prod.id_producto}</td>
                    <td className="px-4 py-3 font-mono text-gray-600">{prod.codigo || '-'}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{prod.nombre}</td>
                    <td className="px-4 py-3 text-gray-600">{(prod.tipo || '').replace('_', ' ')}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        prod.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>{prod.activo ? 'ACTIVO' : 'INACTIVO'}</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button onClick={() => editarProducto(prod)} className="text-green-500 hover:text-green-700" title="Editar">
                          <Edit size={15} />
                        </button>
                        <button onClick={() => toggleProducto(prod)}
                          className={prod.activo ? 'text-orange-500 hover:text-orange-700' : 'text-green-500 hover:text-green-700'}
                          title={prod.activo ? 'Desactivar' : 'Activar'}>
                          {prod.activo ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {productos.length === 0 && (
                  <tr><td colSpan={6} className="text-center py-8 text-gray-400">No hay productos registrados</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ══════════ TAB USUARIOS ══════════ */}
      {tab === 'usuarios' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-700 flex items-center gap-2">
              <Users size={18} className="text-purple-500" /> Gestionar Usuarios
              <span className="text-xs bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full ml-2">{usuarios.length}</span>
            </h2>
            <button onClick={() => { setUserForm({ usuario: '', password: '', rol: 'vendedor', email: '' }); setShowUserForm(true) }}
              className="flex items-center gap-1 bg-purple-500 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-purple-600">
              <Plus size={14} /> Nuevo usuario
            </button>
          </div>

          {/* Form nuevo usuario */}
          {showUserForm && (
            <div className="p-4 bg-purple-50 border-b border-purple-100">
              <form onSubmit={crearUsuario} className="flex items-end gap-3 flex-wrap">
                <div className="w-44">
                  <label className="text-xs text-gray-500 mb-1 block">Usuario *</label>
                  <input value={userForm.usuario} onChange={e => setUserForm({...userForm, usuario: e.target.value})}
                    className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="nombre_usuario" autoFocus />
                </div>
                <div className="w-44">
                  <label className="text-xs text-gray-500 mb-1 block">Contraseña *</label>
                  <div className="relative">
                    <input type={showPwdCreate ? 'text' : 'password'} value={userForm.password}
                      onChange={e => setUserForm({...userForm, password: e.target.value})}
                      className="w-full border rounded-lg px-3 py-2 text-sm pr-8" placeholder="Mín. 6 caracteres" />
                    <button type="button" onClick={() => setShowPwdCreate(v => !v)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                      {showPwdCreate ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>
                <div className="w-36">
                  <label className="text-xs text-gray-500 mb-1 block">Rol</label>
                  <select value={userForm.rol} onChange={e => setUserForm({...userForm, rol: e.target.value})}
                    className="w-full border rounded-lg px-3 py-2 text-sm bg-white">
                    <option value="vendedor">Vendedor</option>
                    <option value="cajero">Cajero</option>
                    <option value="administrador">Administrador</option>
                  </select>
                </div>
                <div className="flex-1 min-w-[180px]">
                  <label className="text-xs text-gray-500 mb-1 block">Email (opcional)</label>
                  <input type="email" value={userForm.email} onChange={e => setUserForm({...userForm, email: e.target.value})}
                    className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="correo@ejemplo.com" />
                </div>
                <button type="submit" className="flex items-center gap-1 bg-purple-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-purple-600">
                  <Save size={14} /> Crear
                </button>
                <button type="button" onClick={() => setShowUserForm(false)} className="text-gray-400 hover:text-gray-600 p-2">
                  <X size={18} />
                </button>
              </form>
            </div>
          )}

          {/* Modal cambiar contraseña */}
          {pwdModal && (
            <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
              <div className="bg-white rounded-xl shadow-xl p-6 w-80">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <KeyRound size={16} className="text-purple-500" /> Cambiar contraseña
                  <span className="text-purple-600 font-bold">— {pwdModal.usuario}</span>
                </h3>
                <form onSubmit={cambiarPassword} className="space-y-3">
                  <div className="relative">
                    <input type={showPwdChange ? 'text' : 'password'} value={nuevaPwd}
                      onChange={e => setNuevaPwd(e.target.value)}
                      className="w-full border rounded-lg px-3 py-2 text-sm pr-10" placeholder="Nueva contraseña (mín. 6 caracteres)" autoFocus />
                    <button type="button" onClick={() => setShowPwdChange(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                      {showPwdChange ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {nuevaPwd && (
                    <p className="text-xs text-gray-500">
                      Contraseña: <span className="font-mono font-bold text-gray-800">{showPwdChange ? nuevaPwd : '••••••••'}</span>
                    </p>
                  )}
                  <div className="flex gap-2 justify-end">
                    <button type="button" onClick={() => { setPwdModal(null); setNuevaPwd(''); setShowPwdChange(false) }}
                      className="px-4 py-2 text-sm text-gray-500 border rounded-lg hover:bg-gray-50">Cancelar</button>
                    <button type="submit" className="px-4 py-2 text-sm bg-purple-500 text-white rounded-lg hover:bg-purple-600">Guardar</button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Tabla usuarios */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="text-left px-4 py-3">Usuario</th>
                  <th className="text-left px-4 py-3">Email</th>
                  <th className="text-center px-4 py-3">Rol</th>
                  <th className="text-center px-4 py-3">Estado</th>
                  <th className="text-center px-4 py-3">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {usuarios.map(u => (
                  <tr key={u.id_usuario} className={`hover:bg-gray-50 ${!u.activo ? 'opacity-50' : ''}`}>
                    <td className="px-4 py-3 font-medium text-gray-800">{u.usuario}</td>
                    <td className="px-4 py-3 text-gray-500">{u.email || '-'}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ROL_BADGE[u.rol] || 'bg-gray-100 text-gray-600'}`}>
                        {u.rol}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${u.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {u.activo ? 'ACTIVO' : 'INACTIVO'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button onClick={() => { setPwdModal(u); setNuevaPwd('') }}
                          className="text-purple-500 hover:text-purple-700" title="Cambiar contraseña">
                          <KeyRound size={15} />
                        </button>
                        <button onClick={() => toggleUsuario(u)}
                          className={u.activo ? 'text-orange-500 hover:text-orange-700' : 'text-green-500 hover:text-green-700'}
                          title={u.activo ? 'Desactivar' : 'Activar'}>
                          {u.activo ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {usuarios.length === 0 && (
                  <tr><td colSpan={5} className="text-center py-8 text-gray-400">No hay usuarios registrados</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ══════════ TAB EMPRESA ══════════ */}
      {tab === 'empresa' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-700 flex items-center gap-2">
              <Building2 size={18} className="text-indigo-500" /> Datos de la Empresa / Factura
            </h2>
            <p className="text-xs text-gray-400 mt-1">Esta información aparece en el encabezado al imprimir facturas.</p>
          </div>
          <div className="p-6 space-y-4 max-w-lg">
            {[
              { label: 'Nombre de la empresa', key: 'nombre', placeholder: 'RALOZ COL SAS' },
              { label: 'NIT', key: 'nit', placeholder: '900.123.456-7' },
              { label: 'Dirección', key: 'direccion', placeholder: 'Calle 12 # 45-67' },
              { label: 'Ciudad', key: 'ciudad', placeholder: 'Bogotá, Colombia' },
              { label: 'Teléfono', key: 'telefono', placeholder: '601 234 5678' },
              { label: 'Email', key: 'email', placeholder: 'ventas@empresa.com' },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-600 mb-1">{label}</label>
                <input
                  value={empresaForm[key]}
                  onChange={e => setEmpresaForm({ ...empresaForm, [key]: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-400"
                  placeholder={placeholder}
                />
              </div>
            ))}
            <button
              onClick={() => { guardarEmpresaLS(empresaForm); setEmpresaSaved(true); setTimeout(() => setEmpresaSaved(false), 2000) }}
              className="flex items-center gap-2 bg-indigo-500 text-white px-5 py-2 rounded-lg text-sm hover:bg-indigo-600 transition-colors"
            >
              <Save size={14} /> {empresaSaved ? '¡Guardado!' : 'Guardar datos'}
            </button>
          </div>
        </div>
      )}

      {/* ══════════ TAB MÉTODOS DE PAGO ══════════ */}
      {tab === 'metodos' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-700 flex items-center gap-2">
              <CreditCard size={18} className="text-red-500" /> Métodos de Pago
              <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full ml-2">{metodos.length}</span>
            </h2>
            <button onClick={() => { setMetForm({ nombre: '' }); setShowMetForm(true) }}
              className="flex items-center gap-1 bg-red-500 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-red-600">
              <Plus size={14} /> Agregar
            </button>
          </div>

          {/* Form */}
          {showMetForm && (
            <div className="p-4 bg-red-50 border-b border-red-100">
              <form onSubmit={guardarMetodo} className="flex items-end gap-3">
                <div className="flex-1">
                  <label className="text-xs text-gray-500 mb-1 block">Nombre del método *</label>
                  <input value={metForm.nombre} onChange={e => setMetForm({ nombre: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm uppercase" placeholder="Ej: NEQUI, DAVIPLATA..." autoFocus />
                </div>
                <button type="submit" className="flex items-center gap-1 bg-red-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-600">
                  <Save size={14} /> Guardar
                </button>
                <button type="button" onClick={() => setShowMetForm(false)} className="text-gray-400 hover:text-gray-600 p-2">
                  <X size={18} />
                </button>
              </form>
            </div>
          )}

          {/* List */}
          <div className="divide-y divide-gray-50">
            {metodos.map(met => (
              <div key={met.id_metodo} className={`flex items-center justify-between px-4 py-3 hover:bg-gray-50 ${!met.activo ? 'opacity-50' : ''}`}>
                <div className="flex items-center gap-3">
                  <CreditCard size={16} className="text-gray-400" />
                  <span className="font-medium text-gray-800">{met.nombre}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    met.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>{met.activo ? 'ACTIVO' : 'INACTIVO'}</span>
                  <button onClick={() => toggleMetodo(met)}
                    className={met.activo ? 'text-orange-500 hover:text-orange-700' : 'text-green-500 hover:text-green-700'}
                    title={met.activo ? 'Desactivar' : 'Activar'}>
                    {met.activo ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
                  </button>
                </div>
              </div>
            ))}
            {metodos.length === 0 && (
              <div className="text-center py-8 text-gray-400">No hay métodos de pago registrados</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
