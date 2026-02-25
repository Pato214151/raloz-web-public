import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Clock, Check } from 'lucide-react'

export default function Pendientes() {
  const [pendientes, setPendientes] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadPendientes() }, [])

  const loadPendientes = async () => {
    try {
      const res = await api.get('/pendientes')
      setPendientes(res.data.pendientes || [])
    } catch {
      toast.error('Error cargando pendientes')
    } finally {
      setLoading(false)
    }
  }

  const entregar = async (id) => {
    try {
      await api.post(`/pendientes/${id}/entregar`)
      toast.success('Marcado como entregado')
      loadPendientes()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Pendientes de Entrega</h2>
        <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-medium">{pendientes.length} pendientes</span>
      </div>

      {pendientes.length === 0 ? (
        <div className="card text-center py-12">
          <Check className="mx-auto text-green-400 mb-4" size={48} />
          <p className="text-gray-500">No hay pendientes de entrega</p>
        </div>
      ) : (
        <div className="space-y-3">
          {pendientes.map(p => (
            <div key={p.id_pendiente} className="card flex items-center justify-between">
              <div>
                <p className="font-semibold">{p.producto_nombre} — Talla {p.talla_individual}</p>
                <p className="text-sm text-gray-500">Factura: {p.numero_factura} • Colegio: {p.colegio_nombre}</p>
                <p className="text-xs text-gray-400">Faltan: {p.cantidad_faltante} uds • {p.fecha_registro}</p>
              </div>
              <button onClick={() => entregar(p.id_pendiente)} className="btn-success flex items-center gap-2">
                <Check size={16} /> Entregar
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
