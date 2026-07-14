import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Send, Users, Loader2, AlertTriangle, History, Megaphone } from 'lucide-react'

const fmtFecha = (iso) => {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('es-CO', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

export default function Avisos() {
  const [texto, setTexto] = useState('')
  const [segmento, setSegmento] = useState('activos')
  const [dest, setDest] = useState({ activos: 0, todos: 0, suscriptores: 0 })
  const [historial, setHistorial] = useState([])
  const [loading, setLoading] = useState(true)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => { cargar() }, [])

  async function cargar() {
    setLoading(true)
    try {
      const { data } = await api.get('/tienda/admin/avisos')
      setDest(data.destinatarios || { activos: 0, todos: 0, suscriptores: 0 })
      setHistorial(data.historial || [])
    } catch {
      toast.error('No se pudo cargar avisos')
    } finally {
      setLoading(false)
    }
  }

  const nDest = dest[segmento] ?? 0

  async function enviar() {
    if (!texto.trim()) { toast.error('Escribe el mensaje'); return }
    if (nDest === 0) { toast.error('No hay destinatarios en este segmento'); return }
    if (!window.confirm(`¿Enviar este aviso por WhatsApp a ${nDest} contacto(s)?`)) return

    setEnviando(true)
    try {
      const { data } = await api.post('/tienda/admin/avisos', { texto, segmento })
      toast.success(`Enviado a ${data.enviados} de ${data.total}`)
      if (data.fallidos > 0) {
        toast(`${data.fallidos} no recibieron (fuera de la ventana de 24h)`, { icon: '⚠️' })
      }
      setTexto('')
      cargar()
    } catch {
      toast.error('No se pudo enviar el aviso')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-lg shrink-0">
          <Megaphone className="w-6 h-6 text-blue-700" />
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Avisos por WhatsApp</h1>
          <p className="text-gray-600 text-xs sm:text-sm">
            Manda una nota a tus clientes que han escrito por WhatsApp.
          </p>
        </div>
      </div>

      {/* Aviso de la regla de 24h */}
      <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-3 text-xs sm:text-sm">
        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
        <span>
          WhatsApp solo permite enviar texto libre a quienes te escribieron en las últimas
          <b> 24 horas</b>. A contactos más antiguos no les llegará (requiere plantillas aprobadas).
        </span>
      </div>

      {/* Redactar */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          maxLength={1000}
          rows={4}
          placeholder="Ej: ¡Hola! Ya está lista la nueva colección de uniformes 2026. Escríbenos para apartar la tuya. 🎒"
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
        <div className="text-xs text-gray-400 -mt-2">{texto.length}/1000</div>

        {/* Segmento */}
        <div className="flex flex-col sm:flex-row gap-2">
          {[
            { id: 'activos', label: 'Activos (24h)', n: dest.activos, hint: 'Reciben seguro' },
            { id: 'suscriptores', label: 'Suscriptores', n: dest.suscriptores, hint: 'Aceptaron recibir info' },
            { id: 'todos', label: 'Todos', n: dest.todos, hint: 'Los viejos quizá no' },
          ].map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setSegmento(s.id)}
              className={`flex-1 flex items-center justify-between gap-2 px-4 py-3 rounded-lg border text-left transition-colors ${
                segmento === s.id ? 'border-blue-600 bg-blue-50' : 'border-gray-200 hover:border-blue-300'
              }`}
            >
              <div>
                <div className="text-sm font-semibold text-gray-800">{s.label}</div>
                <div className="text-[11px] text-gray-400">{s.hint}</div>
              </div>
              <span className="inline-flex items-center gap-1 text-sm font-bold text-gray-700 tabular-nums">
                <Users className="w-4 h-4 text-gray-400" />{s.n}
              </span>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={enviar}
          disabled={enviando || loading}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold px-5 py-2.5 rounded-lg"
        >
          {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          Enviar a {nDest} contacto{nDest === 1 ? '' : 's'}
        </button>
      </div>

      {/* Historial */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="flex items-center gap-2 p-4 border-b border-gray-100">
          <History className="w-4 h-4 text-gray-400" />
          <h2 className="font-semibold text-gray-800">Historial</h2>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-12 text-gray-400">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : historial.length === 0 ? (
          <p className="text-center text-gray-400 py-10 text-sm">Aún no has enviado avisos.</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {historial.map((a) => (
              <div key={a.id_aviso} className="p-4">
                <p className="text-sm text-gray-800 whitespace-pre-wrap">{a.texto}</p>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-[11px] text-gray-400">
                  <span>{fmtFecha(a.fecha)}</span>
                  <span className="text-green-600 font-semibold">{a.enviados} enviados</span>
                  {a.fallidos > 0 && <span className="text-orange-500">{a.fallidos} no llegaron</span>}
                  <span>· segmento: {a.segmento}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
