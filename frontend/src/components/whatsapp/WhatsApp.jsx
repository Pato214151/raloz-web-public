import { useState, useEffect, useRef, useCallback } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Send, Bot, User, RefreshCw, MessageCircle, Image as ImageIcon } from 'lucide-react'

// Respuestas rápidas (plantillas) para el asesor
const RESPUESTAS_RAPIDAS = [
  { label: 'Saludo', text: '¡Hola! 😊 ¿En qué te podemos ayudar?' },
  { label: 'Pedido listo', text: 'Tu pedido ya está listo para recoger en el local 🎉' },
  { label: 'Ubicación', text: 'Nos encuentras en el C.C. San Andresito de la 68, Local M14, Bogotá. Horario: lunes y sábado de 10:00 a.m. a 5:00 p.m.' },
  { label: 'Trae al niñ@', text: 'Para tomar bien la talla, trae al niñ@ al local, sin compromiso 👦👧' },
  { label: 'Gracias', text: '¡Gracias por escribirnos! 🙏 Que tengas un feliz día.' },
]

// Bandeja de WhatsApp: lista de conversaciones + chat. El bot responde solo
// mientras la conversación esté en modo "bot"; al responder desde aquí (o al
// tocar "Atender yo") pasa a modo "humano" y el bot se calla.

function horaCorta(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('es-CO', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    })
  } catch { return '' }
}

// Adjunto (imagen/archivo) de un mensaje: se pide aparte por su id.
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
  if (err) return <p className="text-xs italic opacity-70 mb-1">No se pudo cargar el adjunto</p>
  if (!src) return <p className="text-xs italic opacity-70 mb-1">Cargando adjunto…</p>
  if (tipo === 'image') {
    return (
      <a href={src} target="_blank" rel="noopener" className="block mb-1">
        <img src={src} alt="adjunto" className="rounded-lg max-w-[220px] max-h-[300px] object-contain" />
      </a>
    )
  }
  return <a href={src} download className="text-xs underline mb-1 inline-block">📎 Descargar archivo</a>
}

