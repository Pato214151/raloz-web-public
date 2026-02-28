import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16']

export default function Reportes() {
  const [tab, setTab] = useState('ventas')
  const [reporte, setReporte] = useState(null)
  const [topProductos, setTopProductos] = useState([])
  const [fechaDesde, setFechaDesde] = useState(new Date().toISOString().slice(0, 8) + '01')
  const [fechaHasta, setFechaHasta] = useState(new Date().toISOString().split('T')[0])
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [ventasRes, prodRes] = await Promise.all([
        api.get('/reportes/ventas', { params: { fecha_desde: fechaDesde, fecha_hasta: fechaHasta } }),
        api.get('/reportes/productos-mas-vendidos', { params: { limite: 10 } }),
      ])
      setReporte(ventasRes.data)
      setTopProductos(prodRes.data.productos || [])
    } catch {
      toast.error('Error cargando reportes')
    } finally {
      setLoading(false)
    }
  }

  const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Reportes</h2>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {[
          { id: 'ventas', label: 'Ventas' },
          { id: 'productos', label: 'Top Productos' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t.id ? 'bg-white shadow text-raloz-700' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

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
          </div>

          {reporte && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="card"><p className="text-sm text-gray-500">Facturas</p><p className="text-2xl font-bold">{reporte.resumen.total_facturas}</p></div>
                <div className="card"><p className="text-sm text-gray-500">Ventas</p><p className="text-2xl font-bold text-green-600">{fmt(reporte.resumen.total_ventas)}</p></div>
                <div className="card"><p className="text-sm text-gray-500">Cobrado</p><p className="text-2xl font-bold text-blue-600">{fmt(reporte.resumen.total_cobrado)}</p></div>
                <div className="card"><p className="text-sm text-gray-500">Gastos</p><p className="text-2xl font-bold text-red-600">{fmt(reporte.resumen.total_gastos)}</p></div>
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
      )}

      {/* Top Productos */}
      {tab === 'productos' && (
        <div className="space-y-4">
          <div className="grid md:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Top 10 Productos Mas Vendidos</h3>
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
                    <Pie
                      data={topProductos}
                      dataKey="total_ingresos"
                      nameKey="nombre"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={({ nombre, percent }) => `${nombre?.slice(0, 12)} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {topProductos.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
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
