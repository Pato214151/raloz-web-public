/** Cuentas por cobrar: facturas con saldo pendiente. */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import toast from 'react-hot-toast'

export default function CuentasPorCobrar() {
  const navigate = useNavigate()
  const [cuentas, setCuentas] = useState([])
  const [totalPorCobrar, setTotalPorCobrar] = useState(0)
  const [loading, setLoading] = useState(false)
  const [buscar, setBuscar] = useState('')

  useEffect(() => { loadCuentas() }, [])

  const loadCuentas = async () => {
    setLoading(true)
    try {
      const res = await api.get('/reportes/cuentas-por-cobrar')
      setCuentas(res.data.cuentas || [])
      setTotalPorCobrar(res.data.total_por_cobrar || 0)
    } catch {
      toast.error('Error cargando cuentas por cobrar')
    } finally {
      setLoading(false)
    }
  }

  const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

  const filtradas = cuentas.filter(c => {
    if (!buscar) return true
    const q = buscar.toLowerCase()
    return (
      c.cliente_nombre?.toLowerCase().includes(q) ||
      c.numero_factura?.toLowerCase().includes(q) ||
      c.cliente_telefono?.includes(q)
    )
  })

  const totalFiltrado = filtradas.reduce((sum, c) => sum + (c.saldo || 0), 0)

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center flex-wrap gap-3">
        <h2 className="text-2xl font-bold text-gray-900">Cuentas por Cobrar</h2>
        <div className="card bg-red-50 border-red-200 px-6 py-3">
          <p className="text-sm text-red-600">Total por cobrar</p>
          <p className="text-2xl font-bold text-red-700">{fmt(totalPorCobrar)}</p>
          <p className="text-xs text-red-500">{cuentas.length} facturas pendientes</p>
        </div>
      </div>

      <div className="flex gap-3 items-center">
        <input
          type="text"
          value={buscar}
          onChange={e => setBuscar(e.target.value)}
          placeholder="Buscar por cliente, factura o telefono..."
          className="input-field flex-1"
        />
        <button onClick={loadCuentas} disabled={loading} className="btn-primary">
          {loading ? 'Cargando...' : 'Actualizar'}
        </button>
      </div>

      {buscar && (
        <p className="text-sm text-gray-500">
          {filtradas.length} resultados — Saldo filtrado: <strong className="text-red-600">{fmt(totalFiltrado)}</strong>
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-gray-200">
              <th className="text-left py-3 px-2">Factura</th>
              <th className="text-left py-3 px-2">Cliente</th>
              <th className="text-left py-3 px-2 hidden md:table-cell">Telefono</th>
              <th className="text-left py-3 px-2 hidden lg:table-cell">Fecha</th>
              <th className="text-right py-3 px-2">Total</th>
              <th className="text-right py-3 px-2">Pagado</th>
              <th className="text-right py-3 px-2">Saldo</th>
              <th className="text-left py-3 px-2 hidden md:table-cell">Entrega</th>
              <th className="text-right py-3 px-2"></th>
            </tr>
          </thead>
          <tbody>
            {filtradas.map(c => (
              <tr key={c.id_factura}
                onClick={() => navigate(`/buscar?ver=${c.id_factura}`)}
                className="border-b border-gray-100 hover:bg-raloz-50 cursor-pointer"
                title="Abrir factura para cobrar">
                <td className="py-2 px-2 font-medium text-raloz-700">{c.numero_factura}</td>
                <td className="py-2 px-2">{c.cliente_nombre}</td>
                <td className="py-2 px-2 hidden md:table-cell text-gray-500">{c.cliente_telefono || '-'}</td>
                <td className="py-2 px-2 hidden lg:table-cell text-gray-500">{c.fecha_factura}</td>
                <td className="py-2 px-2 text-right">{fmt(c.total)}</td>
                <td className="py-2 px-2 text-right text-green-600">{fmt(c.total_pagado)}</td>
                <td className="py-2 px-2 text-right font-bold text-red-600">{fmt(c.saldo)}</td>
                <td className="py-2 px-2 hidden md:table-cell">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    c.estado_entrega === 'ENTREGADO'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {c.estado_entrega || 'POR_ENTREGAR'}
                  </span>
                </td>
                <td className="py-2 px-2 text-right">
                  <span className="text-xs font-medium text-raloz-600 whitespace-nowrap">Cobrar →</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filtradas.length === 0 && !loading && (
        <p className="text-center text-gray-400 py-8">No hay cuentas pendientes</p>
      )}
    </div>
  )
}
