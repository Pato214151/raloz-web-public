import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import {
  Megaphone, Star, Eye, EyeOff, Save, Loader2, Search,
  Shirt, MapPin, Store, AlertTriangle,
} from 'lucide-react'
import { fotoProducto } from '../../data/productoImagenes'

const COP = (n) =>
  n == null ? '—' : '$' + Math.round(n).toLocaleString('es-CO')

// Color del ícono según el tipo de prenda (mismo criterio que la tienda)
function tipoColor(tipo = '') {
  const t = tipo.toLowerCase()
  if (t.includes('complet')) return 'bg-indigo-100 text-indigo-600'
  if (t.includes('niña') || t.includes('nina')) return 'bg-pink-100 text-pink-600'
  if (t.includes('niño') || t.includes('nino')) return 'bg-sky-100 text-sky-600'
  if (t.includes('físi') || t.includes('fisi')) return 'bg-emerald-100 text-emerald-600'
  if (t.includes('media') || t.includes('calcet')) return 'bg-slate-100 text-slate-500'
  if (t.includes('diario')) return 'bg-amber-100 text-amber-600'
  return 'bg-gray-100 text-gray-500'
}

export default function Publicaciones() {
  const [banner, setBanner] = useState({ texto: '', activo: true })
  const [savingBanner, setSavingBanner] = useState(false)
  const [colegios, setColegios] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')

  useEffect(() => { cargar() }, [])

  async function cargar() {
    setLoading(true)
    try {
      const [cfg, pub] = await Promise.all([
        api.get('/tienda/admin/config'),
        api.get('/tienda/admin/publicaciones'),
      ])
      setBanner({
        texto: cfg.data.banner_texto || '',
        activo: !!cfg.data.banner_activo,
      })
      setColegios(pub.data.colegios || [])
    } catch {
      toast.error('No se pudo cargar el centro de publicaciones')
    } finally {
      setLoading(false)
    }
  }

  async function guardarBanner() {
    setSavingBanner(true)
    try {
      await api.put('/tienda/admin/config', {
        banner_texto: banner.texto,
        banner_activo: banner.activo,
      })
      toast.success('Banner actualizado')
    } catch {
      toast.error('No se pudo guardar el banner')
    } finally {
      setSavingBanner(false)
    }
  }

  // Activar / desactivar TODO un colegio (oculta o muestra su tienda completa)
  async function toggleColegio(col) {
    const nuevo = !col.activo
    if (!nuevo && !window.confirm(
      `¿Desactivar "${col.nombre}"? Se ocultará TODA su tienda del sitio ` +
      `(sus ${col.productos.length} productos dejarán de verse). Puedes reactivarlo cuando quieras.`,
    )) return

    setColegios((prev) =>
      prev.map((c) => (c.id_colegio === col.id_colegio ? { ...c, activo: nuevo } : c)),
    )
    try {
      await api.put(`/colegios/${col.id_colegio}`, { activo: nuevo })
      toast.success(nuevo ? `${col.nombre} activado` : `${col.nombre} desactivado`)
    } catch {
      toast.error('No se pudo cambiar el colegio')
      cargar()
    }
  }

  // Cambiar un producto (activo/destacado/orden). Es global: afecta al producto
  // en todos los colegios donde aparece, por eso actualizamos todas sus copias.
  async function updateProducto(id, cambios) {
    setColegios((prev) =>
      prev.map((c) => ({
        ...c,
        productos: c.productos.map((p) =>
          p.id_producto === id ? { ...p, ...cambios } : p,
        ),
      })),
    )
    try {
      await api.put(`/productos/${id}`, cambios)
    } catch {
      toast.error('No se pudo actualizar el producto')
      cargar()
    }
  }

  const filtro = q.toLowerCase()

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Megaphone className="w-6 h-6 text-blue-700" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Publicaciones</h1>
            <p className="text-gray-600 text-sm">
              Controla la tienda online: colegios, productos y el banner — todo desde aquí.
            </p>
          </div>
        </div>
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar producto…"
            className="pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
        </div>
      </div>

      {/* Banner */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Banner de la tienda</h2>
          <button
            type="button"
            onClick={() => setBanner((b) => ({ ...b, activo: !b.activo }))}
            className="flex items-center gap-2 text-sm text-gray-600"
          >
            <span>{banner.activo ? 'Visible' : 'Oculto'}</span>
            <span className={`relative w-11 h-6 rounded-full transition-colors ${banner.activo ? 'bg-green-500' : 'bg-gray-300'}`}>
              <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all ${banner.activo ? 'left-[22px]' : 'left-0.5'}`} />
            </span>
          </button>
        </div>
        <textarea
          value={banner.texto}
          onChange={(e) => setBanner((b) => ({ ...b, texto: e.target.value }))}
          maxLength={300}
          rows={2}
          placeholder="Ej: Temporada 2026 — Uniformes en stock…"
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-400">{banner.texto.length}/300</span>
          <button
            type="button"
            onClick={guardarBanner}
            disabled={savingBanner}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg"
          >
            {savingBanner ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Guardar banner
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-gray-400">
          <Loader2 className="w-7 h-7 animate-spin" />
        </div>
      ) : (
        colegios.map((col) => {
          const prods = col.productos.filter((p) =>
            (p.nombre || '').toLowerCase().includes(filtro),
          )
          if (filtro && prods.length === 0) return null
          const publicados = col.productos.filter((p) => p.activo).length

          return (
            <section
              key={col.id_colegio}
              className={`bg-white rounded-xl shadow-sm border transition-colors ${
                col.activo ? 'border-gray-100' : 'border-red-200 bg-red-50/40'
              }`}
            >
              {/* Cabecera del colegio */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-4 border-b border-gray-100">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${col.activo ? 'bg-blue-50 text-blue-600' : 'bg-gray-200 text-gray-400'}`}>
                    <Store className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="font-bold text-gray-800">{col.nombre}</h2>
                      {!col.activo && (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-600 bg-red-100 px-2 py-0.5 rounded-full">
                          <AlertTriangle className="w-3 h-3" /> Oculto en la tienda
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      {col.ciudad && (
                        <span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3" />{col.ciudad}</span>
                      )}
                      <span>{publicados} publicados de {col.productos.length}</span>
                    </div>
                  </div>
                </div>
                {/* Interruptor del colegio completo */}
                <button
                  type="button"
                  onClick={() => toggleColegio(col)}
                  className={`inline-flex items-center gap-2 text-sm font-semibold px-3 py-2 rounded-lg transition-colors ${
                    col.activo
                      ? 'text-gray-600 hover:bg-gray-100'
                      : 'text-white bg-green-600 hover:bg-green-700'
                  }`}
                >
                  <span className={`relative w-11 h-6 rounded-full transition-colors ${col.activo ? 'bg-green-500' : 'bg-gray-300'}`}>
                    <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all ${col.activo ? 'left-[22px]' : 'left-0.5'}`} />
                  </span>
                  {col.activo ? 'Colegio activo' : 'Activar colegio'}
                </button>
              </div>

              {/* Grid de productos */}
              {prods.length === 0 ? (
                <p className="text-center text-gray-400 py-8 text-sm">Sin productos con precio configurado.</p>
              ) : (
                <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4 ${col.activo ? '' : 'opacity-60'}`}>
                  {prods.map((p) => (
                    <div
                      key={p.id_producto}
                      className={`relative border rounded-xl p-4 flex flex-col gap-3 transition-shadow hover:shadow-md ${
                        p.activo ? 'border-gray-200 bg-white' : 'border-gray-200 bg-gray-50'
                      }`}
                    >
                      {/* Destacar (esquina) */}
                      <button
                        type="button"
                        onClick={() => updateProducto(p.id_producto, { destacado: !p.destacado })}
                        title={p.destacado ? 'Quitar de destacados' : 'Destacar'}
                        className={`absolute top-3 right-3 p-1 rounded-lg ${p.destacado ? 'text-amber-500' : 'text-gray-300 hover:text-amber-400'}`}
                      >
                        <Star className="w-5 h-5" fill={p.destacado ? 'currentColor' : 'none'} />
                      </button>

                      {/* Foto del producto (con ícono por tipo de respaldo) */}
                      <div className={`relative w-full aspect-square rounded-lg overflow-hidden ${tipoColor(p.tipo)}`}>
                        <div className="absolute inset-0 grid place-items-center">
                          <Shirt className="w-12 h-12 opacity-70" />
                        </div>
                        {fotoProducto(col.id_colegio, p.id_producto) && (
                          <img
                            src={fotoProducto(col.id_colegio, p.id_producto)}
                            alt={p.nombre}
                            loading="lazy"
                            className="relative w-full h-full object-cover bg-white"
                            onError={(e) => e.currentTarget.remove()}
                          />
                        )}
                      </div>

                      <div>
                        <div className="font-medium text-gray-800 text-sm leading-snug">{p.nombre}</div>
                        {p.tipo && <div className="text-xs text-gray-400">{p.tipo}</div>}
                      </div>

                      <div className="flex items-end justify-between">
                        <div>
                          <div className="text-[11px] text-gray-400 leading-none">Desde</div>
                          <div className="font-bold text-gray-800 tabular-nums">{COP(p.precio_min)}</div>
                        </div>
                        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${p.stock_total > 0 ? 'bg-emerald-50 text-emerald-600' : 'bg-orange-50 text-orange-600'}`}>
                          {p.stock_total > 0 ? `${p.stock_total} disp.` : 'Por pedido'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between gap-2 pt-2 border-t border-gray-100">
                        <span className={`text-[11px] font-semibold px-2 py-1 rounded-full ${p.activo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {p.activo ? 'Publicada' : 'Pausada'}
                        </span>
                        <label className="flex items-center gap-1 text-[11px] text-gray-400">
                          Orden
                          <input
                            type="number"
                            defaultValue={p.orden || 0}
                            onBlur={(e) => {
                              const v = parseInt(e.target.value, 10) || 0
                              if (v !== (p.orden || 0)) updateProducto(p.id_producto, { orden: v })
                            }}
                            className="w-12 text-center border border-gray-200 rounded-md px-1 py-0.5 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-200"
                          />
                        </label>
                        <button
                          type="button"
                          onClick={() => updateProducto(p.id_producto, { activo: !p.activo })}
                          className={`inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1.5 rounded-lg ${
                            p.activo ? 'text-gray-600 hover:bg-gray-100' : 'text-white bg-green-600 hover:bg-green-700'
                          }`}
                        >
                          {p.activo ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                          {p.activo ? 'Pausar' : 'Publicar'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )
        })
      )}

      <p className="text-xs text-gray-400">
        Nota: pausar o destacar un producto aplica en todos los colegios donde se vende.
        Para ocultar solo un colegio, usa el interruptor del colegio.
      </p>
    </div>
  )
}
