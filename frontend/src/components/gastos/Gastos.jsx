import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Plus, Wallet, X, Edit, Printer, Store, Briefcase, AlertTriangle, CheckCircle, Upload } from 'lucide-react'

const formatMoney = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

const CATEGORIAS = [
  'Nómina',
  'Costo Mercancía',
  'Arriendo',
  'Servicios Públicos',
  'Transporte',
  'Alimentación',
  'Suministros',
  'Mantenimiento',
  'Impuestos',
  'Marketing',
  'Otros',
]
const METODOS = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA']

const CATEGORIA_HINTS = {
  'Nómina': 'Sueldos, salarios y pagos a empleados',
  'Costo Mercancía': 'Compras de producto: telas, bordados, insumos de fabricación',
  'Arriendo': 'Pago de arriendo del local',
  'Servicios Públicos': 'Agua, luz, internet, teléfono',
  'Transporte': 'Gasolina, parqueadero, fletes',
  'Alimentación': 'Almuerzos y refrigerios del equipo',
  'Suministros': 'Papelería, empaques, materiales de oficina',
  'Mantenimiento': 'Reparaciones, mantenimiento de equipos',
  'Impuestos': 'ICA, retenciones, obligaciones tributarias',
  'Marketing': 'Publicidad, redes sociales, volantes',
  'Otros': '',
}