export default function WhatsApp() {
  const [conversaciones, setConversaciones] = useState([])
  const [activo, setActivo] = useState(null)        // chat_id seleccionado
  const [mensajes, setMensajes] = useState([])
  const [texto, setTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [enviandoImg, setEnviandoImg] = useState(false)
  const [cargandoConv, setCargandoConv] = useState(true)
  const finRef = useRef(null)
  const fileRef = useRef(null)

  const convActiva = conversaciones.find(c => c.chat_id === activo)

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

  // Carga inicial + refresco automático de la lista cada 20 s
  useEffect(() => {
    cargarConversaciones()
    const id = setInterval(cargarConversaciones, 20000)
    return () => clearInterval(id)
  }, [cargarConversaciones])

  // Al abrir un chat, cargar sus mensajes y refrescarlos cada 12 s
  useEffect(() => {
    if (!activo) return
    cargarMensajes(activo)
    const id = setInterval(() => cargarMensajes(activo), 12000)
    return () => clearInterval(id)
  }, [activo, cargarMensajes])

  // Auto-scroll al último mensaje
  useEffect(() => { finRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [mensajes])

  const abrir = (chatId) => {
    setActivo(chatId)
    // marcar como leído localmente
    setConversaciones(prev => prev.map(c =>
      c.chat_id === chatId ? { ...c, no_leidos: 0 } : c))
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
      toast.success(modo === 'humano' ? 'Tú atiendes este chat' : 'El bot vuelve a responder')
    } catch {
      toast.error('No se pudo cambiar el modo')
    }
  }

  return (
    <div className="flex gap-4 h-[calc(100vh-120px)]">

      {/* ── Lista de conversaciones ── */}
      <div className="w-72 shrink-0 bg-white rounded-xl border border-gray-200 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
            <MessageCircle size={16} className="text-green-600" /> Conversaciones
          </h2>
          <button onClick={cargarConversaciones} title="Actualizar"
            className="p-1 text-gray-400 hover:text-gray-700 rounded">
            <RefreshCw size={14} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {cargandoConv ? (
            <p className="p-4 text-xs text-gray-400">Cargando…</p>
          ) : conversaciones.length === 0 ? (
            <p className="p-4 text-xs text-gray-400">Aún no hay conversaciones.</p>
          ) : conversaciones.map(c => (
            <button key={c.chat_id} onClick={() => abrir(c.chat_id)}
              className={`w-full text-left px-4 py-3 border-b border-gray-50 hover:bg-gray-50 transition ${
                activo === c.chat_id ? 'bg-green-50' : ''}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-gray-800 truncate">
                  {c.nombre || c.chat_id}
                </span>
                {c.no_leidos > 0 && (
                  <span className="bg-green-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center shrink-0">
                    {c.no_leidos > 99 ? '99+' : c.no_leidos}
                  </span>
                )}
              </div>
              <div className="flex items-center justify-between gap-2 mt-0.5">
                <span className="text-xs text-gray-500 truncate">{c.ultimo_mensaje}</span>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0 ${
                  c.modo === 'humano' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                  {c.modo === 'humano' ? 'HUMANO' : 'BOT'}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Chat ── */}
      <div className="flex-1 bg-white rounded-xl border border-gray-200 flex flex-col overflow-hidden">
        {!activo ? (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            Selecciona una conversación para ver los mensajes.
          </div>
        ) : (
          <>
            {/* Cabecera del chat */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-800 truncate">
                  {convActiva?.nombre || activo}
                </p>
                <p className="text-xs text-gray-400">{activo}</p>
              </div>
              <div className="flex items-center gap-2">
                {convActiva?.modo === 'humano' ? (
                  <button onClick={() => cambiarModo('bot')}
                    className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-amber-100 text-amber-700 hover:bg-amber-200 transition">
                    <Bot size={14} /> Devolver al bot
                  </button>
                ) : (
                  <button onClick={() => cambiarModo('humano')}
                    className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200 transition">
                    <User size={14} /> Atender yo
                  </button>
                )}
              </div>
            </div>

            {/* Mensajes */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2 bg-gray-50">
              {mensajes.map(m => (
                <div key={m.id_mensaje}
                  className={`flex ${m.direccion === 'out' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[75%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap ${
                    m.direccion === 'out'
                      ? 'bg-green-600 text-white rounded-br-sm'
                      : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'}`}>
                    {m.tiene_media && <Media id={m.id_mensaje} tipo={m.media_tipo} />}
                    {m.texto}
                    <div className={`text-[9px] mt-1 ${
                      m.direccion === 'out' ? 'text-green-100' : 'text-gray-400'}`}>
                      {m.autor} · {horaCorta(m.fecha)}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={finRef} />
            </div>

            {/* Enviar */}
            <div className="border-t border-gray-100">
              {/* Respuestas rápidas */}
              <div className="flex gap-1.5 px-3 pt-2 flex-wrap">
                {RESPUESTAS_RAPIDAS.map((q, i) => (
                  <button key={i} type="button" onClick={() => setTexto(q.text)}
                    className="text-[11px] font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-600 hover:bg-green-100 hover:text-green-700 transition">
                    {q.label}
                  </button>
                ))}
              </div>
              <form onSubmit={enviar} className="flex items-center gap-2 p-3">
                <input type="file" accept="image/*" ref={fileRef} onChange={enviarImagen} className="hidden" />
                <button type="button" onClick={() => fileRef.current?.click()} disabled={enviandoImg}
                  title="Enviar foto" className="p-2 text-gray-400 hover:text-green-600 rounded-lg disabled:opacity-50">
                  <ImageIcon size={18} />
                </button>
                <input
                  value={texto}
                  onChange={e => setTexto(e.target.value)}
                  placeholder={enviandoImg ? 'Enviando foto…' : 'Escribe un mensaje…'}
                  className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                />
                <button type="submit" disabled={enviando || !texto.trim()}
                  className="flex items-center gap-1.5 bg-green-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 transition">
                  <Send size={15} /> Enviar
                </button>
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
