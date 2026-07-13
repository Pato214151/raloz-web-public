import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Zap, PackageX, Loader2 } from 'lucide-react'

// Metadatos de presentación de cada regla (el backend solo guarda la clave)
const REGLAS_INFO = {
  alerta_stock_bajo: {
    titulo: 'Alerta de stock bajo',
    desc: 'Te avisa por WhatsApp cuando hay productos con pocas unidades. Máximo una vez al día.',
    icon: PackageX,
    campoUmbral: true,
  },
}

const fmtFecha = (iso) => {
  if (!iso) return 'nunca'
  try { return new Date(iso).toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) }
  catch { return iso }
}

export default function Automatizacion() {
  const [reglas, setReglas] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { cargar() }, [])

  async function cargar() {
    setLoading(true)
    try {
      const { data } = await api.get('/tienda/admin/reglas')
      setReglas(data.reglas || [])
    } catch {
      toast.error('No se pudieron cargar las reglas')
    } finally {
      setLoading(false)
    }
  }

  async function actualizar(clave, cambios) {
    setReglas((prev) => prev.map((r) => (r.clave === clave ? { ...r, ...cambios } : r)))
    try {
      await api.put(`/tienda/admin/reglas/${clave}`, cambios)
    } catch {
      toast.error('No se pudo guardar la regla')
      cargar()
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-lg shrink-0">
          <Zap className="w-6 h-6 text-blue-700" />
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Automatización</h1>
          <p className="text-gray-600 text-xs sm:text-sm">
            Reglas que corren solas. Préndelas o apágalas cuando quieras.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-gray-400">
          <Loader2 className="w-7 h-7 animate-spin" />
        </div>
      ) : reglas.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 py-12 text-center text-gray-400 text-sm">
          No hay reglas configuradas todavía.
        </div>
      ) : (
        <div className="space-y-3">
          {reglas.map((r) => {
            const info = REGLAS_INFO[r.clave] || { titulo: r.clave, desc: '', icon: Zap }
            const Icon = info.icon
            return (
              <div key={r.clave} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 sm:p-5">
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <div className={`p-2 rounded-lg shrink-0 ${r.activa ? 'bg-blue-50 text-blue-600' : 'bg-gray-100 text-gray-400'}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h2 className="font-bold text-gray-800">{info.titulo}</h2>
                      <p className="text-sm text-gray-500">{info.desc}</p>
                      <p className="text-[11px] text-gray-400 mt-1">Última ejecución: {fmtFecha(r.ultima_ejecucion)}</p>
                    </div>
                  </div>
                  {/* Interruptor */}
                  <button
                    type="button"
                    onClick={() => actualizar(r.clave, { activa: !r.activa })}
                    className={`w-full sm:w-auto shrink-0 inline-flex items-center justify-center gap-2 text-sm font-semibold px-3 py-2.5 rounded-lg border transition-colors ${
                      r.activa ? 'text-white bg-green-600 border-green-600 hover:bg-green-700' : 'text-gray-700 border-gray-200 hover:bg-gray-100'
                    }`}
                  >
                    <span className={`relative w-11 h-6 rounded-full transition-colors ${r.activa ? 'bg-green-400' : 'bg-gray-300'}`}>
                      <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all ${r.activa ? 'left-[22px]' : 'left-0.5'}`} />
                    </span>
                    {r.activa ? 'Activa' : 'Apagada'}
                  </button>
                </div>

                {/* Config: umbral */}
                {info.campoUmbral && (
                  <label className="flex items-center gap-2 text-sm text-gray-500 mt-4 pt-4 border-t border-gray-100">
                    Avisar cuando el stock sea de o menos:
                    <input
                      type="number"
                      min={1}
                      defaultValue={r.config?.umbral ?? 5}
                      onBlur={(e) => {
                        const v = parseInt(e.target.value, 10) || 5
                        if (v !== (r.config?.umbral ?? 5)) actualizar(r.clave, { config: { ...r.config, umbral: v } })
                      }}
                      className="w-16 text-center border border-gray-200 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
                    />
                    unidades
                  </label>
                )}
              </div>
            )
          })}
        </div>
      )}

      <p className="text-xs text-gray-400">
        Las alertas se envían al WhatsApp del administrador configurado en el sistema.
      </p>
    </div>
  )
}
