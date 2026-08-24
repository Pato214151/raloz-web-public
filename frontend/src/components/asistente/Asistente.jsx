import { useState, useRef, useEffect } from 'react'
import { Sparkles, Send, Loader2, Trash2 } from 'lucide-react'
import api from '../../services/api'

const SUGERENCIAS = [
  '¿Cuánto vendí hoy?',
  '¿Qué prendas tienen stock bajo?',
  '¿Cuántos pedidos hay por entregar?',
  '¿Cuánto me deben (por cobrar)?',
  '¿Cómo imprimo el ticket de una venta?',
]

const STORAGE_KEY = 'raloz_asistente_chat'

// Renderiza el texto de la IA con **negritas** y saltos de línea (sin mostrar los *).
function renderRich(texto) {
  return String(texto).split('\n').map((linea, i) => (
    <div key={i} style={{ minHeight: linea ? undefined : 7 }}>
      {linea.split(/(\*\*[^*]+\*\*)/g).map((parte, j) =>
        parte.startsWith('**') && parte.endsWith('**')
          ? <strong key={j}>{parte.slice(2, -2)}</strong>
          : parte
      )}
    </div>
  ))
}

export default function Asistente() {
  const [mensajes, setMensajes] = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') } catch { return [] }
  })
  const [input, setInput] = useState('')
  const [cargando, setCargando] = useState(false)
  const finRef = useRef(null)

  useEffect(() => { finRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [mensajes, cargando])
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(mensajes.slice(-40))) } catch { /* lleno */ }
  }, [mensajes])

  function limpiar() {
    setMensajes([])
    try { localStorage.removeItem(STORAGE_KEY) } catch { /* ignore */ }
  }

  async function confirmarAccion(idx) {
    const accion = mensajes[idx]?.accion
    if (!accion) return
    setMensajes((m) => m.map((x, i) => (i === idx ? { ...x, accionEstado: 'enviando' } : x)))
    try {
      const res = await api.post('/asistente/ejecutar', accion, { timeout: 60000 })
      setMensajes((m) => {
        const upd = m.map((x, i) => (i === idx ? { ...x, accionEstado: 'hecha' } : x))
        return [...upd, { rol: 'bot', texto: res.data.mensaje || '✅ Hecho.' }]
      })
    } catch (err) {
      const msg = err?.response?.data?.error || 'No pude ejecutar la acción.'
      setMensajes((m) => {
        const upd = m.map((x, i) => (i === idx ? { ...x, accionEstado: 'error' } : x))
        return [...upd, { rol: 'bot', texto: msg, error: true }]
      })
    }
  }

  function cancelarAccion(idx) {
    setMensajes((m) => m.map((x, i) => (i === idx ? { ...x, accionEstado: 'cancelada' } : x)))
  }

  async function preguntar(texto) {
    const pregunta = (texto ?? input).trim()
    if (!pregunta || cargando) return
    setInput('')
    setMensajes((m) => [...m, { rol: 'user', texto: pregunta }])
    setCargando(true)
    try {
      const res = await api.post('/asistente/preguntar', { pregunta }, { timeout: 130000 })
      setMensajes((m) => [...m, { rol: 'bot', texto: res.data.respuesta, accion: res.data.accion || null }])
    } catch (err) {
      const data = err?.response?.data || {}
      let msg =
        data.code === 'sin_config'
          ? '⚙️ El asistente aún no está activo: falta configurar la llave GEMINI_API_KEY en el servidor (Render → Environment).'
          : data.error || 'No pude responder ahora. Intenta de nuevo en un momento.'
      if (data.detalle) msg += `\n\nDetalle técnico: ${data.detalle}`
      setMensajes((m) => [...m, { rol: 'bot', texto: msg, error: true }])
    } finally {
      setCargando(false)
    }
  }

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '16px', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 90px)' }}>
      <style>{`
        @keyframes raloz-spin { to { transform: rotate(360deg); } }
        .raloz-dots::after { content: ''; animation: raloz-dots 1.3s steps(1,end) infinite; }
        @keyframes raloz-dots { 0%{content:'';} 25%{content:'.';} 50%{content:'..';} 75%{content:'...';} }
      `}</style>
      {/* Encabezado */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <div style={{ width: 42, height: 42, borderRadius: 12, background: '#071f4c', display: 'grid', placeItems: 'center', flexShrink: 0 }}>
          <Sparkles size={22} color="#F9C90C" />
        </div>
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: 0, fontSize: 20, color: '#071a3d' }}>Asistente RALOZ</h1>
          <p style={{ margin: 0, fontSize: 12.5, color: '#6b7280' }}>
            Pregunta sobre ventas, stock, pedidos y cómo usar el sistema. Solo consulta datos — no modifica nada.
          </p>
        </div>
        {mensajes.length > 0 && (
          <button onClick={limpiar} title="Limpiar conversación"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6, border: '1px solid #e5e7eb', background: '#fff', color: '#6b7280', borderRadius: 10, padding: '8px 12px', fontSize: 13, cursor: 'pointer' }}>
            <Trash2 size={15} /> Limpiar
          </button>
        )}
      </div>

      {/* Conversación */}
      <div style={{ flex: 1, overflowY: 'auto', background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 14, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {mensajes.length === 0 && (
          <div style={{ margin: 'auto', textAlign: 'center', color: '#94a3b8', maxWidth: 380 }}>
            <Sparkles size={30} color="#c7cdd6" style={{ marginBottom: 8 }} />
            <p style={{ margin: 0, fontSize: 14 }}>Hazme una pregunta sobre tu negocio o sobre cómo usar el sistema.</p>
          </div>
        )}
        {mensajes.map((m, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 6, alignSelf: m.rol === 'user' ? 'flex-end' : 'flex-start', maxWidth: '88%' }}>
            <div style={{
              padding: '10px 14px', borderRadius: 14, fontSize: 14, lineHeight: 1.5, whiteSpace: 'pre-wrap',
              alignSelf: m.rol === 'user' ? 'flex-end' : 'flex-start',
              background: m.rol === 'user' ? '#071f4c' : (m.error ? '#fef2f2' : '#fff'),
              color: m.rol === 'user' ? '#fff' : (m.error ? '#b91c1c' : '#15171c'),
              border: m.rol === 'user' ? 'none' : '1px solid #e5e7eb',
              borderBottomRightRadius: m.rol === 'user' ? 4 : 14,
              borderBottomLeftRadius: m.rol === 'user' ? 14 : 4,
            }}>
              {m.rol === 'bot' && !m.error ? renderRich(m.texto) : m.texto}
            </div>

            {m.accion && (
              <div style={{ border: '1px solid #F9C90C', background: '#fffbeb', borderRadius: 12, padding: '12px 14px' }}>
                <div style={{ fontSize: 12.5, color: '#92400e', fontWeight: 800, marginBottom: 6 }}>⚠️ Confirmar acción</div>
                <div style={{ fontSize: 13.5, color: '#15171c', marginBottom: 10 }}>{m.accion.descripcion}</div>
                {m.accionEstado === 'hecha' ? (
                  <div style={{ fontSize: 13, color: '#166534', fontWeight: 700 }}>✅ Hecho</div>
                ) : m.accionEstado === 'cancelada' ? (
                  <div style={{ fontSize: 13, color: '#6b7280' }}>Cancelada</div>
                ) : (
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={() => confirmarAccion(i)} disabled={m.accionEstado === 'enviando'}
                      style={{ background: '#071f4c', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontWeight: 800, cursor: 'pointer', opacity: m.accionEstado === 'enviando' ? 0.6 : 1 }}>
                      {m.accionEstado === 'enviando' ? 'Ejecutando…' : 'Confirmar'}
                    </button>
                    <button onClick={() => cancelarAccion(i)} disabled={m.accionEstado === 'enviando'}
                      style={{ background: '#fff', color: '#6b7280', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 16px', cursor: 'pointer' }}>
                      Cancelar
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {cargando && (
          <div style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 8, color: '#6b7280', fontSize: 13 }}>
            <Loader2 size={16} style={{ animation: 'raloz-spin 0.8s linear infinite' }} />
            <span>Pensando<span className="raloz-dots" /></span>
          </div>
        )}
        <div ref={finRef} />
      </div>

      {/* Sugerencias */}
      {mensajes.length === 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
          {SUGERENCIAS.map((s) => (
            <button key={s} onClick={() => preguntar(s)} disabled={cargando}
              style={{ border: '1px solid #d7dbe2', background: '#fff', color: '#374151', borderRadius: 999, padding: '7px 14px', fontSize: 13, cursor: 'pointer' }}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Entrada */}
      <form onSubmit={(e) => { e.preventDefault(); preguntar() }}
        style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe tu pregunta…"
          style={{ flex: 1, padding: '12px 16px', borderRadius: 12, border: '1px solid #d7dbe2', fontSize: 15, outline: 'none' }}
        />
        <button type="submit" disabled={cargando || !input.trim()}
          style={{ background: '#F9C90C', color: '#071a3d', border: 'none', borderRadius: 12, padding: '0 18px', fontWeight: 800, cursor: cargando ? 'default' : 'pointer', display: 'flex', alignItems: 'center', gap: 6, opacity: cargando || !input.trim() ? 0.6 : 1 }}>
          <Send size={16} /> Enviar
        </button>
      </form>
    </div>
  )
}
