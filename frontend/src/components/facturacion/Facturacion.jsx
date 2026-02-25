import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Plus, Trash2, Save } from 'lucide-react'

export default function Facturacion() {
  const [colegios, setColegios] = useState([])
  const [productos, setProductos] = useState([])
  const [form, setForm] = useState({
    id_colegio: '', cliente_nombre: '', cliente_telefono: '',
    fecha_factura: new Date().toISOString().split('T')[0],
    metodo_pago: 'EFECTIVO', abono: 0,
  })
  const [detalles, setDetalles] = useState([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([
      api.get('/colegios'),
      api.get('/productos'),
    ]).then(([colRes, prodRes]) => {
      setColegios(colRes.data.colegios || [])
      setProductos(prodRes.data.productos || [])
    }).catch(() => toast.error('Error cargando datos'))
  }, [])

  const agregarLinea = () => {
    setDetalles([...detalles, { id_producto: '', talla_individual: '', cantidad: 1, precio_unitario: 0 }])
  }

  const actualizarLinea = (idx, field, value) => {
    const nuevos = [...detalles]
    nuevos[idx] = { ...nuevos[idx], [field]: value }
    setDetalles(nuevos)
  }

  const eliminarLinea = (idx) => {
    setDetalles(detalles.filter((_, i) => i !== idx))
  }

  const subtotal = detalles.reduce((sum, d) => sum + (d.cantidad * d.precio_unitario), 0)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.id_colegio || !form.cliente_nombre || detalles.length === 0) {
      toast.error('Completa colegio, cliente y al menos un producto')
      return
    }

    setSaving(true)
    try {
      const payload = { ...form, detalles, abono: parseFloat(form.abono) || 0 }
      const res = await api.post('/facturas', payload)
      toast.success(`Factura ${res.data.factura.numero_factura} creada`)
      // Reset
      setDetalles([])
      setForm(f => ({ ...f, cliente_nombre: '', cliente_telefono: '', abono: 0 }))
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al crear factura')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Nueva Venta</h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Datos del cliente */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Datos del Cliente</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Colegio</label>
              <select value={form.id_colegio} onChange={e => setForm({...form, id_colegio: e.target.value})} className="input-field" required>
                <option value="">Seleccionar...</option>
                {colegios.map(c => <option key={c.id_colegio} value={c.id_colegio}>{c.nombre}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
              <input value={form.cliente_nombre} onChange={e => setForm({...form, cliente_nombre: e.target.value})} className="input-field" required placeholder="Nombre del cliente" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
              <input value={form.cliente_telefono} onChange={e => setForm({...form, cliente_telefono: e.target.value})} className="input-field" placeholder="300 123 4567" />
            </div>
          </div>
        </div>

        {/* Productos */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Productos</h3>
            <button type="button" onClick={agregarLinea} className="btn-secondary flex items-center gap-2">
              <Plus size={16} /> Agregar
            </button>
          </div>

          {detalles.length === 0 ? (
            <p className="text-gray-400 text-center py-8">Agrega productos a la factura</p>
          ) : (
            <div className="space-y-3">
              {detalles.map((det, idx) => (
                <div key={idx} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <select value={det.id_producto} onChange={e => actualizarLinea(idx, 'id_producto', e.target.value)} className="input-field flex-1">
                    <option value="">Producto...</option>
                    {productos.map(p => <option key={p.id_producto} value={p.id_producto}>{p.nombre}</option>)}
                  </select>
                  <input value={det.talla_individual} onChange={e => actualizarLinea(idx, 'talla_individual', e.target.value)} className="input-field w-20" placeholder="Talla" />
                  <input type="number" min="1" value={det.cantidad} onChange={e => actualizarLinea(idx, 'cantidad', parseInt(e.target.value) || 0)} className="input-field w-20" />
                  <input type="number" min="0" value={det.precio_unitario} onChange={e => actualizarLinea(idx, 'precio_unitario', parseFloat(e.target.value) || 0)} className="input-field w-28" placeholder="Precio" />
                  <span className="text-sm font-medium w-24 text-right">${(det.cantidad * det.precio_unitario).toLocaleString('es-CO')}</span>
                  <button type="button" onClick={() => eliminarLinea(idx)} className="text-red-400 hover:text-red-600"><Trash2 size={18} /></button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Total y pago */}
        <div className="card">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Método</label>
                <select value={form.metodo_pago} onChange={e => setForm({...form, metodo_pago: e.target.value})} className="input-field">
                  {['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA'].map(m => <option key={m}>{m}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Abono</label>
                <input type="number" min="0" value={form.abono} onChange={e => setForm({...form, abono: e.target.value})} className="input-field w-36" />
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-3xl font-bold text-raloz-700">${subtotal.toLocaleString('es-CO')}</p>
            </div>
          </div>
          <button type="submit" disabled={saving || detalles.length === 0} className="btn-primary w-full mt-4 py-3 flex items-center justify-center gap-2">
            <Save size={18} /> {saving ? 'Guardando...' : 'Crear Factura'}
          </button>
        </div>
      </form>
    </div>
  )
}
