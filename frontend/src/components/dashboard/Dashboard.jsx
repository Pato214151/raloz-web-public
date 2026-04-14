import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import {
  DollarSign, CreditCard, TrendingUp, AlertCircle, ShoppingCart, Scissors,
  RefreshCw, FileText, Search, Package,
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const fmt = (n) => {
  if (n === undefined || n === null) return '$0'
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${Math.round(n / 1_000)}k`
  return '$' + Math.round(n).toLocaleString('es-CO')
}

function KPICard({ icon: Icon, label, value, sub, color = 'blue', onClick }) {
  const colors = {
    blue:   'bg-blue-50   text-blue-600',
    green:  'bg-green-50  text-green-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    red:    'bg-red-50    text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  }
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3 shadow-sm ${onClick ? 'cursor-pointer hover:border-gray-300 hover:shadow transition-all' : ''}`}
    >
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${colors[color]}`}>
        <Icon size={20} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-gray-500 truncate">{label}</p>
        <p className="text-xl font-bold text-gray-900 leading-tight">{value}</p>
        {sub && <p className="text-xs text-gray-400 truncate">{sub}</p>}
      </div>
    </div>
  )
}

const ACCESOS = [
  { label: 'Nueva Venta',     icon: FileText,  path: '/facturacion', color: 'bg-blue-500'   },
  { label: 'Buscar Factura',  icon: Search,    path: '/buscar',      color: 'bg-gray-700'   },
  { label: 'Stock',           icon: Package,   path: '/stock',       color: 'bg-green-600'  },
  { label: 'Fabricación',     icon: Scissors,  path: '/fabricacion', color: 'bg-amber-500'  },
]

export default function Dashboard() {
  const { usuario } = useAuth()
  const navigate = useNavigate()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUp, setLastUp]   = useState(null)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/dashboard/resumen')
      setData(res.data)
      setLastUp(new Date())
    } catch (err) {
      console.error('Error cargando dashboard:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadDashboard() }, [loadDashboard])

  const hora = lastUp
    ? lastUp.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
    : null

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-amber-500" />
      </div>
    )
  }

  const cobros   = data?.cobros_mes   || 0
  const gastos   = data?.gastos_mes   || 0
  const utilidad = cobros - gastos
  const utilPos  = utilidad >= 0

  return (
    <div className="space-y-5">
      {/* Encabezado */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            Hola, {usuario?.usuario} 👋
          </h2>
          <p className="text-sm text-gray-400">
            {new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })}
          </p>
        </div>
        <button
          onClick={loadDashboard}
          disabled={loading}
          title={hora ? `Actualizado a las ${hora}` : 'Actualizar'}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          {hora ? hora : 'Actualizar'}
        </button>
      </div>

      {/* Accesos rápidos */}
      <div className="grid grid-cols-4 gap-2">
        {ACCESOS.map(a => (
          <button key={a.path} onClick={() => navigate(a.path)}
            className={`${a.color} text-white rounded-xl p-3 flex flex-col items-center gap-1.5 hover:opacity-90 transition-opacity text-xs font-semibold shadow-sm`}>
            <a.icon size={18} />
            <span className="leading-tight text-center">{a.label}</span>
          </button>
        ))}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <KPICard icon={DollarSign}   label="Ventas Hoy"    value={fmt(data?.ventas_hoy?.total)}   sub={`${data?.ventas_hoy?.facturas || 0} facturas`}        color="green"  />
        <KPICard icon={TrendingUp}   label="Ventas Mes"    value={fmt(data?.ventas_mes?.total)}    sub={`${data?.ventas_mes?.facturas || 0} facturas`}        color="blue"   />
        <KPICard icon={CreditCard}   label="Cobros Hoy"    value={fmt(data?.cobros_hoy)}           color="purple" />
        <KPICard icon={AlertCircle}  label="Por Cobrar"    value={fmt(data?.total_por_cobrar)}     sub={`${data?.pendientes_entrega || 0} pendientes`}        color="red"    onClick={() => navigate('/cuentas')} />
        <KPICard icon={ShoppingCart} label="Pedidos Web"   value={data?.pedidos_web_pendientes ?? 0} sub="por entregar"  color="orange" onClick={() => navigate('/pedidos-online')} />
        <KPICard icon={Scissors}     label="Fabricación"   value={data?.fabricacion_en_curso ?? 0}   sub="pedidos activos" color="yellow" onClick={() => navigate('/fabricacion')} />
      </div>

      {/* Gráfica */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Ventas — últimos 7 días</h3>
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data?.ventas_7_dias || []} margin={{ top: 0, right: 4, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
              <XAxis dataKey="dia" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tickFormatter={v => `$${(v/1000).toFixed(0)}k`} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
              <Tooltip
                formatter={v => [new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(v), 'Ventas']}
                contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }}
              />
              <Bar dataKey="total" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Resumen financiero del mes */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <p className="text-xs text-gray-500 mb-1">Cobrado este mes</p>
          <p className="text-2xl font-bold text-green-600">{fmt(cobros)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <p className="text-xs text-gray-500 mb-1">Gastos este mes</p>
          <p className="text-2xl font-bold text-red-500">{fmt(gastos)}</p>
          {cobros > 0 && (
            <p className="text-xs text-gray-400 mt-0.5">{((gastos / cobros) * 100).toFixed(1)}% de lo cobrado</p>
          )}
        </div>
        <div className={`bg-white rounded-xl border-l-4 border border-gray-200 p-4 shadow-sm ${utilPos ? 'border-l-green-400' : 'border-l-red-400'}`}>
          <p className="text-xs text-gray-500 mb-1">Utilidad neta</p>
          <p className={`text-2xl font-bold ${utilPos ? 'text-green-600' : 'text-red-500'}`}>
            {utilPos ? '' : '−'}{fmt(Math.abs(utilidad))}
          </p>
          {cobros > 0 && (
            <p className={`text-xs mt-0.5 font-medium ${utilPos ? 'text-green-500' : 'text-red-400'}`}>
              Margen: {Math.abs(((utilidad / cobros) * 100)).toFixed(1)}%
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
