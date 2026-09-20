/**
 * Inicio del panel: resumen del día (ventas, pendientes, caja) y lo que el
 * asistente sugiere atender.
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import {
  DollarSign, CreditCard, TrendingUp, TrendingDown, AlertCircle,
  ShoppingCart, Scissors, RefreshCw, FileText, Search, Package,
  PackageCheck, Wallet, ArrowRight, BookOpen, MessageCircle, Users, Clock, Truck,
  MessageSquare, ClipboardList,
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

// ─── Formateo de moneda ──────────────────────────────────────────
const fmt = (n) => {
  if (n === undefined || n === null) return '$0'
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `$${Math.round(n / 1_000)}k`
  return '$' + Math.round(n).toLocaleString('es-CO')
}

// ─── Colores para KPI cards ──────────────────────────────────────
const COLORS = {
  green:  { bg: 'bg-emerald-50', text: 'text-emerald-600', ring: 'ring-emerald-100' },
  blue:   { bg: 'bg-blue-50',    text: 'text-blue-600',    ring: 'ring-blue-100'    },
  purple: { bg: 'bg-violet-50',  text: 'text-violet-600',  ring: 'ring-violet-100'  },
  red:    { bg: 'bg-red-50',     text: 'text-red-500',     ring: 'ring-red-100'     },
  orange: { bg: 'bg-orange-50',  text: 'text-orange-500',  ring: 'ring-orange-100'  },
  amber:  { bg: 'bg-amber-50',   text: 'text-amber-600',   ring: 'ring-amber-100'   },
}

// ─── KPI Card ───────────────────────────────────────────────────
function KPICard({ icon: Icon, label, value, sub, color = 'blue', onClick, showAlert }) {
  const c = COLORS[color] || COLORS.blue
  return (
    <div
      onClick={onClick}
      className={`
        relative bg-white rounded-xl border border-gray-100 p-4
        flex items-center gap-3.5 shadow-sm
        ${onClick ? 'cursor-pointer hover:border-gray-200 hover:shadow-md transition-all group' : ''}
      `}
    >
      {/* Punto de alerta */}
      {showAlert && (
        <span className="absolute top-3 right-3 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white" />
      )}

      {/* Icono */}
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ring-4 ${c.bg} ${c.text} ${c.ring}`}>
        <Icon size={19} />
      </div>

      {/* Texto */}
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-gray-400 truncate">{label}</p>
        <p className="text-[22px] font-bold text-gray-900 leading-tight tracking-tight">{value}</p>
        {sub && <p className="text-xs text-gray-400 truncate mt-0.5">{sub}</p>}
      </div>

      {/* Flecha (solo clickables) */}
      {onClick && (
        <ArrowRight size={14} className="text-gray-300 group-hover:text-gray-400 flex-shrink-0 transition-colors" />
      )}
    </div>
  )
}

// ─── Acciones rápidas (filtradas por rol) → apuntan a los hubs nuevos ─
const ACCESOS_DEF = [
  { label: 'Nueva venta',    icon: ShoppingCart, path: '/ventas?tab=nueva',     bg: 'bg-slate-800',  roles: ['administrador', 'vendedor', 'cajero'] },
  { label: 'Registrar pago', icon: CreditCard,   path: '/ventas?tab=pago',      bg: 'bg-violet-600', roles: ['administrador', 'cajero']             },
  { label: 'Nuevo cliente',  icon: Users,        path: '/clientes?tab=clientes', bg: 'bg-indigo-600', roles: ['administrador', 'vendedor', 'cajero'] },
  { label: 'Pedidos',        icon: ClipboardList, path: '/operacion',           bg: 'bg-blue-600',   roles: ['administrador', 'vendedor']          },
]

// ─── Skeleton de carga ───────────────────────────────────────────
function LoadingSkeleton() {
  return (
    <div className="space-y-5 animate-pulse">
      <div className="flex justify-between">
        <div className="space-y-2">
          <div className="h-5 w-40 bg-gray-100 rounded-lg" />
          <div className="h-4 w-28 bg-gray-100 rounded-lg" />
        </div>
        <div className="h-8 w-32 bg-gray-100 rounded-lg" />
      </div>
      <div className="grid grid-cols-4 gap-2">
        {[...Array(4)].map((_, i) => <div key={i} className="h-20 bg-gray-100 rounded-xl" />)}
      </div>
      <div className="h-3 w-10 bg-gray-100 rounded" />
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-gray-100 rounded-xl" />)}
      </div>
      <div className="h-3 w-16 bg-gray-100 rounded" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-gray-100 rounded-xl" />)}
      </div>
      <div className="h-64 bg-gray-100 rounded-xl" />
    </div>
  )
}

// ─── Dashboard ───────────────────────────────────────────────────
export default function Dashboard() {
  const { usuario } = useAuth()
  const navigate    = useNavigate()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUp, setLastUp]   = useState(null)
  const [home, setHome]       = useState(null)   // Daily Briefing de RALOZ (admin)

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
  // Daily Briefing del Observador (solo admin; endpoint protegido).
  useEffect(() => {
    if (usuario?.rol !== 'administrador') return
    api.get('/asistente/home').then(r => setHome(r.data)).catch(() => {})
  }, [usuario])

  const rol     = usuario?.rol
  const isAdmin = rol === 'administrador'

  // Hasta 4 accesos filtrados por rol
  const accesos = ACCESOS_DEF.filter(a => a.roles.includes(rol)).slice(0, 4)

  const hora = lastUp
    ? lastUp.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
    : null

  if (loading && !data) return <LoadingSkeleton />

  const cobros   = data?.cobros_mes || 0
  const gastos   = data?.gastos_mes || 0
  const utilidad = cobros - gastos
  const utilPos  = utilidad >= 0

  const totalSemana = (data?.ventas_7_dias || []).reduce((s, d) => s + (d.total || 0), 0)

  return (
    <div className="space-y-5">

      {/* ── Encabezado ── */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-gray-900">
            {(() => { const h = new Date().getHours(); return h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches' })()}, {usuario?.usuario}
          </h2>
          <p className="text-sm text-gray-400 capitalize">
            {new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })}
          </p>
        </div>
        <button
          onClick={loadDashboard}
          disabled={loading}
          title={hora ? `Actualizado a las ${hora}` : 'Actualizar'}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 shrink-0"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          {hora ? `Act. ${hora}` : 'Actualizar'}
        </button>
      </div>

      {/* ── Caja del día ── */}
      {(rol === 'administrador' || rol === 'cajero') && data?.caja && (
        <div
          onClick={() => navigate('/finanzas?tab=caja')}
          className={`rounded-xl p-4 flex items-center justify-between cursor-pointer shadow-sm hover:shadow-md transition-all text-white ${
            data.caja.abierta
              ? 'bg-gradient-to-r from-emerald-500 to-emerald-600'
              : 'bg-gradient-to-r from-slate-700 to-slate-800'
          }`}
        >
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-11 h-11 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
              <BookOpen size={20} />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold flex items-center gap-2">
                Caja {data.caja.abierta ? 'abierta' : 'cerrada'}
                <span className={`w-2 h-2 rounded-full ${data.caja.abierta ? 'bg-emerald-200 animate-pulse' : 'bg-slate-400'}`} />
              </p>
              <p className="text-xs text-white/80 truncate">
                {data.caja.abierta
                  ? `Esperado en caja: ${fmt(data.caja.monto_esperado)}`
                  : 'Ábrela para empezar el día'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-sm font-medium flex-shrink-0">
            {data.caja.abierta ? 'Ver / cerrar' : 'Abrir caja'} <ArrowRight size={15} />
          </div>
        </div>
      )}

      {/* ── ¿Qué hago hoy? (modo simple para atender el día) ── */}
      <button onClick={() => navigate('/mi-dia')}
        className="w-full rounded-2xl p-4 flex items-center gap-3 text-white shadow-sm active:scale-[.99] transition"
        style={{ background: 'linear-gradient(135deg,#071E49,#123a86)' }}>
        <div className="w-11 h-11 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
          <ClipboardList size={22} />
        </div>
        <div className="min-w-0 flex-1 text-left">
          <p className="text-[16px] font-bold leading-tight">¿Qué hago hoy?</p>
          <p className="text-[12.5px] text-white/80">Tus tareas del día, claras y en orden</p>
        </div>
        <ArrowRight size={18} className="opacity-80" />
      </button>

      {/* ── Accesos rápidos ── */}
      {accesos.length > 0 && (
        <div className={`grid gap-2 ${accesos.length >= 4 ? 'grid-cols-4' : `grid-cols-${accesos.length}`}`}>
          {accesos.map(a => (
            <button
              key={a.path}
              onClick={() => navigate(a.path)}
              className={`${a.bg} text-white rounded-xl p-3.5 flex flex-col items-center gap-2 hover:opacity-90 active:scale-95 transition-all shadow-sm`}
            >
              <a.icon size={17} />
              <span className="text-xs font-semibold leading-tight text-center">{a.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* ── RALOZ · Daily Briefing (solo admin) ── */}
      {isAdmin && home && (home.total_alertas > 0 || (home.recomendaciones || []).length > 0 || (home.metas || []).length > 0) && (
        <div className="rounded-2xl overflow-hidden border border-gray-100 shadow-sm">
          <div className="px-4 py-2.5 flex items-center justify-between" style={{ background: '#071E49' }}>
            <p className="text-sm font-semibold text-white flex items-center gap-2">
              <MessageSquare size={15} style={{ color: '#FFD84D' }} /> RALOZ · Buenos días
            </p>
            <button onClick={() => navigate('/asistente')}
              className="text-[12px] font-medium text-white/90 flex items-center gap-1 hover:text-white">
              Abrir <ArrowRight size={13} />
            </button>
          </div>
          <div className="bg-white p-4 space-y-3">
            {/* Alertas */}
            <div className="flex items-center gap-2 flex-wrap">
              {['CRITICO', 'IMPORTANTE', 'PRECAUCION'].map(s => (home.alertas?.[s] || 0) > 0 && (
                <span key={s} className="text-[12px] font-semibold px-2 py-0.5 rounded-full bg-gray-50 border border-gray-100 text-gray-700">
                  {{ CRITICO: '🔴', IMPORTANTE: '🟠', PRECAUCION: '🟡' }[s]} {home.alertas[s]}
                </span>
              ))}
              {(home.total_alertas || 0) === 0 && <span className="text-[13px] text-emerald-600 font-medium">Sin alertas ✓</span>}
              {home.cartera_pendiente > 0 && (
                <span className="text-[12px] text-gray-500 ml-auto">💰 Cartera {fmt(home.cartera_pendiente)}</span>
              )}
            </div>
            {/* Metas */}
            {(home.metas || []).map((m, i) => (
              <div key={i}>
                <div className="flex items-center justify-between text-[12.5px]">
                  <span className="text-gray-500">📈 {m.descripcion || 'Meta'}</span>
                  <span className="font-semibold text-gray-800 tabular-nums">{fmt(m.actual)} / {fmt(m.meta)} · {m.pct}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-gray-100 mt-1 overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${Math.min(100, m.pct)}%`, background: m.proyecta_ok === false ? '#E7B85A' : '#071E49' }} />
                </div>
              </div>
            ))}
            {/* Recomendaciones */}
            {(home.recomendaciones || []).length > 0 && (
              <div className="pt-2 border-t border-gray-100">
                <p className="text-[12px] font-semibold text-gray-800 mb-1.5">🎯 Hoy recomiendo</p>
                <ol className="space-y-1">
                  {home.recomendaciones.map((rec, i) => (
                    <li key={i} className="text-[12px] text-gray-500 flex gap-1.5"><span className="text-gray-400">{i + 1}.</span> {rec}</li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── KPIs: Hoy ── */}
      <div>
        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2 px-0.5">Hoy</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <KPICard
            icon={DollarSign}
            label="Ventas hoy"
            value={fmt(data?.ventas_hoy?.total)}
            sub={`${data?.ventas_hoy?.facturas || 0} facturas`}
            color="green"
          />
          <KPICard
            icon={CreditCard}
            label="Cobrado hoy"
            value={fmt(data?.cobros_hoy)}
            color="purple"
          />
          <KPICard
            icon={TrendingUp}
            label="Ventas del mes"
            value={fmt(data?.ventas_mes?.total)}
            sub={`${data?.ventas_mes?.facturas || 0} facturas`}
            color="blue"
          />
        </div>
      </div>

      {/* ── Canal web (leads) ── */}
      {isAdmin && (data?.leads_pendientes > 0 || data?.leads_mes > 0) && (
        <div
          onClick={() => navigate('/clientes?tab=leads')}
          className="rounded-xl border border-green-200 bg-green-50 p-4 cursor-pointer hover:bg-green-100 transition-colors"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <MessageSquare size={15} className="text-green-600" />
              <p className="text-xs font-bold text-green-700 uppercase tracking-wider">Canal web — Cotizaciones</p>
            </div>
            <span className="text-[10px] text-green-500 font-medium">Ver todos →</span>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex-1">
              <p className="text-2xl font-bold text-green-800">{data?.leads_pendientes ?? 0}</p>
              <p className="text-xs text-green-600">pendientes</p>
            </div>
            {/* Desglose por origen */}
            {(data?.leads_pendientes_web > 0 || data?.leads_pendientes_whatsapp > 0) && (
              <div className="flex gap-3">
                {data?.leads_pendientes_web > 0 && (
                  <div className="text-center">
                    <p className="text-base font-bold text-blue-700">🌐 {data.leads_pendientes_web}</p>
                    <p className="text-[10px] text-blue-500">web</p>
                  </div>
                )}
                {data?.leads_pendientes_whatsapp > 0 && (
                  <div className="text-center">
                    <p className="text-base font-bold text-green-700">💬 {data.leads_pendientes_whatsapp}</p>
                    <p className="text-[10px] text-green-500">WhatsApp</p>
                  </div>
                )}
              </div>
            )}
            <div className="text-right">
              <p className="text-lg font-bold text-green-700">{data?.leads_mes ?? 0}</p>
              <p className="text-xs text-green-600">este mes</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-green-600/80">
            {data?.leads_pendientes > 0
              ? 'Tocá para ver y atender los leads.'
              : 'Los leads llegan desde la tienda web. Si WhatsApp se cae, estos igual se capturan.'}
          </p>
        </div>
      )}

      {/* ── Resumen de Pedidos (sección unificada) ── */}
      <div>
        <div className="flex items-center justify-between mb-2 px-0.5">
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Pedidos pendientes</p>
          <button onClick={() => navigate('/operacion')}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1">
            Ver todo <ArrowRight size={11} />
          </button>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <KPICard
            icon={ShoppingCart}
            label="Pedidos web"
            value={data?.pedidos_web_pendientes ?? 0}
            sub="por procesar"
            color="blue"
            onClick={() => navigate('/operacion')}
            showAlert={(data?.pedidos_web_pendientes || 0) > 0}
          />
          <KPICard
            icon={Scissors}
            label="En fabricación"
            value={data?.fabricacion_en_curso ?? 0}
            sub="pedidos activos"
            color="amber"
            onClick={() => navigate('/operacion')}
          />
          <KPICard
            icon={Package}
            label="Por entregar"
            value={data?.pendientes_entrega ?? 0}
            sub="prendas"
            color="orange"
            onClick={() => navigate('/operacion')}
            showAlert={(data?.pendientes_entrega || 0) > 0}
          />
          <KPICard
            icon={AlertCircle}
            label="Por cobrar"
            value={fmt(data?.total_por_cobrar)}
            color="red"
            onClick={() => navigate('/ventas?tab=porcobrar')}
            showAlert={(data?.total_por_cobrar || 0) > 0}
          />
        </div>
      </div>

      {/* ── Gráfica + Finanzas (admin) ── */}
      <div className={`grid gap-4 ${isAdmin ? 'lg:grid-cols-5' : 'grid-cols-1'}`}>

        {/* Gráfica ventas 7 días */}
        <div className={`bg-white rounded-xl border border-gray-100 p-4 shadow-sm ${isAdmin ? 'lg:col-span-3' : ''}`}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">Ventas — últimos 7 días</h3>
            {totalSemana > 0 && (
              <span className="text-xs font-medium text-gray-400">
                Total: {fmt(totalSemana)}
              </span>
            )}
          </div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.ventas_7_dias || []} margin={{ top: 0, right: 4, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis
                  dataKey="dia"
                  tick={{ fontSize: 11, fill: '#9ca3af' }}
                  axisLine={false} tickLine={false}
                />
                <YAxis
                  tickFormatter={v => `$${(v / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 11, fill: '#9ca3af' }}
                  axisLine={false} tickLine={false} width={38}
                />
                <Tooltip
                  formatter={v => [
                    new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(v),
                    'Ventas',
                  ]}
                  contentStyle={{
                    borderRadius: '10px', border: '1px solid #e5e7eb',
                    fontSize: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                  }}
                  cursor={{ fill: '#f9fafb' }}
                />
                <Bar dataKey="total" fill="#f59e0b" radius={[5, 5, 0, 0]} maxBarSize={48} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Resumen financiero — solo administrador */}
        {isAdmin && (
          <div className="lg:col-span-2 flex flex-col gap-3">

            {/* Cobrado */}
            <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm flex-1">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-7 h-7 bg-emerald-50 text-emerald-600 rounded-lg flex items-center justify-center">
                  <TrendingUp size={13} />
                </div>
                <p className="text-xs font-medium text-gray-400">Cobrado este mes</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{fmt(cobros)}</p>
            </div>

            {/* Gastos */}
            <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm flex-1">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-7 h-7 bg-red-50 text-red-500 rounded-lg flex items-center justify-center">
                  <Wallet size={13} />
                </div>
                <p className="text-xs font-medium text-gray-400">Gastos este mes</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{fmt(gastos)}</p>
              {cobros > 0 && (
                <p className="text-xs text-gray-400 mt-0.5">
                  {((gastos / cobros) * 100).toFixed(1)}% de lo cobrado
                </p>
              )}
            </div>

            {/* Utilidad */}
            <div className={`bg-white rounded-xl border border-gray-100 border-l-4 p-4 shadow-sm flex-1 ${utilPos ? 'border-l-emerald-400' : 'border-l-red-400'}`}>
              <div className="flex items-center gap-2 mb-2">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${utilPos ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'}`}>
                  {utilPos ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                </div>
                <p className="text-xs font-medium text-gray-400">Utilidad neta</p>
              </div>
              <p className={`text-2xl font-bold ${utilPos ? 'text-emerald-600' : 'text-red-500'}`}>
                {utilPos ? '' : '−'}{fmt(Math.abs(utilidad))}
              </p>
              {cobros > 0 && (
                <p className={`text-xs mt-0.5 font-medium ${utilPos ? 'text-emerald-500' : 'text-red-400'}`}>
                  Margen: {Math.abs(((utilidad / cobros) * 100)).toFixed(1)}%
                </p>
              )}
            </div>

          </div>
        )}
      </div>

    </div>
  )
}
