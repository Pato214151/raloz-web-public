import { useState } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Search, Loader2, User, Phone, Send, MessageCircle } from 'lucide-react'

// Normaliza a formato internacional (Colombia: 10 díg. → 57XXXXXXXXXX)
function normalizar(telefono) {
  let t = (telefono || '').replace(/\D/g, '')
  if (t.length === 10 && t.startsWith('3')) t = '57' + t
  return t
}
function waLink(telefono, nombre) {
  const t = normalizar(telefono)
  const saludo = encodeURIComponent(`Hola${nombre ? ' ' + nombre.split(' ')[0] : ''}, te escribo de RALOZ 👋`)
  return `https://wa.me/${t}?text=${saludo}`
}
const ORIGEN_LBL = {
  cliente: 'Cliente', pedido: 'Pedido', 'contacto web': 'Contacto web',
  suscriptor: 'Suscriptor', whatsapp: 'WhatsApp',
}

export default function BuscarContacto() {
  const [q, setQ] = useState('')
  const [contactos, setContactos] = useState([])
  const [loading, setLoading] = useState(false)
  const [buscado, setBuscado] = useState(false)
  // Composer "enviar desde el sistema"
  const [openTel, setOpenTel] = useState(null)
  const [msg, setMsg] = useState('')
  const [sending, setSending] = useState(false)

  async function buscar(e) {
    e?.preventDefault()
    if (q.trim().length < 2) { toast.error('Escribe al menos 2 letras o números'); return }
    setLoading(true)
    setBuscado(true)
    setOpenTel(null)
    try {
      const { data } = await api.get('/tienda/admin/buscar-contacto', { params: { q: q.trim() } })
      setContactos(data.contactos || [])
    } catch {
      toast.error('No se pudo buscar')
    } finally {
      setLoading(false)
    }
  }

  async function enviarSistema(telefono) {
    if (!msg.trim()) { toast.error('Escribe el mensaje'); return }
    setSending(true)
    try {
      await api.post(`/wa/conversaciones/${normalizar(telefono)}/enviar`, { texto: msg.trim() })
      toast.success('¡Enviado desde tu WhatsApp Business!')
      setMsg('')
      setOpenTel(null)
    } catch {
      toast.error(
        'WhatsApp no dejó enviarlo desde el sistema: solo se puede si el cliente te escribió en las últimas 24h. Usa el botón verde “WhatsApp” para escribirle desde tu teléfono.',
        { duration: 8000 },
      )
    } finally {
      setSending(false)
    }
  }

  const soloDigitos = q.replace(/\D/g, '')
  const numeroDirecto = soloDigitos.length >= 7 ? soloDigitos : null

  // Fila reutilizable para un contacto
  const Fila = ({ nombre, telefono, origen, directo }) => {
    const abierto = openTel === telefono
    return (
      <div className={`border rounded-xl p-3 ${directo ? 'border-green-200 bg-green-50' : 'border-gray-100'}`}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gray-100 grid place-items-center text-gray-400 shrink-0">
            {directo ? <Phone className="w-5 h-5" /> : <User className="w-5 h-5" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm text-gray-800 truncate">
              {directo ? `Escribir al número ${telefono}` : (nombre || 'Sin nombre')}
            </div>
            <div className="text-xs text-gray-400">
              {directo ? 'Abre WhatsApp aunque no esté registrado' : `${telefono} · ${ORIGEN_LBL[origen] || origen}`}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => { setOpenTel(abierto ? null : telefono); setMsg('') }}
              className="inline-flex items-center gap-1.5 text-gray-600 hover:bg-gray-100 border border-gray-200 text-sm font-medium px-3 py-2 rounded-lg"
              title="Enviar desde el sistema (bot)"
            >
              <MessageCircle className="w-4 h-4" /> Enviar aquí
            </button>
            <a
              href={waLink(telefono, nombre)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold px-3 py-2 rounded-lg"
            >
              WhatsApp
            </a>
          </div>
        </div>

        {abierto && (
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
            <textarea
              value={msg}
              onChange={(e) => setMsg(e.target.value)}
              rows={2}
              maxLength={1000}
              placeholder="Escribe el mensaje…"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] text-gray-400">Se envía desde tu número del sistema. Solo funciona si el cliente escribió en las últimas 24 h.</span>
              <button
                type="button"
                onClick={() => enviarSistema(telefono)}
                disabled={sending}
                className="inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold px-3 py-2 rounded-lg shrink-0"
              >
                {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Enviar
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-green-100 rounded-lg shrink-0">
          <Search className="w-6 h-6 text-green-700" />
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Escribir a un cliente</h1>
          <p className="text-gray-600 text-xs sm:text-sm">
            Busca a un papá por nombre o número y escríbele por WhatsApp.
          </p>
        </div>
      </div>

      <form onSubmit={buscar} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Nombre o número de WhatsApp…"
            className="w-full pl-9 pr-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-200"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white text-sm font-semibold px-4 py-2.5 rounded-lg"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Buscar
        </button>
      </form>

      {/* Explicación de las dos formas */}
      <div className="text-xs text-gray-500 bg-gray-50 border border-gray-100 rounded-lg p-3 space-y-1">
        <p><b className="text-green-700">WhatsApp</b> → abre tu WhatsApp (Web o celular) para escribirle tú. Funciona con cualquiera.</p>
        <p><b className="text-blue-700">Enviar aquí</b> → manda el mensaje desde el número del sistema, sin salir. Solo si el cliente te escribió en las últimas 24 h.</p>
      </div>

      {numeroDirecto && <Fila telefono={numeroDirecto} directo />}

      {buscado && !loading && (
        contactos.length === 0 ? (
          <p className="text-center text-gray-400 py-8 text-sm">
            No encontré contactos con “{q}”. Si tienes el número, escríbelo arriba para escribir directo.
          </p>
        ) : (
          <div className="space-y-2">
            {contactos.map((c) => (
              <Fila key={c.telefono} nombre={c.nombre} telefono={c.telefono} origen={c.origen} />
            ))}
          </div>
        )
      )}
    </div>
  )
}
