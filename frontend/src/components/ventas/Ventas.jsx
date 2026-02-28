import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Calendar, DollarSign, TrendingUp, TrendingDown, CreditCard, Filter } from 'lucide-react'

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

      {/* Quick Filters */}
      <div className="flex flex-wrap gap-2">
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
