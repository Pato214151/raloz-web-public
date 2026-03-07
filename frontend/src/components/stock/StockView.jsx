import { useState, useEffect } from 'react'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Package, Plus, X, Printer, AlertTriangle, Activity, ChevronRight, Trash2, Edit2, Check } from 'lucide-react'

const TALLAS_NORMAL = ['2', '4', '6', '8', '10', '12', '14', '16', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'Única']
const TALLAS_MEDIAS = ['6-8', '8-10', '10-12', '12-14', '14-16']
const TALLAS_ORDEN = [...TALLAS_NORMAL, ...TALLAS_MEDIAS]

const ACCION_BADGE = {
  ACTUALIZAR: 'bg-blue-100 text-blue-700',
  EDITAR:     'bg-amber-100 text-amber-700',
  ELIMINAR:   'bg-red-100 text-red-700',
}

function tallaCaja(cantidad) {
  if (cantidad === 0) return 'bg-red-100 border-red-300 text-red-700'
  if (cantidad < 5)  return 'bg-amber-100 border-amber-300 text-amber-700'
  return 'bg-green-100 border-green-300 text-green-700'
}

function sortTallas(a, b) {
  const ia = TALLAS_ORDEN.indexOf(a)
  const ib = TALLAS_ORDEN.indexOf(b)
  if (ia !== -1 && ib !== -1) return ia - ib
  if (ia !== -1) return -1
  if (ib !== -1) return 1
  return a.localeCompare(b)
}

function fmtFecha(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
  } catch { return iso }
}

