import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { ClipboardCheck, RefreshCw, Save } from 'lucide-react'

// Filas planas (producto × talla) con el stock del sistema y un input para el conteo real.
export default function ConteoFisico() {
  const [colegios, setColegios] = useState([])
  const [colegioId, setColegioId] = useState('')
  const [filas, setFilas] = useState([])   // {id_producto, nombre, talla, sistema}
  const [conteos, setConteos] = useState({})   // key `${id}|${talla}` → string
  const [loading, setLoading] = useState(false)
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    api.get('/colegios').then(r => setColegios(r.data?.colegios || [])).catch(() => {})
  }, [])

  const cargar = useCallback(async (cid) => {
    if (!cid) { setFilas([]); return }
    setLoading(true)
    try {
      const res = await api.get('/stock/catalogo', { params: { colegio_id: cid } })
      const cat = res.data?.catalogo || res.data?.productos || []
      const out = []
      for (const p of cat) {
        for (const t of (p.tallas || [])) {
          out.push({
            id_producto: p.id_producto,
            nombre: p.producto_nombre || p.nombre,
            talla: t.talla,
            sistema: t.cantidad ?? 0,
          })
        }
      }
      setFilas(out)
      setConteos({})
    } catch {
      toast.error('No pude cargar el inventario del colegio')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { cargar(colegioId) }, [colegioId, cargar])

  const key = (f) => `${f.id_producto}|${f.talla}`
  const cambios = filas.filter(f => {
    const v = conteos[key(f)]
    return v !== undefined && v !== '' && Number(v) !== f.sistema
  })

  const guardar = async () => {
    if (cambios.length === 0) { toast('No hay cambios para guardar'); return }
    if (!window.confirm(`Vas a ajustar ${cambios.length} prenda(s) al conteo real. ¿Confirmas?`)) return
    setGuardando(true)
    let ok = 0
    for (const f of cambios) {
      try {
        await api.post('/stock', {
          id_colegio: Number(colegioId),
          id_producto: f.id_producto,
          talla_individual: f.talla,
          cantidad: Number(conteos[key(f)]),
          observaciones: 'Conteo físico',
        })
        ok++
      } catch { /* seguimos con las demás */ }
    }
    setGuardando(false)
    toast.success(`${ok} de ${cambios.length} prenda(s) ajustada(s) ✅`)
    cargar(colegioId)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
            <ClipboardCheck size={16} className="text-amber-500" /> Conteo físico
          </h3>
          <p className="text-xs text-gray-400">Cuenta lo que tienes en físico y ajusta el sistema de una sola vez. Cada cambio queda en el kardex.</p>
        </div>
        <select value={colegioId} onChange={e => setColegioId(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-amber-400 min-w-[180px]">
          <option value="">Elige un colegio…</option>
          {colegios.map(c => <option key={c.id_colegio} value={c.id_colegio}>{c.nombre}</option>)}
        </select>
      </div>

      {!colegioId ? (
        <div className="bg-white rounded-xl border border-gray-100 py-12 text-center text-sm text-gray-400">
          Elige un colegio para empezar el conteo.
        </div>
      ) : loading ? (
        <div className="bg-white rounded-xl border border-gray-100 py-12 text-center text-sm text-gray-400">Cargando…</div>
      ) : (
        <>
          <div className="bg-white rounded-xl border border-gray-100 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-gray-500">
                  <th className="px-3 py-2.5 text-left font-medium">Prenda</th>
                  <th className="px-3 py-2.5 text-center font-medium">Talla</th>
                  <th className="px-3 py-2.5 text-center font-medium">Sistema</th>
                  <th className="px-3 py-2.5 text-center font-medium">Conteo real</th>
                  <th className="px-3 py-2.5 text-center font-medium">Dif.</th>
                </tr>
              </thead>
              <tbody>
                {filas.map(f => {
                  const v = conteos[key(f)]
                  const cambio = v !== undefined && v !== '' && Number(v) !== f.sistema
                  const dif = cambio ? Number(v) - f.sistema : null
                  return (
                    <tr key={key(f)} className={`border-b border-gray-50 ${cambio ? 'bg-amber-50/40' : ''}`}>
                      <td className="px-3 py-2 text-gray-800">{f.nombre}</td>
                      <td className="px-3 py-2 text-center text-gray-600">{f.talla}</td>
                      <td className="px-3 py-2 text-center font-medium text-gray-700 tabular-nums">{f.sistema}</td>
                      <td className="px-3 py-2 text-center">
                        <input type="number" min="0" inputMode="numeric"
                          value={v ?? ''}
                          onChange={e => setConteos(c => ({ ...c, [key(f)]: e.target.value }))}
                          placeholder="—"
                          className="w-20 text-center px-2 py-1 border border-gray-200 rounded-lg outline-none focus:border-amber-400" />
                      </td>
                      <td className="px-3 py-2 text-center tabular-nums font-medium">
                        {dif === null ? <span className="text-gray-300">·</span>
                          : dif === 0 ? <span className="text-emerald-600">0</span>
                          : <span className={dif > 0 ? 'text-emerald-600' : 'text-red-600'}>{dif > 0 ? '+' : ''}{dif}</span>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Barra de guardar */}
          <div className="flex items-center justify-between gap-3 sticky bottom-0 bg-white/90 backdrop-blur rounded-xl border border-gray-100 px-4 py-3">
            <p className="text-sm text-gray-500">
              {cambios.length > 0
                ? <><b className="text-amber-700">{cambios.length}</b> cambio(s) por guardar</>
                : 'Escribe el conteo real solo en las que difieran'}
            </p>
            <div className="flex gap-2">
              <button onClick={() => cargar(colegioId)} disabled={loading || guardando}
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50">
                <RefreshCw size={14} /> Recargar
              </button>
              <button onClick={guardar} disabled={guardando || cambios.length === 0}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white rounded-lg disabled:opacity-40"
                style={{ background: '#071E49' }}>
                <Save size={15} /> {guardando ? 'Guardando…' : 'Guardar ajustes'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
