import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Calendar, DollarSign, TrendingUp, TrendingDown, CreditCard, Filter, Printer } from 'lucide-react'

/**
 * Hoja de Ventas — Mirrors desktop's ventas_module.py
 * Shows daily income (payments received) and expenses,
 * grouped by payment method for account reconciliation.
 */
export default function Ventas() {
  const [filtro, setFiltro] = useState('hoy')
  const [fechaDesde, setFechaDesde] = useState(new Date().toISOString().split('T')[0])
  const [fechaHasta, setFechaHasta] = useState(new Date().toISOString().split('T')[0])
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => { aplicarFiltro('hoy') }, [])

  const aplicarFiltro = (tipo) => {
    setFiltro(tipo)
    const hoy = new Date()
    let desde, hasta = hoy.toISOString().split('T')[0]

    switch (tipo) {
      case 'hoy':
        desde = hasta
        break
      case 'ayer': {
        const ayer = new Date(hoy)
        ayer.setDate(ayer.getDate() - 1)
        desde = ayer.toISOString().split('T')[0]
        hasta = desde
        break
      }
      case 'semana': {
        const inicio = new Date(hoy)
        inicio.setDate(inicio.getDate() - inicio.getDay())
        desde = inicio.toISOString().split('T')[0]
        break
      }
      case 'mes':
        desde = hoy.toISOString().slice(0, 8) + '01'
        break
      case 'custom':
        return
      default:
        desde = hasta
    }

    setFechaDesde(desde)
    setFechaHasta(hasta)
    loadData(desde, hasta)
  }

  const loadData = async (desde, hasta) => {
    setLoading(true)
    try {
      const res = await api.get('/ventas/hoja', { params: { fecha: desde, fecha_hasta: hasta } })
      setData(res.data)
    } catch {
      toast.error('Error cargando hoja de ventas')
    } finally {
      setLoading(false)
    }
  }

  const handleCustomSearch = () => {
    loadData(fechaDesde, fechaHasta)
  }

  const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

  const filtrosBtns = [
    { key: 'hoy', label: 'Hoy' },
    { key: 'ayer', label: 'Ayer' },
    { key: 'semana', label: 'Esta Semana' },
    { key: 'mes', label: 'Este Mes' },
    { key: 'custom', label: 'Personalizado' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Hoja de Ventas</h2>
        <div className="flex items-center gap-1">
          <Calendar size={16} className="text-gray-400" />
          <span className="text-sm text-gray-500">
            {fechaDesde === fechaHasta ? fechaDesde : `${fechaDesde} a ${fechaHasta}`}
          </span>
        </div>
      </div>

      {/* Quick Filters + Print */}
      <div className="flex flex-wrap gap-2 items-center">
        <button onClick={() => {
          if (!data) return
          const w = window.open('', '_blank')
          const metodos = (data.por_metodo || []).map(m => `<tr><td>${m.metodo}</td><td style="text-align:right;font-weight:bold">${fmt(m.total)}</td><td style="text-align:center">${m.cantidad}</td></tr>`).join('')
          const pagosRows = (data.pagos || []).map(p => `<tr><td>${p.numero_factura}</td><td>${p.cliente_nombre}</td><td>${p.metodo_pago}</td><td style="text-align:right;color:green">${fmt(p.valor)}</td></tr>`).join('')
          const gastosRows = (data.gastos || []).map(g => `<tr><td>${g.fecha}</td><td>${g.descripcion}</td><td>${g.metodo_pago}</td><td style="text-align:right;color:red">${fmt(g.valor)}</td></tr>`).join('')
          const bal = (data.resumen?.total_ingresos || 0) - (data.resumen?.total_gastos || 0)
          w.document.write(`<!DOCTYPE html><html><head><title>Hoja de Ventas</title><style>body{font-family:Arial;margin:20px}h2{color:#1976D2;border-bottom:3px solid #FFC107;padding-bottom:8px}table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}th{background:#f5f5f5;padding:6px;border:1px solid #ddd;text-align:left}td{padding:5px 8px;border:1px solid #eee}.balance{font-size:18px;font-weight:bold;text-align:center;padding:12px;margin:10px 0;border-radius:8px}@media print{body{margin:10px}}</style></head><body>
          <h2>RALOZ COL SAS - Hoja de Ventas</h2><p>Período: ${fechaDesde} ${fechaDesde !== fechaHasta ? 'a ' + fechaHasta : ''}</p>
          <div class="balance" style="background:${bal >= 0 ? '#D4EDDA' : '#F8D7DA'};color:${bal >= 0 ? '#155724' : '#721C24'}">BALANCE: ${fmt(bal)} (Ingresos: ${fmt(data.resumen?.total_ingresos)} - Gastos: ${fmt(data.resumen?.total_gastos)})</div>
          <h3>Resumen por Método</h3><table><thead><tr><th>Método</th><th>Total</th><th>Pagos</th></tr></thead><tbody>${metodos}</tbody></table>
          ${pagosRows ? `<h3>Pagos Recibidos</h3><table><thead><tr><th>Factura</th><th>Cliente</th><th>Método</th><th>Valor</th></tr></thead><tbody>${pagosRows}</tbody></table>` : ''}
          ${gastosRows ? `<h3>Gastos</h3><table><thead><tr><th>Fecha</th><th>Descripción</th><th>Método</th><th>Valor</th></tr></thead><tbody>${gastosRows}</tbody></table>` : ''}
          <hr><p style="text-align:center;font-size:11px;color:#999">RALOZ COL SAS</p></body></html>`)
          w.document.close(); w.print()
        }} className="btn-secondary flex items-center gap-1 ml-auto"><Printer size={16} /> Imprimir</button>
        {filtrosBtns.map(f => (
          <button
            key={f.key}
            onClick={() => aplicarFiltro(f.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filtro === f.key
                ? 'bg-raloz-600 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Custom date range */}
      {filtro === 'custom' && (
        <div className="flex gap-3 items-end bg-white p-4 rounded-lg border border-gray-200">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Desde</label>
            <input type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Hasta</label>
            <input type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} className="input-field" />
          </div>
          <button onClick={handleCustomSearch} disabled={loading} className="btn-primary">
            <Filter size={16} className="inline mr-1" /> Consultar
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-raloz-600"></div>
        </div>
      ) : data ? (
        <>
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp size={16} className="text-green-500" />
                <p className="text-sm text-gray-500">Total Ingresos</p>
              </div>
              <p className="text-2xl font-bold text-green-600">{fmt(data.resumen?.total_ingresos)}</p>
              <p className="text-xs text-gray-400">{data.resumen?.total_pagos || 0} pagos recibidos</p>
            </div>
            <div className="card">
              <div className="flex items-center gap-2 mb-1">
                <TrendingDown size={16} className="text-red-500" />
                <p className="text-sm text-gray-500">Total Gastos</p>
              </div>
              <p className="text-2xl font-bold text-red-600">{fmt(data.resumen?.total_gastos)}</p>
              <p className="text-xs text-gray-400">{data.resumen?.num_gastos || 0} gastos registrados</p>
            </div>
            <div className="card">
              <div className="flex items-center gap-2 mb-1">
                <DollarSign size={16} className="text-blue-500" />
                <p className="text-sm text-gray-500">Utilidad</p>
              </div>
              <p className={`text-2xl font-bold ${(data.resumen?.utilidad || 0) >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                {fmt(data.resumen?.utilidad)}
              </p>
            </div>
            <div className="card">
              <div className="flex items-center gap-2 mb-1">
                <CreditCard size={16} className="text-purple-500" />
                <p className="text-sm text-gray-500">Facturas</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{data.resumen?.total_facturas || 0}</p>
              <p className="text-xs text-gray-400">en este período</p>
            </div>
          </div>

          {/* Income by Payment Method */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Ingresos por Método de Pago</h3>
            {data.por_metodo && data.por_metodo.length > 0 ? (
              <div className="space-y-3">
                {data.por_metodo.map((m, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${
                        m.metodo === 'EFECTIVO' ? 'bg-green-500' :
                        m.metodo === 'NEQUI' ? 'bg-purple-500' :
                        m.metodo === 'DAVIPLATA' ? 'bg-red-500' :
                        m.metodo === 'BANCOLOMBIA' ? 'bg-yellow-500' :
                        'bg-blue-500'
                      }`} />
                      <span className="font-medium text-gray-700">{m.metodo}</span>
                    </div>
                    <div className="text-right">
                      <span className="font-bold text-gray-900">{fmt(m.total)}</span>
                      <span className="text-xs text-gray-400 ml-2">({m.cantidad} pagos)</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 text-center py-4">No hay ingresos en este período</p>
            )}
          </div>

          {/* Payments Detail Table */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Detalle de Pagos Recibidos</h3>
            {data.pagos && data.pagos.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="pb-2 font-medium">Factura</th>
                      <th className="pb-2 font-medium">Cliente</th>
                      <th className="pb-2 font-medium">Método</th>
                      <th className="pb-2 font-medium text-right">Valor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.pagos.map((p, i) => (
                      <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="py-2 font-medium text-raloz-600">{p.numero_factura}</td>
                        <td className="py-2 text-gray-700">{p.cliente_nombre}</td>
                        <td className="py-2">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            p.metodo_pago === 'EFECTIVO' ? 'bg-green-50 text-green-700' :
                            p.metodo_pago === 'NEQUI' ? 'bg-purple-50 text-purple-700' :
                            p.metodo_pago === 'DAVIPLATA' ? 'bg-red-50 text-red-700' :
                            p.metodo_pago === 'BANCOLOMBIA' ? 'bg-yellow-50 text-yellow-700' :
                            'bg-blue-50 text-blue-700'
                          }`}>{p.metodo_pago}</span>
                        </td>
                        <td className="py-2 text-right font-medium text-green-600">{fmt(p.valor)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-400 text-center py-4">No hay pagos en este período</p>
            )}
          </div>

          {/* Expenses Detail Table */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Detalle de Gastos</h3>
            {data.gastos && data.gastos.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="pb-2 font-medium">Fecha</th>
                      <th className="pb-2 font-medium">Descripción</th>
                      <th className="pb-2 font-medium">Método</th>
                      <th className="pb-2 font-medium text-right">Valor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.gastos.map((g, i) => (
                      <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="py-2 text-gray-500">{g.fecha}</td>
                        <td className="py-2 text-gray-700">{g.descripcion}</td>
                        <td className="py-2">
                          <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                            {g.metodo_pago}
                          </span>
                        </td>
                        <td className="py-2 text-right font-medium text-red-600">{fmt(g.valor)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-400 text-center py-4">No hay gastos en este período</p>
            )}
          </div>
        </>
      ) : null}
    </div>
  )
}
