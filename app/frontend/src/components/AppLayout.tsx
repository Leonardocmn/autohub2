import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Truck,
  Users,
  Tag,
  Car,
  Send,
  Handshake,
  Phone,
  History,
  Menu,
  X,
  LogOut,
  MessageSquare,
  UserCheck,
  FolderSearch,
  Search,
  DollarSign,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { client } from '@/lib/api';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Ofertas', href: '/offers', icon: Car },
  { name: 'Distribuição', href: '/distribution', icon: Send },
  { name: 'Negociações', href: '/negotiations', icon: Handshake },
  { name: 'Fornecedores', href: '/suppliers', icon: Truck },
  { name: 'Compradores', href: '/buyers', icon: Users },
  { name: 'Categorias', href: '/categories', icon: Tag },
  { name: 'Números Negociação', href: '/negotiation-numbers', icon: Phone },
  { name: 'Histórico', href: '/history', icon: History },
  { name: 'Consulta Placa', href: '/plate-lookup', icon: Search },
  { name: 'Consulta FIPE', href: '/fipe-lookup', icon: DollarSign },
  { name: 'Dossies', href: '/vehicle-dossiers', icon: FolderSearch },
  { name: 'Meus Veiculos', href: '/my-vehicles', icon: Car },
  { name: 'WhatsApp', href: '/whatsapp-settings', icon: MessageSquare },
  { name: 'Conversas WA', href: '/whatsapp-conversations', icon: MessageSquare },
  { name: 'Números Admin', href: '/admin-phones', icon: UserCheck },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const handleLogout = () => {
    client.auth.logout();
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-200 lg:relative lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
          'bg-[hsl(var(--sidebar-background))] text-[hsl(var(--sidebar-foreground))]'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex h-16 items-center justify-between px-4 border-b border-[hsl(var(--sidebar-border))]">
            <div className="flex items-center gap-2">
              <img src="/autohub-logo.png" alt="AutoHub" className="h-9 w-auto" />
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden text-[hsl(var(--sidebar-foreground))] hover:bg-[hsl(var(--sidebar-accent))]"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto py-4 px-3">
            <ul className="space-y-1">
              {navigation.map((item) => {
                const isActive =
                  item.href === '/'
                    ? location.pathname === '/'
                    : location.pathname.startsWith(item.href);
                return (
                  <li key={item.name}>
                    <Link
                      to={item.href}
                      onClick={() => setSidebarOpen(false)}
                      className={cn(
                        'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-[hsl(var(--sidebar-accent))] text-[hsl(var(--sidebar-primary))]'
                          : 'text-[hsl(var(--sidebar-foreground))] hover:bg-[hsl(var(--sidebar-accent))] hover:text-white'
                      )}
                    >
                      <item.icon className={cn('h-5 w-5 flex-shrink-0', isActive && 'text-[hsl(var(--sidebar-primary))]')} />
                      {item.name}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Logout */}
          <div className="border-t border-[hsl(var(--sidebar-border))] p-3">
            <button
              onClick={handleLogout}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[hsl(var(--sidebar-foreground))] hover:bg-[hsl(var(--sidebar-accent))] hover:text-white transition-colors"
            >
              <LogOut className="h-5 w-5" />
              Sair
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-16 items-center gap-4 border-b bg-background px-4 lg:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex-1" />
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
