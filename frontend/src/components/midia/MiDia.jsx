import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import {
  RefreshCw, Package, Scissors, Wallet, MessageCircle, CalendarClock,
  CheckCircle2, ArrowRight,
} from 'lucide-react'

const cop = (n) => '$' + Math.round(Number(n || 0)).toLocaleString('es-CO')

// Tarjeta grande de una tarea del día
function Tarea({ icon: Icon, color, titulo, resumen, children, onClick, cta }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <div className="flex items-center gap-3">
        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 ${color}`}>
          <Icon size={24} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[17px] font-bold text-gray-900 leading-tight">{titulo}</p>
          {resumen && <p className="text-[14px] text-gray-500 mt-0.5">{resumen}</p>}
        </div>
      </div>
      {children && <div className="mt-3 space-y-1.5">{children}</div>}
      {onClick && (
        <button onClick={onClick}
          className="mt-4 w-full py-3 rounded-xl bg-[#071E49] text-white text-[15px] font-semibold flex items-center justify-center gap-2 active:scale-[.98] transition">
          {cta} <ArrowRight size={17} />
        </button>
      )}
    </div>
  )
}

export default function MiDia() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/asistente/mi-dia')
      setData(res.data)
    } catch (e) {
      setData({ error: true })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  const t = data?.tareas || {}
  const nada = !loading && data && !data.error &&
    !(t.entregar?.total || t.cobrar?.total || t.whatsapp?.chats || t.citas?.total || t.fabricacion_lista?.total)

  return (
    <div className="max-w-xl mx-auto space-y-4 pb-24">
      {/* Encabezado */}
      <div className="rounded-2xl p-5 text-white" style={{ background: '#071E49' }}>
        <p className="text-[13px] text-white/70">
          {data?.dia_semana ? data.dia_semana[0].toUpperCase() + data.dia_semana.slice(1) : 'Hoy'}
        </p>
        <h1 className="text-2xl font-bold mt-0.5">¿Qué hago hoy?</h1>
        <p className="text-[14px] text-white/85 mt-2">
          {data?.atiende_sin_cita
            ? '🟢 Hoy atendemos SIN cita, 10:00 a.m. a 5:00 p.m.'
            : '🟡 Hoy solo con cita previa (sin cita: solo lunes y sábado).'}
        </p>
      </div>

      <div className="flex justify-end">
        <button onClick={cargar} className="text-[13px] text-gray-500 flex items-center gap-1.5 hover:text-gray-700">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Actualizar
        </button>
      </div>

      {loading && !data && <p className="text-center text-gray-400 py-10">Cargando tu día…</p>}

      {data?.error && (
        <div className="bg-red-50 border border-red-100 rounded-xl p-4 text-red-600 text-sm">
          No pude cargar tus tareas ahora. Toca <b>Actualizar</b> en un momento.
        </div>
      )}

      {nada && (
        <div className="bg-emerald-50 border border-emerald-100 rounded-2xl p-6 text-center">
          <CheckCircle2 size={36} className="text-emerald-500 mx-auto mb-2" />
          <p className="text-[16px] font-semibold text-gray-800">¡Todo al día! 🎉</p>
          <p className="text-[14px] text-gray-500 mt-1">No hay nada pendiente por ahora.</p>
        </div>
      )}

      {!loading && data && !data.error && (
        <>
          {/* Entregar pedidos */}
          {t.entregar?.total > 0 && (
            <Tarea icon={Package} color="bg-blue-50 text-blue-600"
              titulo={`📦 Entregar ${t.entregar.total} pedido${t.entregar.total === 1 ? '' : 's'}`}
              resumen="Pedidos pagados esperando empaque o entrega"
              onClick={() => navigate('/operacion')} cta="Ver pedidos">
              {(t.entregar.items || []).slice(0, 6).map((p, i) => (
                <div key={i} className="flex items-center justify-between text-[13.5px] bg-gray-50 rounded-lg px-3 py-2">
                  <span className="text-gray-800 truncate">{p.cliente} <span className="text-gray-400">· {p.numero}</span></span>
                  <span className="text-[12px] text-gray-500 shrink-0 ml-2">{p.estado}</span>
                </div>
              ))}
            </Tarea>
          )}

          {/* Fabricaciones listas */}
          {t.fabricacion_lista?.total > 0 && (
            <Tarea icon={Scissors} color="bg-violet-50 text-violet-600"
              titulo={`🧵 ${t.fabricacion_lista.total} fabricación(es) lista(s)`}
              resumen="Listas para entregar o llamar al cliente"
              onClick={() => navigate('/fabricacion')} cta="Ver fabricación" />
          )}

          {/* Cobrar */}
          {t.cobrar?.total > 0 && (
            <Tarea icon={Wallet} color="bg-amber-50 text-amber-600"
              titulo={`💰 Cobrar ${t.cobrar.total} factura${t.cobrar.total === 1 ? '' : 's'}`}
              resumen={`${cop(t.cobrar.monto)} pendiente por cobrar`}
              onClick={() => navigate('/cuentas')} cta="Ver cartera">
              {(t.cobrar.items || []).slice(0, 6).map((f, i) => (
                <div key={i} className="flex items-center justify-between text-[13.5px] bg-gray-50 rounded-lg px-3 py-2">
                  <span className="text-gray-800 truncate">{f.cliente} <span className="text-gray-400">· {f.numero}</span></span>
                  <span className="font-semibold text-gray-800 shrink-0 ml-2">{cop(f.saldo)}</span>
                </div>
              ))}
            </Tarea>
          )}

          {/* WhatsApp */}
          {t.whatsapp?.chats > 0 && (
            <Tarea icon={MessageCircle} color="bg-emerald-50 text-emerald-600"
              titulo={`💬 Responder ${t.whatsapp.chats} chat${t.whatsapp.chats === 1 ? '' : 's'}`}
              resumen={`${t.whatsapp.mensajes} mensaje(s) de clientes sin leer`}
              onClick={() => navigate('/whatsapp')} cta="Abrir WhatsApp" />
          )}

          {/* Citas */}
          {t.citas?.total > 0 && (
            <Tarea icon={CalendarClock} color="bg-sky-50 text-sky-600"
              titulo={`📅 ${t.citas.total} cita${t.citas.total === 1 ? '' : 's'} por atender`}
              resumen="Clientes que agendaron para medir/comprar"
              onClick={() => navigate('/citas')} cta="Ver citas">
              {(t.citas.items || []).slice(0, 5).map((c, i) => (
                <div key={i} className="text-[13.5px] bg-gray-50 rounded-lg px-3 py-2 text-gray-800">
                  {c.nombre} <span className="text-gray-400">· {c.dia || ''} {c.hora || ''} {c.colegio ? '· ' + c.colegio : ''}</span>
                </div>
              ))}
            </Tarea>
          )}
        </>
      )}
    </div>
  )
}
