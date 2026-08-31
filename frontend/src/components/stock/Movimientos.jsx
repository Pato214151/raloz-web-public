import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { RefreshCw, ArrowDownCircle, ArrowUpCircle, SlidersHorizontal, Search } from 'lucide-react'

const TIPOS = [
  { id: '', label: 'Todos' },
  { id: 'SALIDA', label: 'Salidas' },
  { id: 'ENTRADA', label: 'Entradas' },
  { id: 'AJUSTE', label: 'Ajustes' },
]

const BADGE = {
  SALIDA: { cls: 'bg-red-50 text-red-600', icon: ArrowDownCircle, signo: '−' },
  ENTRADA: { cls: 'bg-emerald-50 text-emerald-700', icon: ArrowUpCircle, signo: '+' },
  AJUSTE: { cls: 'bg-amber-50 text-amber-700', icon: SlidersHorizontal, signo: '=' },
}

const fechaHora = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'))
  return d.toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export default function Movimientos() {
  const [movs, setMovs] = useState([])
  const [loading, setLoading] = useState(true)
  const [tipo, setTipo] = useState('')
  const [q, setQ] = useState('')

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/stock/movimientos', { params: { tipo: tipo || undefined, limite: 300 } })
      setMovs(res.data?.movimientos || [])
    } catch {
      toast.error('No pude cargar los movimientos')
    } finally {
      setLoading(false)
    }
  }, [tipo])

  useEffect(() => { cargar() }, [cargar])

  const filtrados = movs.filter(m => {
    if (!q.trim()) return true
    const t = `${m.producto_nombre || ''} ${m.colegio_nombre || ''} ${m.referencia || ''} ${m.usuario || ''} ${m.motivo || ''} ${m.talla_individual || ''}`.toLowerCase()
    return t.includes(q.trim().toLowerCase())
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h3 className="text-sm font-bold text-gray-900">Movimientos de inventario (Kardex)</h3>
          <p className="text-xs text-gray-400">Cada entrada, salida y ajuste — con su factura, motivo y quién lo hizo.</p>
        </div>
        <button onClick={cargar} disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50">
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Actualizar
        </button>
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex gap-1">
          {TIPOS.map(t => (
            <button key={t.id} onClick={() => setTipo(t.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                tipo === t.id ? 'bg-slate-800 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
          <input value={q} onChange={e => setQ(e.target.value)}
            placeholder="Buscar prenda, factura (FAC-…), usuario, motivo…"
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-amber-400" />
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-100 overflow-x-auto">
        {loading ? (
          <div className="py-12 text-center text-sm text-gray-400">Cargando…</div>
        ) : filtrados.length === 0 ? (
          <div className="py-12 text-center text-sm text-gray-400">Sin movimientos.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-gray-500">
                <th className="px-3 py-2.5 text-left font-medium">Fecha</th>
                <th className="px-3 py-2.5 text-left font-medium">Producto</th>
                <th className="px-3 py-2.5 text-center font-medium">Talla</th>
                <th className="px-3 py-2.5 text-center font-medium">Movimiento</th>
                <th className="px-3 py-2.5 text-right font-medium">Queda</th>
                <th className="px-3 py-2.5 text-left font-medium">Motivo / Factura</th>
                <th className="px-3 py-2.5 text-left font-medium">Usuario</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map(m => {
                const b = BADGE[m.tipo] || BADGE.AJUSTE
                return (
                  <tr key={m.id} className="border-b border-gray-50 hover:bg-gray-50/60">
                    <td className="px-3 py-2.5 text-gray-500 whitespace-nowrap text-xs">{fechaHora(m.fecha)}</td>
                    <td className="px-3 py-2.5">
                      <p className="font-medium text-gray-800">{m.producto_nombre || `#${m.id_producto}`}</p>
                      {m.colegio_nombre && <p className="text-[11px] text-gray-400">{m.colegio_nombre}</p>}
                    </td>
                    <td className="px-3 py-2.5 text-center text-gray-700">{m.talla_individual}</td>
                    <td className="px-3 py-2.5 text-center">
                      <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${b.cls}`}>
                        <b.icon size={12} /> {b.signo}{m.cantidad}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right font-semibold text-gray-800 tabular-nums">{m.stock_resultante}</td>
                    <td className="px-3 py-2.5">
                      <p className="text-gray-700 text-xs">{m.motivo || '—'}</p>
                      {m.referencia && <p className="text-[11px] text-amber-700 font-medium">{m.referencia}</p>}
                    </td>
                    <td className="px-3 py-2.5 text-gray-500 text-xs">{m.usuario || '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
