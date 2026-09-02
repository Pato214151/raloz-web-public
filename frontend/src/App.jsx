import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { Toaster } from 'react-hot-toast'
// Eager: se necesitan de inmediato en el primer render.
import Login from './components/auth/Login'
import Layout from './components/common/Layout'
import DucklabBadge from './components/common/DucklabBadge'
// Lazy: cada vista carga en su propio chunk → bundle inicial mucho más liviano
// (mejor carga en celular). recharts, WhatsApp, etc. salen del arranque.
const Dashboard = lazy(() => import('./components/dashboard/Dashboard'))
const Asistente = lazy(() => import('./components/asistente/Asistente'))
const Facturacion = lazy(() => import('./components/facturacion/Facturacion'))
const Vender = lazy(() => import('./components/facturacion/Vender'))
const BuscarFacturas = lazy(() => import('./components/facturacion/BuscarFacturas'))
const Pagos = lazy(() => import('./components/pagos/Pagos'))
const StockView = lazy(() => import('./components/stock/StockView'))
const Ventas = lazy(() => import('./components/ventas/Ventas'))
const Clientes = lazy(() => import('./components/clientes/Clientes'))
const Gastos = lazy(() => import('./components/gastos/Gastos'))
const Caja = lazy(() => import('./components/caja/Caja'))
const Pendientes = lazy(() => import('./components/pendientes/Pendientes'))
const Precios = lazy(() => import('./components/precios/Precios'))
const Empaque = lazy(() => import('./components/empaque/Empaque'))
const Usuarios = lazy(() => import('./components/usuarios/Usuarios'))
const CuentasPorCobrar = lazy(() => import('./components/reportes/CuentasPorCobrar'))
const Reportes = lazy(() => import('./components/reportes/Reportes'))
const Configuracion = lazy(() => import('./components/configuracion/Configuracion'))
const Publicaciones = lazy(() => import('./components/publicaciones/Publicaciones'))
const Avisos = lazy(() => import('./components/avisos/Avisos'))
const Automatizacion = lazy(() => import('./components/automatizacion/Automatizacion'))
const Tareas = lazy(() => import('./components/tareas/Tareas'))
const Operaciones = lazy(() => import('./components/operaciones/Operaciones'))
const PedidosOnline = lazy(() => import('./components/pedidos/PedidosOnline'))
const CentroPedidos = lazy(() => import('./components/pedidos/CentroPedidos'))
const PedidosFabricacion = lazy(() => import('./components/fabricacion/PedidosFabricacion'))
const StockPendienteFab = lazy(() => import('./components/fabricacion/StockPendienteFab'))
const OrdenesProduccion = lazy(() => import('./components/ordenes-produccion/OrdenesProduccion'))
const WhatsApp = lazy(() => import('./components/whatsapp/WhatsApp'))
const BuscarContacto = lazy(() => import('./components/whatsapp/BuscarContacto'))
const Citas = lazy(() => import('./components/citas/Citas'))
const Leads = lazy(() => import('./components/leads/Leads'))
// Hubs (centros por área) — reúnen los componentes de arriba en pestañas
const VentasHub = lazy(() => import('./components/secciones/VentasHub'))
const ClientesHub = lazy(() => import('./components/secciones/ClientesHub'))
const FinanzasHub = lazy(() => import('./components/secciones/FinanzasHub'))
const CatalogoHub = lazy(() => import('./components/secciones/CatalogoHub'))
const ConfigHub = lazy(() => import('./components/secciones/ConfigHub'))

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
      <DucklabBadge />
      <Toaster position="top-right" toastOptions={{
        duration: 3000,
        style: { borderRadius: '10px', background: '#333', color: '#fff' },
      }} />

      <Suspense fallback={
        <div className="flex items-center justify-center h-screen">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-raloz-600"></div>
        </div>
      }>
      <Routes>
        <Route path="/login" element={usuario ? <Navigate to="/" /> : <Login />} />

        <Route path="/" element={
          <ProtectedRoute><Layout /></ProtectedRoute>
        }>
          <Route index element={<Dashboard />} />
          <Route path="asistente" element={<Asistente />} />

          {/* ── ÁREAS PRINCIPALES (hubs con pestañas) ── */}
          <Route path="ventas" element={<VentasHub />} />
          <Route path="operacion" element={<Operaciones />} />
          <Route path="catalogo" element={<CatalogoHub />} />
          <Route path="clientes" element={<ClientesHub />} />
          <Route path="finanzas" element={
            <ProtectedRoute roles={['administrador', 'cajero', 'vendedor']}><FinanzasHub /></ProtectedRoute>
          } />
          <Route path="tienda" element={
            <ProtectedRoute roles={['administrador']}><Publicaciones /></ProtectedRoute>
          } />
          <Route path="config" element={
            <ProtectedRoute roles={['administrador', 'vendedor', 'cajero']}><ConfigHub /></ProtectedRoute>
          } />

          {/* ── Rutas directas (compatibilidad + barra móvil + enlaces internos) ── */}
          <Route path="facturacion" element={<Facturacion />} />
          <Route path="vender" element={<Vender />} />
          <Route path="buscar" element={<BuscarFacturas />} />
          <Route path="pagos" element={<Pagos />} />
          <Route path="stock" element={<StockView />} />
          <Route path="hoja-ventas" element={<Ventas />} />
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
          <Route path="avisos" element={
            <ProtectedRoute roles={['administrador']}><Avisos /></ProtectedRoute>
          } />
          <Route path="automatizacion" element={
            <ProtectedRoute roles={['administrador']}><Automatizacion /></ProtectedRoute>
          } />
          <Route path="configuracion" element={
            <ProtectedRoute roles={['administrador']}><Configuracion /></ProtectedRoute>
          } />
          <Route path="usuarios" element={
            <ProtectedRoute roles={['administrador']}><Usuarios /></ProtectedRoute>
          } />
          <Route path="whatsapp" element={<WhatsApp />} />
          <Route path="escribir-cliente" element={<BuscarContacto />} />
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
      </Suspense>
    </>
  )
}
