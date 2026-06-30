import { useState, useEffect } from 'react'
import api from '../../services/api'
import { toast } from 'react-hot-toast'
import {
  Scissors, Plus, Printer, Trash2, X, Save, Loader2, Search, FileText,
} from 'lucide-react'

const INSUMOS_DEFAULT = [
  { insumo: 'Tela principal', especificacion: '', cantidad: '', unidad: 'mts', observacion: '' },
  { insumo: 'Malla',          especificacion: '', cantidad: '', unidad: 'mts', observacion: '' },
  { insumo: 'Forro',          especificacion: '', cantidad: '', unidad: 'mts', observacion: '' },
  { insumo: 'Cremallera',     especificacion: '', cantidad: '', unidad: 'und', observacion: '' },
  { insumo: 'Hilo',           especificacion: '', cantidad: '', unidad: 'conos', observacion: '' },
  { insumo: 'Elástico',       especificacion: '', cantidad: '', unidad: 'mts', observacion: '' },
]
const TALLAS_DEFAULT = ['6-8', '10-12', '14-16', 'S-M', 'L', 'XL']

const FORM_VACIO = () => ({
  prenda: '', id_colegio: '', taller: '', fecha_entrega: '',
  insumos: INSUMOS_DEFAULT.map(i => ({ ...i })),
  tallas: TALLAS_DEFAULT.map(t => ({ talla: t, cantidad: '' })),
  logo_descripcion: '', logo_ubicacion: '', logo_tecnica: 'Bordado', logo_tamano: '',
  observaciones: '', costo_tela: '', costo_insumos: '', costo_mano_obra: '',
})

