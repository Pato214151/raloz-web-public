import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Package } from 'lucide-react'

export default function StockView() {
  const [resumen, setResumen] = useState([])
  const [stock, setStock] = useState([])
  const [colegioId, setColegioId] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadResumen()
  }, [])

  const loadResumen = async () => {
    try {
      const res = await api.get('/stock/resumen')
      setResumen(res.data.resumen || [])
    } catch {
      toast.error('Error cargando stock')
    } finally {
      setLoading(false)
    }
  }

  const loadStock = async (id) => {
    setColegioId(id)
    try {
      const res = await api.get('/stock', { params: { colegio_id: id, solo_disponible: 'true' } })
      setStock(res.data.stock || [])
    } catch {
      toast.error('Error cargando detalle')
    }
  }

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Inventario</h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {resumen.map(r => (
          <div key={r.id_colegio} onClick={() => loadStock(r.id_colegio)}
            className={`card cursor-pointer hover:shadow-md transition-shadow ${colegioId === r.id_colegio ? 'ring-2 ring-raloz-500' : ''}`}>
            <div className="flex items-center gap-3">
              <Package className="text-raloz-600" size={24} />
              <div>
                <p className="font-semibold">{r.colegio}</p>
                <p className="text-sm text-gray-500">{r.total_unidades} unidades • {r.total_items} items</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {stock.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Detalle de Stock</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-gray-200">
                <th className="text-left py-2 px-3 text-gray-600">Producto</th>
                <th className="text-left py-2 px-3 text-gray-600">Talla</th>
                <th className="text-right py-2 px-3 text-gray-600">Cantidad</th>
              </tr></thead>
              <tbody>
                {stock.map(s => (
                  <tr key={s.id_stock} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 px-3">{s.id_producto}</td>
                    <td className="py-2 px-3">{s.talla_individual}</td>
                    <td className="py-2 px-3 text-right font-medium">{s.cantidad}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
