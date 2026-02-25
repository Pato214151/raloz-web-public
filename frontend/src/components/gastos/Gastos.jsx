import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Plus, Wallet } from 'lucide-react'

export default function Gastos() {
  const [gastos, setGastos] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ descripcion: '', valor: '', metodo_pago: 'EFECTIVO', fecha: new Date().toISOString().split('T')[0] })

  useEffect(() => { loadGastos() }, [])

  const loadGastos = async () => {
    try {
      const res = await api.get('/gastos', { params: { per_page: 50 } })
      setGastos(res.data.gastos || [])
    } catch {
      toast.error('Error cargando gastos')
    }
  }

  const crearGasto = async (e) => {
    e.preventDefault()
    try {
      await api.post('/gastos', { ...form, valor: parseFloat(form.valor) })
      toast.success('Gasto registrado')
      setShowForm(false)
      setForm({ descripcion: '', valor: '', metodo_pago: 'EFECTIVO', fecha: new Date().toISOString().split('T')[0] })
      loadGastos()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Gastos</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2"><Plus size={18} /> Nuevo Gasto</button>
      </div>

      {showForm && (
        <form onSubmit={crearGasto} className="card space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input value={form.descripcion} onChange={e => setForm({...form, descripcion: e.target.value})} className="input-field" placeholder="Descripción" required />
            <input type="number" min="1" value={form.valor} onChange={e => setForm({...form, valor: e.target.value})} className="input-field" placeholder="Valor" required />
            <select value={form.metodo_pago} onChange={e => setForm({...form, metodo_pago: e.target.value})} className="input-field">
              {['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA'].map(m => <option key={m}>{m}</option>)}
            </select>
            <input type="date" value={form.fecha} onChange={e => setForm({...form, fecha: e.target.value})} className="input-field" />
          </div>
          <div className="flex gap-3">
            <button type="submit" className="btn-success">Guardar</button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancelar</button>
          </div>
        </form>
      )}

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b">
              <th className="text-left py-2 px-3 text-gray-600">Fecha</th>
              <th className="text-left py-2 px-3 text-gray-600">Descripción</th>
              <th className="text-left py-2 px-3 text-gray-600">Método</th>
              <th className="text-right py-2 px-3 text-gray-600">Valor</th>
            </tr></thead>
            <tbody>
              {gastos.map(g => (
                <tr key={g.id_gasto} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-2 px-3">{g.fecha}</td>
                  <td className="py-2 px-3">{g.descripcion}</td>
                  <td className="py-2 px-3"><span className="bg-gray-100 px-2 py-0.5 rounded text-xs">{g.metodo_pago}</span></td>
                  <td className="py-2 px-3 text-right font-medium text-red-600">${Math.round(g.valor).toLocaleString('es-CO')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