export default function OrdenesProduccion() {
  const [ordenes, setOrdenes] = useState([])
  const [colegios, setColegios] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [imprimiendo, setImprimiendo] = useState(null)
  const [form, setForm] = useState(FORM_VACIO())

  const cargar = async () => {
    setLoading(true)
    try {
      const res = await api.get('/ordenes-produccion', { params: { q, per_page: 100 } })
      setOrdenes(res.data?.ordenes || [])
    } catch {
      toast.error('No se pudieron cargar las órdenes')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    api.get('/colegios').then(r => setColegios(r.data?.colegios || [])).catch(() => {})
  }, [])
  useEffect(() => { cargar() }, [])  // eslint-disable-line

  const set = (campo, valor) => setForm(f => ({ ...f, [campo]: valor }))
  const setInsumo = (i, campo, valor) =>
    setForm(f => ({ ...f, insumos: f.insumos.map((x, idx) => idx === i ? { ...x, [campo]: valor } : x) }))
  const addInsumo = () =>
    setForm(f => ({ ...f, insumos: [...f.insumos, { insumo: '', especificacion: '', cantidad: '', unidad: '', observacion: '' }] }))
  const delInsumo = (i) =>
    setForm(f => ({ ...f, insumos: f.insumos.filter((_, idx) => idx !== i) }))
  const setTalla = (i, valor) =>
    setForm(f => ({ ...f, tallas: f.tallas.map((x, idx) => idx === i ? { ...x, cantidad: valor } : x) }))

  const totalPrendas = form.tallas.reduce((s, t) => s + (parseInt(t.cantidad) || 0), 0)

  const abrirNueva = () => { setForm(FORM_VACIO()); setShowForm(true) }

  const onColegio = (id) => {
    set('id_colegio', id)
    const col = colegios.find(c => String(c.id_colegio) === String(id))
    if (col && !form.logo_descripcion) set('logo_descripcion', `Escudo ${col.nombre}`)
  }

  const guardar = async () => {
    if (!form.prenda.trim()) { toast.error('Escribe la prenda'); return }
    setGuardando(true)
    try {
      const payload = {
        ...form,
        id_colegio: form.id_colegio || null,
        insumos: form.insumos.filter(i => (i.insumo || '').trim() || (i.cantidad || '').toString().trim()),
        tallas: form.tallas.filter(t => (parseInt(t.cantidad) || 0) > 0),
        costo_tela: parseFloat(form.costo_tela) || 0,
        costo_insumos: parseFloat(form.costo_insumos) || 0,
        costo_mano_obra: parseFloat(form.costo_mano_obra) || 0,
      }
      await api.post('/ordenes-produccion', payload)
      toast.success('Orden creada')
      setShowForm(false)
      cargar()
    } catch (e) {
      toast.error(e.response?.data?.error || 'Error al guardar')
    } finally {
      setGuardando(false)
    }
  }

  const imprimir = async (o) => {
    setImprimiendo(o.id_orden)
    try {
      const res = await api.get(`/ordenes-produccion/${o.id_orden}/pdf`, { responseType: 'blob' })
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch {
      toast.error('No se pudo generar el PDF')
    } finally {
      setImprimiendo(null)
    }
  }

  const eliminar = async (o) => {
    if (!confirm(`¿Eliminar la orden ${o.numero_fmt}?`)) return
    try {
      await api.delete(`/ordenes-produccion/${o.id_orden}`)
      toast.success('Orden eliminada')
      cargar()
    } catch {
      toast.error('No se pudo eliminar')
    }
  }

  const fmt = (n) => '$' + (Number(n) || 0).toLocaleString('es-CO')

  return (
    <div className="space-y-4">
      {/* Encabezado */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Scissors className="text-amber-500" size={20} />
          <h2 className="text-lg font-bold text-gray-900">Órdenes de Producción</h2>
        </div>
        <button onClick={abrirNueva}
          className="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors">
          <Plus size={16} /> Nueva orden
        </button>
      </div>

      {/* Buscador */}
      <div className="flex items-center gap-2 max-w-md">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === 'Enter' && cargar()}
            placeholder="Buscar prenda, colegio, taller…"
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-400 focus:border-amber-400 outline-none" />
        </div>
        <button onClick={cargar} className="text-sm px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Buscar</button>
      </div>

      {/* Lista */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-gray-400"><Loader2 className="animate-spin inline" size={22} /></div>
        ) : ordenes.length === 0 ? (
          <div className="p-10 text-center text-gray-400">
            <FileText size={30} className="mx-auto mb-2 opacity-40" />
            Aún no hay órdenes. Crea la primera con “Nueva orden”.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                <tr>
                  <th className="text-left px-4 py-2.5">N°</th>
                  <th className="text-left px-4 py-2.5">Prenda</th>
                  <th className="text-left px-4 py-2.5">Colegio</th>
                  <th className="text-left px-4 py-2.5">Taller</th>
                  <th className="text-center px-4 py-2.5">Prendas</th>
                  <th className="text-left px-4 py-2.5">Fecha</th>
                  <th className="text-right px-4 py-2.5">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {ordenes.map(o => (
                  <tr key={o.id_orden} className="hover:bg-amber-50/40">
                    <td className="px-4 py-2.5 font-semibold text-gray-800">{o.numero_fmt}</td>
                    <td className="px-4 py-2.5">{o.prenda}</td>
                    <td className="px-4 py-2.5 text-gray-600">{o.nombre_colegio || '—'}</td>
                    <td className="px-4 py-2.5 text-gray-600">{o.taller || '—'}</td>
                    <td className="px-4 py-2.5 text-center font-medium">{o.total_prendas}</td>
                    <td className="px-4 py-2.5 text-gray-500">{(o.fecha || '').slice(0, 10)}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center justify-end gap-1.5">
                        <button onClick={() => imprimir(o)} disabled={imprimiendo === o.id_orden}
                          className="inline-flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-900 text-white">
                          {imprimiendo === o.id_orden ? <Loader2 size={13} className="animate-spin" /> : <Printer size={13} />} Imprimir
                        </button>
                        <button onClick={() => eliminar(o)}
                          className="p-1.5 rounded-md text-red-500 hover:bg-red-50" title="Eliminar">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Formulario (modal) */}
      {showForm && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-start justify-center p-3 overflow-y-auto">
          <div className="bg-white rounded-2xl w-full max-w-3xl my-4 shadow-xl">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-200 sticky top-0 bg-white rounded-t-2xl">
              <h3 className="font-bold text-gray-900 flex items-center gap-2"><Scissors size={18} className="text-amber-500" /> Nueva orden de producción</h3>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-700"><X size={20} /></button>
            </div>

            <div className="p-5 space-y-5">
              {/* Datos generales */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Field label="Prenda *">
                  <input value={form.prenda} onChange={e => set('prenda', e.target.value)}
                    placeholder="Ej: Chaqueta Diario" className={inputCls} />
                </Field>
                <Field label="Colegio">
                  <select value={form.id_colegio} onChange={e => onColegio(e.target.value)} className={inputCls}>
                    <option value="">— Sin colegio —</option>
                    {colegios.map(c => <option key={c.id_colegio} value={c.id_colegio}>{c.nombre}</option>)}
                  </select>
                </Field>
                <Field label="Taller / Proveedor">
                  <input value={form.taller} onChange={e => set('taller', e.target.value)} className={inputCls} />
                </Field>
                <Field label="Fecha de entrega">
                  <input type="date" value={form.fecha_entrega} onChange={e => set('fecha_entrega', e.target.value)} className={inputCls} />
                </Field>
              </div>

              {/* Insumos */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">Materiales / Insumos</p>
                  <button onClick={addInsumo} className="text-xs text-amber-600 hover:text-amber-700 inline-flex items-center gap-1"><Plus size={13} /> Agregar</button>
                </div>
                <div className="space-y-1.5">
                  {form.insumos.map((it, i) => (
                    <div key={i} className="grid grid-cols-12 gap-1.5 items-center">
                      <input value={it.insumo} onChange={e => setInsumo(i, 'insumo', e.target.value)} placeholder="Insumo" className={`${inputSm} col-span-3`} />
                      <input value={it.especificacion} onChange={e => setInsumo(i, 'especificacion', e.target.value)} placeholder="Tipo / color" className={`${inputSm} col-span-4`} />
                      <input value={it.cantidad} onChange={e => setInsumo(i, 'cantidad', e.target.value)} placeholder="Cant." className={`${inputSm} col-span-2`} />
                      <input value={it.unidad} onChange={e => setInsumo(i, 'unidad', e.target.value)} placeholder="Und" className={`${inputSm} col-span-2`} />
                      <button onClick={() => delInsumo(i)} className="col-span-1 text-red-400 hover:text-red-600 flex justify-center"><Trash2 size={14} /></button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Tallas */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">Tallas y cantidades</p>
                  <span className="text-xs text-gray-500">Total: <b className="text-amber-600">{totalPrendas}</b></span>
                </div>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                  {form.tallas.map((t, i) => (
                    <div key={t.talla} className="text-center">
                      <p className="text-[11px] font-semibold text-gray-500 mb-0.5">{t.talla}</p>
                      <input value={t.cantidad} onChange={e => setTalla(i, e.target.value)} inputMode="numeric"
                        className="w-full text-center text-sm border border-gray-300 rounded-md py-1.5 focus:ring-2 focus:ring-amber-400 outline-none" />
                    </div>
                  ))}
                </div>
              </div>

              {/* Logo */}
              <div>
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1.5">Logo / Marca</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <Field label="Descripción"><input value={form.logo_descripcion} onChange={e => set('logo_descripcion', e.target.value)} className={inputCls} /></Field>
                  <Field label="Ubicación"><input value={form.logo_ubicacion} onChange={e => set('logo_ubicacion', e.target.value)} placeholder="Pecho izquierdo…" className={inputCls} /></Field>
                  <Field label="Técnica">
                    <select value={form.logo_tecnica} onChange={e => set('logo_tecnica', e.target.value)} className={inputCls}>
                      <option>Bordado</option><option>Estampado</option><option>Sublimado</option><option>Otro</option>
                    </select>
                  </Field>
                  <Field label="Tamaño"><input value={form.logo_tamano} onChange={e => set('logo_tamano', e.target.value)} placeholder="8 x 8 cm" className={inputCls} /></Field>
                </div>
                <p className="text-[11px] text-gray-400 mt-1">El escudo del colegio se agrega solo en el PDF.</p>
              </div>

              {/* Observaciones + costos */}
              <Field label="Observaciones">
                <textarea value={form.observaciones} onChange={e => set('observaciones', e.target.value)} rows={2} className={inputCls} />
              </Field>
              <div>
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1.5">Costos (opcional)</p>
                <div className="grid grid-cols-3 gap-3">
                  <Field label="Tela"><input value={form.costo_tela} onChange={e => set('costo_tela', e.target.value)} inputMode="numeric" className={inputCls} /></Field>
                  <Field label="Insumos"><input value={form.costo_insumos} onChange={e => set('costo_insumos', e.target.value)} inputMode="numeric" className={inputCls} /></Field>
                  <Field label="Mano de obra"><input value={form.costo_mano_obra} onChange={e => set('costo_mano_obra', e.target.value)} inputMode="numeric" className={inputCls} /></Field>
                </div>
                <p className="text-xs text-gray-500 mt-1 text-right">
                  Total: <b>{fmt((parseFloat(form.costo_tela) || 0) + (parseFloat(form.costo_insumos) || 0) + (parseFloat(form.costo_mano_obra) || 0))}</b>
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-gray-200 sticky bottom-0 bg-white rounded-b-2xl">
              <button onClick={() => setShowForm(false)} className="text-sm px-4 py-2 rounded-lg border border-gray-300 hover:bg-gray-50">Cancelar</button>
              <button onClick={guardar} disabled={guardando}
                className="inline-flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white disabled:opacity-60">
                {guardando ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} Guardar orden
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const inputCls = 'w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-400 focus:border-amber-400 outline-none'
const inputSm = 'px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-amber-400 outline-none'

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-gray-600 mb-1 block">{label}</span>
      {children}
    </label>
  )
}
