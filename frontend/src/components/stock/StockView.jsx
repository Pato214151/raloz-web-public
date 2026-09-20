/**
 * Stock por colegio, producto y talla: edición rápida, balance y actividad
 * reciente del equipo.
 */

import { useState, useEffect } from 'react'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Package, Plus, X, Printer, AlertTriangle, Activity, BarChart3 } from 'lucide-react'

const TALLAS_NORMAL = ['2', '4', '6', '8', '10', '12', '14', '16', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'Única']
const TALLAS_MEDIAS = ['4-6', '6-8', '8-10', '10-12', '12-14']
const TALLAS_ORDEN = [...TALLAS_NORMAL, ...TALLAS_MEDIAS]

// El tipo en la base puede venir como 'Medias' (mayúscula); comparar sin distinguir.
const esMedias = (tipo) => (tipo || '').toLowerCase().includes('media')

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
  const [catalogo, setCatalogo]     = useState([])
  const [productos, setProductos]   = useState([])
  const [loading, setLoading]       = useState(true)
  const [loadingStock, setLoadingStock] = useState(false)


  // Modal agregar
  const [showAdd, setShowAdd] = useState(false)
  const [newStock, setNewStock] = useState({ producto_id: '', talla: '', cantidad: '', observaciones: '', modo: 'entrada' })

  // ── Actividad ──
  const [actividad, setActividad]           = useState([])
  const [actUsuarios, setActUsuarios]       = useState([])
  const [actFiltroUsuario, setActFiltroUsuario] = useState('')
  const [loadingAct, setLoadingAct]         = useState(false)

  // Reportes / balance de prendas
  const [balance, setBalance]       = useState([])
  const [totalesBal, setTotalesBal] = useState(null)
  const [loadingBal, setLoadingBal] = useState(false)
  const [repDesde, setRepDesde]     = useState('')
  const [repHasta, setRepHasta]     = useState('')

  useEffect(() => { cargarInicial() }, [])

  useEffect(() => {
    if (colegioSel) cargarStock(colegioSel.id_colegio)
  }, [colegioSel])

  useEffect(() => {
    if (tab === 'actividad') cargarActividad()
    if (tab === 'reportes' && colegioSel) cargarBalance()
  }, [tab, actFiltroUsuario, colegioSel])

  async function cargarBalance() {
    if (!colegioSel) return
    setLoadingBal(true)
    try {
      const params = { colegio_id: colegioSel.id_colegio }
      if (repDesde) params.desde = repDesde
      if (repHasta) params.hasta = repHasta
      const res = await api.get('/stock/balance', { params })
      setBalance(res.data.balance || [])
      setTotalesBal(res.data.totales || null)
    } catch {
      toast.error('Error cargando balance')
    } finally {
      setLoadingBal(false)
    }
  }

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
      const [resStock, resCat] = await Promise.all([
        api.get('/stock', { params: { colegio_id: colegioId } }),
        api.get('/stock/catalogo', { params: { colegio_id: colegioId } }),
      ])
      setStock(resStock.data.stock || [])
      setCatalogo(resCat.data.catalogo || [])
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
    const esEntrada = (newStock.modo || 'entrada') === 'entrada'
    try {
      if (esEntrada) {
        // ENTRADA: suma al stock (cuando llega mercancía) y queda en el kardex
        await api.post('/stock/entrada', {
          id_colegio:       colegioSel.id_colegio,
          id_producto:      newStock.producto_id,
          talla_individual: newStock.talla,
          cantidad:         parseInt(newStock.cantidad),
          motivo:           newStock.observaciones || 'Recepción de mercancía',
        })
        toast.success(`Entrada registrada: +${newStock.cantidad}`)
      } else {
        // AJUSTE: fija el valor exacto (corrección de inventario)
        await api.post('/stock', {
          id_colegio:       colegioSel.id_colegio,
          id_producto:      newStock.producto_id,
          talla_individual: newStock.talla,
          cantidad:         parseInt(newStock.cantidad),
          observaciones:    newStock.observaciones,
        })
        toast.success('Stock ajustado')
      }
      setShowAdd(false)
      setNewStock({ producto_id: '', talla: '', cantidad: '', observaciones: '', modo: 'entrada' })
      cargarStock(colegioSel.id_colegio)
      const r = await api.get('/stock/resumen')
      setResumen(r.data.resumen || [])
    } catch (e) {
      toast.error(e.response?.data?.error || 'Error')
    }
  }

  // Tallas para el producto seleccionado en el modal
  const prodSeleccionado = productos.find(p => String(p.id_producto) === String(newStock.producto_id))
  const tallasModal = esMedias(prodSeleccionado?.tipo) ? TALLAS_MEDIAS : TALLAS_NORMAL

  // Lookup de stock real para edición/eliminación inline (por producto+talla → id_stock)
  const stockLookup = {}
  stock.forEach(s => { stockLookup[`${s.id_producto}-${s.talla_individual}`] = s })

  // Inventario armado desde el CATÁLOGO completo → muestra TODAS las prendas que
  // vende el colegio con sus tallas, incluidas las que están en 0.
  const porProducto = {}
  catalogo.forEach(prod => {
    const key = prod.producto_nombre
    porProducto[key] = {
      tipo: prod.producto_tipo,
      items: prod.tallas.map(t => {
        const sk = stockLookup[`${prod.id_producto}-${t.talla}`]
        return {
          id_stock: sk ? sk.id_stock : null,
          id_producto: prod.id_producto,
          talla_individual: t.talla,
          // Usa el stock REAL (que se actualiza al editar), no la cantidad del
          // catálogo (que quedaba vieja → por eso tocaba F5 para ver el cambio).
          cantidad: sk ? sk.cantidad : (t.cantidad || 0),
        }
      }),
    }
  })

  // Prendas SIN precio en este colegio (descontinuadas / stock viejo): solo se
  // muestran si TIENEN unidades, y marcadas como "sin precio" para que no se
  // confundan con las del catálogo (evita ver prendas "repetidas").
  const idsConPrecio = new Set(catalogo.map(p => p.id_producto))
  stock.forEach(s => {
    if ((s.cantidad || 0) <= 0) return            // orfanas vacías: no mostrar
    if (idsConPrecio.has(s.id_producto)) return    // ya está en el catálogo: no duplicar
    const key = s.producto_nombre || `Producto ${s.id_producto}`
    if (!porProducto[key]) porProducto[key] = { tipo: s.producto_tipo, sinPrecio: true, items: [] }
    if (!porProducto[key].items.some(it => it.talla_individual === s.talla_individual)) {
      porProducto[key].items.push({
        id_stock: s.id_stock, id_producto: s.id_producto,
        talla_individual: s.talla_individual, cantidad: s.cantidad,
      })
    }
  })

  const allItems = Object.values(porProducto).flatMap(g => g.items)
  const totalUnidades = allItems.reduce((s, x) => s + x.cantidad, 0)
  const bajoStock = allItems.filter(x => x.cantidad > 0 && x.cantidad < 5).length
  const sinStock  = allItems.filter(x => x.cantidad === 0).length

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
        <button onClick={() => setTab('reportes')}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
            tab === 'reportes' ? 'border-emerald-500 text-emerald-600 bg-emerald-50' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}>
          <BarChart3 size={15} /> Reportes
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
      {/* En celular se apilan: 224px de columna fija + el contenido no caben
          en 375px, y todo quedaba cortado a lado y lado. */}
      {tab === 'inventario' && (
        <div className="flex flex-col lg:flex-row gap-4" style={{ minHeight: '70vh' }}>

          {/* Panel izquierdo: colegios */}
          <div className="w-full lg:w-56 flex-shrink-0 space-y-1">
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
                    <p className="text-gray-500">Este colegio no tiene prendas configuradas (sin precios)</p>
                    <p className="text-gray-400 text-xs mt-1">Configura los precios del colegio para que sus prendas aparezcan aquí.</p>
                    <button onClick={() => setShowAdd(true)} className="btn-primary mt-3 text-sm">
                      Agregar stock manual
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(porProducto).map(([nombreProd, grupo]) => (
                      <div key={nombreProd} className="card">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <p className="font-semibold text-gray-800">{nombreProd}</p>
                            {esMedias(grupo.tipo) && (
                              <span className="text-xs bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full">medias</span>
                            )}
                            {grupo.sinPrecio && (
                              <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full" title="Esta prenda no tiene precio en este colegio (stock viejo / descontinuada)">sin precio</span>
                            )}
                          </div>
                          <p className="text-xs text-gray-400">
                            {grupo.items.reduce((s, x) => s + x.cantidad, 0)} uds total
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {grupo.items.map(s => (
                            <div key={`${s.id_producto}-${s.talla_individual}`} className="relative group">
                              <div
                                onClick={() => {
                                  setNewStock({ producto_id: String(s.id_producto), talla: s.talla_individual, cantidad: '', observaciones: '', modo: 'entrada' })
                                  setShowAdd(true)
                                }}
                                title={s.id_stock ? 'Clic para registrar entrada o ajustar' : 'Sin stock — clic para registrar entrada'}
                                className={`cursor-pointer flex flex-col items-center justify-center w-16 h-16 rounded-xl border-2 font-bold text-sm transition-all hover:scale-105 hover:shadow-sm ${tallaCaja(s.cantidad)}`}>
                                <span className="text-xs font-normal opacity-70">{s.talla_individual}</span>
                                <span className="text-lg leading-tight">{s.cantidad}</span>
                              </div>
                              {/* Botón eliminar (solo si la talla ya tiene registro de stock) */}
                              {s.id_stock && (
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
                            onClick={() => { setNewStock({ producto_id: String(grupo.items[0].id_producto), talla: '', cantidad: '', observaciones: '', modo: 'entrada' }); setShowAdd(true) }}
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

      {/* ════════════════ TAB REPORTES ════════════════ */}
      {tab === 'reportes' && (
        <div className="space-y-4">
          {/* Filtros */}
          <div className="card flex flex-wrap items-end gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Colegio</label>
              <select value={colegioSel?.id_colegio || ''}
                onChange={e => setColegioSel(colegios.find(c => String(c.id_colegio) === e.target.value) || null)}
                className="input-field text-sm">
                <option value="">Seleccionar...</option>
                {colegios.map(c => <option key={c.id_colegio} value={c.id_colegio}>{c.nombre}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Desde <span className="text-gray-400">(opcional)</span></label>
              <input type="date" value={repDesde} onChange={e => setRepDesde(e.target.value)} className="input-field text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Hasta <span className="text-gray-400">(opcional)</span></label>
              <input type="date" value={repHasta} onChange={e => setRepHasta(e.target.value)} className="input-field text-sm" />
            </div>
            <button onClick={cargarBalance} className="btn-primary text-sm">Ver reporte</button>
          </div>

          {!colegioSel ? (
            <div className="card text-center py-12 text-gray-400">
              <BarChart3 className="mx-auto mb-3 opacity-30" size={44} />
              Elige un colegio para ver su balance de prendas.
            </div>
          ) : loadingBal ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin h-8 w-8 border-b-2 border-emerald-600 rounded-full" />
            </div>
          ) : (
            <>
              {/* Totales */}
              {totalesBal && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="card text-center"><p className="text-xs text-gray-500">Entraron</p><p className="text-2xl font-bold text-green-600">{totalesBal.entradas}</p></div>
                  <div className="card text-center"><p className="text-xs text-gray-500">Salieron</p><p className="text-2xl font-bold text-red-500">{totalesBal.salidas}</p></div>
                  <div className="card text-center"><p className="text-xs text-gray-500">En stock</p><p className="text-2xl font-bold text-gray-800">{totalesBal.stock_actual}</p></div>
                  <div className="card text-center"><p className="text-xs text-gray-500">Valor inventario</p><p className="text-xl font-bold text-emerald-600">${(totalesBal.valor_inventario || 0).toLocaleString('es-CO')}</p></div>
                </div>
              )}

              {/* Tabla por prenda */}
              <div className="card overflow-x-auto">
                {balance.length === 0 ? (
                  <p className="text-center py-8 text-gray-400">Sin movimientos para este colegio en el periodo.</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-500 border-b">
                        <th className="py-2 pr-3">Prenda</th>
                        <th className="py-2 px-3 text-center text-green-600">Entraron</th>
                        <th className="py-2 px-3 text-center text-red-500">Salieron</th>
                        <th className="py-2 px-3 text-center">Quedan</th>
                        <th className="py-2 pl-3 text-right">Valor inventario</th>
                      </tr>
                    </thead>
                    <tbody>
                      {balance.map(b => (
                        <tr key={b.id_producto} className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="py-2 pr-3 font-medium text-gray-800">{b.producto_nombre}</td>
                          <td className="py-2 px-3 text-center text-green-600 font-semibold">{b.entradas}</td>
                          <td className="py-2 px-3 text-center text-red-500 font-semibold">{b.salidas}</td>
                          <td className={`py-2 px-3 text-center font-semibold ${b.stock_actual === 0 ? 'text-red-400' : b.stock_actual < 5 ? 'text-amber-500' : 'text-gray-800'}`}>{b.stock_actual}</td>
                          <td className="py-2 pl-3 text-right text-gray-700">${(b.valor_inventario || 0).toLocaleString('es-CO')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
              <p className="text-xs text-gray-400">Ordenado por más vendidas. El balance sale del kardex (libro de movimientos), así siempre cuadra.</p>
            </>
          )}
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
              {(newStock.modo || 'entrada') === 'entrada' ? 'Registrar entrada' : 'Ajustar stock'} — {colegioSel.nombre}
            </h3>
            <form onSubmit={agregarStock} className="space-y-4">
              <div className="grid grid-cols-2 gap-2">
                <button type="button"
                  onClick={() => setNewStock({ ...newStock, modo: 'entrada' })}
                  className={`py-2 rounded-lg text-sm font-medium border ${(newStock.modo || 'entrada') === 'entrada' ? 'bg-green-600 text-white border-green-600' : 'bg-white text-gray-600 border-gray-300'}`}>
                  📥 Entrada (suma)
                </button>
                <button type="button"
                  onClick={() => setNewStock({ ...newStock, modo: 'ajuste' })}
                  className={`py-2 rounded-lg text-sm font-medium border ${newStock.modo === 'ajuste' ? 'bg-orange-500 text-white border-orange-500' : 'bg-white text-gray-600 border-gray-300'}`}>
                  ✏️ Ajuste (fija)
                </button>
              </div>
              <p className="text-xs text-gray-500 -mt-2">
                {(newStock.modo || 'entrada') === 'entrada'
                  ? 'Llegó mercancía: se SUMA a lo que ya hay.'
                  : 'Corrección: fija el stock en el valor exacto que escribas.'}
              </p>
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
                {esMedias(prodSeleccionado?.tipo) && (
                  <p className="text-xs text-purple-600 mt-1">Tallas de medias</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  {(newStock.modo || 'entrada') === 'entrada' ? '¿Cuántas llegaron? *' : 'Cantidad exacta *'}
                </label>
                <input type="number" required min={(newStock.modo || 'entrada') === 'entrada' ? '1' : '0'} value={newStock.cantidad}
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
                  onClick={() => { setShowAdd(false); setNewStock({ producto_id: '', talla: '', cantidad: '', observaciones: '', modo: 'entrada' }) }}
                  className="btn-secondary">Cancelar</button>
                <button type="submit" className="btn-primary">
                  {(newStock.modo || 'entrada') === 'entrada' ? 'Registrar entrada' : 'Guardar ajuste'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
