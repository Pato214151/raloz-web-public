import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Plus, Trash2, Image as ImageIcon, X, Loader2, Eye, EyeOff } from 'lucide-react'

// Reduce la imagen en el navegador (máx 900px, JPEG) para no guardar fotos pesadas.
async function fileADataUrl(file, maxW = 900, quality = 0.82) {
  const img = await new Promise((res, rej) => {
    const i = new Image()
    i.onload = () => res(i)
    i.onerror = rej
    i.src = URL.createObjectURL(file)
  })
  const scale = Math.min(1, maxW / img.width)
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(img.width * scale)
  canvas.height = Math.round(img.height * scale)
  canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
  URL.revokeObjectURL(img.src)
  return canvas.toDataURL('image/jpeg', quality)
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
    } catch {
      toast.error('No se pudo procesar la imagen')
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
