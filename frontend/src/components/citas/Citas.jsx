import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { CalendarClock, RefreshCw, Check, X, UserCheck } from 'lucide-react'

// Citas agendadas por los clientes desde el bot de WhatsApp.
// Estados: pendiente → confirmada → atendida (o cancelada).

const FILTROS = [
  { key: '', label: 'Todas' },
  { key: 'pendiente', label: 'Pendientes' },
  { key: 'confirmada', label: 'Confirmadas' },
  { key: 'atendida', label: 'Atendidas' },
  { key: 'cancelada', label: 'Canceladas' },
]

const ESTADO_STYLE = {
  pendiente: 'bg-amber-100 text-amber-700',
  confirmada: 'bg-blue-100 text-blue-700',
  atendida: 'bg-green-100 text-green-700',
  cancelada: 'bg-gray-200 text-gray-500',
}

function fecha(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString('es-CO', {
      day: '2-digit', month: '2-digit', year: '2-digit',
    })
  } catch { return '' }
}

export default function Citas() {
  const [citas, setCitas] = useState([])
  const [filtro, setFiltro] = useState('')
  const [cargando, setCargando] = useState(true)

  const cargar = useCallback(async () => {
    try {
      const q = filtro ? `?estado=${filtro}` : ''
      const res = await api.get(`/citas${q}`)
      setCitas(res.data || [])
    } catch {
      toast.error('No se pudieron cargar las citas')
    } finally { setCargando(false) }
  }, [filtro])

  useEffect(() => {
    cargar()
    const id = setInterval(cargar, 30000)
    return () => clearInterval(id)
  }, [cargar])

  const cambiarEstado = async (id, estado) => {
    try {
      await api.post(`/citas/${id}/estado`, { estado })
      toast.success('Cita actualizada')
      cargar()
    } catch {
      toast.error('No se pudo actualizar')
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Filtros */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {FILTROS.map(f => (
          <button key={f.key} onClick={() => setFiltro(f.key)}
            className={`text-xs font-medium px-3 py-1.5 rounded-lg transition ${
              filtro === f.key ? 'bg-slate-800 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'}`}>
            {f.label}
          </button>
        ))}
        <button onClick={cargar} title="Actualizar"
          className="ml-auto p-2 text-gray-400 hover:text-gray-700 rounded-lg border border-gray-200 bg-white">
          <RefreshCw size={14} />
        </button>
      </div>

      {cargando ? (
        <p className="text-sm text-gray-400 py-10 text-center">Cargando…</p>
      ) : citas.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <CalendarClock size={40} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">No hay citas {filtro && `(${filtro}s)`}.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {citas.map(c => (
            <div key={c.id_cita}
              className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-amber-100 text-amber-600 flex items-center justify-center shrink-0">
                <CalendarClock size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-800 truncate">
                  {c.nombre || 'Sin nombre'}
                  <span className={`ml-2 text-[10px] font-bold px-2 py-0.5 rounded ${ESTADO_STYLE[c.estado] || ''}`}>
                    {(c.estado || 'pendiente').toUpperCase()}
                  </span>
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  📆 {c.dia} · 🕘 {c.hora} · 🏫 {c.colegio || '—'}
                </p>
                <p className="text-[10px] text-gray-400 mt-0.5">
                  Solicitada {fecha(c.creada)} · {c.chat_id}
                </p>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {c.estado === 'pendiente' && (
                  <button onClick={() => cambiarEstado(c.id_cita, 'confirmada')}
                    title="Confirmar"
                    className="flex items-center gap-1 text-xs font-medium px-2.5 py-1.5 rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200">
                    <Check size={13} /> Confirmar
                  </button>
                )}
                {(c.estado === 'pendiente' || c.estado === 'confirmada') && (
                  <>
                    <button onClick={() => cambiarEstado(c.id_cita, 'atendida')}
                      title="Marcar atendida"
                      className="flex items-center gap-1 text-xs font-medium px-2.5 py-1.5 rounded-lg bg-green-100 text-green-700 hover:bg-green-200">
                      <UserCheck size={13} /> Atendida
                    </button>
                    <button onClick={() => cambiarEstado(c.id_cita, 'cancelada')}
                      title="Cancelar"
                      className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50">
                      <X size={15} />
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
