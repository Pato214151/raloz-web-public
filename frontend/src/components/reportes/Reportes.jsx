/**
 * Reportes: ventas por período, productos más vendidos, cuentas y balance
 * (ventas contra gastos), con impresión.
 */

import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { Printer, Download, FileSpreadsheet } from 'lucide-react'

const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16']
const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

export default function Reportes() {
  const [tab, setTab] = useState('balance')
  const [reporte, setReporte] = useState(null)
  const [topProductos, setTopProductos] = useState([])
  const [gastosCat, setGastosCat] = useState([])
  const [totalGastos, setTotalGastos] = useState(0)
  const [cuentas, setCuentas] = useState(null)
  const [fechaDesde, setFechaDesde] = useState(new Date().toISOString().slice(0, 8) + '01')
  const [fechaHasta, setFechaHasta] = useState(new Date().toISOString().split('T')[0])
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [ventasRes, prodRes, gastosRes, cuentasRes] = await Promise.all([
        api.get('/reportes/ventas', { params: { fecha_desde: fechaDesde, fecha_hasta: fechaHasta } }),
        api.get('/reportes/productos-mas-vendidos', { params: { limite: 10 } }),
        api.get('/gastos', { params: { fecha_desde: fechaDesde, fecha_hasta: fechaHasta, per_page: 500 } }),
        api.get('/reportes/cuentas', { params: { fecha_desde: fechaDesde, fecha_hasta: fechaHasta } }),
      ])
      setReporte(ventasRes.data)
      setTopProductos(prodRes.data.productos || [])
      setCuentas(cuentasRes.data)

      // Agrupar gastos por categoría
      const gastos = gastosRes.data.gastos || []
      const catMap = {}
      gastos.forEach(g => {
        const cat = g.categoria || 'Otros'
        catMap[cat] = (catMap[cat] || 0) + (g.valor || 0)
      })
      const catArr = Object.entries(catMap)
        .map(([categoria, total]) => ({ categoria, total }))
        .sort((a, b) => b.total - a.total)
      setGastosCat(catArr)
      setTotalGastos(gastos.reduce((s, g) => s + (g.valor || 0), 0))
    } catch {
      toast.error('Error cargando reportes')
    } finally {
      setLoading(false)
    }
  }

  const imprimirReporteVentas = () => {
    if (!reporte) return
    const w = window.open('', '_blank')
    const dailyRows = (reporte.ventas_diarias || []).map(d =>
      `<tr><td>${d.fecha}</td><td style="text-align:right;font-weight:bold">${fmt(d.total)}</td><td style="text-align:center">${d.cantidad || ''}</td></tr>`
    ).join('')

    w.document.write(`<!DOCTYPE html><html><head><title>Reporte de Ventas</title>
      <style>body{font-family:Arial;margin:20px}h2{color:#1976D2;border-bottom:3px solid #FFC107;padding-bottom:8px}
      table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}
      th{background:#f5f5f5;padding:6px;border:1px solid #ddd;text-align:left}
      td{padding:5px 8px;border:1px solid #eee}
      .kpi{display:inline-block;padding:12px 20px;margin:5px;border-radius:8px;text-align:center;min-width:120px}
      @media print{body{margin:10px}}</style></head><body>
      <h2>RALOZ COL SAS - Reporte de Ventas</h2>
      <p>Período: ${fechaDesde} a ${fechaHasta}</p>
      <div>
        <div class="kpi" style="background:#D4EDDA;color:#155724"><small>Facturas</small><br><b style="font-size:20px">${reporte.resumen?.total_facturas || 0}</b></div>
        <div class="kpi" style="background:#D4EDDA;color:#155724"><small>Ventas</small><br><b style="font-size:20px">${fmt(reporte.resumen?.total_ventas)}</b></div>
        <div class="kpi" style="background:#D1ECF1;color:#0C5460"><small>Cobrado</small><br><b style="font-size:20px">${fmt(reporte.resumen?.total_cobrado)}</b></div>
        <div class="kpi" style="background:#F8D7DA;color:#721C24"><small>Gastos</small><br><b style="font-size:20px">${fmt(reporte.resumen?.total_gastos)}</b></div>
        <div class="kpi" style="background:#E8D5F5;color:#4A1A6B"><small>Utilidad</small><br><b style="font-size:20px">${fmt(reporte.resumen?.utilidad_neta)}</b></div>
      </div>
      <h3>Ventas Diarias</h3>
      <table><thead><tr><th>Fecha</th><th style="text-align:right">Total</th><th style="text-align:center">Facturas</th></tr></thead>
      <tbody>${dailyRows}</tbody></table>
      <hr><p style="text-align:center;font-size:11px;color:#999">RALOZ COL SAS</p></body></html>`)
    w.document.close()
    w.print()
  }

  const imprimirReporteProductos = () => {
    if (!topProductos.length) return
    const w = window.open('', '_blank')
    const rows = topProductos.map((p, i) =>
      `<tr><td>${i + 1}</td><td>${p.nombre}</td><td style="text-align:right">${p.total_vendido}</td><td style="text-align:right;font-weight:bold;color:green">${fmt(p.total_ingresos)}</td></tr>`
    ).join('')

    w.document.write(`<!DOCTYPE html><html><head><title>Top Productos</title>
      <style>body{font-family:Arial;margin:20px}h2{color:#1976D2;border-bottom:3px solid #FFC107;padding-bottom:8px}
      table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}
      th{background:#f5f5f5;padding:6px;border:1px solid #ddd;text-align:left}
      td{padding:5px 8px;border:1px solid #eee}
      @media print{body{margin:10px}}</style></head><body>
      <h2>RALOZ COL SAS - Top Productos Más Vendidos</h2>
      <table><thead><tr><th>#</th><th>Producto</th><th style="text-align:right">Unidades</th><th style="text-align:right">Ingresos</th></tr></thead>
      <tbody>${rows}</tbody></table>
      <hr><p style="text-align:center;font-size:11px;color:#999">RALOZ COL SAS</p></body></html>`)
    w.document.close()
    w.print()
  }

  const exportarCSV = () => {
    if (!reporte?.ventas_diarias?.length) return
    let csv = 'Fecha,Total,Facturas\n'
    reporte.ventas_diarias.forEach(d => {
      csv += `${d.fecha},${d.total},${d.cantidad || ''}\n`
    })
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `reporte_ventas_${fechaDesde}_${fechaHasta}.csv`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('CSV descargado')
  }

  const exportarContadora = async () => {
    try {
      const res = await api.get('/reportes/contadora', {
        params: { desde: fechaDesde, hasta: fechaHasta },
        responseType: 'blob',
      })
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `ventas_iva_${fechaDesde}_a_${fechaHasta}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      toast.success('Reporte para contadora descargado')
    } catch {
      toast.error('Error generando el reporte')
    }
  }

  const imprimirBalance = () => {
    if (!cuentas) return
    const r = cuentas.resumen || {}
    const cpp = cuentas.cuentas_por_pagar || {}
    const colRows = (cuentas.por_colegio || []).map(c =>
      `<tr><td>${c.colegio_nombre || '—'}</td>
        <td style="text-align:right">${fmt(c.ingresos)}</td>
        <td style="text-align:right">${fmt(c.cobrado)}</td>
        <td style="text-align:right;color:#b45309">${fmt(c.pendiente)}</td>
        <td style="text-align:right;font-weight:bold;color:#6b21a8">${fmt(c.utilidad)}</td></tr>`
    ).join('')
    const deudaRows = (cpp.detalle || []).map(d =>
      `<tr><td>${d.fecha || ''}</td><td>${d.descripcion || ''}</td><td>${d.categoria || ''}</td>
        <td style="text-align:right;color:#7e22ce;font-weight:bold">${fmt(d.valor)}</td></tr>`
    ).join('')
    const w = window.open('', '_blank')
    w.document.write(`<!DOCTYPE html><html><head><title>Balance ${cuentas.fecha_desde} a ${cuentas.fecha_hasta}</title>
      <style>
        body{font-family:Arial;margin:24px;color:#222}
        h1{color:#1e3a8a;font-size:22px;margin-bottom:2px}
        .sub{color:#666;font-size:13px;margin-bottom:18px}
        .kpis{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px}
        .kpi{flex:1;min-width:130px;padding:14px;border-radius:10px;text-align:center}
        .kpi small{font-size:11px;text-transform:uppercase;letter-spacing:.5px}
        .kpi b{display:block;font-size:20px;margin-top:4px}
        table{width:100%;border-collapse:collapse;margin:8px 0 20px;font-size:13px}
        th{background:#1e3a8a;color:#fff;padding:8px;text-align:left;font-size:12px}
        td{padding:6px 8px;border-bottom:1px solid #eee}
        h3{color:#1e3a8a;font-size:15px;margin:16px 0 6px}
        @media print{body{margin:12px}}
      </style></head><body>
      <h1>RALOZ COL SAS — Balance del periodo</h1>
      <div class="sub">${cuentas.fecha_desde} a ${cuentas.fecha_hasta} · generado ${new Date().toLocaleString('es-CO')}</div>
      <div class="kpis">
        <div class="kpi" style="background:#dcfce7;color:#166534"><small>Ingresos (ventas)</small><b>${fmt(r.total_ingresos)}</b></div>
        <div class="kpi" style="background:#fee2e2;color:#991b1b"><small>Gastos pagados</small><b>${fmt(r.total_gastos)}</b></div>
        <div class="kpi" style="background:#ede9fe;color:#5b21b6"><small>Utilidad</small><b>${fmt(r.utilidad_neta)}</b></div>
        <div class="kpi" style="background:#fef9c3;color:#854d0e"><small>Por cobrar</small><b>${fmt(r.total_pendiente)}</b></div>
        <div class="kpi" style="background:#f3e8ff;color:#7e22ce"><small>Por pagar (deudas)</small><b>${fmt(cpp.total)}</b></div>
      </div>
      <h3>Por colegio</h3>
      <table><thead><tr><th>Colegio</th><th style="text-align:right">Ventas</th><th style="text-align:right">Cobrado</th><th style="text-align:right">Por cobrar</th><th style="text-align:right">Utilidad</th></tr></thead>
      <tbody>${colRows || '<tr><td colspan=5 style="text-align:center;color:#999">Sin datos</td></tr>'}</tbody></table>
      ${deudaRows ? `<h3>Cuentas por pagar (deudas pendientes)</h3>
      <table><thead><tr><th>Fecha</th><th>Concepto</th><th>Categoría</th><th style="text-align:right">Valor</th></tr></thead>
      <tbody>${deudaRows}</tbody></table>` : ''}
      <hr><p style="text-align:center;font-size:11px;color:#999">RALOZ COL SAS</p>
      <script>window.onload=function(){window.print()}<\/script>
      </body></html>`)
    w.document.close()
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Reportes</h2>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {[
          { id: 'balance', label: 'Balance del mes' },
          { id: 'ventas', label: 'Ventas' },
          { id: 'gastos', label: 'Gastos' },
          { id: 'productos', label: 'Top Productos' },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t.id ? 'bg-white shadow text-raloz-700' : 'text-gray-500 hover:text-gray-700'
            }`}>{t.label}</button>
        ))}
      </div>

      {/* Balance del mes */}
      {tab === 'balance' && (
        <div className="space-y-4">
          <div className="flex gap-3 items-end flex-wrap">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Desde</label>
              <input type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Hasta</label>
              <input type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} className="input-field" />
            </div>
            <button onClick={loadData} disabled={loading} className="btn-primary">Consultar</button>
            <button onClick={imprimirBalance} className="btn-secondary flex items-center gap-1"><Printer size={16} /> Imprimir balance (PDF)</button>
            <button onClick={exportarContadora} className="btn-primary flex items-center gap-1 bg-emerald-600 hover:bg-emerald-700"><FileSpreadsheet size={16} /> Excel para contadora</button>
          </div>
          <p className="text-xs text-gray-400 -mt-2">Resumen del periodo para presentar a la gerencia: lo que entró, lo que salió, la utilidad, lo que te deben y lo que la empresa debe.</p>

          {cuentas && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="card text-center"><p className="text-xs text-gray-500">Ingresos (ventas)</p><p className="text-2xl font-bold text-green-600">{fmt(cuentas.resumen?.total_ingresos)}</p></div>
                <div className="card text-center"><p className="text-xs text-gray-500">Gastos pagados</p><p className="text-2xl font-bold text-red-600">{fmt(cuentas.resumen?.total_gastos)}</p></div>
                <div className="card text-center border-2 border-purple-200"><p className="text-xs text-purple-600 font-semibold">Utilidad</p><p className="text-2xl font-bold text-purple-700">{fmt(cuentas.resumen?.utilidad_neta)}</p></div>
                <div className="card text-center"><p className="text-xs text-gray-500">Por cobrar</p><p className="text-2xl font-bold text-amber-600">{fmt(cuentas.resumen?.total_pendiente)}</p></div>
                <div className="card text-center"><p className="text-xs text-gray-500">Por pagar (deudas)</p><p className="text-2xl font-bold text-fuchsia-700">{fmt(cuentas.cuentas_por_pagar?.total)}</p></div>
              </div>

              <div className="card">
                <h3 className="text-lg font-semibold mb-3">Por colegio</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead><tr className="border-b bg-gray-50">
                      <th className="px-3 py-2 text-left font-medium text-gray-600">Colegio</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">Ventas</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">Cobrado</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">Por cobrar</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">Utilidad</th>
                    </tr></thead>
                    <tbody>
                      {(cuentas.por_colegio || []).map((c) => (
                        <tr key={c.id_colegio} className="border-b border-gray-50">
                          <td className="px-3 py-2 font-medium">{c.colegio_nombre || '—'}</td>
                          <td className="px-3 py-2 text-right text-green-600">{fmt(c.ingresos)}</td>
                          <td className="px-3 py-2 text-right text-blue-600">{fmt(c.cobrado)}</td>
                          <td className="px-3 py-2 text-right text-amber-600">{fmt(c.pendiente)}</td>
                          <td className="px-3 py-2 text-right font-bold text-purple-700">{fmt(c.utilidad)}</td>
                        </tr>
                      ))}
                      {(!cuentas.por_colegio || cuentas.por_colegio.length === 0) && (
                        <tr><td colSpan={5} className="px-3 py-6 text-center text-gray-400">Sin ventas en el período</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {cuentas.cuentas_por_pagar?.cantidad > 0 && (
                <div className="card">
                  <h3 className="text-lg font-semibold mb-3 text-fuchsia-700">Cuentas por pagar (deudas pendientes)</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead><tr className="border-b bg-gray-50">
                        <th className="px-3 py-2 text-left font-medium text-gray-600">Fecha</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-600">Concepto</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-600">Categoría</th>
                        <th className="px-3 py-2 text-right font-medium text-gray-600">Valor</th>
                      </tr></thead>
                      <tbody>
                        {cuentas.cuentas_por_pagar.detalle.map((d, i) => (
                          <tr key={i} className="border-b border-gray-50">
                            <td className="px-3 py-2">{d.fecha || '—'}</td>
                            <td className="px-3 py-2 font-medium">{d.descripcion}</td>
                            <td className="px-3 py-2 text-gray-500">{d.categoria || '—'}</td>
                            <td className="px-3 py-2 text-right font-bold text-fuchsia-700">{fmt(d.valor)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Ventas */}
      {tab === 'ventas' && (
        <div className="space-y-4">
          <div className="flex gap-3 items-end flex-wrap">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Desde</label>
              <input type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Hasta</label>
              <input type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} className="input-field" />
            </div>
            <button onClick={loadData} disabled={loading} className="btn-primary">Consultar</button>
            <button onClick={imprimirReporteVentas} className="btn-secondary flex items-center gap-1">
              <Printer size={16} /> Imprimir
            </button>
            <button onClick={exportarCSV} className="btn-secondary flex items-center gap-1">
              <Download size={16} /> CSV
            </button>
            <button onClick={exportarContadora} className="btn-primary flex items-center gap-1 bg-emerald-600 hover:bg-emerald-700">
              <FileSpreadsheet size={16} /> Para contadora (Excel + IVA)
            </button>
          </div>
          <p className="text-xs text-gray-400 -mt-2">
            "Para contadora": Excel del periodo con cliente, NIT, cómo pagó y el IVA (19%) desglosado, listo para enviarle.
          </p>

          {reporte && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="card"><p className="text-sm text-gray-500">Facturas</p><p className="text-2xl font-bold">{reporte.resumen?.total_facturas || 0}</p></div>
                <div className="card"><p className="text-sm text-gray-500">Ventas</p><p className="text-2xl font-bold text-green-600">{fmt(reporte.resumen?.total_ventas)}</p></div>
                <div className="card"><p className="text-sm text-gray-500">Cobrado</p><p className="text-2xl font-bold text-blue-600">{fmt(reporte.resumen?.total_cobrado)}</p></div>
                <div className="card"><p className="text-sm text-gray-500">Gastos</p><p className="text-2xl font-bold text-red-600">{fmt(reporte.resumen?.total_gastos)}</p></div>
                <div className="card"><p className="text-sm text-gray-500">Utilidad</p><p className="text-2xl font-bold text-purple-600">{fmt(reporte.resumen?.utilidad_neta)}</p></div>
              </div>

              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Ventas Diarias</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={reporte.ventas_diarias}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="fecha" tick={{ fontSize: 10 }} />
                      <YAxis tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 10 }} />
                      <Tooltip formatter={(v) => [fmt(v), 'Ventas']} />
                      <Bar dataKey="total" fill="#22c55e" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Tabla detallada */}
              {reporte.ventas_diarias && reporte.ventas_diarias.length > 0 && (
                <div className="card">
                  <h3 className="text-lg font-semibold mb-4">Detalle Diario</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-gray-50">
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Fecha</th>
                          <th className="px-4 py-2 text-right font-medium text-gray-600">Total Ventas</th>
                          <th className="px-4 py-2 text-center font-medium text-gray-600">Facturas</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reporte.ventas_diarias.map((d, i) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                            <td className="px-4 py-2 font-medium">{d.fecha}</td>
                            <td className="px-4 py-2 text-right font-bold text-green-600">{fmt(d.total)}</td>
                            <td className="px-4 py-2 text-center">{d.cantidad || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Gastos por Categoría */}
      {tab === 'gastos' && (
        <div className="space-y-4">
          <div className="flex gap-3 items-end flex-wrap">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Desde</label>
              <input type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Hasta</label>
              <input type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} className="input-field" />
            </div>
            <button onClick={loadData} disabled={loading} className="btn-primary">Consultar</button>
          </div>

          <div className="card">
            <p className="text-sm text-gray-500">Total Gastos en el período</p>
            <p className="text-3xl font-bold text-red-600">{fmt(totalGastos)}</p>
          </div>

          {gastosCat.length > 0 ? (
            <>
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Distribución por Categoría</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={gastosCat} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis type="number" tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 10 }} />
                      <YAxis type="category" dataKey="categoria" tick={{ fontSize: 11 }} width={130} />
                      <Tooltip formatter={v => [fmt(v), 'Total']} />
                      <Bar dataKey="total" fill="#ef4444" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Detalle</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-gray-200">
                      <th className="text-left py-3 px-2">Categoría</th>
                      <th className="text-right py-3 px-2">Total</th>
                      <th className="text-right py-3 px-2">% del total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gastosCat.map((g, i) => (
                      <tr key={g.categoria} className="border-b border-gray-100">
                        <td className="py-2 px-2 font-medium">
                          <span className="inline-block w-3 h-3 rounded-full mr-2" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                          {g.categoria}
                        </td>
                        <td className="py-2 px-2 text-right font-semibold text-red-600">{fmt(g.total)}</td>
                        <td className="py-2 px-2 text-right text-gray-500">
                          {totalGastos > 0 ? ((g.total / totalGastos) * 100).toFixed(1) + '%' : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {gastosCat.some(g => g.categoria === 'Otros') && (
                  <p className="mt-3 text-xs text-amber-600 bg-amber-50 p-2 rounded">
                    ⚠️ Hay gastos en "Otros" — considera reclasificarlos para un mejor análisis contable.
                  </p>
                )}
              </div>
            </>
          ) : (
            <div className="card text-center py-12 text-gray-400">No hay gastos en el período seleccionado.</div>
          )}
        </div>
      )}

      {/* Top Productos */}
      {tab === 'productos' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button onClick={imprimirReporteProductos} className="btn-secondary flex items-center gap-1">
              <Printer size={16} /> Imprimir
            </button>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Top 10 Productos Más Vendidos</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topProductos} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis type="number" tick={{ fontSize: 10 }} />
                    <YAxis type="category" dataKey="nombre" tick={{ fontSize: 10 }} width={140} />
                    <Tooltip formatter={(v, name) => [name === 'total_vendido' ? `${v} uds` : fmt(v), name === 'total_vendido' ? 'Cantidad' : 'Ingresos']} />
                    <Bar dataKey="total_vendido" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Ingresos por Producto</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={topProductos} dataKey="total_ingresos" nameKey="nombre" cx="50%" cy="50%" outerRadius={100}
                      label={({ nombre, percent }) => `${nombre?.slice(0, 12)} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                      {topProductos.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(v) => fmt(v)} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Detalle</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-gray-200">
                  <th className="text-left py-3 px-2">#</th>
                  <th className="text-left py-3 px-2">Producto</th>
                  <th className="text-right py-3 px-2">Unidades</th>
                  <th className="text-right py-3 px-2">Ingresos</th>
                </tr>
              </thead>
              <tbody>
                {topProductos.map((p, i) => (
                  <tr key={p.id_producto} className="border-b border-gray-100">
                    <td className="py-2 px-2 text-gray-400">{i + 1}</td>
                    <td className="py-2 px-2 font-medium">{p.nombre}</td>
                    <td className="py-2 px-2 text-right">{p.total_vendido}</td>
                    <td className="py-2 px-2 text-right font-medium text-green-600">{fmt(p.total_ingresos)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