export default function StockView() {
  const { isAdmin } = useAuth()
  const [tab, setTab] = useState('inventario')

  // ── Inventario ──
  const [colegioSel, setColegioSel] = useState(null)
  const [colegios, setColegios]     = useState([])
  const [resumen, setResumen]       = useState([])
  const [stock, setStock]           = useState([])
  const [productos, setProductos]   = useState([])
  const [loading, setLoading]       = useState(true)
  const [loadingStock, setLoadingStock] = useState(false)

  // Edición inline
  const [editKey, setEditKey] = useState(null)
  const [editVal, setEditVal] = useState('')
  const [editObs, setEditObs] = useState('')

  // Modal agregar
  const [showAdd, setShowAdd] = useState(false)
  const [newStock, setNewStock] = useState({ producto_id: '', talla: '', cantidad: '', observaciones: '' })

  // ── Actividad ──
  const [actividad, setActividad]           = useState([])
  const [actUsuarios, setActUsuarios]       = useState([])
  const [actFiltroUsuario, setActFiltroUsuario] = useState('')
  const [loadingAct, setLoadingAct]         = useState(false)

  useEffect(() => { cargarInicial() }, [])

  useEffect(() => {
    if (colegioSel) cargarStock(colegioSel.id_colegio)
  }, [colegioSel])

  useEffect(() => {
    if (tab === 'actividad') cargarActividad()
  }, [tab, actFiltroUsuario])

  async function cargarInicial() {
    try {
      const [resRes, prodRes, colRes] = await Promise.all([
        api.get('/stock/resumen'),
        api.get('/productos'),
        api.get('/colegios'),
      ])
      const cols = colRes.data.colegios || []
      setResumen(resRes.data.resumen || [])
      setProductos(prodRes.data.productos || [])
      setColegios(cols)
      if (cols.length > 0) setColegioSel(cols[0])
    } catch {
      toast.error('Error cargando inventario')
    } finally {
      setLoading(false)
    }
  }

  async function cargarStock(colegioId) {
    setLoadingStock(true)
    try {
      const res = await api.get('/stock', { params: { colegio_id: colegioId } })
      setStock(res.data.stock || [])
    } catch {
      toast.error('Error cargando stock')
    } finally {
      setLoadingStock(false)
    }
  }

  async function cargarActividad() {
    setLoadingAct(true)
    try {
      const params = {}
      if (actFiltroUsuario) params.usuario = actFiltroUsuario
      const res = await api.get('/stock/actividad', { params })
      setActividad(res.data.actividad || [])
      setActUsuarios(res.data.usuarios || [])
    } catch {
      toast.error('Error cargando actividad')
    } finally {
      setLoadingAct(false)
    }
  }

  async function guardarEdicion(id_stock) {
    const val = parseInt(editVal)
    if (isNaN(val) || val < 0) { toast.error('Cantidad inválida'); return }
    try {
      await api.put(`/stock/${id_stock}`, { cantidad: val, observaciones: editObs })
      setStock(prev => prev.map(s => s.id_stock === id_stock ? { ...s, cantidad: val } : s))
      const r = await api.get('/stock/resumen')
      setResumen(r.data.resumen || [])
      setEditKey(null)
      setEditObs('')
      toast.success('Cantidad actualizada')
    } catch (e) {
      toast.error(e.response?.data?.error || 'Error')
    }
  }

  async function eliminar(id_stock, nombre, talla) {
    if (!confirm(`¿Eliminar talla ${talla} de ${nombre}?`)) return
    try {
      await api.delete(`/stock/${id_stock}`)
      setStock(prev => prev.filter(s => s.id_stock !== id_stock))
      const r = await api.get('/stock/resumen')
      setResumen(r.data.resumen || [])
      toast.success('Eliminado')
    } catch (e) {
      toast.error(e.response?.data?.error || 'Error')
    }
  }

  async function agregarStock(e) {
    e.preventDefault()
    if (!newStock.producto_id || !newStock.talla || newStock.cantidad === '') {
      toast.error('Completa todos los campos'); return
    }
    try {
      await api.post('/stock', {
        id_colegio:      colegioSel.id_colegio,
        id_producto:     newStock.producto_id,
        talla_individual: newStock.talla,
        cantidad:        parseInt(newStock.cantidad),
        observaciones:   newStock.observaciones,
      })
      toast.success('Stock agregado')
      setShowAdd(false)
      setNewStock({ producto_id: '', talla: '', cantidad: '', observaciones: '' })
      cargarStock(colegioSel.id_colegio)
      const r = await api.get('/stock/resumen')
      setResumen(r.data.resumen || [])
    } catch (e) {
      toast.error(e.response?.data?.error || 'Error')
    }
  }

  // Tallas para el producto seleccionado en el modal
  const prodSeleccionado = productos.find(p => String(p.id_producto) === String(newStock.producto_id))
  const tallasModal = prodSeleccionado?.tipo === 'medias' ? TALLAS_MEDIAS : TALLAS_NORMAL

  // Agrupar stock por producto
  const porProducto = {}
  stock.forEach(s => {
    const key = s.producto_nombre || `Producto ${s.id_producto}`
    if (!porProducto[key]) porProducto[key] = { items: [], tipo: s.producto_tipo }
    porProducto[key].items.push(s)
  })
  Object.values(porProducto).forEach(g =>
    g.items.sort((a, b) => sortTallas(a.talla_individual, b.talla_individual))
  )

  const totalUnidades = stock.reduce((s, x) => s + x.cantidad, 0)
  const bajoStock = stock.filter(s => s.cantidad > 0 && s.cantidad < 5).length
  const sinStock  = stock.filter(s => s.cantidad === 0).length

  function imprimir() {
    if (!stock.length) return
    let empresa = { nombre: 'RALOZ COL SAS' }
    try { empresa = JSON.parse(localStorage.getItem('raloz_empresa') || 'null') || empresa } catch { /* default */ }
    const w = window.open('', '_blank')
    const bloques = Object.entries(porProducto).map(([prod, g]) => {
      const filas = g.items.map(s => {
        const color = s.cantidad === 0 ? '#dc2626' : s.cantidad < 5 ? '#d97706' : '#16a34a'
        return `<td style="padding:6px 10px;border:1px solid #ddd;text-align:center;font-weight:bold;color:${color}">
          <div style="font-size:10px;color:#555">${s.talla_individual}</div>${s.cantidad}</td>`
      }).join('')
      return `<tr><td style="padding:6px 10px;border:1px solid #ddd;font-weight:600;min-width:160px">${prod}</td>${filas}</tr>`
    }).join('')
    w.document.write(`<!DOCTYPE html><html><head><title>Inventario</title>
      <style>body{font-family:Arial,sans-serif;margin:20px;font-size:13px}h2{color:#1976d2}
      table{border-collapse:collapse;margin-top:10px}@media print{.no-print{display:none}}</style></head>
      <body><h2>${empresa.nombre} — Inventario ${colegioSel?.nombre || ''}</h2>
      <p>Total: <b>${totalUnidades}</b> uds &nbsp;·&nbsp; Bajo stock: <b>${bajoStock}</b> &nbsp;·&nbsp; Sin stock: <b>${sinStock}</b></p>
      <table><tbody>${bloques}</tbody></table>
      <p style="font-size:10px;color:#999;margin-top:20px">Impreso ${new Date().toLocaleString('es-CO')}</p>
      </body></html>`)
    w.document.close()
    w.print()
  }

  function imprimirActividad() {
    if (!actividad.length) return
    let empresa = { nombre: 'RALOZ COL SAS' }
    try { empresa = JSON.parse(localStorage.getItem('raloz_empresa') || 'null') || empresa } catch { /* default */ }
    const w = window.open('', '_blank')
    const filas = actividad.map(a => `
      <tr>
        <td style="padding:5px 8px;border:1px solid #eee;font-size:11px">${fmtFecha(a.fecha_hora)}</td>
        <td style="padding:5px 8px;border:1px solid #eee;font-weight:600">${a.usuario}</td>
        <td style="padding:5px 8px;border:1px solid #eee">${a.accion}</td>
        <td style="padding:5px 8px;border:1px solid #eee">${a.comentario || '—'}</td>
      </tr>`).join('')
    w.document.write(`<!DOCTYPE html><html><head><title>Actividad Stock</title>
      <style>body{font-family:Arial,sans-serif;margin:20px;font-size:13px}h2{color:#1976d2}
      table{border-collapse:collapse;width:100%;margin-top:10px}
      th{background:#f5f5f5;padding:6px 8px;text-align:left;border:1px solid #ddd;font-size:11px}</style></head>
      <body><h2>${empresa.nombre} — Actividad de Stock${actFiltroUsuario ? ` (${actFiltroUsuario})` : ''}</h2>
      <table><thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Detalle</th></tr></thead>
      <tbody>${filas}</tbody></table>
      <p style="font-size:10px;color:#999;margin-top:16px">Impreso ${new Date().toLocaleString('es-CO')}</p>
      </body></html>`)
    w.document.close()
    w.print()
  }

  if (loading) return (
    <div className="flex justify-center py-20">
      <div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full" />
    </div>
  )

  return (
    <div className="space-y-4">

      {/* ── Tabs principales ── */}
      <div className="flex gap-1 border-b border-gray-200">
        <button onClick={() => setTab('inventario')}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
            tab === 'inventario' ? 'border-raloz-500 text-raloz-600 bg-raloz-50' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}>
          <Package size={15} /> Inventario
        </button>
        {isAdmin() && (
          <button onClick={() => setTab('actividad')}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
              tab === 'actividad' ? 'border-purple-500 text-purple-600 bg-purple-50' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>
            <Activity size={15} /> Actividad del equipo
          </button>
        )}
      </div>

      {/* ════════════════ TAB INVENTARIO ════════════════ */}
      {tab === 'inventario' && (
        <div className="flex gap-4" style={{ minHeight: '70vh' }}>

          {/* Panel izquierdo: colegios */}
          <div className="w-56 flex-shrink-0 space-y-1">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-2 mb-2">Colegios</p>
            {colegios.map(c => {
              const resCol = resumen.find(r => r.id_colegio === c.id_colegio)
              const activo = colegioSel?.id_colegio === c.id_colegio
              return (
                <button key={c.id_colegio} onClick={() => setColegioSel(c)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    activo ? 'bg-raloz-600 text-white' : 'hover:bg-gray-100 text-gray-700'
                  }`}>
                  <p className="font-medium leading-tight">{c.nombre}</p>
                  <p className={`text-xs mt-0.5 ${activo ? 'text-raloz-200' : 'text-gray-400'}`}>
                    {resCol ? `${resCol.total_unidades} uds` : 'Sin stock'}
                  </p>
                </button>
              )
            })}
          </div>

          {/* Panel derecho: productos */}
          <div className="flex-1 min-w-0 space-y-4">
            {!colegioSel ? (
              <div className="flex items-center justify-center h-full text-gray-400">
                <Package size={40} className="opacity-30" />
              </div>
            ) : (
              <>
                {/* Header */}
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{colegioSel.nombre}</h2>
                    <p className="text-sm text-gray-500">{totalUnidades} unidades en stock</p>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={imprimir} className="btn-secondary text-sm flex items-center gap-1.5">
                      <Printer size={14} /> Imprimir
                    </button>
                    <button onClick={() => setShowAdd(true)} className="btn-primary text-sm flex items-center gap-1.5">
                      <Plus size={14} /> Agregar stock
                    </button>
                  </div>
                </div>

                {/* Alertas */}
                {(bajoStock > 0 || sinStock > 0) && (
                  <div className="flex gap-2 flex-wrap">
                    {sinStock > 0 && (
                      <span className="flex items-center gap-1 text-xs bg-red-50 text-red-700 border border-red-200 px-2 py-1 rounded-full">
                        <AlertTriangle size={11} /> {sinStock} sin stock
                      </span>
                    )}
                    {bajoStock > 0 && (
                      <span className="flex items-center gap-1 text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2 py-1 rounded-full">
                        <AlertTriangle size={11} /> {bajoStock} bajo stock (&lt;5)
                      </span>
                    )}
                  </div>
                )}

                {/* Grid de productos */}
                {loadingStock ? (
                  <div className="flex justify-center py-12">
                    <div className="animate-spin h-8 w-8 border-b-2 border-raloz-600 rounded-full" />
                  </div>
                ) : Object.keys(porProducto).length === 0 ? (
                  <div className="card text-center py-12">
                    <Package className="mx-auto text-gray-300 mb-3" size={44} />
                    <p className="text-gray-500">No hay stock registrado para este colegio</p>
                    <button onClick={() => setShowAdd(true)} className="btn-primary mt-3 text-sm">
                      Agregar stock
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(porProducto).map(([nombreProd, grupo]) => (
                      <div key={nombreProd} className="card">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <p className="font-semibold text-gray-800">{nombreProd}</p>
                            {grupo.tipo === 'medias' && (
                              <span className="text-xs bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full">medias</span>
                            )}
                          </div>
                          <p className="text-xs text-gray-400">
                            {grupo.items.reduce((s, x) => s + x.cantidad, 0)} uds total
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {grupo.items.map(s => (
                            <div key={s.id_stock} className="relative group">
                              {editKey === s.id_stock ? (
                                <div className="bg-white border-2 border-raloz-400 rounded-xl p-2 flex flex-col items-center gap-1 w-20">
                                  <span className="text-xs text-gray-500 font-medium">{s.talla_individual}</span>
                                  <input type="number" min="0" value={editVal}
                                    onChange={e => setEditVal(e.target.value)}
                                    onKeyDown={e => {
                                      if (e.key === 'Enter') guardarEdicion(s.id_stock)
                                      if (e.key === 'Escape') { setEditKey(null); setEditObs('') }
                                    }}
                                    autoFocus
                                    className="w-14 text-center border rounded text-sm font-bold py-1 focus:outline-none" />
                                  <input type="text" value={editObs}
                                    onChange={e => setEditObs(e.target.value)}
                                    placeholder="Obs..."
                                    className="w-16 text-xs border rounded px-1 py-0.5 focus:outline-none" />
                                  <button onClick={() => guardarEdicion(s.id_stock)}
                                    className="text-green-600 hover:bg-green-50 rounded p-0.5">
                                    <Check size={12} />
                                  </button>
                                </div>
                              ) : (
                                <div
                                  onClick={() => { setEditKey(s.id_stock); setEditVal(s.cantidad.toString()); setEditObs('') }}
                                  title="Clic para editar"
                                  className={`cursor-pointer flex flex-col items-center justify-center w-16 h-16 rounded-xl border-2 font-bold text-sm transition-all hover:scale-105 hover:shadow-sm ${tallaCaja(s.cantidad)}`}>
                                  <span className="text-xs font-normal opacity-70">{s.talla_individual}</span>
                                  <span className="text-lg leading-tight">{s.cantidad}</span>
                                </div>
                              )}
                              {/* Botón eliminar */}
                              {editKey !== s.id_stock && (
                                <button
                                  onClick={() => eliminar(s.id_stock, nombreProd, s.talla_individual)}
                                  className="absolute -top-1.5 -right-1.5 hidden group-hover:flex items-center justify-center w-4 h-4 bg-red-500 text-white rounded-full hover:bg-red-600"
                                  title="Eliminar talla">
                                  <X size={9} />
                                </button>
                              )}
                            </div>
                          ))}
                          {/* Botón agregar talla extra para este producto */}
                          <button
                            onClick={() => { setNewStock({ producto_id: String(grupo.items[0].id_producto), talla: '', cantidad: '', observaciones: '' }); setShowAdd(true) }}
                            className="w-16 h-16 rounded-xl border-2 border-dashed border-gray-300 text-gray-400 hover:border-raloz-400 hover:text-raloz-500 flex items-center justify-center transition-colors"
                            title="Agregar talla">
                            <Plus size={18} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* ════════════════ TAB ACTIVIDAD ════════════════ */}
      {tab === 'actividad' && isAdmin() && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Actividad del equipo</h2>
              <p className="text-sm text-gray-500">Registro de todo lo que se agregó, editó o eliminó en inventario</p>
            </div>
            <div className="flex gap-2 items-center">
              <select value={actFiltroUsuario} onChange={e => setActFiltroUsuario(e.target.value)}
                className="input-field text-sm">
                <option value="">Todos los usuarios</option>
                {actUsuarios.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
              <button onClick={imprimirActividad} className="btn-secondary text-sm flex items-center gap-1.5">
                <Printer size={14} /> Imprimir
              </button>
            </div>
          </div>

          {loadingAct ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin h-8 w-8 border-b-2 border-purple-600 rounded-full" />
            </div>
          ) : actividad.length === 0 ? (
            <div className="card text-center py-12 text-gray-400">
              <Activity size={40} className="mx-auto mb-3 opacity-30" />
              <p>No hay actividad registrada aún</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                  <tr>
                    <th className="text-left px-4 py-3">Fecha y hora</th>
                    <th className="text-left px-4 py-3">Usuario</th>
                    <th className="text-center px-4 py-3">Acción</th>
                    <th className="text-left px-4 py-3">Detalle</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {actividad.map(a => (
                    <tr key={a.id_auditoria} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-400 whitespace-nowrap text-xs">{fmtFecha(a.fecha_hora)}</td>
                      <td className="px-4 py-3 font-semibold text-gray-800">{a.usuario}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ACCION_BADGE[a.accion] || 'bg-gray-100 text-gray-600'}`}>
                          {a.accion}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{a.comentario || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Modal agregar stock ── */}
      {showAdd && colegioSel && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-2xl">
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Plus size={18} className="text-raloz-600" />
              Agregar Stock — {colegioSel.nombre}
            </h3>
            <form onSubmit={agregarStock} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Producto *</label>
                <select required value={newStock.producto_id}
                  onChange={e => setNewStock({ ...newStock, producto_id: e.target.value, talla: '' })}
                  className="input-field w-full">
                  <option value="">Seleccionar producto...</option>
                  {productos.map(p => (
                    <option key={p.id_producto} value={p.id_producto}>{p.nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Talla *</label>
                <select required value={newStock.talla}
                  onChange={e => setNewStock({ ...newStock, talla: e.target.value })}
                  className="input-field w-full">
                  <option value="">Seleccionar talla...</option>
                  {tallasModal.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                {prodSeleccionado?.tipo === 'medias' && (
                  <p className="text-xs text-purple-600 mt-1">Tallas de medias</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Cantidad *</label>
                <input type="number" required min="0" value={newStock.cantidad}
                  onChange={e => setNewStock({ ...newStock, cantidad: e.target.value })}
                  className="input-field w-full" placeholder="0" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Observaciones <span className="text-gray-400 font-normal">(opcional)</span></label>
                <input type="text" value={newStock.observaciones}
                  onChange={e => setNewStock({ ...newStock, observaciones: e.target.value })}
                  className="input-field w-full" placeholder="Ej: entrada de nueva mercancía, ajuste inventario..." />
              </div>
              <div className="flex gap-3 justify-end pt-2 border-t">
                <button type="button"
                  onClick={() => { setShowAdd(false); setNewStock({ producto_id: '', talla: '', cantidad: '', observaciones: '' }) }}
                  className="btn-secondary">Cancelar</button>
                <button type="submit" className="btn-primary">Agregar</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
