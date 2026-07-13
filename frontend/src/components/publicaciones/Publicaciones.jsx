import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Megaphone, Star, Eye, EyeOff, Save, Loader2, Search } from 'lucide-react'

export default function Publicaciones() {
  const [banner, setBanner] = useState({ texto: '', activo: true })
  const [savingBanner, setSavingBanner] = useState(false)
  const [productos, setProductos] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')

  useEffect(() => { cargar() }, [])

  async function cargar() {
    setLoading(true)
    try {
      const [cfg, prods] = await Promise.all([
        api.get('/tienda/admin/config'),
        api.get('/productos?activos=false'), // todos, incluidos los pausados
      ])
      setBanner({
        texto: cfg.data.banner_texto || '',
        activo: !!cfg.data.banner_activo,
      })
      const lista = (prods.data.productos || []).sort(
        (a, b) => (a.orden || 0) - (b.orden || 0) || a.nombre.localeCompare(b.nombre),
      )
      setProductos(lista)
    } catch {
      toast.error('No se pudo cargar la configuración de la tienda')
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

  // Actualización optimista: cambia la UI ya y persiste; si falla, recarga.
  async function actualizar(id, cambios) {
    setProductos((prev) =>
      prev.map((p) => (p.id_producto === id ? { ...p, ...cambios } : p)),
    )
    try {
      await api.put(`/productos/${id}`, cambios)
    } catch {
      toast.error('No se pudo actualizar el producto')
      cargar()
    }
  }

  const visibles = productos.filter((p) =>
    (p.nombre || '').toLowerCase().includes(q.toLowerCase()),
  )
  const publicados = productos.filter((p) => p.activo).length

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-lg">
          <Megaphone className="w-6 h-6 text-blue-700" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Publicaciones</h1>
          <p className="text-gray-600 text-sm">
            Controla qué se muestra en la tienda online y el mensaje del banner.
          </p>
        </div>
      </div>

      {/* Editor de banner */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Banner de la tienda</h2>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
            <span>{banner.activo ? 'Visible' : 'Oculto'}</span>
            <button
              type="button"
              onClick={() => setBanner((b) => ({ ...b, activo: !b.activo }))}
              className={`relative w-11 h-6 rounded-full transition-colors ${
                banner.activo ? 'bg-green-500' : 'bg-gray-300'
              }`}
              aria-pressed={banner.activo}
              aria-label="Mostrar u ocultar el banner"
            >
              <span
                className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all ${
                  banner.activo ? 'left-[22px]' : 'left-0.5'
                }`}
              />
            </button>
          </label>
        </div>
        <textarea
          value={banner.texto}
          onChange={(e) => setBanner((b) => ({ ...b, texto: e.target.value }))}
          maxLength={300}
          rows={2}
          placeholder="Ej: Temporada 2026 — Uniformes en stock para Marillac, Adventista y Manyanet"
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-400">{banner.texto.length}/300</span>
          <button
            type="button"
            onClick={guardarBanner}
            disabled={savingBanner}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            {savingBanner ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Guardar banner
          </button>
        </div>
      </div>

      {/* Tabla de productos */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="flex flex-wrap items-center justify-between gap-3 p-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-800">
            Productos <span className="text-gray-400 font-normal">· {publicados} publicados de {productos.length}</span>
          </h2>
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

        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-400">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : visibles.length === 0 ? (
          <p className="text-center text-gray-400 py-12 text-sm">No hay productos que coincidan.</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {visibles.map((p) => (
              <div key={p.id_producto} className="flex flex-wrap items-center gap-3 p-4">
                {/* Destacar */}
                <button
                  type="button"
                  onClick={() => actualizar(p.id_producto, { destacado: !p.destacado })}
                  title={p.destacado ? 'Quitar de destacados' : 'Destacar'}
                  className={`p-1.5 rounded-lg transition-colors ${
                    p.destacado ? 'text-amber-500 hover:bg-amber-50' : 'text-gray-300 hover:bg-gray-50'
                  }`}
                  aria-label="Destacar producto"
                >
                  <Star className="w-5 h-5" fill={p.destacado ? 'currentColor' : 'none'} />
                </button>

                {/* Nombre + tipo */}
                <div className="flex-1 min-w-[160px]">
                  <div className="font-medium text-gray-800 text-sm">{p.nombre}</div>
                  {p.tipo && <div className="text-xs text-gray-400">{p.tipo}</div>}
                </div>

                {/* Orden */}
                <label className="flex items-center gap-1.5 text-xs text-gray-400">
                  Orden
                  <input
                    type="number"
                    defaultValue={p.orden || 0}
                    onBlur={(e) => {
                      const v = parseInt(e.target.value, 10) || 0
                      if (v !== (p.orden || 0)) actualizar(p.id_producto, { orden: v })
                    }}
                    className="w-14 text-center border border-gray-200 rounded-md px-1 py-1 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  />
                </label>

                {/* Estado */}
                <span
                  className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                    p.activo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {p.activo ? 'Publicada' : 'Pausada'}
                </span>

                {/* Publicar / pausar */}
                <button
                  type="button"
                  onClick={() => actualizar(p.id_producto, { activo: !p.activo })}
                  className={`inline-flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors ${
                    p.activo
                      ? 'text-gray-600 hover:bg-gray-100'
                      : 'text-white bg-green-600 hover:bg-green-700'
                  }`}
                >
                  {p.activo ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  {p.activo ? 'Pausar' : 'Publicar'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
