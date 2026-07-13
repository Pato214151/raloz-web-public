import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { Toaster } from 'react-hot-toast'
import Login from './components/auth/Login'
import Layout from './components/common/Layout'
import Dashboard from './components/dashboard/Dashboard'
import Facturacion from './components/facturacion/Facturacion'
import BuscarFacturas from './components/facturacion/BuscarFacturas'
import Pagos from './components/pagos/Pagos'
import StockView from './components/stock/StockView'
import Ventas from './components/ventas/Ventas'
import Clientes from './components/clientes/Clientes'
import Gastos from './components/gastos/Gastos'
import Caja from './components/caja/Caja'
import Pendientes from './components/pendientes/Pendientes'
import Precios from './components/precios/Precios'
import Empaque from './components/empaque/Empaque'
import Usuarios from './components/usuarios/Usuarios'
import CuentasPorCobrar from './components/reportes/CuentasPorCobrar'
import Reportes from './components/reportes/Reportes'
import Configuracion from './components/configuracion/Configuracion'
import Publicaciones from './components/publicaciones/Publicaciones'
import Tareas from './components/tareas/Tareas'
import Operaciones from './components/operaciones/Operaciones'
import PedidosOnline from './components/pedidos/PedidosOnline'
import CentroPedidos from './components/pedidos/CentroPedidos'
import PedidosFabricacion from './components/fabricacion/PedidosFabricacion'
import StockPendienteFab from './components/fabricacion/StockPendienteFab'
import OrdenesProduccion from './components/ordenes-produccion/OrdenesProduccion'
import WhatsApp from './components/whatsapp/WhatsApp'
import Citas from './components/citas/Citas'
import Leads from './components/leads/Leads'

function ProtectedRoute({ children, roles }) {
  const { usuario, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-raloz-600"></div>
      </div>
    )
  }

  if (!usuario) return <Navigate to="/login" />
  if (roles && !roles.includes(usuario.rol)) return <Navigate to="/" />

  return children
}

export default function App() {
  const { usuario } = useAuth()

  return (
    <>
      <Toaster position="top-right" toastOptions={{
        duration: 3000,
        style: { borderRadius: '10px', background: '#333', color: '#fff' },
      }} />

      <Routes>
        <Route path="/login" element={usuario ? <Navigate to="/" /> : <Login />} />

        <Route path="/" element={
          <ProtectedRoute><Layout /></ProtectedRoute>
        }>
          <Route index element={<Dashboard />} />
          <Route path="facturacion" element={<Facturacion />} />
          <Route path="buscar" element={<BuscarFacturas />} />
          <Route path="pagos" element={<Pagos />} />
          <Route path="stock" element={<StockView />} />
          <Route path="ventas" element={<Ventas />} />
          <Route path="clientes" element={<Clientes />} />
          <Route path="gastos" element={
            <ProtectedRoute roles={['administrador', 'cajero']}><Gastos /></ProtectedRoute>
          } />
          <Route path="caja" element={
            <ProtectedRoute roles={['administrador', 'cajero']}><Caja /></ProtectedRoute>
          } />
          <Route path="pendientes" element={<Pendientes />} />
          <Route path="empaque" element={<Empaque />} />
          <Route path="precios" element={
            <ProtectedRoute roles={['administrador']}><Precios /></ProtectedRoute>
          } />
          <Route path="cuentas" element={<CuentasPorCobrar />} />
          <Route path="reportes" element={
            <ProtectedRoute roles={['administrador']}><Reportes /></ProtectedRoute>
          } />
          <Route path="publicaciones" element={
            <ProtectedRoute roles={['administrador']}><Publicaciones /></ProtectedRoute>
          } />
          <Route path="configuracion" element={
            <ProtectedRoute roles={['administrador']}><Configuracion /></ProtectedRoute>
          } />
          <Route path="usuarios" element={
            <ProtectedRoute roles={['administrador']}><Usuarios /></ProtectedRoute>
          } />
          <Route path="whatsapp" element={<WhatsApp />} />
          <Route path="citas" element={<Citas />} />
          <Route path="leads" element={<Leads />} />
          <Route path="tareas" element={<Tareas />} />
          <Route path="operaciones" element={<Operaciones />} />
          <Route path="pedidos-online" element={<CentroPedidos />} />
          <Route path="pedidos-web-legacy" element={<PedidosOnline />} />
          <Route path="fabricacion" element={<PedidosFabricacion />} />
          <Route path="fabricacion/stock" element={<StockPendienteFab />} />
          <Route path="ordenes-produccion" element={
            <ProtectedRoute roles={['administrador']}><OrdenesProduccion /></ProtectedRoute>
          } />
        </Route>

        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </>
  )
}
