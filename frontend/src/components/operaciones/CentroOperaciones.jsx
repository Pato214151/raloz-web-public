/** Centro de operaciones: qué está por preparar y qué está listo para entregar. */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { RefreshCw, Package, Scissors, ShoppingCart, ClipboardList, ArrowRight } from 'lucide-react'

const TIPO = {
  local:       { label: 'Local',       cls: 'bg-blue-100 text-blue-700',     icon: Package },
  fabricacion: { label: 'Fabricación', cls: 'bg-amber-100 text-amber-700',   icon: Scissors },
  web:         { label: 'Web',         cls: 'bg-violet-100 text-violet-700', icon: ShoppingCart },
}

function Card({ it, onClick }) {
  const t = TIPO[it.tipo] || TIPO.local
  const Icon = t.icon
  return (
    <div onClick={onClick}
      className="bg-white rounded-lg border border-gray-100 p-3 shadow-sm hover:shadow-md hover:border-gray-200 cursor-pointer transition-all group">
      <div className="flex items-center justify-between mb-1">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 ${t.cls}`}>
          <Icon size={11} /> {t.label}
        </span>
        <ArrowRight size={13} className="text-gray-300 group-hover:text-gray-500" />
      </div>
      <p className="font-semibold text-gray-800 text-sm leading-tight">{it.titulo}</p>
      <p className="text-xs text-gray-500 mt-0.5 truncate">
        {it.cliente || 'Sin cliente'}{it.colegio ? ` · ${it.colegio}` : ''}
      </p>
      {it.detalle && <p className="text-xs text-gray-400 mt-0.5">{it.detalle}</p>}
    </div>
  )
}

function Columna({ titulo, items, color, hint, navigate }) {
  return (
    <div className="flex-1 min-w-0">
      <div className="flex items-center justify-between mb-2 px-1">
        <h3 className="text-sm font-bold text-gray-700 flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${color}`} /> {titulo}
        </h3>
        <span className="text-xs font-semibold text-gray-400">{items.length}</span>
      </div>
      <div className="space-y-2">
        {items.length === 0 ? (
          <p className="text-xs text-gray-300 text-center py-8 border-2 border-dashed border-gray-100 rounded-lg">{hint}</p>
        ) : (
          items.map(it => <Card key={it.id} it={it} onClick={() => navigate(it.link)} />)
        )}
      </div>
    </div>
  )
}

export default function CentroOperaciones() {
  const navigate = useNavigate()
  const [data, setData] = useState({ por_preparar: [], listo: [], totales: {} })
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get('/operaciones/tablero')
      setData(res.data)
    } catch {
      toast.error('Error cargando operaciones')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <ClipboardList size={20} className="text-raloz-600" /> Centro de Operaciones
          </h2>
          <p className="text-sm text-gray-400">Todo lo que hay que preparar y entregar, en un solo lugar.</p>
        </div>
        <button onClick={load} disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 shrink-0">
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Actualizar
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin h-8 w-8 border-b-2 border-raloz-600 rounded-full" />
        </div>
      ) : (
        <div className="flex flex-col md:flex-row gap-4">
          <Columna titulo="Por preparar" items={data.por_preparar} color="bg-amber-400"
            hint="Nada por preparar 🎉" navigate={navigate} />
          <Columna titulo="Listo para entregar" items={data.listo} color="bg-emerald-500"
            hint="Nada listo aún" navigate={navigate} />
        </div>
      )}

      <p className="text-xs text-gray-400">
        Junta ventas del local (pendientes), fabricación y pedidos web. Clic en una tarjeta para ir a gestionarla.
      </p>
    </div>
  )
}
