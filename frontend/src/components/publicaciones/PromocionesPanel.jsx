/** Ofertas y publicaciones que se muestran en la tienda. */

import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Plus, Trash2, Image as ImageIcon, X, Loader2, Eye, EyeOff } from 'lucide-react'

// Lee el archivo tal cual como data URL (sin procesar). Respaldo a prueba de balas.
function fileRawDataUrl(file) {
  return new Promise((res, rej) => {
    const fr = new FileReader()
    fr.onload = () => res(fr.result)
    fr.onerror = () => rej(new Error('read'))
    fr.readAsDataURL(file)
  })
}

// Reduce la imagen en el navegador (máx 1000px, JPEG) para no guardar fotos pesadas.
// Si algo falla al redimensionar, guarda la imagen tal cual (mientras no sea enorme).
async function fileADataUrl(file, maxW = 1000, quality = 0.82) {
  if (!file.type || !file.type.startsWith('image/')) {
    const e = new Error('no-imagen'); e.code = 'no-imagen'; throw e
  }
  if (/image\/hei[cf]/i.test(file.type) || /\.(heic|heif)$/i.test(file.name || '')) {
    const e = new Error('heic'); e.code = 'heic'; throw e
  }
  try {
    // createImageBitmap decodifica el archivo de forma más robusta que <img>.
    const bmp = await createImageBitmap(file)
    const scale = Math.min(1, maxW / bmp.width)
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(bmp.width * scale))
    canvas.height = Math.max(1, Math.round(bmp.height * scale))
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('sin-contexto')
    ctx.drawImage(bmp, 0, 0, canvas.width, canvas.height)
    bmp.close?.()
    const url = canvas.toDataURL('image/jpeg', quality)
    if (url && url.length > 100) return url
    throw new Error('vacio')
  } catch (e) {
    // Respaldo: subir el archivo original si no es muy pesado (≤ 3 MB).
    if (file.size <= 3_000_000) return await fileRawDataUrl(file)
    const err = new Error('pesada'); err.code = 'pesada'; throw err
  }
}

const VACIO = { titulo: '', texto: '', foto: null }

