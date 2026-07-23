import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import {
  MessageSquare, RefreshCw, Globe, MessageCircle,
  Phone, Mail, Filter, Clock, User,
} from 'lucide-react'

// Leads capturados desde la tienda web o el bot de WhatsApp.
// Estados: pendiente → contactado → convertido / descartado.

const ORIGEN_LABEL = {
  web:       { label: 'Web',  icon: Globe,       cls: 'bg-blue-100 text-blue-700'    },
  whatsapp:  { label: 'WhatsApp', icon: MessageCircle, cls: 'bg-green-100 text-green-700' },
}
const ORIGEN_STYLE = Object.fromEntries(
  Object.entries(ORIGEN_LABEL).map(([k, v]) => [k, v.cls])
)

const ESTADO_STYLE = {
  pendiente:  'bg-amber-100 text-amber-700',
  contactado: 'bg-blue-100 text-blue-700',
  convertido: 'bg-emerald-100 text-emerald-700',
  descartado:'bg-gray-200 text-gray-500',
}

const FILTRO_ESTADO = [
  { key: '',          label: 'Todos' },
  { key: 'pendiente', label: 'Pendientes' },
  { key: 'contactado',label: 'Contactados' },
  { key: 'convertido',label: 'Convertidos' },
  { key: 'descartado',label: 'Descartados' },
]

const FILTRO_ORIGEN = [
  { key: '',          label: 'Canal' },
  { key: 'web',       label: '🌐 Web' },
  { key: 'whatsapp',  label: '💬 WhatsApp' },
]

