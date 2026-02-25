import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { BookOpen, DollarSign } from 'lucide-react'

export default function Caja() {
  const [caja, setCaja] = useState(null)
  const [montoInicial, setMontoInicial] = useState('')
  const [montoReal, setMontoReal] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadCaja() }, [])

  const loadCaja = async () => {
    try {
      const res = await api.get('/caja/actual')
      setCaja(res.data.caja)
    } catch {
      toast.error('Error cargando caja')
    } finally {
      setLoading(false)
    }
  }

  const abrirCaja = async () => {
    try {
      await api.post('/caja/abrir', { monto_inicial: parseFloat(montoInicial) || 0 })
      toast.success('Caja abierta')
      setMontoInicial('')
      loadCaja()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const cerrarCaja = async () => {
    try {
      await api.post('/caja/cerrar', { monto_real: parseFloat(montoReal) || 0 })
      toast.success('Caja cerrada')
      setMontoReal('')
      loadCaja()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Caja Diaria</h2>

      {!caja ? (
        <div className="card text-center py-12">
          <BookOpen className="mx-auto text-gray-300 mb-4" size={48} />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">No hay caja abierta</h3>
          <div className="flex items-center justify-center gap-3 mt-4">
            <input type="number" value={montoInicial} onChange={e => setMontoInicial(e.target.value)} className="input-field w-48" placeholder="Monto inicial" />
            <button onClick={abrirCaja} className="btn-success">Abrir Caja</button>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card"><p className="text-sm text-gray-500">Monto Inicial</p><p className="text-xl font-bold">{fmt(caja.monto_inicial)}</p></div>
            <div className="card"><p className="text-sm text-gray-500">Ventas</p><p className="text-xl font-bold text-green-600">{fmt(caja.total_ventas)}</p></div>
            <div className="card"><p className="text-sm text-gray-500">Gastos</p><p className="text-xl font-bold text-red-600">{fmt(caja.total_gastos)}</p></div>
            <div className="card"><p className="text-sm text-gray-500">Esperado</p><p className="text-xl font-bold text-blue-600">{fmt(caja.monto_esperado)}</p></div>
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Cerrar Caja</h3>
            <div className="flex items-end gap-3">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Monto Real en Caja</label>
                <input type="number" value={montoReal} onChange={e => setMontoReal(e.target.value)} className="input-field w-48" placeholder="Contar dinero..." />
              </div>
              <button onClick={cerrarCaja} className="btn-danger">Cerrar Caja</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