export default function Gastos() {
  const [gastos, setGastos] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [showImportar, setShowImportar] = useState(false)
  const [textoImportar, setTextoImportar] = useState('')
  const [importando, setImportando] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [filtroFechaDesde, setFiltroFechaDesde] = useState('')
  const [filtroFechaHasta, setFiltroFechaHasta] = useState('')
  const [filtroCategoria, setFiltroCategoria] = useState('')
  const [filtroMetodo, setFiltroMetodo] = useState('')
  const [filtroTipo, setFiltroTipo] = useState('')
  const [buscarDesc, setBuscarDesc] = useState('')
  const [form, setForm] = useState({
    descripcion: '',
    valor: '',
    metodo_pago: 'EFECTIVO',
    categoria: '',
    tipo_gasto: 'EMPRESA',
    es_deuda: false,
    fecha: new Date().toISOString().split('T')[0]
  })

  useEffect(() => {
    loadGastos()
  }, [filtroFechaDesde, filtroFechaHasta, filtroCategoria, filtroMetodo, filtroTipo])

  const loadGastos = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filtroFechaDesde) params.fecha_desde = filtroFechaDesde
      if (filtroFechaHasta) params.fecha_hasta = filtroFechaHasta
      if (filtroCategoria) params.categoria = filtroCategoria
      if (filtroMetodo) params.metodo_pago = filtroMetodo
      if (filtroTipo) params.tipo_gasto = filtroTipo
      const res = await api.get('/gastos', { params: { ...params, per_page: 500 } })
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
        tipo_gasto: gasto.tipo_gasto || 'TIENDA',
        fecha: gasto.fecha || new Date().toISOString().split('T')[0]
      })
    } else {
      setEditingId(null)
      setForm({
        descripcion: '',
        valor: '',
        metodo_pago: 'EFECTIVO',
        categoria: '',
        tipo_gasto: 'EMPRESA',
        es_deuda: false,
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
    if (!form.categoria) { toast.error('Selecciona una categoría'); return }
    try {
      const datos = { ...form, valor: parseFloat(form.valor) }
      if (editingId) {
        await api.put(`/gastos/${editingId}`, datos)
        toast.success('Gasto actualizado')
      } else {
        const res = await api.post('/gastos', datos)
        toast.success(res.data?.message || 'Gasto registrado')
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

  const pagarDeuda = async (g) => {
    if (!confirm(`¿Marcar como PAGADA la deuda "${g.descripcion}" (${formatMoney(g.valor)})? Se registrará como gasto de hoy.`)) return
    try {
      await api.post(`/gastos/${g.id_gasto}/pagar`, { metodo_pago: g.metodo_pago })
      toast.success('Deuda pagada — ya cuenta como gasto de hoy')
      loadGastos()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al pagar la deuda')
    }
  }

  // Filtrar por búsqueda local
  const gastosFiltered = buscarDesc.trim()
    ? gastos.filter(g => g.descripcion?.toLowerCase().includes(buscarDesc.toLowerCase()))
    : gastos

  // Una deuda (estado PENDIENTE) NO cuenta como gasto hasta pagarse.
  const esDeuda = (g) => (g.estado_pago || 'PAGADO') === 'PENDIENTE'
  const gastosReales = gastosFiltered.filter(g => !esDeuda(g))
  const deudas = gastosFiltered.filter(esDeuda)
  const totalDeudas = deudas.reduce((sum, g) => sum + (g.valor || 0), 0)
  const totalGastosFiltered = gastosReales.reduce((sum, g) => sum + (g.valor || 0), 0)

  // Cálculos (solo gastos reales; las deudas pendientes van aparte)
  const totalGastos = gastosReales.reduce((sum, g) => sum + (g.valor || 0), 0)
  const totalTienda = gastosReales.filter(g => (g.tipo_gasto || 'TIENDA') === 'TIENDA').reduce((sum, g) => sum + g.valor, 0)
  const totalEmpresa = gastosReales.filter(g => g.tipo_gasto === 'EMPRESA').reduce((sum, g) => sum + g.valor, 0)
  // Importar una lista pegada. Cada línea:
  //   fecha | descripción | valor | categoría | método | deuda
  // Sólo fecha, descripción y valor son obligatorios.
  const parsearLineas = (texto) => {
    const filas = []
    const errores = []
    texto.split('\n').forEach((linea, i) => {
      const cruda = linea.trim()
      if (!cruda || cruda.startsWith('#')) return
      const c = cruda.split('|').map(x => x.trim())
      if (c.length < 3) { errores.push(`Línea ${i + 1}: faltan datos`); return }
      // el valor puede venir como "1.576.986" o "$ 600.000"
      const valor = parseFloat(c[2].replace(/[^0-9,.-]/g, '').replace(/\./g, '').replace(',', '.'))
      if (!valor || valor <= 0) { errores.push(`Línea ${i + 1}: valor inválido (${c[2]})`); return }
      if (!/^\d{4}-\d{2}-\d{2}$/.test(c[0])) { errores.push(`Línea ${i + 1}: fecha debe ser AAAA-MM-DD`); return }
      filas.push({
        fecha: c[0],
        descripcion: c[1],
        valor,
        categoria: c[3] || 'Otros',
        metodo_pago: (c[4] || 'EFECTIVO').toUpperCase(),
        tipo_gasto: 'TIENDA',
        es_deuda: /deuda/i.test(c[5] || ''),
      })
    })
    return { filas, errores }
  }

  const importarGastos = async () => {
    const { filas, errores } = parsearLineas(textoImportar)
    if (errores.length) { toast.error(errores[0]); return }
    if (!filas.length) { toast.error('No hay nada que importar'); return }
    setImportando(true)
    let ok = 0
    const fallaron = []
    // Uno por uno: si alguno falla, los demás igual entran y el usuario
    // sabe exactamente cuál repetir.
    for (const fila of filas) {
      try {
        await api.post('/gastos', fila)
        ok++
      } catch {
        fallaron.push(fila.descripcion)
      }
    }
    setImportando(false)
    if (ok) toast.success(`${ok} registro${ok === 1 ? '' : 's'} importado${ok === 1 ? '' : 's'}`)
    if (fallaron.length) toast.error(`No entraron: ${fallaron.join(', ')}`)
    if (!fallaron.length) { setShowImportar(false); setTextoImportar('') }
    loadGastos()
  }

  const previa = parsearLineas(textoImportar)

  const gastosPorCategoria = CATEGORIAS.map(cat => ({
    categoria: cat,
    total: gastosReales.filter(g => g.categoria === cat).reduce((sum, g) => sum + g.valor, 0)
  })).filter(x => x.total > 0)
  const gastosPorMetodo = METODOS.map(met => ({
    metodo: met,
    total: gastosReales.filter(g => g.metodo_pago === met).reduce((sum, g) => sum + g.valor, 0)
  })).filter(x => x.total > 0)

  if (loading && gastos.length === 0) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-bold text-gray-900">Gastos</h2>
        <div className="flex gap-2">
          <button onClick={() => setShowImportar(true)} className="btn-secondary flex items-center gap-2">
            <Upload size={18} /> Importar lista
          </button>
          <button onClick={() => openForm()} className="btn-primary flex items-center gap-2">
            <Plus size={18} /> Nuevo Gasto
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <p className="text-xs text-gray-500 mb-1">Total Gastos</p>
          <p className="text-2xl font-bold text-red-600">{formatMoney(totalGastos)}</p>
          <p className="text-xs text-gray-400 mt-1">{gastosReales.length} registros</p>
        </div>
        <div className="card text-center border-l-4 border-orange-400">
          <div className="flex items-center justify-center gap-1 mb-1">
            <Store size={14} className="text-orange-500" />
            <p className="text-xs text-orange-600 font-semibold">Gastos Almacén</p>
          </div>
          <p className="text-2xl font-bold text-orange-600">{formatMoney(totalTienda)}</p>
          <p className="text-xs text-gray-400 mt-1">operación diaria</p>
        </div>
        <div className="card text-center border-l-4 border-blue-400">
          <div className="flex items-center justify-center gap-1 mb-1">
            <Briefcase size={14} className="text-blue-500" />
            <p className="text-xs text-blue-600 font-semibold">Gastos Empresa</p>
          </div>
          <p className="text-2xl font-bold text-blue-600">{formatMoney(totalEmpresa)}</p>
          <p className="text-xs text-gray-400 mt-1">empresariales</p>
        </div>
        <div className="card text-center">
          <p className="text-xs text-gray-500 mb-1">Gasto Promedio</p>
          <p className="text-2xl font-bold text-gray-700">
            {gastosReales.length > 0 ? formatMoney(totalGastos / gastosReales.length) : '$0'}
          </p>
          <p className="text-xs text-gray-400 mt-1">por registro</p>
        </div>
        {deudas.length > 0 && (
          <div className="card text-center border-l-4 border-purple-400">
            <p className="text-xs text-purple-600 font-semibold mb-1">Deudas pendientes</p>
            <p className="text-2xl font-bold text-purple-600">{formatMoney(totalDeudas)}</p>
            <p className="text-xs text-gray-400 mt-1">{deudas.length} por pagar · no cuentan como gasto</p>
          </div>
        )}
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
            <label className="block text-xs text-gray-600 mb-1">Tipo</label>
            <select value={filtroTipo} onChange={(e) => setFiltroTipo(e.target.value)} className="input-field text-sm">
              <option value="">Todos</option>
              <option value="TIENDA">Almacén</option>
              <option value="EMPRESA">Empresa</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Buscar</label>
            <input type="text" value={buscarDesc} onChange={(e) => setBuscarDesc(e.target.value)} placeholder="Descripción..." className="input-field text-sm w-36" />
          </div>
          <button onClick={() => { setFiltroFechaDesde(''); setFiltroFechaHasta(''); setFiltroCategoria(''); setFiltroMetodo(''); setFiltroTipo(''); setBuscarDesc('') }} className="btn-secondary text-sm">Limpiar</button>
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
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Tipo</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Categoría</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Método</th>
                <th className="px-4 py-3 text-right text-gray-600 font-medium">Valor</th>
                <th className="px-4 py-3 text-center text-gray-600 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {gastosFiltered.map(g => (
                <tr key={g.id_gasto} className={`border-b border-gray-50 hover:bg-gray-50 ${esDeuda(g) ? 'bg-purple-50/50' : ''}`}>
                  <td className="px-4 py-3 font-medium text-gray-900">{g.fecha}</td>
                  <td className="px-4 py-3 text-gray-700">
                    {g.descripcion}
                    {esDeuda(g) && <span className="ml-2 bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full text-[10px] font-bold align-middle">DEUDA</span>}
                  </td>
                  <td className="px-4 py-3">
                    {(g.tipo_gasto || 'TIENDA') === 'TIENDA'
                      ? <span className="bg-orange-100 text-orange-700 px-2 py-1 rounded text-xs font-medium flex items-center gap-1 w-fit"><Store size={11} /> Almacén</span>
                      : <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-medium flex items-center gap-1 w-fit"><Briefcase size={11} /> Empresa</span>
                    }
                  </td>
                  <td className="px-4 py-3">
                    <span className="bg-gray-100 px-2 py-1 rounded text-xs">{g.categoria || '—'}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="bg-blue-100 px-2 py-1 rounded text-xs text-blue-700">{g.metodo_pago}</span>
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold ${esDeuda(g) ? 'text-purple-600' : 'text-red-600'}`}>{formatMoney(g.valor)}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      {esDeuda(g) && (
                        <button
                          onClick={() => pagarDeuda(g)}
                          className="text-green-600 hover:text-green-800 p-1"
                          title="Marcar como pagada"
                        >
                          <CheckCircle size={15} />
                        </button>
                      )}
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

      {/* Modal Importar lista */}
      {showImportar && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Upload size={20} className="text-raloz-600" /> Importar lista de gastos
              </h3>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
                <p className="font-medium mb-1">Una línea por gasto, separando con <b>|</b></p>
                <code className="block bg-white/70 rounded p-2 text-xs leading-relaxed">
                  fecha | descripción | valor | categoría | método | deuda
                </code>
                <p className="mt-2 text-xs">
                  Sólo <b>fecha, descripción y valor</b> son obligatorios. La fecha va como
                  <b> 2026-08-11</b>. Escribe <b>deuda</b> al final si es algo que pagas después.
                </p>
              </div>
              <textarea
                value={textoImportar}
                onChange={e => setTextoImportar(e.target.value)}
                rows={12}
                className="input-field font-mono text-xs"
                placeholder={'2026-08-11 | Telas Lafayette | 511578 | Costo Mercancía | BANCOLOMBIA'}
              />
              {textoImportar.trim() && (
                <div className="text-sm">
                  {previa.errores.length > 0 ? (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700">
                      {previa.errores.slice(0, 5).map((e, i) => <p key={i}>⚠️ {e}</p>)}
                    </div>
                  ) : (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-green-800">
                      ✅ {previa.filas.length} registro{previa.filas.length === 1 ? '' : 's'} listo
                      {previa.filas.length === 1 ? '' : 's'} · total{' '}
                      <b>{formatMoney(previa.filas.reduce((t, f) => t + f.valor, 0))}</b>
                    </div>
                  )}
                </div>
              )}
              <div className="flex gap-3 pt-2">
                <button onClick={importarGastos} disabled={importando || !previa.filas.length}
                        className="btn-primary flex-1 disabled:opacity-50">
                  {importando ? 'Importando…' : `Importar ${previa.filas.length || ''}`}
                </button>
                <button onClick={() => { setShowImportar(false); setTextoImportar('') }}
                        className="btn-secondary flex-1">Cancelar</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Crear/Editar */}
      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md max-h-screen overflow-y-auto">
            <h3 className="text-lg font-bold mb-4">
              {editingId ? 'Editar Gasto' : (form.es_deuda ? 'Nueva Deuda' : 'Nuevo Gasto')}
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
                <label className="block text-sm font-medium mb-1">¿Es gasto del almacén o empresarial?</label>
                <div className="grid grid-cols-2 gap-2">
                  <button type="button"
                    onClick={() => setForm({...form, tipo_gasto: 'TIENDA'})}
                    className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg border-2 text-sm font-medium transition-colors ${form.tipo_gasto === 'TIENDA' ? 'border-orange-400 bg-orange-50 text-orange-700' : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}>
                    <Store size={15} /> Almacén
                  </button>
                  <button type="button"
                    onClick={() => setForm({...form, tipo_gasto: 'EMPRESA'})}
                    className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg border-2 text-sm font-medium transition-colors ${form.tipo_gasto === 'EMPRESA' ? 'border-blue-400 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}>
                    <Briefcase size={15} /> Empresa
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Categoría *</label>
                <select
                  required
                  value={form.categoria}
                  onChange={e => setForm({...form, categoria: e.target.value})}
                  className={`input-field w-full ${!form.categoria ? 'border-amber-400' : ''}`}
                >
                  <option value="">— Selecciona una categoría —</option>
                  {CATEGORIAS.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                {form.categoria && CATEGORIA_HINTS[form.categoria] && (
                  <p className="text-xs text-gray-400 mt-1">{CATEGORIA_HINTS[form.categoria]}</p>
                )}
                {form.categoria === 'Otros' && (
                  <p className="text-xs text-amber-600 mt-1 flex items-center gap-1">
                    <AlertTriangle size={11} /> ¿Hay alguna categoría más específica? Usar "Otros" dificulta el análisis contable.
                  </p>
                )}
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
                {(form.metodo_pago === 'NEQUI' || form.metodo_pago === 'DAVIPLATA') && (
                  <p className="text-xs text-amber-600 mt-1 flex items-center gap-1">
                    <AlertTriangle size={11} /> Verifica que este sea un gasto real y no un pago de cliente registrado por error.
                  </p>
                )}
              </div>

              {!editingId && (
                <div className={`rounded-lg border-2 p-3 transition-colors ${form.es_deuda ? 'border-purple-300 bg-purple-50' : 'border-gray-200'}`}>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.es_deuda}
                      onChange={e => setForm({...form, es_deuda: e.target.checked})}
                      className="w-4 h-4 text-purple-600 rounded"
                    />
                    <span className="text-sm font-medium text-gray-800">Es una deuda (la debo ahora, pago después)</span>
                  </label>
                  {form.es_deuda && (
                    <p className="text-xs text-purple-600 mt-1.5 ml-6">
                      Quedará pendiente y NO contará como gasto hasta que la marques pagada (ahí se registra como gasto del día del pago).
                    </p>
                  )}
                </div>
              )}

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
