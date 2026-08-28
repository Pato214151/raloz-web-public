import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import {
  ShoppingCart, Scissors, PackageCheck, Package, Truck, RefreshCw, Store,
} from 'lucide-react'

// Mapea los items del tablero (tipo local/fabricacion/web + etapa) a las 5
// etapas visuales. Regla de negocio respetada: la venta LOCAL (con stock) NO
// pasa por producción → cae directo en "Por entregar".
const COLUMNAS = [
  { id: 'pedido',     label: 'Pedido',       hint: 'Web por procesar', icon: ShoppingCart, dot: 'bg-blue-500',   head: 'text-blue-700 bg-blue-50 border-blue-200',
    match: (it) => it.tipo === 'web' && it.etapa === 'por_preparar' },
  { id: 'produccion', label: 'Producción',   hint: 'En confección',    icon: Scissors,     dot: 'bg-amber-500',  head: 'text-amber-700 bg-amber-50 border-amber-200',
    match: (it) => it.tipo === 'fabricacion' && it.etapa === 'por_preparar' },
  { id: 'listo',      label: 'Listo',        hint: 'Fabricación lista', icon: PackageCheck, dot: 'bg-violet-500', head: 'text-violet-700 bg-violet-50 border-violet-200',
    match: (it) => it.tipo === 'fabricacion' && it.etapa === 'listo' },
  { id: 'empaque',    label: 'Empaque',      hint: 'Web empacado',      icon: Package,      dot: 'bg-cyan-600',   head: 'text-cyan-700 bg-cyan-50 border-cyan-200',
    match: (it) => it.tipo === 'web' && it.etapa === 'listo' },
  { id: 'entrega',    label: 'Por entregar', hint: 'Ventas en el local', icon: Truck,       dot: 'bg-emerald-500', head: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    match: (it) => it.tipo === 'local' },
]

const TIPO_ICONO = { local: Store, fabricacion: Scissors, web: ShoppingCart }

function tiempoRel(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const dias = Math.floor((Date.now() - d.getTime()) / 86400000)
  if (dias <= 0) return 'hoy'
  if (dias === 1) return 'ayer'
  if (dias < 30) return `hace ${dias} d`
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short' })
}

function Tarjeta({ it, onClick }) {
  const Icon = TIPO_ICONO[it.tipo] || Package
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white border border-gray-200 rounded-lg p-3 shadow-sm
                 hover:border-amber-300 hover:shadow-md transition-all"
    >
      <div className="flex items-start gap-2">
        <div className="w-7 h-7 rounded-md bg-gray-100 text-gray-500 flex items-center justify-center shrink-0">
          <Icon size={14} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-semibold text-gray-900 truncate leading-tight">{it.titulo}</p>
          {it.cliente && <p className="text-xs text-gray-500 truncate">{it.cliente}</p>}
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          {it.colegio && (
            <span className="text-[10px] font-medium text-gray-500 bg-gray-100 rounded px-1.5 py-0.5 truncate max-w-[110px]">
              {it.colegio}
            </span>
          )}
          {it.detalle && (
            <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 rounded px-1.5 py-0.5 truncate">
              {it.detalle}
            </span>
          )}
        </div>
        <span className="text-[10px] text-gray-400 shrink-0">{tiempoRel(it.fecha)}</span>
      </div>
    </button>
  )
}

export default function TableroKanban() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/operaciones/tablero')
      const d = res.data || {}
      setItems([...(d.por_preparar || []), ...(d.listo || [])])
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const cols = COLUMNAS.map(c => ({ ...c, cards: items.filter(c.match) }))
  const total = items.length

  return (
    <div className="space-y-3">
      {/* Encabezado del tablero */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-gray-900">Tablero de operación</h3>
          <p className="text-xs text-gray-400">
            {loading ? 'Cargando…' : `${total} pedido${total === 1 ? '' : 's'} en curso · el flujo va de izquierda a derecha`}
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 shrink-0"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Actualizar
        </button>
      </div>

      {/* Columnas (scroll horizontal en pantallas chicas) */}
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin -mx-1 px-1">
        {cols.map(col => (
          <div key={col.id} className="flex-shrink-0 w-[240px] flex flex-col">
            {/* Cabecera de columna */}
            <div className={`flex items-center justify-between gap-2 px-3 py-2 rounded-lg border ${col.head}`}>
              <div className="flex items-center gap-2 min-w-0">
                <col.icon size={14} className="shrink-0" />
                <div className="min-w-0">
                  <p className="text-[12.5px] font-bold leading-none">{col.label}</p>
                  <p className="text-[10px] opacity-70 leading-tight mt-0.5">{col.hint}</p>
                </div>
              </div>
              <span className="text-[11px] font-bold bg-white/70 rounded-full min-w-[20px] h-5 px-1.5 flex items-center justify-center shrink-0">
                {col.cards.length}
              </span>
            </div>

            {/* Cards */}
            <div className="mt-2 flex flex-col gap-2 min-h-[80px]">
              {!loading && col.cards.length === 0 && (
                <div className="text-center text-[11px] text-gray-300 py-6 border border-dashed border-gray-200 rounded-lg">
                  Sin pedidos
                </div>
              )}
              {col.cards.map(it => (
                <Tarjeta key={it.id} it={it} onClick={() => it.link && navigate(it.link)} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
