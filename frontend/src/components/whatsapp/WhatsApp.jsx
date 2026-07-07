import { useState, useEffect, useRef, useCallback } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Send, RefreshCw, MessageCircle, Image as ImageIcon, ArrowLeft } from 'lucide-react'

// ── Estilos base para el fondo tipo WhatsApp ──
const WA_BG = 'bg-[#efeae2]'
const WA_GREEN = 'bg-[#dcf8c6]'
const WA_HEADER_BG = '#075e54'
const WA_TAB_BG = '#f0f2f5'
const WA_CHAT_BAR_BG = '#ffffff'

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
    api.get(`/wa/media/${id}`)
      .then(r => { if (ok) setSrc(r.data.media_b64) })
      .catch(() => { if (ok) setErr(true) })
    return () => { ok = false }
  }, [id])
  if (err) return null
  if (!src) return null
  if (tipo === 'image') {
    return (
      <a href={src} target="_blank" rel="noopener" className="block mb-1">
        <img src={src} alt="adjunto" className="rounded-lg max-w-[260px] max-h-[320px] object-contain" />
      </a>
    )
  }
  return <a href={src} download className="text-xs underline mb-1 inline-block">📎 Descargar archivo</a>
}

// ── Burbuja de mensaje ──
function Mensaje({ m }) {
  const esOut = m.direccion === 'out'
  return (
    <div className={`flex ${esOut ? 'justify-end' : 'justify-start'} animate-[fadeInUp_0.2s_ease-out]`}>
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
          {esOut && (
            <span className="text-[10px] ml-0.5">
              {m.leido ? '✓✓' : m.autor === 'sistema' ? '' : '✓'}
            </span>
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
            {horaCorta(c.ultima_actividad || c.fecha_creacion)}
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
  const [ultimoDia, setUltimoDia] = useState(null)
  const finRef = useRef(null)
  const fileRef = useRef(null)
  const textareaRef = useRef(null)

  const convActiva = conversaciones.find(c => c.chat_id === activo)
  const [panelMovil, setPanelMovil] = useState('lista')

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

  // Agrupar mensajes por día para separadores
  const mensajesConSeparador = mensajes.map(m => {
    const d = new Date(m.fecha).toDateString()
    const sep = d !== ultimoDia
    if (sep) setUltimoDia(d)
    return { ...m, nuevoDia: sep }
  })

  // Totales
  const totalSinLeer = conversaciones.reduce((s, c) => s + (c.no_leidos || 0), 0)
  const totalConv = conversaciones.length

  return (
    <div className={`flex h-[calc(100vh-80px)] lg:h-[calc(100vh-120px)] overflow-hidden`}>

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
          <button onClick={cargarConversaciones} title="Actualizar"
            className="p-2 text-[#8696a0] hover:text-[#075e54] hover:bg-gray-100 rounded-full transition">
            <RefreshCw size={16} className={cargandoConv ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Search bar (visual, funcionalmente no filtra aún) */}
        <div className="px-3 py-2 border-b border-gray-100/60">
          <div className="flex items-center gap-2 bg-[#f0f2f5] rounded-lg px-3 py-2">
            <svg width="14" height="14" fill="#8696a0" viewBox="0 0 24 24">
              <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
            <input
              type="text"
              placeholder="Buscar o iniciar.chat"
              className="flex-1 bg-transparent text-[13px] text-gray-700 placeholder-[#8696a0] outline-none"
            />
          </div>
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
          ) : conversaciones.map(c => (
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
        {!activo ? (
          /* Empty state desktop */
          <div className="flex-1 flex flex-col items-center justify-center bg-[#f0f2f5]"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60'%3E%3Crect width='60' height='60' fill='%23ece5dd'/%3E%3Ccircle cx='30' cy='30' r='20' fill='none' stroke='%23d4d1c9' stroke-width='1'/%3E%3Cpath d='M22 26c0-4.4 3.6-8 8-8s8 3.6 8 8' stroke='%23d4d1c9' stroke-width='1' fill='none'/%3E%3Ccircle cx='23' cy='24' r='1.5' fill='%23d4d1c9'/%3E%3Ccircle cx='37' cy='24' r='1.5' fill='%23d4d1c9'/%3E%3C/svg%3E")`,
              backgroundSize: '60px 60px'
            }}>
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
                <p className="text-[11.5px] text-[#8696a0] truncate">
                  {activo}
                  {convActiva?.modo === 'humano' ? ' · Atendido por ti' : ' · Atendido por bot'}
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
            </div>

            {/* Área de mensajes */}
            <div className={`flex-1 overflow-y-auto p-3 lg:p-4 ${WA_BG}`}
              style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='40'%3E%3Crect width='40' height='40' fill='%23eae3dc'/%3E%3Ccircle cx='20' cy='20' r='18' fill='none' stroke='%23ddd5cc' stroke-width='0.5'/%3E%3C/svg%3E")`,
                backgroundSize: '40px 40px'
              }}>
              {(() => {
                let ultD = null
                return mensajes.map(m => {
                  const d = new Date(m.fecha).toDateString()
                  const sep = d !== ultD
                  if (sep) ultD = d
                  return (
                    <div key={m.id_mensaje}>
                      {sep && <DiaSeparador fecha={m.fecha} />}
                      <Mensaje m={m} />
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
      </div>
    </div>
  )
}
