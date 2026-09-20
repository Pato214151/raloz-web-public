/** Centro de Clientes: clientes, WhatsApp, citas y leads en pestañas. */

import { Users, MessageCircle, CalendarClock, MessageSquare } from 'lucide-react'
import Hub from '../common/Hub'
import Clientes from '../clientes/Clientes'
import WhatsApp from '../whatsapp/WhatsApp'
import Citas from '../citas/Citas'
import Leads from '../leads/Leads'

// 👥 Clientes: la relación completa (ficha, chat, citas y leads) en un solo lugar.
export default function ClientesHub() {
  return (
    <Hub tabs={[
      { id: 'clientes', label: 'Clientes', icon: Users,         element: <Clientes /> },
      { id: 'whatsapp', label: 'WhatsApp', icon: MessageCircle, element: <WhatsApp /> },
      { id: 'citas',    label: 'Citas',    icon: CalendarClock, element: <Citas /> },
      { id: 'leads',    label: 'Leads',    icon: MessageSquare, element: <Leads />, roles: ['administrador', 'vendedor'] },
    ]} />
  )
}
