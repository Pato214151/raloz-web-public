import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Package, Plus, X, Printer, AlertTriangle } from 'lucide-react'

const TALLAS_ORDEN = ['2', '4', '6', '8', '10', '12', '14', '16', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'Única']

function tallaCaja(cantidad) {
  if (cantidad === 0) return 'bg-red-100 border-red-300 text-red-700'
  if (cantidad < 5) return 'bg-amber-100 border-amber-300 text-amber-700'
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

export default function StockView() {
  const [colegioSel, setColegioSel] = useState(null)
  const [colegios, setColegios] = useState([])   // TODOS los colegios
  const [resumen, setResumen] = useState([])      // solo los que tienen stock
  const [stock, setStock] = useState([])
  const [productos, setProductos] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingStock, setLoadingStock] = useState(false)

  // Edición inline de talla
  const [editKey, setEditKey] = useState(null) // key = id_stock
  const [editVal, setEditVal] = useState('')

  // Modal agregar
  const [showAdd, setShowAdd] = useState(false)
  const [newStock, setNewStock] = useState({ producto_id: '', talla: '', cantidad: '' })

  useEffect(() => {
    cargarInicial()
  }, [])

  useEffect(() => {
    if (colegioSel) cargarStock(colegioSel.id_colegio)
  }, [colegioSel])

  async function cargarInicial() {
    try {
      const [resRes, prodRes, colRes] = await Promise.all([
        api.get('/stock/resumen'),
        api.get('/productos'),
        api.get('/colegios'),
      ])
      const res = resRes.data.resumen || []
      const cols = colRes.data.colegios || []
      setResumen(res)
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

  async function guardarEdicion(id_stock) {
    const val = parseInt(editVal)
    if (isNaN(val) || val < 0) { toast.error('Cantidad inválida'); return }
    try {
      await api.put(`/stock/${id_stock}`, { cantidad: val })
      setStock(prev => prev.map(s => s.id_stock === id_stock ? { ...s, cantidad: val } : s))
      // Refresh resumen
      const r = await api.get('/stock/resumen')
      setResumen(r.data.resumen || [])
      setEditKey(null)
    } catch (e) {
      toast.error(e.response?.data?.error || 'Error')
    }
  }

  async function eliminar(id_stock) {
    if (!confirm('¿Eliminar este ítem de stock?')) return
    try {
      await api.delete(`/stock/${id_stock}`)
      setStock(prev => prev.filter(s => s.id_stock !== id_stock))
      const r = await api.get('/stock/resumen')
      setResumen(r.data.resumen || [])
    } catch (e) {
      toast.error(e.response?.data?.error || 'Error')
    }
  }

  async function agregarStock(e) {
    e.preventDefault()
    if (!newStock.producto_id || !newStock.talla || !newStock.cantidad) {
      toast.error('Completa todos los campos'); return
    }
    try {
      await api.post('/stock', {
        id_colegio: colegioSel.id_colegio,
        id_producto: newStock.producto_id,
        talla_individual: newStock.talla.trim(),
        cantidad: parseInt(newStock.cantidad)
      })
      toast.success('Stock agregado')
      setShowAdd(false)
      setNewStock({ producto_id: '', talla: '', cantidad: '' })
      cargarStock(colegioSel.id_colegio)
      const r = await api.get('/stock/resumen')
      setResumen(r.data.resumen || [])
    } catch (e) {
      toast.error(e.response?.data?.error || 'Error')
    }
  }

  // Agrupar stock por producto
  const porProducto = {}
  stock.forEach(s => {
    const nombre = s.producto_nombre || `Producto ${s.id_producto}`
    if (!porProducto[nombre]) porProducto[nombre] = []
    porProducto[nombre].push(s)
  })
  // Ordenar tallas dentro de cada producto
  Object.values(porProducto).forEach(arr =>
    arr.sort((a, b) => sortTallas(a.talla_individual, b.talla_individual))
  )

  const totalUnidades = stock.reduce((s, x) => s + x.cantidad, 0)
  const bajoStock = stock.filter(s => s.cantidad > 0 && s.cantidad < 5).length
  const sinStock = stock.filter(s => s.cantidad === 0).length

  function imprimir() {
    if (!stock.length) return
    const w = window.open('', '_blank')
    const bloques = Object.entries(porProducto).map(([prod, items]) => {
      const filas = items.map(s => {
        const color = s.cantidad === 0 ? '#dc2626' : s.cantidad < 5 ? '#d97706' : '#16a34a'
        return `<td style="padding:6px 10px;border:1px solid #ddd;text-align:center;font-weight:bold;color:${color}">
          <div style="font-size:10px;color:#555">${s.talla_individual}</div>${s.cantidad}</td>`
      }).join('')
      return `<tr><td style="padding:6px 10px;border:1px solid #ddd;font-weight:600">${prod}</td>${filas}</tr>`
    }).join('')
    w.document.write(`<!DOCTYPE html><html><head><title>Inventario - ${colegioSel?.nombre || ''}</title>
      <style>body{font-family:Arial,sans-serif;margin:20px;font-size:13px}
      h2{color:#1976d2}table{border-collapse:collapse;margin-top:10px}
      @media print{.no-print{display:none}}</style></head>
      <body><h2>RALOZ COL SAS — Inventario ${colegioSel?.nombre || ''}</h2>
      <p>Total: <b>${totalUnidades}</b> uds &nbsp; Bajo stock: <b>${bajoStock}</b> &nbsp; Sin stock: <b>${sinStock}</b></p>
      <table><tbody>${bloques}</tbody></table>
      <p style="font-size:10px;color:#999;margin-top:20px">Impreso ${new Date().toLocaleString('es-CO')}</p>
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
    <div className="flex gap-4 h-full" style={{ minHeight: '70vh' }}>
      {/* ─── Panel izquierdo: TODOS los colegios ─── */}
      <div className="w-56 flex-shrink-0 space-y-1">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-2 mb-2">Colegios</p>
        {colegios.length === 0 ? (
          <p className="text-xs text-gray-400 px-2">Sin colegios</p>
        ) : (
          colegios.map(c => {
            const resumenCol = resumen.find(r => r.id_colegio === c.id_colegio)
            const activo = colegioSel?.id_colegio === c.id_colegio
            return (
              <button
                key={c.id_colegio}
                onClick={() => setColegioSel(c)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  activo ? 'bg-raloz-600 text-white' : 'hover:bg-gray-100 text-gray-700'
                }`}
              >
                <p className="font-medium leading-tight">{c.nombre}</p>
                <p className={`text-xs mt-0.5 ${activo ? 'text-raloz-200' : 'text-gray-400'}`}>
                  {resumenCol ? `${resumenCol.total_unidades} uds` : 'Sin stock'}
                </p>
              </button>
            )
          })
        )}
      </div>

      {/* ─── Panel derecho: inventario ─── */}
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
                <h2 className="text-xl font-bold text-gray-900">{colegioSel.nombre || colegioSel.colegio}</h2>
                <p className="text-sm text-gray-500">{totalUnidades} unidades en stock</p>
              </div>
              <div className="flex gap-2">
                <button onClick={imprimir} className="btn-secondary text-sm flex items-center gap-1.5">
                  <Printer size={14} /> Imprimir
                </button>
                <button onClick={() => setShowAdd(true)} className="btn-primary text-sm flex items-center gap-1.5">
                  <Plus size={14} /> Agregar
                </button>
              </div>
            </div>

            {/* Badges resumen */}
            {(bajoStock > 0 || sinStock > 0) && (
              <div className="flex gap-2 flex-wrap">
                {sinStock > 0 && (
                  <span className="flex items-center gap-1 text-xs bg-red-50 text-red-700 border border-red-200 px-2 py-1 rounded-full">
                    <AlertTriangle size={11} /> {sinStock} sin stock
                  </span>
                )}
                {bajoStock > 0 && (
                  <span className="flex items-center gap-1 text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2 py-1 rounded-full">
                    <AlertTriangle size={11} /> {bajoStock} bajo stock
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
                {Object.entries(porProducto).map(([nombreProd, items]) => (
                  <div key={nombreProd} className="card">
                    <div className="flex items-center justify-between mb-3">
                      <p className="font-semibold text-gray-800">{nombreProd}</p>
                      <p className="text-xs text-gray-400">
                        {items.reduce((s, x) => s + x.cantidad, 0)} uds
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {items.map(s => (
                        <div key={s.id_stock} className="relative group">
                          {editKey === s.id_stock ? (
                            <div className="flex flex-col items-center gap-1">
                              <span className="text-xs text-gray-500 font-medium">{s.talla_individual}</span>
                              <input
                                type="number"
                                min="0"
                                value={editVal}
                                onChange={e => setEditVal(e.target.value)}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') guardarEdicion(s.id_stock)
                                  if (e.key === 'Escape') setEditKey(null)
                                }}
                                onBlur={() => guardarEdicion(s.id_stock)}
                                autoFocus
                                className="w-14 text-center border-2 border-raloz-400 rounded-lg text-sm font-bold py-1 focus:outline-none"
                              />
                            </div>
                          ) : (
                            <div
                              onClick={() => { setEditKey(s.id_stock); setEditVal(s.cantidad.toString()) }}
                              title="Clic para editar cantidad"
                              className={`cursor-pointer flex flex-col items-center justify-center w-16 h-16 rounded-xl border-2 font-bold text-sm transition-all hover:scale-105 hover:shadow-sm ${tallaCaja(s.cantidad)}`}
                            >
                              <span className="text-xs font-normal opacity-70">{s.talla_individual}</span>
                              <span className="text-lg leading-tight">{s.cantidad}</span>
                            </div>
                          )}
                          {/* Botón eliminar al hover */}
                          <button
                            onClick={() => eliminar(s.id_stock)}
                            className="absolute -top-1.5 -right-1.5 hidden group-hover:flex items-center justify-center w-4 h-4 bg-red-500 text-white rounded-full text-xs hover:bg-red-600"
                            title="Eliminar"
                          >
                            <X size={9} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* ─── Modal agregar stock ─── */}
      {showAdd && colegioSel && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm">
            <h3 className="text-lg font-bold mb-4">Agregar Stock — {colegioSel.nombre || colegioSel.colegio}</h3>
            <form onSubmit={agregarStock} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Producto *</label>
                <select required value={newStock.producto_id}
                  onChange={e => setNewStock({ ...newStock, producto_id: e.target.value })}
                  className="input-field w-full">
                  <option value="">Seleccionar producto</option>
                  {productos.map(p => (
                    <option key={p.id_producto} value={p.id_producto}>{p.nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Talla *</label>
                <input type="text" required value={newStock.talla}
                  onChange={e => setNewStock({ ...newStock, talla: e.target.value })}
                  className="input-field w-full" placeholder="Ej: 4, 6, S, M, L" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Cantidad *</label>
                <input type="number" required min="0" value={newStock.cantidad}
                  onChange={e => setNewStock({ ...newStock, cantidad: e.target.value })}
                  className="input-field w-full" placeholder="0" />
              </div>
              <div className="flex gap-3 justify-end pt-2 border-t">
                <button type="button" onClick={() => { setShowAdd(false); setNewStock({ producto_id: '', talla: '', cantidad: '' }) }}
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
