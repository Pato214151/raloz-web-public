import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Settings, School, Package, CreditCard, Plus, Edit, ToggleLeft, ToggleRight, X, Save } from 'lucide-react'

const TABS = [
  { id: 'colegios', label: 'Colegios', icon: School, color: 'blue' },
  { id: 'productos', label: 'Productos', icon: Package, color: 'green' },
  { id: 'metodos', label: 'Métodos de Pago', icon: CreditCard, color: 'red' },
]

const TIPOS_PRODUCTO = ['uniforme_niño', 'uniforme_niña', 'edu_fisica', 'accesorio']

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

  useEffect(() => {
    loadColegios()
    loadProductos()
    loadMetodos()
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
