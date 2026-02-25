import { useState } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Search, FileText } from 'lucide-react'

export default function BuscarFacturas() {
  const [buscar, setBuscar] = useState('')
  const [facturas, setFacturas] = useState([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState(null)

  const handleSearch = async (e) => {
    e?.preventDefault()
    if (!buscar.trim()) return

    setLoading(true)
    try {
      const res = await api.get('/facturas', { params: { buscar, per_page: 50 } })
      setFacturas(res.data.facturas || [])
      if (res.data.facturas?.length === 0) toast('No se encontraron facturas')
    } catch {
      toast.error('Error en búsqueda')
    } finally {
      setLoading(false)
    }
  }

  const verDetalle = async (id) => {
    try {
      const res = await api.get(`/facturas/${id}`)
      setSelected(res.data.factura)
    } catch {
      toast.error('Error cargando factura')
    }
  }

  const badgeClass = (estado) => {
    const map = { PENDIENTE: 'badge-pendiente', PAGADA: 'badge-pagada', ANULADA: 'badge-anulada', ABONO: 'badge-abono' }
    return map[estado] || 'badge-pendiente'
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Buscar Facturas</h2>

      <form onSubmit={handleSearch} className="flex gap-3">
        <input value={buscar} onChange={e => setBuscar(e.target.value)} className="input-field flex-1" placeholder="Número, nombre o teléfono..." />
        <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
          <Search size={18} /> Buscar
        </button>
      </form>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Lista */}
        <div className="space-y-2">
          {facturas.map(f => (
            <div key={f.id_factura} onClick={() => verDetalle(f.id_factura)}
              className={`card cursor-pointer hover:shadow-md transition-shadow ${selected?.id_factura === f.id_factura ? 'ring-2 ring-raloz-500' : ''}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-gray-900">{f.numero_factura}</p>
                  <p className="text-sm text-gray-500">{f.cliente_nombre}</p>
                  <p className="text-xs text-gray-400">{f.fecha_factura}</p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-gray-900">${Math.round(f.total).toLocaleString('es-CO')}</p>
                  <span className={badgeClass(f.estado)}>{f.estado}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Detalle */}
        {selected && (
          <div className="card sticky top-4">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="text-raloz-600" size={20} />
              <h3 className="text-lg font-semibold">{selected.numero_factura}</h3>
              <span className={badgeClass(selected.estado)}>{selected.estado}</span>
            </div>

            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">Cliente</span><span>{selected.cliente_nombre}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Colegio</span><span>{selected.colegio_nombre}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Fecha</span><span>{selected.fecha_factura}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Total</span><span className="font-bold">${Math.round(selected.total).toLocaleString('es-CO')}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Pagado</span><span className="text-green-600">${Math.round(selected.total_pagado || 0).toLocaleString('es-CO')}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Saldo</span><span className="text-red-600 font-bold">${Math.round(selected.saldo || 0).toLocaleString('es-CO')}</span></div>
            </div>

            {selected.detalles?.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Productos</h4>
                <div className="space-y-1">
                  {selected.detalles.map(d => (
                    <div key={d.id_detalle} className="flex justify-between text-sm py-1 border-b border-gray-50">
                      <span>{d.producto_nombre} - {d.talla_individual} x{d.cantidad}</span>
                      <span>${Math.round(d.total_linea).toLocaleString('es-CO')}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selected.pagos?.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Pagos</h4>
                <div className="space-y-1">
                  {selected.pagos.map(p => (
                    <div key={p.id_pago} className="flex justify-between text-sm py-1 border-b border-gray-50">
                      <span>{p.fecha_pago} - {p.metodo_pago}</span>
                      <span className="text-green-600">${Math.round(p.valor).toLocaleString('es-CO')}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