function relativa(iso) {
  if (!iso) return ''
  try {
    const diff = (Date.now() - new Date(iso)) / 1000
    if (diff < 60)   return 'hace un momento'
    if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`
    if (diff < 86400) return `hace ${Math.floor(diff / 3600)} h`
    return `hace ${Math.floor(diff / 86400)} d`
  } catch { return '' }
}

export default function Leads() {
  const [leads, setLeads]     = useState([])
  const [total, setTotal]     = useState(0)
  const [fEstado, setFEstado] = useState('')
  const [fOrigen, setFOrigen] = useState('')
  const [cargando, setCargando] = useState(true)

  const cargar = useCallback(async () => {
    setCargando(true)
    try {
      const params = new URLSearchParams()
      if (fEstado) params.set('estado', fEstado)
      if (fOrigen) params.set('origen', fOrigen)
      const q = params.toString() ? `?${params}` : ''
      const res = await api.get(`/leads${q}`)
      setLeads(res.data?.leads || [])
      setTotal(res.data?.total || 0)
    } catch {
      toast.error('No se pudieron cargar los leads')
    } finally { setCargando(false) }
  }, [fEstado, fOrigen])

  useEffect(() => { cargar() }, [cargar])

  const cambiarEstado = async (id, estado) => {
    try {
      await api.patch(`/leads/${id}/estado`, { estado })
      toast.success('Lead actualizado')
      cargar()
    } catch {
      toast.error('No se pudo actualizar')
    }
  }

  const ESTADOS_SIGUIENTE = {
    pendiente:  'contactado',
    contactado:  'convertido',
    convertido:  'descartado',
    descartado: 'pendiente',
  }

  const SIGUIENTE_LABEL = {
    pendiente:  'Marcar contactado',
    contactado: 'Marcar convertido',
    convertido: 'Descartar',
    descartado: 'Reabrir',
  }

  return (
    <div className="max-w-3xl mx-auto">

      {/* Filtros */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {/* Origen */}
        <div className="flex items-center gap-1 text-xs text-gray-400">
          <Filter size={12} />
          <span>Canal:</span>
        </div>
        {FILTRO_ORIGEN.map(f => (
          <button key={f.key} onClick={() => setFOrigen(f.key)}
            className={`text-xs font-medium px-2.5 py-1.5 rounded-lg transition ${
              fOrigen === f.key
                ? 'bg-slate-800 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'}`}>
            {f.label}
          </button>
        ))}

        <span className="text-gray-300 mx-1">·</span>

        {/* Estado */}
        <div className="flex items-center gap-1 text-xs text-gray-400">
          <Filter size={12} />
          <span>Estado:</span>
        </div>
        {FILTRO_ESTADO.map(f => (
          <button key={f.key} onClick={() => setFEstado(f.key)}
            className={`text-xs font-medium px-2.5 py-1.5 rounded-lg transition ${
              fEstado === f.key
                ? 'bg-slate-800 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'}`}>
            {f.label}
          </button>
        ))}

        <button onClick={cargar} title="Actualizar"
          className="ml-auto p-2 text-gray-400 hover:text-gray-700 rounded-lg border border-gray-200 bg-white">
          <RefreshCw size={13} className={cargando ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Conteo */}
      <p className="text-xs text-gray-400 mb-3 px-0.5">
        {total} lead{total !== 1 ? 's' : ''}
        {fOrigen === 'web' ? ' desde la web' : fOrigen === 'whatsapp' ? ' por WhatsApp' : ''}
        {fEstado ? ` · ${fEstado}s` : ''}
      </p>

      {cargando ? (
        <p className="text-sm text-gray-400 py-12 text-center">Cargando…</p>
      ) : leads.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <MessageSquare size={40} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">No hay leads con esos filtros.</p>
          <p className="text-xs mt-1">Revisa la tienda web o espera a que alguien complete el formulario.</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {leads.map(lead => {
            const origenInfo = ORIGEN_LABEL[lead.origen]
            const OrigenIcon = origenInfo?.icon || MessageSquare
            return (
              <div key={lead.id_lead}
                className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">

                {/* Header: origen + estado */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    {/* Badge origen */}
                    {lead.origen && (
                      <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${ORIGEN_STYLE[lead.origen] || ''}`}>
                        <OrigenIcon size={10} />
                        {origenInfo?.label || lead.origen}
                      </span>
                    )}
                    {/* Badge estado */}
                    <span className={`inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded-full ${ESTADO_STYLE[lead.estado] || ''}`}>
                      {lead.estado || 'pendiente'}
                    </span>
                    {/* Tiempo relativo */}
                    <span className="text-[10px] text-gray-400 flex items-center gap-0.5">
                      <Clock size={10} />
                      {relativa(lead.creada)}
                    </span>
                  </div>

                  {/* Acción rápida siguiente estado */}
                  {lead.estado !== 'descartado' && (
                    <button
                      onClick={() => cambiarEstado(lead.id_lead, ESTADOS_SIGUIENTE[lead.estado])}
                      className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 whitespace-nowrap shrink-0">
                      {SIGUIENTE_LABEL[lead.estado]}
                    </button>
                  )}
                  {lead.estado === 'descartado' && (
                    <button
                      onClick={() => cambiarEstado(lead.id_lead, 'pendiente')}
                      className="text-[11px] font-semibold text-gray-400 hover:text-gray-600 whitespace-nowrap shrink-0">
                      Reabrir
                    </button>
                  )}
                </div>

                {/* Nombre */}
                {lead.nombre && (
                  <p className="text-sm font-bold text-gray-900 mb-1 flex items-center gap-1.5">
                    <User size={13} className="text-gray-400" />
                    {lead.nombre}
                  </p>
                )}

                {/* Contacto */}
                <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
                  {lead.telefono && (
                    <a href={`tel:${lead.telefono}`}
                      className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                      <Phone size={11} />{lead.telefono}
                    </a>
                  )}
                  {lead.email && (
                    <a href={`mailto:${lead.email}`}
                      className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                      <Mail size={11} />{lead.email}
                    </a>
                  )}
                </div>

                {/* Mensaje */}
                {lead.mensaje && (
                  <p className="text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-2 leading-relaxed">
                    "{lead.mensaje}"
                  </p>
                )}

                {/* Selector rápido de estado */}
                <div className="flex items-center gap-1.5 mt-2.5 flex-wrap">
                  {Object.entries(ESTADO_STYLE).map(([est, cls]) => (
                    <button
                      key={est}
                      onClick={() => cambiarEstado(lead.id_lead, est)}
                      className={`text-[10px] font-semibold px-2.5 py-1 rounded-lg transition border ${
                        lead.estado === est
                          ? `${cls} border-transparent`
                          : 'bg-white text-gray-400 border-gray-200 hover:border-gray-300 hover:text-gray-600'
                      }`}>
                      {est.charAt(0).toUpperCase() + est.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