export default function PromocionesPanel() {
  const [promos, setPromos] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(VACIO)
  const [saving, setSaving] = useState(false)

  useEffect(() => { cargar() }, [])

  async function cargar() {
    setLoading(true)
    try {
      const { data } = await api.get('/tienda/admin/promociones')
      setPromos(data.promociones || [])
    } catch {
      toast.error('No se pudieron cargar las publicaciones')
    } finally {
      setLoading(false)
    }
  }

  async function onFoto(e) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const url = await fileADataUrl(file)
      setForm((f) => ({ ...f, foto: url }))
    } catch (err) {
      if (err?.code === 'no-imagen') {
        toast.error('Debe ser una imagen JPG o PNG (no PDF).')
      } else if (err?.code === 'heic') {
        toast.error('Es una foto HEIC de iPhone. Tómale una captura de pantalla y sube esa, o guárdala como JPG.', { duration: 6000 })
      } else if (err?.code === 'pesada') {
        toast.error('La imagen es muy pesada. Usa una más liviana (menos de 3 MB).')
      } else {
        toast.error('No pude procesar esa imagen. Prueba con una foto JPG o PNG.')
      }
    }
  }

  async function guardar() {
    if (!form.titulo.trim()) { toast.error('Ponle un título'); return }
    setSaving(true)
    try {
      await api.post('/tienda/admin/promociones', form)
      toast.success('Publicación creada')
      setForm(VACIO)
      setShowForm(false)
      cargar()
    } catch (e) {
      toast.error(e?.response?.data?.error || 'No se pudo crear')
    } finally {
      setSaving(false)
    }
  }

  async function toggle(p) {
    setPromos((prev) => prev.map((x) => (x.id_promocion === p.id_promocion ? { ...x, activa: !x.activa } : x)))
    try {
      await api.put(`/tienda/admin/promociones/${p.id_promocion}`, { activa: !p.activa })
    } catch {
      toast.error('No se pudo actualizar'); cargar()
    }
  }

  async function eliminar(p) {
    if (!window.confirm(`¿Eliminar "${p.titulo}"?`)) return
    setPromos((prev) => prev.filter((x) => x.id_promocion !== p.id_promocion))
    try {
      await api.delete(`/tienda/admin/promociones/${p.id_promocion}`)
    } catch {
      toast.error('No se pudo eliminar'); cargar()
    }
  }

  const inputCls = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200'

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h2 className="font-semibold text-gray-800">Ofertas y publicaciones</h2>
          <p className="text-xs text-gray-400">Aparecen como un segmento en la portada de la tienda.</p>
        </div>
        <button
          type="button"
          onClick={() => setShowForm((v) => !v)}
          className="inline-flex items-center justify-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-3 py-2.5 rounded-lg"
        >
          <Plus className="w-4 h-4" /> Agregar publicación
        </button>
      </div>

      {showForm && (
        <div className="border border-gray-200 rounded-lg p-4 space-y-3 bg-gray-50">
          <input
            value={form.titulo}
            onChange={(e) => setForm((f) => ({ ...f, titulo: e.target.value }))}
            maxLength={120}
            placeholder="Título — ej: ¡Oferta de hoy!"
            className={inputCls}
          />
          <textarea
            value={form.texto}
            onChange={(e) => setForm((f) => ({ ...f, texto: e.target.value }))}
            rows={2}
            maxLength={2000}
            placeholder="Ej: 2 pares por tan solo $80.000"
            className={inputCls}
          />
          <div className="flex items-center gap-3">
            {form.foto ? (
              <div className="relative">
                <img src={form.foto} alt="" className="w-20 h-20 object-cover rounded-lg border border-gray-200" />
                <button
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, foto: null }))}
                  className="absolute -top-2 -right-2 bg-white rounded-full shadow p-0.5 border border-gray-100"
                >
                  <X className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            ) : (
              <label className="inline-flex items-center gap-2 text-sm text-blue-600 cursor-pointer border border-dashed border-gray-300 rounded-lg px-3 py-2 hover:bg-white">
                <ImageIcon className="w-4 h-4" /> Agregar foto (opcional)
                <input type="file" accept="image/*" className="hidden" onChange={onFoto} />
              </label>
            )}
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => { setShowForm(false); setForm(VACIO) }}
              className="text-sm text-gray-500 px-3 py-2 hover:text-gray-700"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={guardar}
              disabled={saving}
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold px-4 py-2 rounded-lg"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              Publicar
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-8 text-gray-400"><Loader2 className="w-6 h-6 animate-spin" /></div>
      ) : promos.length === 0 ? (
        <p className="text-center text-gray-400 py-6 text-sm">Aún no has creado publicaciones.</p>
      ) : (
        <div className="space-y-2">
          {promos.map((p) => (
            <div key={p.id_promocion} className="flex items-center gap-3 border border-gray-100 rounded-lg p-3">
              {p.foto ? (
                <img src={p.foto} alt="" className="w-12 h-12 object-cover rounded-lg shrink-0" />
              ) : (
                <div className="w-12 h-12 rounded-lg bg-gray-100 grid place-items-center text-gray-300 shrink-0">
                  <ImageIcon className="w-5 h-5" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-gray-800 truncate">{p.titulo}</div>
                {p.texto && <div className="text-xs text-gray-400 truncate">{p.texto}</div>}
              </div>
              <span className={`text-[11px] font-semibold px-2 py-1 rounded-full shrink-0 ${p.activa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                {p.activa ? 'Visible' : 'Oculta'}
              </span>
              <button type="button" onClick={() => toggle(p)} className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg shrink-0" title={p.activa ? 'Ocultar' : 'Mostrar'}>
                {p.activa ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
              <button type="button" onClick={() => eliminar(p)} className="p-2 text-red-500 hover:bg-red-50 rounded-lg shrink-0" title="Eliminar">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
