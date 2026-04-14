import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Hammer, RefreshCw, PlusCircle } from 'lucide-react'

function formatCant(n) { return n === 1 ? '1 unidad' : `${n} unidades` }

export default function StockPendienteFab() {
  const [items, setItems]           = useState([])
  const [loading, setLoading]       = useState(false)
  const [modal, setModal]           = useState(null)   // item seleccionado para registrar fab
  const [cantFab, setCantFab]       = useState(0)
  const [guardando, setGuardando]   = useState(false)
  const [msgOk, setMsgOk]           = useState('')

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/tienda/admin/fabricacion/stock-pendiente')
      setItems(res.data.items || [])
    } catch {
      toast.error('Error cargando stock pendiente')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  const abrirModal = (item) => {
    setModal(item)
    setCantFab(item.cantidad_pendiente)
    setMsgOk('')
  }

  const registrar = async () => {
    if (!modal || cantFab <= 0) return
    setGuardando(true)
    try {
      await api.post('/tienda/admin/fabricacion/stock-pendiente/registrar', {
        id_pendiente: modal.id_pendiente,
        cantidad_fabricada: cantFab,
      })
      setMsgOk(`✓ Se registraron ${cantFab} unidades. Stock actualizado.`)
      await cargar()
      setTimeout(() => setModal(null), 2000)
    } catch {
      toast.error('Error al registrar fabricación')
    } finally {
      setGuardando(false)
    }
  }

  // Agrupar por colegio
  const porColegio = items.reduce((acc, item) => {
    const key = item.nombre_colegio || 'Sin colegio'
    if (!acc[key]) acc[key] = []
    acc[key].push(item)
    return acc
  }, {})

  return (
    <div className="space-y-4">
      {/* Cabecera */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Hammer size={20} className="text-amber-700" /> Stock Pendiente de Fabricación
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">{items.length} lote{items.length !== 1 ? 's' : ''} pendientes</p>
        </div>
        <button onClick={cargar} disabled={loading}
          className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 text-gray-500">
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {loading && <p className="text-center text-gray-400 py-10">Cargando...</p>}
      {!loading && !items.length && (
        <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-gray-400">
          <Hammer size={36} className="mx-auto mb-3 opacity-30" />
          <p>No hay stock pendiente de fabricación</p>
        </div>
      )}

      {/* Grupos por colegio */}
      {Object.entries(porColegio).map(([colegio, lotes]) => (
        <div key={colegio} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="bg-amber-50 border-b border-amber-100 px-4 py-2.5">
            <p className="font-semibold text-amber-800 text-sm">{colegio}</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  {['Producto', 'Talla', 'Pendiente', 'Pedidos asociados', 'Acción'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {lotes.map(item => (
                  <tr key={item.id_pendiente} className="hover:bg-gray-50/50">
                    <td className="px-4 py-3 font-medium text-gray-900">{item.nombre_producto}</td>
                    <td className="px-4 py-3">
                      <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs font-bold">{item.talla}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-amber-700 font-bold">{formatCant(item.cantidad_pendiente)}</span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500 font-mono">
                      {item.ids_pedidos ? item.ids_pedidos.split(',').map(id => `#${id}`).join(', ') : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={() => abrirModal(item)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 text-white rounded-lg text-xs font-semibold hover:bg-amber-700">
                        <PlusCircle size={13} /> Registrar fabricación
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {/* Modal registrar fabricación */}
      {modal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setModal(null)}>
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Hammer size={18} className="text-amber-700" /> Registrar Fabricación
            </h3>
            <div className="bg-amber-50 rounded-lg p-3 text-sm space-y-1">
              <p><span className="text-gray-500">Producto:</span> <strong>{modal.nombre_producto}</strong></p>
              <p><span className="text-gray-500">Talla:</span> <strong>{modal.talla}</strong></p>
              <p><span className="text-gray-500">Colegio:</span> <strong>{modal.nombre_colegio}</strong></p>
              <p><span className="text-gray-500">Pendiente actual:</span> <strong className="text-amber-700">{modal.cantidad_pendiente} unidades</strong></p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cantidad fabricada</label>
              <input
                type="number" min={1} max={modal.cantidad_pendiente}
                value={cantFab}
                onChange={e => setCantFab(parseInt(e.target.value) || 0)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
              />
              <p className="text-xs text-gray-400 mt-1">
                Esta cantidad se sumará al stock real y se actualizarán los pedidos afectados.
              </p>
            </div>

            {msgOk && <p className="text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2">{msgOk}</p>}

            <div className="flex gap-2 pt-1">
              <button onClick={registrar} disabled={guardando || cantFab <= 0}
                className="flex-1 py-2 bg-amber-600 text-white rounded-lg text-sm font-semibold hover:bg-amber-700 disabled:opacity-50">
                {guardando ? 'Guardando...' : 'Confirmar fabricación'}
              </button>
              <button onClick={() => setModal(null)}
                className="px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
