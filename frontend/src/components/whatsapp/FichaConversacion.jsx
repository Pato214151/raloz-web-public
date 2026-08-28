import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import {
  User, Phone, School, GraduationCap, ExternalLink, ShoppingCart, ClipboardList,
  CalendarClock, Send, UserCheck, Bot, CheckCircle2,
} from 'lucide-react'

const TIENDA_URL = 'https://ralozcolsas.com'

// Solo dígitos; deja los últimos 10 (celular CO sin indicativo) para buscar al cliente.
const tel10 = (s) => String(s || '').replace(/\D/g, '').slice(-10)

function Accion({ icon: Icon, label, onClick, tone = 'default' }) {
  const tones = {
    default: 'border-gray-200 text-gray-700 hover:bg-gray-50',
    amber: 'border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100',
    green: 'border-green-200 text-green-700 hover:bg-green-50',
  }
  return (
    <button onClick={onClick}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-[12.5px] font-medium transition-colors ${tones[tone]}`}>
      <Icon size={15} className="shrink-0" /> <span className="truncate">{label}</span>
    </button>
  )
}

export default function FichaConversacion({ conv, onEnviarMensaje, onToggleModo }) {
  const navigate = useNavigate()
  const [cliente, setCliente] = useState(null)
  const [buscando, setBuscando] = useState(false)

  const phone = tel10(conv?.chat_id)
  const esHumano = conv?.modo === 'humano'

  useEffect(() => {
    if (!phone) { setCliente(null); return }
    let vivo = true
    setBuscando(true)
    setCliente(null)
    api.get('/clientes', { params: { buscar: phone, per_page: 5 } })
      .then(res => {
        if (!vivo) return
        const lista = res.data?.clientes || []
        const match = lista.find(c => tel10(c.telefono) === phone || tel10(c.celular) === phone) || lista[0] || null
        setCliente(match)
      })
      .catch(() => { if (vivo) setCliente(null) })
      .finally(() => { if (vivo) setBuscando(false) })
    return () => { vivo = false }
  }, [phone])

  if (!conv) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-6 text-gray-400">
        <User size={30} className="mb-2 opacity-40" />
        <p className="text-[13px]">Abre una conversación para ver la ficha del cliente.</p>
      </div>
    )
  }

  const nombre = cliente?.nombre || conv.nombre || conv.chat_id
  const telMostrar = conv.chat_id?.startsWith('57') ? '+' + conv.chat_id : (conv.chat_id || '')

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Cabecera */}
      <div className="px-4 py-4 border-b border-gray-100 flex flex-col items-center text-center">
        <div className="w-16 h-16 rounded-full bg-[#dcf8c6] text-[#075e54] flex items-center justify-center text-2xl font-bold mb-2">
          {nombre.charAt(0).toUpperCase()}
        </div>
        <p className="text-[15px] font-bold text-gray-900 leading-tight">{nombre}</p>
        <p className="text-[12.5px] text-gray-400 flex items-center gap-1 mt-0.5">
          <Phone size={12} /> {telMostrar}
        </p>
        <span className={`mt-2 text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${
          esHumano ? 'bg-blue-50 text-blue-700' : 'bg-green-50 text-green-700'
        }`}>
          {esHumano ? '💬 Atendido por asesor' : '🤖 Atendido por el bot'}
        </span>
      </div>

      {/* Información del cliente */}
      <div className="px-4 py-3 border-b border-gray-100">
        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">Información del cliente</p>
        {buscando ? (
          <p className="text-[12.5px] text-gray-400">Buscando cliente…</p>
        ) : cliente ? (
          <div className="space-y-2 text-[13px]">
            <Fila icon={School}         label="Colegio"    valor={cliente.colegio_nombre} />
            <Fila icon={GraduationCap}  label="Estudiante" valor={cliente.estudiante_nombre} />
            <Fila icon={User}           label="Grado"      valor={cliente.estudiante_grado} />
            <button onClick={() => navigate('/clientes')}
              className="mt-1 flex items-center gap-1 text-[12.5px] font-medium text-amber-700 hover:text-amber-800">
              Ver perfil completo <ExternalLink size={12} />
            </button>
          </div>
        ) : (
          <div className="text-[12.5px] text-gray-500">
            <p>Este número no está registrado como cliente.</p>
            <button onClick={() => navigate('/clientes')}
              className="mt-1.5 flex items-center gap-1 text-amber-700 font-medium hover:text-amber-800">
              + Crear cliente <ExternalLink size={12} />
            </button>
          </div>
        )}
      </div>

      {/* Acciones rápidas */}
      <div className="px-4 py-3 border-b border-gray-100">
        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">Acciones rápidas</p>
        <div className="grid grid-cols-2 gap-2">
          <Accion icon={ClipboardList} label="Ver pedidos"     onClick={() => navigate('/operacion')} />
          <Accion icon={ShoppingCart}  label="Nueva venta"     onClick={() => navigate('/ventas?tab=nueva')} />
          <Accion icon={CalendarClock} label="Crear cita"      onClick={() => navigate('/clientes?tab=citas')} />
          <Accion icon={Send}          label="Enviar catálogo" onClick={() => onEnviarMensaje?.(
            `¡Hola${cliente?.nombre ? ' ' + cliente.nombre.split(' ')[0] : ''}! 👋 Mira nuestro catálogo y compra en línea aquí 👉 ${TIENDA_URL}`
          )} />
          {esHumano ? (
            <Accion icon={CheckCircle2} tone="green" label="Marcar atendido" onClick={() => onToggleModo?.('bot')} />
          ) : (
            <Accion icon={UserCheck}    tone="amber" label="Atenderlo yo"    onClick={() => onToggleModo?.('humano')} />
          )}
        </div>
      </div>

      {/* Contexto (etiquetas de solo lectura por ahora) */}
      <div className="px-4 py-3">
        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">Etiquetas</p>
        <div className="flex flex-wrap gap-1.5">
          {cliente?.colegio_nombre && <Chip>{cliente.colegio_nombre}</Chip>}
          <Chip tone={esHumano ? 'blue' : 'green'}>{esHumano ? 'Con asesor' : 'Con bot'}</Chip>
          {(conv.no_leidos || 0) > 0 && <Chip tone="red">Sin leer</Chip>}
        </div>
        <p className="text-[11px] text-gray-300 mt-2">Etiquetas y notas editables — próximamente.</p>
      </div>
    </div>
  )
}

function Fila({ icon: Icon, label, valor }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="flex items-center gap-1.5 text-gray-500"><Icon size={13} /> {label}</span>
      <span className="font-semibold text-gray-800 truncate max-w-[55%] text-right">{valor || '—'}</span>
    </div>
  )
}

function Chip({ children, tone = 'gray' }) {
  const tones = {
    gray: 'bg-gray-100 text-gray-600',
    green: 'bg-green-50 text-green-700',
    blue: 'bg-blue-50 text-blue-700',
    red: 'bg-red-50 text-red-600',
  }
  return <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${tones[tone]}`}>{children}</span>
}
