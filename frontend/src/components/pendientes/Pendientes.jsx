import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Clock, Check, Search, Plus, Package, X, Download, MoreVertical } from 'lucide-react'

const formatMoney = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

export default function Pendientes() {
  const [prendas, setPrendas] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtro, setFiltro] = useState('PENDIENTE')
  const [escuela, setEscuela] = useState('')
  const [genero, setGenero] = useState('')
  const [buscar, setBuscar] = useState('')
  const [escuelas, setEscuelas] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [selectAll, setSelectAll] = useState(false)
  const [selected, setSelected] = useState(new Set())
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [detailPrenda, setDetailPrenda] = useState(null)
  const [nuevaPrenda, setNuevaPrenda] = useState({
    id_factura: '', producto_nombre: '', talla: '', cantidad: 1, genero: 'NIÑO', observaciones: ''
  })

  useEffect(() => {
    loadEscuelas()
    loadPrendas()
  }, [])

  useEffect(() => {
    loadPrendas()
  }, [filtro, escuela, genero])

  const loadEscuelas = async () => {
    try {
      const res = await api.get('/colegios')
      setEscuelas(res.data.colegios || [])
    } catch {
      toast.error('Error cargando escuelas')
    }
  }

  const loadPrendas = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filtro) params.estado = filtro
      if (escuela) params.colegio_id = escuela
      if (genero) params.genero = genero
      if (buscar) params.buscar = buscar
      const res = await api.get('/prendas', { params })
      setPrendas(res.data.prendas || [])
      setSelected(new Set())
      setSelectAll(false)
    } catch (err) {
      toast.error('Error cargando pendientes')
    } finally {
      setLoading(false)
    }
  }

  const handleBuscar = (e) => {
    e.preventDefault()
    loadPrendas()
  }

  const handleSelectAll = () => {
    if (selectAll) {
      setSelected(new Set())
      setSelectAll(false)
    } else {
      const newSelected = new Set(prendas.map(p => p.id_pendiente))
      setSelected(newSelected)
      setSelectAll(true)
    }
  }

  const toggleSelect = (id) => {
    const newSelected = new Set(selected)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelected(newSelected)
    setSelectAll(newSelected.size === prendas.length && prendas.length > 0)
  }

  const entregarSeleccionadas = async () => {
    if (selected.size === 0) {
      toast.error('Selecciona al menos una prenda')
      return
    }
    if (!confirm(`¿Marcar ${selected.size} prenda(s) como entregadas?`)) return
    try {
      await api.post('/prendas/entregar-batch', { ids: Array.from(selected) })
      toast.success(`${selected.size} prenda(s) entregada(s)`)
      loadPrendas()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const entregar = async (id) => {
    if (!confirm('¿Marcar como entregado?')) return
    try {
      await api.post(`/prendas/${id}/entregar`)
      toast.success('Marcado como entregado')
      loadPrendas()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const crearPrenda = async (e) => {
    e.preventDefault()
    try {
      await api.post('/prendas', nuevaPrenda)
      toast.success('Prenda pendiente creada')
      setShowModal(false)
      setNuevaPrenda({ id_factura: '', producto_nombre: '', talla: '', cantidad: 1, genero: 'NIÑO', observaciones: '' })
      loadPrendas()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error creando prenda')
    }
  }

  const eliminar = async (id) => {
    if (!confirm('¿Eliminar esta prenda pendiente?')) return
    try {
      await api.delete(`/prendas/${id}`)
      toast.success('Eliminado')
      loadPrendas()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const printList = () => {
    const contenido = generarListaImpresion()
    const ventana = window.open('', '', 'width=800,height=600')
    ventana.document.write(contenido)
    ventana.document.close()
    ventana.print()
  }

  const generarListaImpresion = () => {
    const html = `
      <html>
      <head>
        <title>Listado de Prendas Pendientes</title>
        <style>
          body { font-family: Arial; margin: 20px; }
          table { width: 100%; border-collapse: collapse; margin: 20px 0; }
          th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
          th { background-color: #f5f5f5; }
          .header { text-align: center; margin-bottom: 20px; }
          .checkbox { width: 30px; }
        </style>
      </head>
      <body>
        <div class="header">
          <h2>RALOZ COL SAS - Listado de Prendas Pendientes</h2>
          <p>Fecha: ${new Date().toLocaleDateString('es-CO')}</p>
        </div>
        <table>
          <thead>
            <tr>
              <th class="checkbox">✓</th>
              <th>Factura</th>
              <th>Cliente</th>
              <th>Producto</th>
              <th>Talla</th>
              <th>Cantidad</th>
              <th>Género</th>
              <th>Escuela</th>
            </tr>
          </thead>
          <tbody>
            ${prendas.map(p => `
              <tr>
                <td class="checkbox">☐</td>
                <td>${p.numero_factura || ''}</td>
                <td>${p.cliente_nombre || ''}</td>
                <td>${p.producto_nombre}</td>
                <td>${p.talla || '—'}</td>
                <td>${p.cantidad}</td>
                <td>${p.genero}</td>
                <td>${p.colegio_nombre || ''}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </body>
      </html>
    `
    return html
  }

  const pendientesCount = prendas.filter(p => p.estado === 'PENDIENTE').length
  const entregadosCount = prendas.filter(p => p.estado === 'ENTREGADO').length

  if (loading && prendas.length === 0) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-bold text-gray-900">Prendas Pendientes</h2>
        <div className="flex gap-2">
          {selected.size > 0 && (
            <button onClick={entregarSeleccionadas} className="btn-success flex items-center gap-2">
              <Check size={16} /> Entregar {selected.size}
            </button>
          )}
          <button onClick={printList} className="btn-secondary flex items-center gap-2">
            <Download size={16} /> Imprimir
          </button>
          <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> Nueva Prenda
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card bg-yellow-50 border-yellow-200">
          <div className="flex items-center gap-3">
            <Clock className="text-yellow-600" size={24} />
            <div>
              <p className="text-sm text-yellow-600">Pendientes</p>
              <p className="text-2xl font-bold text-yellow-700">{pendientesCount}</p>
            </div>
          </div>
        </div>
        <div className="card bg-green-50 border-green-200">
          <div className="flex items-center gap-3">
            <Check className="text-green-600" size={24} />
            <div>
              <p className="text-sm text-green-600">Entregados</p>
              <p className="text-2xl font-bold text-green-700">{entregadosCount}</p>
            </div>
          </div>
        </div>
        <div className="card bg-blue-50 border-blue-200">
          <div className="flex items-center gap-3">
            <Package className="text-blue-600" size={24} />
            <div>
              <p className="text-sm text-blue-600">Total</p>
              <p className="text-2xl font-bold text-blue-700">{prendas.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="card">
        <div className="space-y-4">
          <form onSubmit={handleBuscar} className="flex gap-2 flex-wrap">
            <div className="relative flex-1 min-w-60">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
              <input
                type="text"
                value={buscar}
                onChange={(e) => setBuscar(e.target.value)}
                placeholder="Buscar por cliente, producto, factura..."
                className="input pl-10 w-full"
              />
            </div>
            <button type="submit" className="btn-primary">Buscar</button>
          </form>

          <div className="flex flex-wrap gap-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Escuela</label>
              <select value={escuela} onChange={(e) => setEscuela(e.target.value)} className="input text-sm">
                <option value="">Todas</option>
                {escuelas.map(e => (
                  <option key={e.id_colegio} value={e.id_colegio}>{e.nombre}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Género</label>
              <select value={genero} onChange={(e) => setGenero(e.target.value)} className="input text-sm">
                <option value="">Todos</option>
                <option value="NIÑO">Niño</option>
                <option value="NIÑA">Niña</option>
              </select>
            </div>
            <div className="flex gap-1 items-end">
              {['PENDIENTE', 'ENTREGADO', ''].map((estado) => (
                <button
                  key={estado}
                  onClick={() => setFiltro(estado)}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                    filtro === estado ? 'bg-raloz-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {estado === '' ? 'Todos' : estado === 'PENDIENTE' ? 'Pendientes' : 'Entregados'}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Lista */}
      {prendas.length === 0 ? (
        <div className="card text-center py-12">
          <Package className="mx-auto text-gray-300 mb-4" size={48} />
          <p className="text-gray-500">No hay prendas {filtro === 'PENDIENTE' ? 'pendientes' : filtro === 'ENTREGADO' ? 'entregadas' : ''}</p>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectAll}
                    onChange={handleSelectAll}
                    className="cursor-pointer"
                  />
                </th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Factura</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Producto</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Talla</th>
                <th className="px-4 py-3 text-center text-gray-600 font-medium">Cantidad</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Género</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Cliente</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Escuela</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Estado</th>
                <th className="px-4 py-3 text-center text-gray-600 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {prendas.map(p => (
                <tr key={p.id_pendiente} className={`border-b border-gray-50 hover:bg-gray-50 ${
                  p.estado === 'ENTREGADO' ? 'bg-green-50' : ''
                }`}>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selected.has(p.id_pendiente)}
                      onChange={() => toggleSelect(p.id_pendiente)}
                      disabled={p.estado === 'ENTREGADO'}
                      className="cursor-pointer"
                    />
                  </td>
                  <td className="px-4 py-3 font-semibold text-gray-900">{p.numero_factura || '—'}</td>
                  <td className="px-4 py-3">{p.producto_nombre}</td>
                  <td className="px-4 py-3">{p.talla || '—'}</td>
                  <td className="px-4 py-3 text-center font-medium">{p.cantidad}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                      p.genero === 'NIÑA' ? 'bg-pink-100 text-pink-700' : 'bg-blue-100 text-blue-700'
                    }`}>{p.genero}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-700">{p.cliente_nombre || '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{p.colegio_nombre || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                      p.estado === 'PENDIENTE' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
                    }`}>{p.estado}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-1">
                      {p.estado === 'PENDIENTE' && (
                        <button onClick={() => entregar(p.id_pendiente)} className="text-green-600 hover:text-green-800" title="Entregar">
                          <Check size={14} />
                        </button>
                      )}
                      <button onClick={() => { setDetailPrenda(p); setShowDetailModal(true) }} className="text-blue-600 hover:text-blue-800" title="Detalles">
                        <MoreVertical size={14} />
                      </button>
                      <button onClick={() => eliminar(p.id_pendiente)} className="text-red-500 hover:text-red-700" title="Eliminar">
                        <X size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal Crear Prenda */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md max-h-screen overflow-y-auto">
            <h3 className="text-lg font-bold mb-4">Nueva Prenda Pendiente</h3>
            <form onSubmit={crearPrenda} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">ID Factura *</label>
                <input type="number" required value={nuevaPrenda.id_factura}
                  onChange={e => setNuevaPrenda({...nuevaPrenda, id_factura: e.target.value})}
                  className="input w-full" placeholder="Número de ID de factura" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Producto *</label>
                <input type="text" required value={nuevaPrenda.producto_nombre}
                  onChange={e => setNuevaPrenda({...nuevaPrenda, producto_nombre: e.target.value})}
                  className="input w-full" placeholder="Nombre del producto" />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Talla</label>
                  <input type="text" value={nuevaPrenda.talla}
                    onChange={e => setNuevaPrenda({...nuevaPrenda, talla: e.target.value})}
                    className="input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Cantidad *</label>
                  <input type="number" min="1" required value={nuevaPrenda.cantidad}
                    onChange={e => setNuevaPrenda({...nuevaPrenda, cantidad: parseInt(e.target.value) || 1})}
                    className="input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Género</label>
                  <select value={nuevaPrenda.genero}
                    onChange={e => setNuevaPrenda({...nuevaPrenda, genero: e.target.value})}
                    className="input w-full">
                    <option value="NIÑO">NIÑO</option>
                    <option value="NIÑA">NIÑA</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Observaciones</label>
                <textarea value={nuevaPrenda.observaciones}
                  onChange={e => setNuevaPrenda({...nuevaPrenda, observaciones: e.target.value})}
                  className="input w-full" rows={2} />
              </div>
              <div className="flex gap-3 justify-end">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">Cancelar</button>
                <button type="submit" className="btn-primary">Crear</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Detalles */}
      {showDetailModal && detailPrenda && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4">Detalles de Prenda</h3>
            <div className="space-y-3 text-sm">
              <div><p className="text-gray-600">Factura</p><p className="font-semibold">{detailPrenda.numero_factura || '—'}</p></div>
              <div><p className="text-gray-600">Producto</p><p className="font-semibold">{detailPrenda.producto_nombre}</p></div>
              <div><p className="text-gray-600">Cliente</p><p className="font-semibold">{detailPrenda.cliente_nombre || '—'}</p></div>
              <div><p className="text-gray-600">Escuela</p><p className="font-semibold">{detailPrenda.colegio_nombre || '—'}</p></div>
              <div className="grid grid-cols-3 gap-3">
                <div><p className="text-gray-600">Talla</p><p className="font-semibold">{detailPrenda.talla || '—'}</p></div>
                <div><p className="text-gray-600">Cantidad</p><p className="font-semibold">{detailPrenda.cantidad}</p></div>
                <div><p className="text-gray-600">Género</p><p className="font-semibold">{detailPrenda.genero}</p></div>
              </div>
              {detailPrenda.observaciones && (
                <div><p className="text-gray-600">Observaciones</p><p className="font-semibold">{detailPrenda.observaciones}</p></div>
              )}
              <div className="border-t pt-3">
                <p className="text-gray-600 text-xs">Registrado: {detailPrenda.fecha_registro}</p>
                {detailPrenda.fecha_entrega && <p className="text-gray-600 text-xs">Entregado: {detailPrenda.fecha_entrega}</p>}
              </div>
            </div>
            <div className="flex gap-3 justify-end mt-4">
              <button onClick={() => setShowDetailModal(false)} className="btn-secondary">Cerrar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
