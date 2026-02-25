import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function Ventas() {
  const [reporte, setReporte] = useState(null)
  const [fechaDesde, setFechaDesde] = useState(new Date().toISOString().slice(0, 8) + '01')
  const [fechaHasta, setFechaHasta] = useState(new Date().toISOString().split('T')[0])
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadReporte() }, [])

  const loadReporte = async () => {
    setLoading(true)
    try {
      const res = await api.get('/reportes/ventas', { params: { fecha_desde: fechaDesde, fecha_hasta: fechaHasta } })
      setReporte(res.data)
    } catch {
      toast.error('Error cargando reporte')
    } finally {
      setLoading(false)
    }
  }

  const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Hoja de Ventas</h2>

      <div className="flex gap-3 items-end">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Desde</label>
          <input type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} className="input-field" />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Hasta</label>
          <input type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} className="input-field" />
        </div>
        <button onClick={loadReporte} disabled={loading} className="btn-primary">Consultar</button>
      </div>

      {reporte && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card"><p className="text-sm text-gray-500">Facturas</p><p className="text-2xl font-bold">{reporte.resumen.total_facturas}</p></div>
            <div className="card"><p className="text-sm text-gray-500">Ventas</p><p className="text-2xl font-bold text-green-600">{fmt(reporte.resumen.total_ventas)}</p></div>
            <div className="card"><p className="text-sm text-gray-500">Cobrado</p><p className="text-2xl font-bold text-blue-600">{fmt(reporte.resumen.total_cobrado)}</p></div>
            <div className="card"><p className="text-sm text-gray-500">Utilidad</p><p className="text-2xl font-bold text-purple-600">{fmt(reporte.resumen.utilidad_neta)}</p></div>
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Ventas Diarias</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={reporte.ventas_diarias}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="fecha" tick={{ fontSize: 10 }} />
                  <YAxis tickFormatter={v => `$${(v/1000).toFixed(0)}k`} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(v) => [fmt(v), 'Ventas']} />
                  <Bar dataKey="total" fill="#22c55e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
