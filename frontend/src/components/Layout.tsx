import { ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Outlet } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LayoutDashboard,
  LineChart,
  Users,
  Settings,
  Bell,
  Wallet,
  ShoppingCart,
  Shield,
  LogOut,
  TrendingUp,
  Cog,
  Menu,
  X,
  Zap,
  Link2,
} from 'lucide-react';
import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '@/App';

const NAV_ITEMS = [
  { path: '/trading', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/strategies', icon: LineChart, label: 'Strategies' },
  { path: '/portfolio', icon: Wallet, label: 'Portfolio' },
  { path: '/orders', icon: ShoppingCart, label: 'Orders' },
  { path: '/analytics', icon: TrendingUp, label: 'Analytics' },
  { path: '/paper-trading', icon: TrendingUp, label: 'Paper Trading' },
  { path: '/live-trading', icon: Zap, label: 'Live Trading' },
  { path: '/notifications', icon: Bell, label: 'Notifications' },
];

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation();
  const { user } = useAuth();
  
  const isAdmin = user?.role === 'admin';
  
  const navItems = [...NAV_ITEMS];
  
  if (isAdmin) {
    navItems.push(
      { path: '/admin', icon: Shield, label: 'Admin' },
      { path: '/admin/users', icon: Users, label: 'User Management' },
      { path: '/admin/assign-strategies', icon: Link2, label: 'Strategy Assignment' }
    );
  }
  
  const bottomNavItems = [
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];
  
  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-surface-900/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed left-0 top-0 h-full w-64 bg-surface-900 text-white',
          'flex flex-col z-50 transition-transform duration-300',
          'lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Logo */}
        <div className="px-6 py-5 border-b border-surface-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-primary-600 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-semibold">EasyTrade</span>
          </div>
          <button onClick={onClose} className="lg:hidden text-surface-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path || 
                (item.path !== '/trading' && location.pathname.startsWith(item.path));
              
              return (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    onClick={() => window.innerWidth < 1024 && onClose()}
                    className={clsx(
                      'flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors',
                      isActive
                        ? 'text-white bg-surface-800 border-l-4 border-primary-500'
                        : 'text-surface-300 hover:text-white hover:bg-surface-800'
                    )}
                  >
                    <item.icon className="w-5 h-5" />
                    {item.label}
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Bottom Navigation */}
        <div className="border-t border-surface-800 py-4">
          <ul className="space-y-1">
            {bottomNavItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  onClick={() => window.innerWidth < 1024 && onClose()}
                  className={clsx(
                    'flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors',
                    location.pathname === item.path
                      ? 'text-white bg-surface-800'
                      : 'text-surface-300 hover:text-white hover:bg-surface-800'
                  )}
                >
                  <item.icon className="w-5 h-5" />
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>

        {/* User Info */}
        <div className="px-6 py-4 border-t border-surface-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-surface-700 rounded-full flex items-center justify-center">
              <Users className="w-5 h-5 text-surface-300" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.first_name || 'Trader'}
              </p>
              <p className="text-xs text-surface-400 truncate">
                {user?.email || 'User'}
              </p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

interface NavbarProps {
  onMenuClick: () => void;
}

export function Navbar({ onMenuClick }: NavbarProps) {
  const location = useLocation();
  const { logout } = useAuth();
  
  const getPageTitle = () => {
    const item = NAV_ITEMS.find(i => location.pathname === i.path || location.pathname.startsWith(i.path + '/'));
    return item?.label || 'Dashboard';
  };

  return (
    <header className="fixed top-0 left-64 right-0 h-16 bg-white border-b border-surface-200 z-30">
      <div className="flex items-center justify-between h-full px-6">
        {/* Left Side */}
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 text-surface-600 hover:bg-surface-100 rounded-lg"
          >
            <Menu className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-semibold text-surface-900">{getPageTitle()}</h1>
        </div>

        {/* Right Side */}
        <div className="flex items-center gap-3">
          <button className="p-2 text-surface-600 hover:bg-surface-100 rounded-lg relative">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-danger rounded-full" />
          </button>
          <button className="p-2 text-surface-600 hover:bg-surface-100 rounded-lg">
            <Cog className="w-5 h-5" />
          </button>
          <button
            onClick={logout}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-surface-600 hover:text-surface-900 hover:bg-surface-100 rounded-lg"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}

interface LayoutProps {
  children?: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  return (
    <div className="min-h-screen bg-surface-50">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <Navbar onMenuClick={() => setSidebarOpen(true)} />
      
      <main className="lg:ml-64 pt-16">
        <div className="p-6">
          {children || <Outlet />}
        </div>
      </main>
    </div>
  );
}