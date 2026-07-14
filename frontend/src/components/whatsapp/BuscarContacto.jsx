import { useState } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Search, Loader2, User, Phone } from 'lucide-react'

// Normaliza a formato internacional para wa.me (Colombia: 10 díg. → 57XXXXXXXXXX)
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

  async function buscar(e) {
    e?.preventDefault()
    if (q.trim().length < 2) { toast.error('Escribe al menos 2 letras o números'); return }
    setLoading(true)
    setBuscado(true)
    try {
      const { data } = await api.get('/tienda/admin/buscar-contacto', { params: { q: q.trim() } })
      setContactos(data.contactos || [])
    } catch {
      toast.error('No se pudo buscar')
    } finally {
      setLoading(false)
    }
  }

  const soloDigitos = q.replace(/\D/g, '')
  const numeroDirecto = soloDigitos.length >= 7 ? soloDigitos : null

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-green-100 rounded-lg shrink-0">
          <Search className="w-6 h-6 text-green-700" />
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Escribir a un cliente</h1>
          <p className="text-gray-600 text-xs sm:text-sm">
            Busca a un papá por nombre o número y escríbele directo por WhatsApp.
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

      {/* Escribir directo a un número tecleado */}
      {numeroDirecto && (
        <a
          href={waLink(numeroDirecto)}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between gap-3 border border-green-200 bg-green-50 rounded-xl p-4 hover:bg-green-100 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Phone className="w-5 h-5 text-green-600" />
            <div>
              <div className="font-medium text-gray-800 text-sm">Escribir al número {numeroDirecto}</div>
              <div className="text-xs text-gray-500">Abre WhatsApp aunque no esté registrado</div>
            </div>
          </div>
          <span className="text-sm font-semibold text-green-700">WhatsApp →</span>
        </a>
      )}

      {/* Resultados */}
      {buscado && !loading && (
        contactos.length === 0 ? (
          <p className="text-center text-gray-400 py-8 text-sm">
            No encontré contactos con “{q}”. Si tienes el número, escríbelo arriba para escribir directo.
          </p>
        ) : (
          <div className="space-y-2">
            {contactos.map((c) => (
              <div key={c.telefono} className="flex items-center gap-3 border border-gray-100 rounded-xl p-3">
                <div className="w-10 h-10 rounded-full bg-gray-100 grid place-items-center text-gray-400 shrink-0">
                  <User className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-gray-800 truncate">{c.nombre || 'Sin nombre'}</div>
                  <div className="text-xs text-gray-400">{c.telefono} · {ORIGEN_LBL[c.origen] || c.origen}</div>
                </div>
                <a
                  href={waLink(c.telefono, c.nombre)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold px-3 py-2 rounded-lg shrink-0"
                >
                  WhatsApp
                </a>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  )
}
