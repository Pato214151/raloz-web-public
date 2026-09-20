/**
 * Centro de Configuración: colegios y productos, usuarios, automatización,
 * avisos y tareas en pestañas.
 */

import { Settings, UserCog, Zap, Megaphone, ListTodo } from 'lucide-react'
import Hub from '../common/Hub'
import Configuracion from '../configuracion/Configuracion'
import Usuarios from '../usuarios/Usuarios'
import Automatizacion from '../automatizacion/Automatizacion'
import Avisos from '../avisos/Avisos'
import Tareas from '../tareas/Tareas'

// ⚙️ Configuración: colegios y productos, usuarios, automatización, avisos y tareas.
export default function ConfigHub() {
  return (
    <Hub tabs={[
      { id: 'general',        label: 'Colegios y productos', icon: Settings,  element: <Configuracion />,  roles: ['administrador'] },
      { id: 'usuarios',       label: 'Usuarios',             icon: UserCog,   element: <Usuarios />,       roles: ['administrador'] },
      { id: 'automatizacion', label: 'Automatización',       icon: Zap,       element: <Automatizacion />, roles: ['administrador'] },
      { id: 'avisos',         label: 'Avisos',               icon: Megaphone, element: <Avisos />,         roles: ['administrador'] },
      { id: 'tareas',         label: 'Tareas',               icon: ListTodo,  element: <Tareas /> },
    ]} />
  )
}
