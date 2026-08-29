import { useState, useEffect, useRef, useCallback, Component } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Send, RefreshCw, MessageCircle, Image as ImageIcon, ArrowLeft, AlertTriangle, Download, Bell, Trash2, UserRound, X } from 'lucide-react'
import { activarNotificaciones, estadoNotificaciones } from '../../services/push'
import FichaConversacion from './FichaConversacion'

// ── Error boundary: aísla fallos de render ──
// Evita que un solo mensaje/chat problemático tumbe toda la bandeja.
// Se le puede pasar `resetKey`: al cambiar (p.ej. al abrir otro chat) el
// boundary se reinicia y vuelve a intentar renderizar.
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  componentDidUpdate(prevProps) {
    if (this.state.hasError && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false })
    }
  }
  componentDidCatch(error, info) {
    // Log para diagnóstico; no relanza para no tumbar el árbol.
    console.error('[WhatsApp] error de render aislado:', error, info)
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="flex items-center gap-1.5 text-[11px] text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1 my-1">
          <AlertTriangle size={12} className="shrink-0" />
          <span>No se pudo cargar este mensaje</span>
        </div>
      )
    }
    return this.props.children
  }
}

// ── Estilos base para el fondo tipo WhatsApp ──
const WA_BG = 'wa-chat-bg'
const WA_TAB_BG = 'bg-[#f0f2f5]'

// Respuestas rápidas (plantillas) para el asesor
const RESPUESTAS_RAPIDAS = [
  { label: 'Saludo', text: '¡Hola! 😊 ¿En qué te podemos ayudar?' },
  { label: 'Pedido listo', text: 'Tu pedido ya está listo para recoger en el local 🎉' },
  { label: 'Ubicación', text: 'Nos encuentras en el C.C. San Andresito de la 68, Local M14, Bogotá. Horario: lunes y sábado de 10:00 a.m. a 5:00 p.m.' },
  { label: 'Trae al niñ@', text: 'Para tomar bien la talla, trae al niñ@ al local, sin compromiso 👦👧' },
  { label: 'Gracias', text: '¡Gracias por escribirnos! 🙏 Que tengas un feliz día.' },
]

function horaCorta(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('es-CO', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    })
  } catch { return '' }
}

function horaMensaje(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('es-CO', {
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return '' }
}

// Formatea fecha para separador de día
function diaSeparador(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const hoy = new Date()
    const ayer = new Date(hoy)
    ayer.setDate(ayer.getDate() - 1)
    if (d.toDateString() === hoy.toDateString()) return 'Hoy'
    if (d.toDateString() === ayer.toDateString()) return 'Ayer'
    return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'long' })
  } catch { return '' }
}

// ── Adjunto (imagen/archivo) ──
function Media({ id, tipo }) {
  const [src, setSrc] = useState(null)
  const [err, setErr] = useState(false)
  useEffect(() => {
    let ok = true
    setSrc(null)
    setErr(false)
    api.get(`/wa/media/${id}`)
      .then(r => {
        const b64 = r?.data?.media_b64
        if (ok) {
          if (typeof b64 === 'string' && b64) setSrc(b64)
          else setErr(true)
        }
      })
      .catch(() => { if (ok) setErr(true) })
    return () => { ok = false }
  }, [id])
  if (err) {
    return (
      <div className="mb-1 text-[11px] text-[#8696a0] italic">📎 Adjunto no disponible</div>
    )
  }
  if (!src) {
    return (
      <div className="mb-1 text-[11px] text-[#8696a0] italic">Cargando adjunto…</div>
    )
  }
  if (tipo === 'image') {
    return (
      <a href={src} target="_blank" rel="noopener" className="block mb-1">
        <img
          src={src}
          alt="adjunto"
          className="rounded-lg max-w-[260px] max-h-[320px] object-contain"
          onError={() => setErr(true)}
        />
      </a>
    )
  }
  if (tipo === 'audio') {
    return (
      <div className="mb-1">
        <audio controls preload="metadata" src={src} className="max-w-[260px] w-[260px]" />
        <a href={src} download="nota-de-voz.ogg" className="block text-[11px] text-[#8696a0] underline mt-0.5">
          Descargar audio
        </a>
      </div>
    )
  }
  return (
    <div className="mb-1">
      <a href={src} download className="text-xs underline">📎 Descargar archivo</a>
    </div>
  )
}

