import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui';
import { Button } from '@/components/ui';
import { User, Bell, Shield, Palette, Link2, CreditCard, Settings as SettingsIcon } from 'lucide-react';

const settingsSections = [
  {
    title: 'Profile',
    description: 'Manage your account details',
    icon: <User className="w-5 h-5" />,
    href: '/settings/profile',
    available: true,
  },
  {
    title: 'Broker Connections',
    description: 'Connect and manage broker accounts',
    icon: <Link2 className="w-5 h-5" />,
    href: '/settings/brokers',
    available: true,
  },
  {
    title: 'Notifications',
    description: 'Configure alert preferences',
    icon: <Bell className="w-5 h-5" />,
    href: '/notifications',
    available: true,
  },
  {
    title: 'Security',
    description: 'Password and authentication settings',
    icon: <Shield className="w-5 h-5" />,
    href: '/settings/security',
    available: true,
  },
  {
    title: 'Trading Preferences',
    description: 'Default order types and settings',
    icon: <CreditCard className="w-5 h-5" />,
    href: '/settings/trading',
    available: true,
  },
  {
    title: 'Risk Rules',
    description: 'Configure risk management rules',
    icon: <Shield className="w-5 h-5" />,
    href: '/settings/risk',
    available: true,
  },
];

export default function Settings() {
  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-gray-500 mt-1">Manage your account and preferences</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {settingsSections.map((section) => (
          <Card key={section.title} className={section.available ? '' : 'opacity-60'}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="h-10 w-10 bg-primary/10 rounded-lg flex items-center justify-center text-primary">
                  {section.icon}
                </div>
                {!section.available && (
                  <span className="text-xs text-gray-400">Coming Soon</span>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <h3 className="font-semibold text-lg">{section.title}</h3>
              <p className="text-sm text-gray-500 mt-1">{section.description}</p>
              {section.available ? (
                <Button variant="outline" className="mt-4 w-full" asChild>
                  <Link to={section.href}>Configure</Link>
                </Button>
              ) : (
                <Button variant="outline" className="mt-4 w-full" disabled>
                  Coming Soon
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Links</CardTitle>
          <CardDescription>Frequently used settings</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Button variant="outline" className="h-auto py-4" asChild>
            <Link to="/settings/brokers" className="flex flex-col items-center gap-2">
              <Link2 className="w-5 h-5" />
              <span className="text-sm">Brokers</span>
            </Link>
          </Button>
          <Button variant="outline" className="h-auto py-4" asChild>
            <Link to="/settings/profile" className="flex flex-col items-center gap-2">
              <User className="w-5 h-5" />
              <span className="text-sm">Profile</span>
            </Link>
          </Button>
          <Button variant="outline" className="h-auto py-4" disabled>
            <Bell className="w-5 h-5" />
            <span className="text-sm">Notifications</span>
          </Button>
          <Button variant="outline" className="h-auto py-4" disabled>
            <Shield className="w-5 h-5" />
            <span className="text-sm">Security</span>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
