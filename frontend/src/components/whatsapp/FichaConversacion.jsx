/** Ficha del cliente dentro del chat: sus datos e historial de compras. */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { useAuth } from '../../context/AuthContext'
import {
  User, Phone, School, GraduationCap, ExternalLink, ShoppingCart, ClipboardList,
  CalendarClock, Send, UserCheck, CheckCircle2, X, Plus, UserPlus, FileText,
} from 'lucide-react'

const TIENDA_URL = 'https://ralozcolsas.com'
const tel10 = (s) => String(s || '').replace(/\D/g, '').slice(-10)
const fmt = (n) => '$' + Math.round(Number(n || 0)).toLocaleString('es-CO')

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

function Fila({ icon: Icon, label, valor }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="flex items-center gap-1.5 text-gray-500"><Icon size={13} /> {label}</span>
      <span className="font-semibold text-gray-800 truncate max-w-[55%] text-right">{valor || '—'}</span>
    </div>
  )
}

export default function FichaConversacion({ conv, onEnviarMensaje, onToggleModo, onActualizar }) {
  const navigate = useNavigate()
  const { usuario } = useAuth()
  const [tab, setTab] = useState('detalles')
  const [cliente, setCliente] = useState(null)
  const [buscando, setBuscando] = useState(false)
  const [historial, setHistorial] = useState(null)
  const [nuevaEtiqueta, setNuevaEtiqueta] = useState('')
  const [notas, setNotas] = useState(conv?.notas || '')
  const [guardandoNotas, setGuardandoNotas] = useState(false)

  const phone = tel10(conv?.chat_id)
  const esHumano = conv?.modo === 'humano'
  const etiquetas = conv?.etiquetas || []

  // Buscar el cliente por teléfono
  useEffect(() => {
    if (!phone) { setCliente(null); return }
    let vivo = true
    setBuscando(true); setCliente(null); setHistorial(null)
    api.get('/clientes', { params: { buscar: phone, per_page: 5 } })
      .then(res => {
        if (!vivo) return
        const lista = res.data?.clientes || []
        setCliente(lista.find(c => tel10(c.telefono) === phone || tel10(c.celular) === phone) || lista[0] || null)
      })
      .catch(() => { if (vivo) setCliente(null) })
      .finally(() => { if (vivo) setBuscando(false) })
    return () => { vivo = false }
  }, [phone])

  // Sincronizar notas cuando cambia la conversación
  useEffect(() => { setNotas(conv?.notas || ''); setTab('detalles') }, [conv?.chat_id])

  // Cargar historial al abrir esa pestaña
  const cargarHistorial = useCallback(async () => {
    if (!cliente?.id_cliente) { setHistorial({ facturas: [], resumen: null }); return }
    try {
      const res = await api.get(`/clientes/${cliente.id_cliente}/historial`)
      setHistorial({ facturas: res.data?.facturas || [], resumen: res.data?.resumen || null })
    } catch { setHistorial({ facturas: [], resumen: null }) }
  }, [cliente])
  useEffect(() => { if (tab === 'historial' && historial === null) cargarHistorial() }, [tab, historial, cargarHistorial])

  // ── Acciones que tocan el backend ──
  const post = async (path, body, okMsg) => {
    try {
      await api.post(`/wa/conversaciones/${conv.chat_id}/${path}`, body)
      onActualizar?.()
      if (okMsg) toast.success(okMsg)
      return true
    } catch (e) {
      toast.error(e.response?.data?.error || 'No se pudo guardar')
      return false
    }
  }
  const asignarme = () => post('asignar', { asignado_a: usuario?.usuario }, 'Chat asignado a ti 🙌')
  const quitarAsignacion = () => post('asignar', { asignado_a: '' }, 'Sin asignar')
  const agregarEtiqueta = () => {
    const e = nuevaEtiqueta.trim()
    if (!e) return
    post('etiquetas', { etiquetas: [...etiquetas, e] })
    setNuevaEtiqueta('')
  }
  const quitarEtiqueta = (e) => post('etiquetas', { etiquetas: etiquetas.filter(x => x !== e) })
  const guardarNotas = async () => {
    setGuardandoNotas(true)
    await post('notas', { notas }, 'Notas guardadas ✅')
    setGuardandoNotas(false)
  }

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

  const TABS = [
    { id: 'detalles',  label: 'Detalles' },
    { id: 'historial', label: 'Historial' },
    { id: 'notas',     label: 'Notas' },
  ]

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Cabecera */}
      <div className="px-4 py-4 border-b border-gray-100 flex flex-col items-center text-center shrink-0">
        <div className="w-16 h-16 rounded-full bg-[#dcf8c6] text-[#075e54] flex items-center justify-center text-2xl font-bold mb-2">
          {nombre.charAt(0).toUpperCase()}
        </div>
        <p className="text-[15px] font-bold text-gray-900 leading-tight">{nombre}</p>
        <p className="text-[12.5px] text-gray-400 flex items-center gap-1 mt-0.5"><Phone size={12} /> {telMostrar}</p>
        {conv.asignado_a ? (
          <span className="mt-2 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 flex items-center gap-1">
            <UserCheck size={11} /> Asignado a {conv.asignado_a}
          </span>
        ) : (
          <span className={`mt-2 text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${esHumano ? 'bg-blue-50 text-blue-700' : 'bg-green-50 text-green-700'}`}>
            {esHumano ? '💬 Con asesor' : '🤖 Con el bot'}
          </span>
        )}
      </div>

      {/* Pestañas */}
      <div className="flex border-b border-gray-100 shrink-0">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex-1 py-2.5 text-[12.5px] font-semibold transition-colors relative ${
              tab === t.id ? 'text-slate-900' : 'text-gray-400 hover:text-gray-600'
            }`}>
            {t.label}
            {tab === t.id && <span className="absolute left-3 right-3 -bottom-px h-0.5 rounded-full bg-amber-400" />}
          </button>
        ))}
      </div>

      {/* Contenido */}
      <div className="flex-1 overflow-y-auto">
        {tab === 'detalles' && (
          <div>
            {/* Info cliente */}
            <div className="px-4 py-3 border-b border-gray-100">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">Información del cliente</p>
              {buscando ? (
                <p className="text-[12.5px] text-gray-400">Buscando…</p>
              ) : cliente ? (
                <div className="space-y-2 text-[13px]">
                  <Fila icon={School} label="Colegio" valor={cliente.colegio_nombre} />
                  <Fila icon={GraduationCap} label="Estudiante" valor={cliente.estudiante_nombre} />
                  <Fila icon={User} label="Grado" valor={cliente.estudiante_grado} />
                  <button onClick={() => navigate('/clientes')} className="mt-1 flex items-center gap-1 text-[12.5px] font-medium text-amber-700 hover:text-amber-800">
                    Ver perfil completo <ExternalLink size={12} />
                  </button>
                </div>
              ) : (
                <div className="text-[12.5px] text-gray-500">
                  <p>Este número no está registrado como cliente.</p>
                  <button onClick={() => navigate('/clientes')} className="mt-1.5 flex items-center gap-1 text-amber-700 font-medium hover:text-amber-800">
                    + Crear cliente <ExternalLink size={12} />
                  </button>
                </div>
              )}
            </div>

            {/* Asignación */}
            <div className="px-4 py-3 border-b border-gray-100">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">Asignación</p>
              {conv.asignado_a ? (
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[13px] text-gray-700 flex items-center gap-1.5"><UserCheck size={14} className="text-amber-600" /> {conv.asignado_a}</span>
                  <button onClick={quitarAsignacion} className="text-[12px] text-gray-400 hover:text-red-500">Quitar</button>
                </div>
              ) : (
                <button onClick={asignarme} className="flex items-center gap-2 px-3 py-2 rounded-lg border border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100 text-[12.5px] font-medium w-full justify-center">
                  <UserPlus size={15} /> Asignármelo (yo lo atiendo)
                </button>
              )}
            </div>

            {/* Acciones rápidas */}
            <div className="px-4 py-3 border-b border-gray-100">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">Acciones rápidas</p>
              <div className="grid grid-cols-2 gap-2">
                <Accion icon={ClipboardList} label="Ver pedidos" onClick={() => navigate('/operacion')} />
                <Accion icon={ShoppingCart} label="Nueva venta" onClick={() => navigate('/ventas?tab=nueva')} />
                <Accion icon={CalendarClock} label="Crear cita" onClick={() => navigate('/clientes?tab=citas')} />
                <Accion icon={Send} label="Enviar catálogo" onClick={() => onEnviarMensaje?.(
                  `¡Hola${cliente?.nombre ? ' ' + cliente.nombre.split(' ')[0] : ''}! 👋 Mira nuestro catálogo y compra en línea aquí 👉 ${TIENDA_URL}`
                )} />
                {esHumano
                  ? <Accion icon={CheckCircle2} tone="green" label="Marcar atendido" onClick={() => onToggleModo?.('bot')} />
                  : <Accion icon={UserCheck} tone="amber" label="Atenderlo yo" onClick={() => onToggleModo?.('humano')} />}
              </div>
            </div>

            {/* Etiquetas editables */}
            <div className="px-4 py-3">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">Etiquetas</p>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {etiquetas.length === 0 && <span className="text-[11.5px] text-gray-300">Sin etiquetas aún</span>}
                {etiquetas.map(e => (
                  <span key={e} className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-50 text-amber-800">
                    {e}
                    <button onClick={() => quitarEtiqueta(e)} className="hover:text-red-500"><X size={11} /></button>
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-1.5">
                <input value={nuevaEtiqueta} onChange={e => setNuevaEtiqueta(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') agregarEtiqueta() }}
                  placeholder="Nueva etiqueta…"
                  className="flex-1 text-[12.5px] border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-amber-400" />
                <button onClick={agregarEtiqueta} className="p-1.5 rounded-lg bg-amber-400 text-slate-900 hover:bg-amber-500"><Plus size={15} /></button>
              </div>
            </div>
          </div>
        )}

        {tab === 'historial' && (
          <div className="px-4 py-3">
            {historial === null ? (
              <p className="text-[12.5px] text-gray-400">Cargando…</p>
            ) : !cliente ? (
              <p className="text-[12.5px] text-gray-400">Cliente no registrado — sin historial.</p>
            ) : (
              <>
                {historial.resumen && (
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    <div className="bg-gray-50 rounded-lg p-2 text-center"><p className="text-[10px] text-gray-400">Compras</p><p className="text-[13px] font-bold text-gray-800">{fmt(historial.resumen.total_compras)}</p></div>
                    <div className="bg-emerald-50 rounded-lg p-2 text-center"><p className="text-[10px] text-emerald-600">Pagado</p><p className="text-[13px] font-bold text-emerald-700">{fmt(historial.resumen.total_pagado)}</p></div>
                    <div className="bg-red-50 rounded-lg p-2 text-center"><p className="text-[10px] text-red-500">Saldo</p><p className="text-[13px] font-bold text-red-600">{fmt(historial.resumen.saldo_pendiente)}</p></div>
                  </div>
                )}
                {historial.facturas.length === 0 ? (
                  <p className="text-[12.5px] text-gray-400">Sin compras registradas.</p>
                ) : historial.facturas.map(f => (
                  <button key={f.id_factura} onClick={() => navigate(`/buscar?ver=${f.id_factura}`)}
                    className="w-full text-left border border-gray-100 rounded-lg p-2.5 mb-2 hover:border-amber-300 hover:bg-amber-50/40 transition">
                    <div className="flex items-center justify-between">
                      <span className="text-[12.5px] font-semibold text-gray-800 flex items-center gap-1.5"><FileText size={13} className="text-gray-400" /> {f.numero_factura}</span>
                      <span className="text-[12px] font-bold text-gray-800">{fmt(f.total)}</span>
                    </div>
                    <div className="flex items-center justify-between mt-1 text-[11px]">
                      <span className="text-gray-400">{f.fecha}</span>
                      {f.saldo_pendiente > 0
                        ? <span className="text-red-500 font-medium">Saldo {fmt(f.saldo_pendiente)}</span>
                        : <span className="text-green-600 font-medium">Pagada</span>}
                    </div>
                  </button>
                ))}
              </>
            )}
          </div>
        )}

        {tab === 'notas' && (
          <div className="px-4 py-3">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">Notas internas</p>
            <textarea value={notas} onChange={e => setNotas(e.target.value)} rows={8}
              placeholder="Anota lo importante de este cliente (solo lo ve el equipo)…"
              className="w-full text-[13px] border border-gray-200 rounded-lg p-3 outline-none focus:border-amber-400 resize-none" />
            <button onClick={guardarNotas} disabled={guardandoNotas}
              className="mt-2 w-full py-2 rounded-lg bg-slate-800 text-white text-[13px] font-semibold hover:bg-slate-900 disabled:opacity-50">
              {guardandoNotas ? 'Guardando…' : 'Guardar notas'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
