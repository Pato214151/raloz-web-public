import { useState, useEffect } from 'react'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import { DollarSign, FileText, CreditCard, Clock, TrendingUp, AlertCircle } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

function KPICard({ icon: Icon, label, value, sub, color = 'blue' }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
  }

  return (
    <div className="card flex items-center gap-4">
      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colors[color]}`}>
        <Icon size={24} />
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {sub && <p className="text-xs text-gray-400">{sub}</p>}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { usuario } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    try {
      const res = await api.get('/dashboard/resumen')
      setData(res.data)
    } catch (err) {
      console.error('Error cargando dashboard:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatMoney = (n) => {
    if (n === undefined || n === null) return '$0'
    return '$' + Math.round(n).toLocaleString('es-CO')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-raloz-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">
          Hola, {usuario?.usuario}
        </h2>
        <p className="text-gray-500 text-sm">Resumen del negocio</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          icon={DollarSign}
          label="Ventas Hoy"
          value={formatMoney(data?.ventas_hoy?.total)}
          sub={`${data?.ventas_hoy?.facturas || 0} facturas`}
          color="green"
        />
        <KPICard
          icon={TrendingUp}
          label="Ventas del Mes"
          value={formatMoney(data?.ventas_mes?.total)}
          sub={`${data?.ventas_mes?.facturas || 0} facturas`}
          color="blue"
        />
        <KPICard
          icon={CreditCard}
          label="Cobros Hoy"
          value={formatMoney(data?.cobros_hoy)}
          color="purple"
        />
        <KPICard
          icon={AlertCircle}
          label="Por Cobrar"
          value={formatMoney(data?.total_por_cobrar)}
          sub={`${data?.pendientes_entrega || 0} pendientes entrega`}
          color="red"
        />
      </div>

      {/* Gráfica de ventas 7 días */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Ventas - Últimos 7 días</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data?.ventas_7_dias || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="dia" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} tick={{ fontSize: 12 }} />
              <Tooltip
                formatter={(value) => [formatMoney(value), 'Ventas']}
                contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
              />
              <Bar dataKey="total" fill="#3b52ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Resumen financiero mes */}
      {(() => {
        const cobros = data?.cobros_mes || 0
        const gastos = data?.gastos_mes || 0
        const utilidad = cobros - gastos
        const margen = cobros > 0 ? ((utilidad / cobros) * 100).toFixed(1) : null
        const utilPositiva = utilidad >= 0
        return (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card">
              <p className="text-sm text-gray-500">Cobrado este mes</p>
              <p className="text-xl font-bold text-green-600">{formatMoney(cobros)}</p>
            </div>
            <div className="card">
              <p className="text-sm text-gray-500">Gastos este mes</p>
              <p className="text-xl font-bold text-red-600">{formatMoney(gastos)}</p>
              {cobros > 0 && (
                <p className="text-xs text-gray-400 mt-1">
                  {((gastos / cobros) * 100).toFixed(1)}% de lo cobrado
                </p>
              )}
            </div>
            <div className={`card border-l-4 ${utilPositiva ? 'border-green-400' : 'border-red-400'}`}>
              <p className="text-sm text-gray-500">Utilidad neta</p>
              <p className={`text-xl font-bold ${utilPositiva ? 'text-green-600' : 'text-red-600'}`}>
                {utilPositiva ? '' : '−'}{formatMoney(Math.abs(utilidad))}
              </p>
              {margen !== null && (
                <p className={`text-xs mt-1 font-medium ${utilPositiva ? 'text-green-500' : 'text-red-500'}`}>
                  Margen: {utilPositiva ? '' : '-'}{Math.abs(parseFloat(margen))}%
                </p>
              )}
            </div>
          </div>
        )
      })()}
    </div>
  )
}
