import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Plus, Wallet, X, Edit, TrendingDown, Calendar, Printer, Search } from 'lucide-react'

const formatMoney = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

const CATEGORIAS = ['Servicios', 'Mantenimiento', 'Suministros', 'Personal', 'Impuestos', 'Otros']
const METODOS = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA']

export default function Gastos() {
  const [gastos, setGastos] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [filtroFechaDesde, setFiltroFechaDesde] = useState('')
  const [filtroFechaHasta, setFiltroFechaHasta] = useState('')
  const [filtroCategoria, setFiltroCategoria] = useState('')
  const [filtroMetodo, setFiltroMetodo] = useState('')
  const [buscarDesc, setBuscarDesc] = useState('')
  const [form, setForm] = useState({
    descripcion: '',
    valor: '',
    metodo_pago: 'EFECTIVO',
    categoria: 'Otros',
    fecha: new Date().toISOString().split('T')[0]
  })

  useEffect(() => {
    loadGastos()
  }, [filtroFechaDesde, filtroFechaHasta, filtroCategoria, filtroMetodo])

  const loadGastos = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filtroFechaDesde) params.fecha_desde = filtroFechaDesde
      if (filtroFechaHasta) params.fecha_hasta = filtroFechaHasta
      if (filtroCategoria) params.categoria = filtroCategoria
      if (filtroMetodo) params.metodo_pago = filtroMetodo
      const res = await api.get('/gastos', { params: { ...params, per_page: 200 } })
      setGastos(res.data.gastos || [])
    } catch (err) {
      toast.error('Error cargando gastos')
    } finally {
      setLoading(false)
    }
  }

  const openForm = (gasto = null) => {
    if (gasto) {
      setEditingId(gasto.id_gasto)
      setForm({
        descripcion: gasto.descripcion || '',
        valor: gasto.valor.toString(),
        metodo_pago: gasto.metodo_pago || 'EFECTIVO',
        categoria: gasto.categoria || 'Otros',
        fecha: gasto.fecha || new Date().toISOString().split('T')[0]
      })
    } else {
      setEditingId(null)
      setForm({
        descripcion: '',
        valor: '',
        metodo_pago: 'EFECTIVO',
        categoria: 'Otros',
        fecha: new Date().toISOString().split('T')[0]
      })
    }
    setShowForm(true)
  }

  const closeForm = () => {
    setShowForm(false)
    setEditingId(null)
  }

  const guardarGasto = async (e) => {
    e.preventDefault()
    try {
      const datos = { ...form, valor: parseFloat(form.valor) }
      if (editingId) {
        await api.put(`/gastos/${editingId}`, datos)
        toast.success('Gasto actualizado')
      } else {
        await api.post('/gastos', datos)
        toast.success('Gasto registrado')
      }
      closeForm()
      loadGastos()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const eliminarGasto = async (id) => {
    if (!confirm('¿Eliminar este gasto?')) return
    try {
      await api.delete(`/gastos/${id}`)
      toast.success('Gasto eliminado')
      loadGastos()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error eliminando gasto')
    }
  }

  // Filtrar por búsqueda local
  const gastosFiltered = buscarDesc.trim()
    ? gastos.filter(g => g.descripcion?.toLowerCase().includes(buscarDesc.toLowerCase()))
    : gastos
  const totalGastosFiltered = gastosFiltered.reduce((sum, g) => sum + (g.valor || 0), 0)

  // Cálculos
  const totalGastos = gastosFiltered.reduce((sum, g) => sum + (g.valor || 0), 0)
  const gastosPorCategoria = CATEGORIAS.map(cat => ({
    categoria: cat,
    total: gastosFiltered.filter(g => g.categoria === cat).reduce((sum, g) => sum + g.valor, 0)
  })).filter(x => x.total > 0)
  const gastosPorMetodo = METODOS.map(met => ({
    metodo: met,
    total: gastosFiltered.filter(g => g.metodo_pago === met).reduce((sum, g) => sum + g.valor, 0)
  })).filter(x => x.total > 0)

  if (loading && gastos.length === 0) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-bold text-gray-900">Gastos</h2>
        <button onClick={() => openForm()} className="btn-primary flex items-center gap-2">
          <Plus size={18} /> Nuevo Gasto
        </button>
      </div>

      {/* Stats */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-600">Total Gastos</p>
            <p className="text-3xl font-bold text-red-600">{formatMoney(totalGastos)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Número de Gastos</p>
            <p className="text-3xl font-bold text-gray-700">{gastosFiltered.length}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Gasto Promedio</p>
            <p className="text-3xl font-bold text-blue-600">
              {gastosFiltered.length > 0 ? formatMoney(totalGastos / gastosFiltered.length) : '$0'}
            </p>
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="card">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-600 mb-1">Desde</label>
            <input type="date" value={filtroFechaDesde} onChange={(e) => setFiltroFechaDesde(e.target.value)} className="input-field text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Hasta</label>
            <input type="date" value={filtroFechaHasta} onChange={(e) => setFiltroFechaHasta(e.target.value)} className="input-field text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Categoría</label>
            <select value={filtroCategoria} onChange={(e) => setFiltroCategoria(e.target.value)} className="input-field text-sm">
              <option value="">Todas</option>
              {CATEGORIAS.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Método</label>
            <select value={filtroMetodo} onChange={(e) => setFiltroMetodo(e.target.value)} className="input-field text-sm">
              <option value="">Todos</option>
              {METODOS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Buscar</label>
            <input type="text" value={buscarDesc} onChange={(e) => setBuscarDesc(e.target.value)} placeholder="Descripción..." className="input-field text-sm w-36" />
          </div>
          <button onClick={() => { setFiltroFechaDesde(''); setFiltroFechaHasta(''); setFiltroCategoria(''); setFiltroMetodo(''); setBuscarDesc('') }} className="btn-secondary text-sm">Limpiar</button>
          <button onClick={() => {
            if (!gastos.length) return
            const w = window.open('', '_blank')
            const rows = gastosFiltered.map(g => `<tr><td>${g.fecha}</td><td>${g.descripcion}</td><td>${g.categoria || 'Otros'}</td><td>${g.metodo_pago}</td><td style="text-align:right;color:red;font-weight:bold">${formatMoney(g.valor)}</td></tr>`).join('')
            w.document.write(`<!DOCTYPE html><html><head><title>Gastos</title><style>body{font-family:Arial;margin:20px}h2{color:#e74c3c;border-bottom:3px solid #FFC107;padding-bottom:8px}table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}th{background:#f5f5f5;padding:6px;border:1px solid #ddd;text-align:left}td{padding:5px 8px;border:1px solid #eee}.total{font-size:20px;font-weight:bold;color:#e74c3c;text-align:center;padding:15px;background:#fce4ec;border-radius:8px;margin:15px 0}@media print{body{margin:10px}}</style></head><body><h2>RALOZ COL SAS - Registro de Gastos</h2><div class="total">Total: ${formatMoney(totalGastosFiltered)} (${gastosFiltered.length} gastos)</div><table><thead><tr><th>Fecha</th><th>Descripción</th><th>Categoría</th><th>Método</th><th style="text-align:right">Valor</th></tr></thead><tbody>${rows}</tbody></table><hr><p style="text-align:center;font-size:11px;color:#999">RALOZ COL SAS</p></body></html>`)
            w.document.close(); w.print()
          }} className="btn-secondary text-sm flex items-center gap-1"><Printer size={14} /> Imprimir</button>
        </div>
      </div>

      {/* Resumen por Categoría */}
      {gastosPorCategoria.length > 0 && (
        <div className="card">
          <h3 className="font-semibold mb-3">Resumen por Categoría</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
            {gastosPorCategoria.map(item => (
              <div key={item.categoria} className="bg-gray-50 p-3 rounded text-center">
                <p className="text-xs text-gray-600">{item.categoria}</p>
                <p className="font-semibold text-red-600 text-sm">{formatMoney(item.total)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Resumen por Método */}
      {gastosPorMetodo.length > 0 && (
        <div className="card">
          <h3 className="font-semibold mb-3">Resumen por Método de Pago</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
            {gastosPorMetodo.map(item => (
              <div key={item.metodo} className="bg-gray-50 p-3 rounded text-center">
                <p className="text-xs text-gray-600">{item.metodo}</p>
                <p className="font-semibold text-red-600 text-sm">{formatMoney(item.total)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabla de Gastos */}
      {gastosFiltered.length === 0 ? (
        <div className="card text-center py-12">
          <Wallet className="mx-auto text-gray-300 mb-4" size={48} />
          <p className="text-gray-500">No hay gastos registrados</p>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Fecha</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Descripción</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Categoría</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Método</th>
                <th className="px-4 py-3 text-right text-gray-600 font-medium">Valor</th>
                <th className="px-4 py-3 text-center text-gray-600 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {gastosFiltered.map(g => (
                <tr key={g.id_gasto} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{g.fecha}</td>
                  <td className="px-4 py-3 text-gray-700">{g.descripcion}</td>
                  <td className="px-4 py-3">
                    <span className="bg-gray-100 px-2 py-1 rounded text-xs">{g.categoria || '—'}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="bg-blue-100 px-2 py-1 rounded text-xs text-blue-700">{g.metodo_pago}</span>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-red-600">{formatMoney(g.valor)}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button
                        onClick={() => openForm(g)}
                        className="text-amber-600 hover:text-amber-800 p-1"
                        title="Editar"
                      >
                        <Edit size={14} />
                      </button>
                      <button
                        onClick={() => eliminarGasto(g.id_gasto)}
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
          <div className="bg-white rounded-xl p-6 w-full max-w-md max-h-screen overflow-y-auto">
            <h3 className="text-lg font-bold mb-4">
              {editingId ? 'Editar Gasto' : 'Nuevo Gasto'}
            </h3>
            <form onSubmit={guardarGasto} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Descripción *</label>
                <input
                  type="text"
                  required
                  value={form.descripcion}
                  onChange={e => setForm({...form, descripcion: e.target.value})}
                  className="input-field w-full"
                  placeholder="Descripción del gasto"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Valor *</label>
                <input
                  type="number"
                  required
                  min="0.01"
                  step="0.01"
                  value={form.valor}
                  onChange={e => setForm({...form, valor: e.target.value})}
                  className="input-field w-full"
                  placeholder="0.00"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Categoría</label>
                <select
                  value={form.categoria}
                  onChange={e => setForm({...form, categoria: e.target.value})}
                  className="input-field w-full"
                >
                  {CATEGORIAS.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Método Pago</label>
                <select
                  value={form.metodo_pago}
                  onChange={e => setForm({...form, metodo_pago: e.target.value})}
                  className="input-field w-full"
                >
                  {METODOS.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Fecha</label>
                <input
                  type="date"
                  value={form.fecha}
                  onChange={e => setForm({...form, fecha: e.target.value})}
                  className="input-field w-full"
                />
              </div>

              <div className="flex gap-3 justify-end pt-4 border-t">
                <button type="button" onClick={closeForm} className="btn-secondary">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  {editingId ? 'Actualizar' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
