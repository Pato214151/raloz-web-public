import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { BookOpen, DollarSign, TrendingUp, TrendingDown, AlertCircle, Check } from 'lucide-react'

const formatMoney = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

export default function Caja() {
  const [caja, setCaja] = useState(null)
  const [movimientos, setMovimientos] = useState([])
  const [loading, setLoading] = useState(true)
  const [montoInicial, setMontoInicial] = useState('')
  const [montoReal, setMontoReal] = useState('')
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    loadCaja()
  }, [])

  const loadCaja = async () => {
    setLoading(true)
    try {
      const res = await api.get('/caja/actual')
      setCaja(res.data.caja)
      if (res.data.caja) {
        const movRes = await api.get(`/caja/${res.data.caja.id_caja}/movimientos`)
        setMovimientos(movRes.data.movimientos || [])
      }
    } catch (err) {
      toast.error('Error cargando caja')
    } finally {
      setLoading(false)
    }
  }

  const abrirCaja = async (e) => {
    e.preventDefault()
    try {
      await api.post('/caja/abrir', { monto_inicial: parseFloat(montoInicial) || 0 })
      toast.success('Caja abierta')
      setMontoInicial('')
      setShowForm(false)
      loadCaja()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const cerrarCaja = async (e) => {
    e.preventDefault()
    if (!montoReal) {
      toast.error('Ingresa el monto real')
      return
    }
    try {
      await api.post('/caja/cerrar', { monto_real: parseFloat(montoReal) })
      toast.success('Caja cerrada')
      setMontoReal('')
      loadCaja()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  if (loading) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Caja Diaria</h2>

      {!caja ? (
        <div className="card">
          <div className="text-center py-12">
            <BookOpen className="mx-auto text-gray-300 mb-4" size={48} />
            <h3 className="text-lg font-semibold text-gray-700 mb-2">No hay caja abierta</h3>
            <p className="text-gray-500 mb-6">Abre una caja para comenzar el turno</p>

            {!showForm ? (
              <button
                onClick={() => setShowForm(true)}
                className="btn-primary"
              >
                Abrir Caja
              </button>
            ) : (
              <form onSubmit={abrirCaja} className="max-w-sm mx-auto space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Monto Inicial</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={montoInicial}
                    onChange={e => setMontoInicial(e.target.value)}
                    className="input w-full"
                    placeholder="0.00"
                    autoFocus
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => { setShowForm(false); setMontoInicial('') }}
                    className="btn-secondary flex-1"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="btn-success flex-1"
                  >
                    Abrir
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Status */}
          <div className="card bg-gradient-to-r from-blue-50 to-blue-100 border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-600 font-medium">Estado: ABIERTA</p>
                <p className="text-xs text-blue-500">{caja.fecha_apertura}</p>
              </div>
              <Check className="text-green-600" size={32} />
            </div>
          </div>

          {/* Resumen */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-600 mb-1">Monto Inicial</p>
                  <p className="text-2xl font-bold text-gray-900">{formatMoney(caja.monto_inicial)}</p>
                </div>
                <DollarSign className="text-blue-500" size={24} />
              </div>
            </div>

            <div className="card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-600 mb-1">Ventas</p>
                  <p className="text-2xl font-bold text-green-600">{formatMoney(caja.total_ventas)}</p>
                </div>
                <TrendingUp className="text-green-500" size={24} />
              </div>
            </div>

            <div className="card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-600 mb-1">Gastos</p>
                  <p className="text-2xl font-bold text-red-600">{formatMoney(caja.total_gastos)}</p>
                </div>
                <TrendingDown className="text-red-500" size={24} />
              </div>
            </div>

            <div className="card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-600 mb-1">Esperado</p>
                  <p className="text-2xl font-bold text-blue-600">{formatMoney(caja.monto_esperado)}</p>
                </div>
                <AlertCircle className="text-amber-500" size={24} />
              </div>
            </div>
          </div>

          {/* Detalles */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="card">
              <h3 className="font-semibold mb-4">Desglose</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center pb-3 border-b">
                  <span className="text-gray-600">Monto Inicial</span>
                  <span className="font-semibold">{formatMoney(caja.monto_inicial)}</span>
                </div>
                <div className="flex justify-between items-center pb-3 border-b">
                  <span className="text-gray-600">+ Ventas</span>
                  <span className="font-semibold text-green-600">+{formatMoney(caja.total_ventas)}</span>
                </div>
                <div className="flex justify-between items-center pb-3 border-b">
                  <span className="text-gray-600">- Gastos</span>
                  <span className="font-semibold text-red-600">-{formatMoney(caja.total_gastos)}</span>
                </div>
                <div className="flex justify-between items-center bg-blue-50 p-3 rounded font-bold">
                  <span>Esperado</span>
                  <span className="text-blue-600">{formatMoney(caja.monto_esperado)}</span>
                </div>
              </div>
            </div>

            {/* Movimientos recientes */}
            <div className="card">
              <h3 className="font-semibold mb-4">Movimientos Recientes</h3>
              {movimientos.length === 0 ? (
                <p className="text-sm text-gray-500">Sin movimientos registrados</p>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {movimientos.slice(0, 10).map(m => (
                    <div key={m.id_movimiento} className="flex justify-between items-center py-2 border-b text-sm">
                      <div>
                        <p className="font-medium">{m.tipo}</p>
                        <p className="text-xs text-gray-500">{m.descripcion}</p>
                      </div>
                      <p className={`font-semibold ${m.tipo === 'INGRESO' ? 'text-green-600' : 'text-red-600'}`}>
                        {m.tipo === 'INGRESO' ? '+' : '-'}{formatMoney(m.monto)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Cerrar caja */}
          <div className="card bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200">
            <h3 className="text-lg font-semibold mb-4">Cerrar Caja</h3>
            <form onSubmit={cerrarCaja} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Monto Real Contado</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={montoReal}
                  onChange={e => setMontoReal(e.target.value)}
                  className="input w-full lg:w-96"
                  placeholder="Ingresa el dinero contado..."
                />
              </div>

              {montoReal && (
                <div className="p-3 bg-white rounded border-l-4 border-blue-500">
                  <p className="text-sm text-gray-600 mb-2">Diferencia:</p>
                  <p className={`text-2xl font-bold ${
                    Math.abs(parseFloat(montoReal) - caja.monto_esperado) < 0.01
                      ? 'text-green-600'
                      : parseFloat(montoReal) > caja.monto_esperado
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}>
                    {parseFloat(montoReal) > caja.monto_esperado ? '+' : ''}
                    {formatMoney(parseFloat(montoReal) - caja.monto_esperado)}
                  </p>
                </div>
              )}

              <button
                type="submit"
                className="btn-danger w-full lg:w-auto"
              >
                Cerrar Caja
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