// ── Burbuja de mensaje ──
function Mensaje({ m, onEliminar }) {
  const esOut = m.direccion === 'out'
  return (
    <div className={`group flex items-center gap-1 ${esOut ? 'justify-end' : 'justify-start'} animate-[fadeInUp_0.2s_ease-out]`}>
      {/* Borrar (aparece al pasar el mouse) — solo del panel */}
      {esOut && onEliminar && (
        <button
          onClick={() => onEliminar(m.id_mensaje)}
          title="Borrar del panel (no del WhatsApp del cliente)"
          className="opacity-0 group-hover:opacity-100 transition-opacity text-[#8696a0] hover:text-red-500 p-1 shrink-0 order-first"
        >
          <Trash2 size={13} />
        </button>
      )}
      <div className={`relative max-w-[80%] lg:max-w-[70%] rounded-2xl px-3 py-1.5 shadow-sm ${
        esOut
          ? 'bg-[#dcf8c6] rounded-tr-sm'
          : 'bg-white rounded-tl-sm'
      }`}>
        {m.tiene_media && <Media id={m.id_mensaje} tipo={m.media_tipo} />}
        {m.texto && (
          <p className="text-[14.5px] leading-[1.45] text-gray-800 whitespace-pre-wrap break-words">
            {m.texto}
          </p>
        )}
        <div className={`flex items-center justify-end gap-1 mt-0.5 ${
          esOut ? 'text-[#8696a0]' : 'text-[#8696a0]'}`}>
          {m.autor !== 'sistema' && m.autor && (
            <span className="text-[10px] font-medium opacity-70">{m.autor}</span>
          )}
          <span className="text-[10px]">{horaMensaje(m.fecha)}</span>
          {esOut && m.autor !== 'sistema' && (
            // Un solo ✓ = enviado. El ✓✓ (leído) queda pendiente: requiere que el
            // bot procese los webhooks de estado de Meta y guardar el wamid al enviar.
            <span className="text-[10px] ml-0.5">✓</span>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Separador de día ──
function DiaSeparador({ fecha }) {
  return (
    <div className="flex items-center justify-center my-3">
      <span className="bg-white/80 backdrop-blur-sm text-[#54656f] text-[11px] font-medium px-3 py-1 rounded-lg shadow-sm border border-gray-100">
        {diaSeparador(fecha)}
      </span>
    </div>
  )
}

// ── Indicador de escribiendo ──
function Escribiendo() {
  return (
    <div className="flex items-center gap-1 px-4 pb-1">
      <div className="flex gap-[3px]">
        {[0, 1, 2].map(i => (
          <span key={i} className="w-1.5 h-1.5 bg-[#8696a0] rounded-full animate-[bounce_1.2s_infinite]"
            style={{ animationDelay: `${i * 0.2}s` }} />
        ))}
      </div>
      <span className="text-[11px] text-[#8696a0] ml-1">escribiendo…</span>
    </div>
  )
}

// ── Item de conversación ──
function ConvItem({ c, activo, onClick }) {
  const tieneLeidos = c.no_leidos > 0
  const esBot = c.modo !== 'humano'

  return (
    <button
      onClick={onClick}
      className={`w-full text-left flex items-center gap-3 px-4 py-3 border-b border-gray-100/60 hover:bg-gray-50/80 active:bg-gray-100 transition-all duration-150 ${
        activo ? 'bg-[#dcf8c6]/50' : ''
      }`}
    >
      {/* Avatar */}
      <div className="relative shrink-0">
        <div className={`w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold ${
          activo ? 'bg-[#25d366] text-white' : 'bg-[#dcf8c6] text-[#075e54]'
        }`}>
          {(c.nombre || c.chat_id).charAt(0).toUpperCase()}
        </div>
        {esBot && (
          <div className="absolute -bottom-0.5 -right-0.5 w-5 h-5 bg-[#25d366] rounded-full flex items-center justify-center border-2 border-white shadow-sm">
            <svg width="10" height="10" fill="white" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12c0 1.54.36 2.98.97 4.29L2 22l5.71-.97A9.96 9.96 0 0012 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm-.5 14.5v-1h1v-1.5c0-.28.22-.5.5-.5s.5.22.5.5v1.5h.5c.28 0 .5.22.5.5s-.22.5-.5.5h-2.5v1h2.5c.28 0 .5.22.5.5s-.22.5-.5.5h-.5v1.5c0 .28-.22.5-.5.5s-.5-.22-.5-.5V17h-1v1.5c0 .28-.22.5-.5.5s-.5-.22-.5-.5zm3.5-4.5c-2.48 0-4.5-2.02-4.5-4.5s2.02-4.5 4.5-4.5 4.5 2.02 4.5 4.5-2.02 4.5-4.5 4.5z"/>
            </svg>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className={`text-[14px] font-semibold truncate ${
            tieneLeidos ? 'text-gray-900' : 'text-gray-700'
          }`}>
            {c.nombre || c.chat_id}
          </span>
          <span className="text-[11px] text-[#8696a0] shrink-0">
            {horaCorta(c.ultima_fecha)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-2 mt-0.5">
          <span className="text-[12.5px] text-[#8696a0] truncate flex items-center gap-1">
            {esBot && (
              <svg width="12" height="12" fill="#8696a0" viewBox="0 0 24 24" className="shrink-0">
                <path d="M12 2C6.48 2 2 6.48 2 12c0 1.54.36 2.98.97 4.29L2 22l5.71-.97A9.96 9.96 0 0012 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm-.5 14.5v-1h1v-1.5c0-.28.22-.5.5-.5s.5.22.5.5v1.5h.5c.28 0 .5.22.5.5s-.22.5-.5.5h-2.5v1h2.5c.28 0 .5.22.5.5s-.22.5-.5.5h-.5v1.5c0 .28-.22.5-.5.5s-.5-.22-.5-.5V17h-1v1.5c0 .28-.22.5-.5.5s-.5-.22-.5-.5zm3.5-4.5c-2.48 0-4.5-2.02-4.5-4.5s2.02-4.5 4.5-4.5 4.5 2.02 4.5 4.5-2.02 4.5-4.5 4.5z"/>
              </svg>
            )}
            {c.ultimo_mensaje || 'Sin mensajes'}
          </span>
          {tieneLeidos && (
            <span className="bg-[#25d366] text-white text-[10px] font-bold rounded-full min-w-[20px] h-[20px] px-1.5 flex items-center justify-center shrink-0 shadow-sm">
              {c.no_leidos > 99 ? '99+' : c.no_leidos}
            </span>
          )}
        </div>
      </div>
    </button>
  )
}

// ── Main ──
export default function WhatsApp() {
  const [conversaciones, setConversaciones] = useState([])
  const [activo, setActivo] = useState(null)
  const [mensajes, setMensajes] = useState([])
  const [texto, setTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [enviandoImg, setEnviandoImg] = useState(false)
  const [cargandoConv, setCargandoConv] = useState(true)
  const [escribiendo, setEscribiendo] = useState(false)
  const finRef = useRef(null)
  const fileRef = useRef(null)
  const textareaRef = useRef(null)

  const convActiva = conversaciones.find(c => c.chat_id === activo)
  const [panelMovil, setPanelMovil] = useState('lista')
  const [filtro, setFiltro] = useState('todas')   // todas | no_leidas | bot | asesor
  const [busqueda, setBusqueda] = useState('')
  const [fichaMovil, setFichaMovil] = useState(false)  // ficha como panel deslizante en <xl

  const [descargando, setDescargando] = useState(false)
  const [notif, setNotif] = useState(estadoNotificaciones())
  const [activandoNotif, setActivandoNotif] = useState(false)

  const activarNotif = async () => {
    setActivandoNotif(true)
    try {
      const r = await activarNotificaciones()
      if (r.ok) { toast.success('Notificaciones activadas ✅'); setNotif('granted') }
      else toast.error(r.motivo || 'No se pudieron activar')
    } finally {
      setActivandoNotif(false)
    }
  }
  const descargarTodo = async () => {
    setDescargando(true)
    try {
      const res = await api.get('/wa/exportar', { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `whatsapp_raloz_${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      toast.success('Descargando el historial de WhatsApp')
    } catch {
      toast.error('No se pudo descargar')
    } finally {
      setDescargando(false)
    }
  }

  const cargarConversaciones = useCallback(async () => {
    try {
      const res = await api.get('/wa/conversaciones')
      setConversaciones(res.data || [])
    } catch { /* silencioso */ }
    finally { setCargandoConv(false) }
  }, [])

  const cargarMensajes = useCallback(async (chatId) => {
    if (!chatId) return
    try {
      const res = await api.get(`/wa/conversaciones/${chatId}/mensajes`)
      setMensajes(res.data || [])
    } catch { /* silencioso */ }
  }, [])

  useEffect(() => {
    cargarConversaciones()
    const id = setInterval(cargarConversaciones, 20000)
    return () => clearInterval(id)
  }, [cargarConversaciones])

  useEffect(() => {
    if (!activo) return
    cargarMensajes(activo)
    const id = setInterval(() => cargarMensajes(activo), 12000)
    return () => clearInterval(id)
  }, [activo, cargarMensajes])

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes])

  // Detectar "escribiendo" por actividad reciente del cliente
  useEffect(() => {
    if (!convActiva) return
    const recientes = mensajes.filter(m =>
      m.direccion === 'in' &&
      new Date(m.fecha) > new Date(Date.now() - 60000)
    )
    setEscribiendo(recientes.length > 0)
    const t = setTimeout(() => setEscribiendo(false), 5000)
    return () => clearTimeout(t)
  }, [mensajes, convActiva])

  const abrir = (chatId) => {
    setActivo(chatId)
    setConversaciones(prev => prev.map(c =>
      c.chat_id === chatId ? { ...c, no_leidos: 0 } : c))
    setPanelMovil('chat')
    setTimeout(() => textareaRef.current?.focus(), 300)
  }

  const volverALista = () => {
    setActivo(null)
    setPanelMovil('lista')
  }

  const enviar = async (e) => {
    e?.preventDefault()
    const t = texto.trim()
    if (!t || !activo) return
    setEnviando(true)
    try {
      await api.post(`/wa/conversaciones/${activo}/enviar`, { texto: t })
      setTexto('')
      await cargarMensajes(activo)
      cargarConversaciones()
    } catch (err) {
      toast.error(err.response?.data?.error || 'No se pudo enviar')
    } finally { setEnviando(false) }
  }

  // Enviar un texto puntual (p. ej. "Enviar catálogo" desde la ficha)
  const enviarTexto = async (t) => {
    if (!t || !activo) return
    try {
      await api.post(`/wa/conversaciones/${activo}/enviar`, { texto: t })
      await cargarMensajes(activo)
      cargarConversaciones()
      toast.success('Mensaje enviado ✅')
    } catch (err) {
      toast.error(err.response?.data?.error || 'No se pudo enviar')
    }
  }

  // Borra un mensaje SOLO del panel (no del WhatsApp del cliente — Meta no lo permite)
  const eliminarMensaje = async (idMensaje) => {
    if (!activo || !idMensaje) return
    if (!window.confirm('¿Borrar este mensaje del panel?\n\nOjo: se quita solo de aquí, NO del WhatsApp del cliente.')) return
    // Optimista: lo quitamos de la vista ya
    setMensajes(prev => prev.filter(m => m.id_mensaje !== idMensaje))
    try {
      await api.delete(`/wa/conversaciones/${activo}/mensajes/${idMensaje}`)
      cargarConversaciones()
    } catch (err) {
      toast.error(err.response?.data?.error || 'No se pudo borrar')
      cargarMensajes(activo)   // revertir si falló
    }
  }

  const enviarImagen = (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !activo) return
    const reader = new FileReader()
    reader.onload = async () => {
      setEnviandoImg(true)
      try {
        await api.post(`/wa/conversaciones/${activo}/enviar-imagen`,
          { imagen_b64: reader.result, caption: texto.trim() })
        setTexto('')
        await cargarMensajes(activo)
        cargarConversaciones()
      } catch (err) {
        toast.error(err.response?.data?.error || 'No se pudo enviar la imagen')
      } finally { setEnviandoImg(false) }
    }
    reader.readAsDataURL(file)
  }

  const cambiarModo = async (modo) => {
    if (!activo) return
    try {
      await api.post(`/wa/conversaciones/${activo}/modo`, { modo })
      setConversaciones(prev => prev.map(c =>
        c.chat_id === activo ? { ...c, modo } : c))
      toast.success(modo === 'humano' ? 'Ahora tú atiendes 💬' : 'El bot vuelve 🤖')
    } catch {
      toast.error('No se pudo cambiar el modo')
    }
  }

  // Totales
  const totalSinLeer = conversaciones.reduce((s, c) => s + (c.no_leidos || 0), 0)
  const totalConv = conversaciones.length
  const contConNoLeidos = conversaciones.filter(c => (c.no_leidos || 0) > 0).length
  const contAsignadas = conversaciones.filter(c => c.asignado_a).length

  // Filtro + búsqueda sobre la lista
  const q = busqueda.trim().toLowerCase()
  const convFiltradas = conversaciones.filter(c => {
    if (filtro === 'no_leidas' && !(c.no_leidos > 0)) return false
    if (filtro === 'asignadas' && !c.asignado_a) return false
    if (filtro === 'sin_asignar' && c.asignado_a) return false
    if (q) {
      const txt = `${c.nombre || ''} ${c.chat_id || ''} ${c.ultimo_mensaje || ''}`.toLowerCase()
      if (!txt.includes(q)) return false
    }
    return true
  })

  const FILTROS = [
    { id: 'todas',       label: 'Todas',       n: totalConv },
    { id: 'no_leidas',   label: 'No leídas',   n: contConNoLeidos },
    { id: 'asignadas',   label: 'Asignadas',   n: contAsignadas },
    { id: 'sin_asignar', label: 'Sin asignar', n: totalConv - contAsignadas },
  ]

  return (
    <div className={`flex h-[calc(100dvh-160px)] lg:h-[calc(100vh-120px)] overflow-hidden rounded-none lg:rounded-xl`}>

      {/* ────────────────────────────────────
          PANEL LISTA DE CONVERSACIONES
      ──────────────────────────────────── */}
      <div className={`
        flex flex-col bg-white w-full lg:max-w-[340px] lg:shrink-0
        border-r border-gray-200/80
        ${panelMovil === 'lista' ? 'flex' : 'hidden lg:flex'}
      `}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100/80"
          style={{ background: WA_TAB_BG }}>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full bg-[#25d366] flex items-center justify-center shadow-sm">
              <svg width="18" height="18" fill="white" viewBox="0 0 24 24">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
                <path d="M12 0C5.373 0 0 5.373 0 12c0 2.025.507 3.934 1.395 5.638L0 24l6.362-1.395A11.94 11.94 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-1.855 0-3.627-.444-5.212-1.234l-.374-.201-3.879.851.83-3.837-.218-.364A9.46 9.46 0 012 12C2 6.477 6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z"/>
              </svg>
            </div>
            <div>
              <h2 className="text-[14px] font-semibold text-gray-800">WhatsApp</h2>
              <p className="text-[11px] text-[#8696a0]">
                {totalConv} conversación{totalConv !== 1 ? 's' : ''}
                {totalSinLeer > 0 && ` · ${totalSinLeer} sin leer`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button onClick={activarNotif} disabled={activandoNotif}
              title={notif === 'granted' ? 'Notificaciones activas' : 'Activar notificaciones'}
              className={`p-2 rounded-full transition disabled:opacity-50 hover:bg-gray-100 ${
                notif === 'granted' ? 'text-[#25d366]' : 'text-[#8696a0] hover:text-[#075e54]'
              }`}>
              <Bell size={16} className={activandoNotif ? 'animate-pulse' : ''} fill={notif === 'granted' ? 'currentColor' : 'none'} />
            </button>
            <button onClick={descargarTodo} disabled={descargando} title="Descargar historial (CSV)"
              className="p-2 text-[#8696a0] hover:text-[#075e54] hover:bg-gray-100 rounded-full transition disabled:opacity-50">
              {descargando ? <RefreshCw size={16} className="animate-spin" /> : <Download size={16} />}
            </button>
            <button onClick={cargarConversaciones} title="Actualizar"
              className="p-2 text-[#8696a0] hover:text-[#075e54] hover:bg-gray-100 rounded-full transition">
              <RefreshCw size={16} className={cargandoConv ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Buscador funcional */}
        <div className="px-3 py-2 border-b border-gray-100/60">
          <div className="flex items-center gap-2 bg-[#f0f2f5] rounded-lg px-3 py-2">
            <svg width="14" height="14" fill="#8696a0" viewBox="0 0 24 24">
              <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
            <input
              type="text"
              value={busqueda}
              onChange={e => setBusqueda(e.target.value)}
              placeholder="Buscar conversación…"
              className="flex-1 bg-transparent text-[13px] text-gray-700 placeholder-[#8696a0] outline-none"
            />
          </div>
        </div>

        {/* Filtros */}
        <div className="flex items-center gap-1.5 px-3 py-2 border-b border-gray-100/60 overflow-x-auto scrollbar-thin">
          {FILTROS.map(f => (
            <button key={f.id} onClick={() => setFiltro(f.id)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[12px] font-medium whitespace-nowrap transition-colors ${
                filtro === f.id ? 'bg-[#25d366] text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}>
              {f.label}
              <span className={`text-[10px] font-bold ${filtro === f.id ? 'text-white/90' : 'text-gray-400'}`}>{f.n}</span>
            </button>
          ))}
        </div>

        {/* Lista */}
        <div className="flex-1 overflow-y-auto">
          {cargandoConv ? (
            <div className="flex flex-col items-center justify-center h-40 gap-3">
              <div className="w-8 h-8 border-2 border-[#25d366] border-t-transparent rounded-full animate-spin" />
              <p className="text-[12px] text-[#8696a0]">Cargando conversaciones…</p>
            </div>
          ) : conversaciones.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-52 gap-3">
              <div className="w-16 h-16 rounded-full bg-[#dcf8c6] flex items-center justify-center">
                <MessageCircle size={28} className="text-[#25d366]" />
              </div>
              <p className="text-[13px] text-[#8696a0] font-medium">Aún no hay conversaciones</p>
              <p className="text-[11px] text-[#8696a0]/70">Los mensajes de clientes aparecerán aquí</p>
            </div>
          ) : convFiltradas.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 gap-2 text-center px-6">
              <p className="text-[13px] text-[#8696a0] font-medium">Sin resultados</p>
              <p className="text-[11px] text-[#8696a0]/70">Prueba otro filtro o búsqueda</p>
            </div>
          ) : convFiltradas.map(c => (
            <ConvItem
              key={c.chat_id}
              c={c}
              activo={activo === c.chat_id}
              onClick={() => abrir(c.chat_id)}
            />
          ))}
        </div>
      </div>

      {/* ────────────────────────────────────
          PANEL CHAT
      ──────────────────────────────────── */}
      <div className={`
        flex flex-col flex-1 overflow-hidden
        ${panelMovil === 'chat' ? 'flex' : 'hidden lg:flex'}
      `}>
        <ErrorBoundary
          resetKey={activo}
          fallback={
            <div className="flex-1 flex flex-col items-center justify-center wa-chat-bg p-6 text-center">
              <div className="w-14 h-14 rounded-full bg-amber-100 flex items-center justify-center mb-3">
                <AlertTriangle size={26} className="text-amber-500" />
              </div>
              <p className="text-[14px] font-semibold text-gray-700 mb-1">No se pudo mostrar este chat</p>
              <p className="text-[12px] text-[#8696a0] max-w-xs mb-4">
                Ocurrió un problema al cargar esta conversación. Puedes abrir otra o volver a la lista.
              </p>
              <button onClick={volverALista}
                className="text-[13px] font-medium px-4 py-2 rounded-full bg-[#25d366] text-white hover:bg-[#20bd5a] transition shadow-sm">
                Volver a la lista
              </button>
            </div>
          }
        >
        {!activo ? (
          /* Empty state desktop */
          <div className="flex-1 flex flex-col items-center justify-center wa-chat-bg">
            <div className="bg-white rounded-2xl p-8 shadow-lg text-center max-w-sm mx-4">
              <div className="w-20 h-20 rounded-full bg-[#dcf8c6] flex items-center justify-center mx-auto mb-4 shadow-sm">
                <svg width="36" height="36" fill="#075e54" viewBox="0 0 24 24">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
                  <path d="M12 0C5.373 0 0 5.373 0 12c0 2.025.507 3.934 1.395 5.638L0 24l6.362-1.395A11.94 11.94 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0z"/>
                </svg>
              </div>
              <h3 className="text-[17px] font-bold text-gray-800 mb-1">WhatsApp Business</h3>
              <p className="text-[13px] text-[#8696a0] leading-relaxed">
                Selecciona una conversación de la lista para ver los mensajes y atender a tus clientes.
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Header del chat */}
            <div className="flex items-center gap-3 px-3 lg:px-4 py-2.5 border-b border-gray-200/80 bg-white shadow-sm z-10"
              style={{ background: 'white' }}>
              {/* Volver (móvil) */}
              <button onClick={volverALista}
                className="p-1.5 text-[#54656f] hover:bg-gray-100 rounded-full transition lg:hidden">
                <ArrowLeft size={20} />
              </button>

              {/* Avatar */}
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-[15px] font-bold shrink-0 ${
                convActiva?.modo === 'humano' ? 'bg-[#25d366] text-white' : 'bg-[#dcf8c6] text-[#075e54]'
              }`}>
                {(convActiva?.nombre || activo).charAt(0).toUpperCase()}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-[15px] font-semibold text-gray-800 truncate">
                  {convActiva?.nombre || activo}
                </p>
                <p className="text-[11.5px] text-[#8696a0] truncate flex items-center gap-1">
                  {convActiva?.asignado_a ? (
                    <span className="text-amber-600 font-medium">Asignado a {convActiva.asignado_a}</span>
                  ) : (
                    <>{activo}{convActiva?.modo === 'humano' ? ' · Atendido por ti' : ' · Atendido por bot'}</>
                  )}
                </p>
              </div>

              {/* Botón modo */}
              {convActiva?.modo === 'humano' ? (
                <button onClick={() => cambiarModo('bot')}
                  className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-full bg-[#dcf8c6] text-[#075e54] hover:bg-[#c8f0c0] transition shadow-sm">
                  <svg width="12" height="12" fill="#075e54" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12c0 1.54.36 2.98.97 4.29L2 22l5.71-.97A9.96 9.96 0 0012 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm-.5 14.5v-1h1v-1.5c0-.28.22-.5.5-.5s.5.22.5.5v1.5h.5c.28 0 .5.22.5.5s-.22.5-.5.5h-2.5v1h2.5c.28 0 .5.22.5.5s-.22.5-.5.5h-.5v1.5c0 .28-.22.5-.5.5s-.5-.22-.5-.5V17h-1v1.5c0 .28-.22.5-.5.5s-.5-.22-.5-.5zm3.5-4.5c-2.48 0-4.5-2.02-4.5-4.5s2.02-4.5 4.5-4.5 4.5 2.02 4.5 4.5-2.02 4.5-4.5 4.5z"/>
                  </svg>
                  Bot
                </button>
              ) : (
                <button onClick={() => cambiarModo('humano')}
                  className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-full bg-[#25d366] text-white hover:bg-[#20bd5a] transition shadow-sm">
                  Yo
                </button>
              )}
              {/* Ver ficha del cliente (solo <xl, donde la 3ª columna no cabe) */}
              <button onClick={() => setFichaMovil(true)} title="Ficha del cliente"
                className="xl:hidden p-2 text-[#54656f] hover:text-[#075e54] hover:bg-gray-100 rounded-full transition">
                <UserRound size={18} />
              </button>
            </div>

            {/* Área de mensajes */}
            <div className={`flex-1 overflow-y-auto p-3 lg:p-4 ${WA_BG}`}>
              {(() => {
                let ultD = null
                return mensajes.map(m => {
                  const d = new Date(m.fecha).toDateString()
                  const sep = d !== ultD
                  if (sep) ultD = d
                  return (
                    <div key={m.id_mensaje}>
                      {sep && <DiaSeparador fecha={m.fecha} />}
                      <ErrorBoundary resetKey={m.id_mensaje}>
                        <Mensaje m={m} onEliminar={eliminarMensaje} />
                      </ErrorBoundary>
                    </div>
                  )
                })
              })()}
              {escribiendo && <Escribiendo />}
              <div ref={finRef} className="h-2" />
            </div>

            {/* Respuestas rápidas + input */}
            <div className="bg-[#f0f2f5] border-t border-gray-200/60">
              {/* Respuestas rápidas */}
              <div className="flex gap-1.5 px-3 pt-2 overflow-x-auto whitespace-nowrap scrollbar-hide"
                style={{ scrollbarWidth: 'none' }}>
                {RESPUESTAS_RAPIDAS.map((q, i) => (
                  <button key={i} type="button" onClick={() => {
                    setTexto(q.text)
                    textareaRef.current?.focus()
                  }}
                    className="text-[11px] font-medium px-3 py-1 rounded-full bg-white text-[#54656f] border border-gray-200 hover:bg-[#dcf8c6] hover:text-[#075e54] hover:border-[#c8f0c0] transition shadow-sm shrink-0">
                    {q.label}
                  </button>
                ))}
              </div>

              {/* Input */}
              <form onSubmit={enviar} className="flex items-end gap-2 p-2 lg:p-3">
                <input type="file" accept="image/*" ref={fileRef} onChange={enviarImagen} className="hidden" />
                <button type="button" onClick={() => fileRef.current?.click()} disabled={enviandoImg}
                  title="Enviar foto"
                  className="p-2.5 text-[#54656f] hover:text-[#075e54] hover:bg-gray-200 rounded-full transition disabled:opacity-50 shrink-0">
                  {enviandoImg ? (
                    <div className="w-5 h-5 border-2 border-[#8696a0] border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <ImageIcon size={20} />
                  )}
                </button>
                <div className="flex-1 relative">
                  <textarea
                    ref={textareaRef}
                    value={texto}
                    onChange={e => setTexto(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        enviar()
                      }
                    }}
                    placeholder="Escribe un mensaje…"
                    rows={1}
                    className="w-full px-4 py-2.5 text-[14px] bg-white border border-gray-200 rounded-3xl resize-none outline-none focus:border-[#25d366] focus:ring-2 focus:ring-[#25d366]/20 transition-all"
                    style={{ minHeight: '44px', maxHeight: '120px' }}
                  />
                </div>
                <button type="submit" disabled={enviando || !texto.trim()}
                  className={`p-2.5 rounded-full transition shrink-0 ${
                    texto.trim()
                      ? 'bg-[#00a884] text-white hover:bg-[#008069] shadow-sm'
                      : 'bg-[#dcf8c6] text-[#8696a0]'
                  }`}>
                  <Send size={18} className={enviando ? 'animate-pulse' : ''} />
                </button>
              </form>
            </div>
          </>
        )}
        </ErrorBoundary>
      </div>

      {/* ────────────────────────────────────
          PANEL FICHA (Cliente 360) — 3ª columna
          Se muestra en pantallas anchas cuando hay un chat activo.
      ──────────────────────────────────── */}
      {activo && (
        <div className="hidden xl:flex flex-col bg-white w-[330px] shrink-0 border-l border-gray-200/80">
          <FichaConversacion conv={convActiva} onEnviarMensaje={enviarTexto} onToggleModo={cambiarModo} onActualizar={cargarConversaciones} />
        </div>
      )}

      {/* Ficha como panel deslizante en pantallas <xl */}
      {activo && fichaMovil && (
        <div className="xl:hidden fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/40" onClick={() => setFichaMovil(false)} />
          <div className="relative bg-white w-[85%] max-w-[340px] h-full flex flex-col shadow-2xl animate-[fadeInUp_0.15s_ease-out]">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <span className="text-[14px] font-semibold text-gray-800">Ficha del cliente</span>
              <button onClick={() => setFichaMovil(false)} className="p-1.5 text-gray-400 hover:text-gray-700 rounded-full hover:bg-gray-100">
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <FichaConversacion conv={convActiva} onEnviarMensaje={enviarTexto} onToggleModo={cambiarModo} onActualizar={cargarConversaciones} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
