import { useState, useEffect, useCallback } from 'react';
import { Bell, Check, CheckCheck, Settings, Mail, Smartphone, Webhook, TrendingUp, Shield, Cpu, FileText, MessageCircle, Send } from 'lucide-react';
import { Card, CardContent, Button, Badge, Switch, Input, Label } from '@/components/ui';
import { notificationApi, Notification, NotificationPreferences } from '@/services/notificationApi';

export default function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);
  const [activeTab, setActiveTab] = useState<'notifications' | 'preferences'>('notifications');
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [savingPrefs, setSavingPrefs] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      const data = await notificationApi.getNotifications(showUnreadOnly);
      setNotifications(data);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    } finally {
      setLoading(false);
    }
  }, [showUnreadOnly]);

  const fetchPreferences = useCallback(async () => {
    try {
      const data = await notificationApi.getPreferences();
      setPreferences(data);
    } catch (error) {
      console.error('Failed to fetch preferences:', error);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  useEffect(() => {
    if (activeTab === 'preferences') {
      fetchPreferences();
    }
  }, [activeTab, fetchPreferences]);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const handleMarkAsRead = async (id: string) => {
    try {
      await notificationApi.markAsRead([id]);
      setNotifications(prev =>
        prev.map(n => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await notificationApi.markAllAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const handlePreferenceChange = async (key: keyof NotificationPreferences, value: boolean | string | null) => {
    if (!preferences) return;
    setSavingPrefs(true);
    try {
      const updated = await notificationApi.updatePreferences({ [key]: value });
      setPreferences(updated);
    } catch (error) {
      console.error('Failed to update preference:', error);
    } finally {
      setSavingPrefs(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  const filteredNotifications = showUnreadOnly
    ? notifications.filter(n => !n.is_read)
    : notifications;

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bell className="w-6 h-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Notifications</h1>
            <p className="text-sm text-muted-foreground">Stay updated on your trading activity</p>
          </div>
          {unreadCount > 0 && activeTab === 'notifications' && (
            <Badge variant="destructive" className="ml-2">
              {unreadCount}
            </Badge>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            variant={activeTab === 'notifications' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveTab('notifications')}
          >
            <Bell className="w-4 h-4 mr-2" />
            Notifications
          </Button>
          <Button
            variant={activeTab === 'preferences' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveTab('preferences')}
          >
            <Settings className="w-4 h-4 mr-2" />
            Settings
          </Button>
        </div>
      </div>

      {activeTab === 'notifications' && (
        <>
          <div className="flex gap-2">
            <Button
              variant={showUnreadOnly ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowUnreadOnly(!showUnreadOnly)}
            >
              {showUnreadOnly ? 'Showing Unread' : 'Show Unread Only'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleMarkAllAsRead}
              disabled={unreadCount === 0}
            >
              <CheckCheck className="w-4 h-4 mr-2" />
              Mark All Read
            </Button>
          </div>

          {loading ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                Loading notifications...
              </CardContent>
            </Card>
          ) : filteredNotifications.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                No notifications
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filteredNotifications.map(notification => (
                <Card
                  key={notification.id}
                  className={notification.is_read ? '' : 'border-primary/50 bg-primary/5'}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className={getPriorityColor(notification.priority)}>
                            {notification.priority}
                          </Badge>
                          <span className="text-sm text-muted-foreground">
                            {formatTime(notification.created_at)}
                          </span>
                        </div>
                        <h3 className="font-semibold">{notification.title}</h3>
                        <p className="text-muted-foreground mt-1">{notification.message}</p>
                      </div>
                      {!notification.is_read && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleMarkAsRead(notification.id)}
                        >
                          <Check className="w-5 h-5" />
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === 'preferences' && preferences && (
        <div className="space-y-6">
          <Card>
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold mb-4">Delivery Methods</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Mail className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Email Notifications</p>
                      <p className="text-sm text-muted-foreground">Receive notifications via email</p>
                    </div>
                  </div>
                  <Switch
                    checked={preferences.email_enabled}
                    onCheckedChange={(checked) => handlePreferenceChange('email_enabled', checked)}
                    disabled={savingPrefs}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Smartphone className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Push Notifications</p>
                      <p className="text-sm text-muted-foreground">Receive push notifications on your device</p>
                    </div>
                  </div>
                  <Switch
                    checked={preferences.push_enabled}
                    onCheckedChange={(checked) => handlePreferenceChange('push_enabled', checked)}
                    disabled={savingPrefs}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Webhook className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Webhook</p>
                      <p className="text-sm text-muted-foreground">Send notifications to a webhook URL</p>
                    </div>
                  </div>
                  <Switch
                    checked={preferences.webhook_enabled}
                    onCheckedChange={(checked) => handlePreferenceChange('webhook_enabled', checked)}
                    disabled={savingPrefs}
                  />
                </div>
                {preferences.webhook_enabled && (
                  <div className="ml-8">
                    <input
                      type="text"
                      placeholder="https://your-webhook-url.com/notify"
                      value={preferences.webhook_url || ''}
                      onChange={(e) => handlePreferenceChange('webhook_url', e.target.value)}
                      className="w-full px-3 py-2 border rounded-md"
                    />
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Send className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Telegram Notifications</p>
                      <p className="text-sm text-muted-foreground">Receive notifications via Telegram bot</p>
                    </div>
                  </div>
                  <Switch
                    checked={preferences.telegram_enabled}
                    onCheckedChange={(checked) => handlePreferenceChange('telegram_enabled', checked)}
                    disabled={savingPrefs}
                  />
                </div>
                {preferences.telegram_enabled && (
                  <div className="ml-8 space-y-3">
                    <div>
                      <Label className="text-sm">Telegram Bot Token</Label>
                      <Input
                        type="password"
                        placeholder="Enter your Telegram bot token"
                        value={preferences.telegram_bot_token || ''}
                        onChange={(e) => handlePreferenceChange('telegram_bot_token', e.target.value)}
                        className="mt-1"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Create a bot via @BotFather and paste the token here
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm">Telegram Chat ID</Label>
                      <Input
                        placeholder="Enter your Telegram chat ID (e.g., 123456789)"
                        value={preferences.telegram_chat_id || ''}
                        onChange={(e) => handlePreferenceChange('telegram_chat_id', e.target.value)}
                        className="mt-1"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Message @userinfobot on Telegram to get your Chat ID
                      </p>
                    </div>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <MessageCircle className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">WhatsApp Notifications</p>
                      <p className="text-sm text-muted-foreground">Receive notifications via WhatsApp webhook</p>
                    </div>
                  </div>
                  <Switch
                    checked={preferences.whatsapp_enabled}
                    onCheckedChange={(checked) => handlePreferenceChange('whatsapp_enabled', checked)}
                    disabled={savingPrefs}
                  />
                </div>
                {preferences.whatsapp_enabled && (
                  <div className="ml-8 space-y-3">
                    <div>
                      <Label className="text-sm">WhatsApp Phone Number</Label>
                      <Input
                        placeholder="Enter phone number (e.g., +911234567890)"
                        value={preferences.whatsapp_phone || ''}
                        onChange={(e) => handlePreferenceChange('whatsapp_phone', e.target.value)}
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-sm">WhatsApp Webhook URL</Label>
                      <Input
                        placeholder="https://your-whatsapp-gateway.com/send"
                        value={preferences.whatsapp_webhook_url || ''}
                        onChange={(e) => handlePreferenceChange('whatsapp_webhook_url', e.target.value)}
                        className="mt-1"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Configure a WhatsApp Business API webhook or use services like Twilio, MessageBird, etc.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold mb-4">Notification Types</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <TrendingUp className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Trade Notifications</p>
                      <p className="text-sm text-muted-foreground">Order fills, trades, position updates</p>
                    </div>
                  </div>
                  <Switch
                    checked={preferences.trade_notifications}
                    onCheckedChange={(checked) => handlePreferenceChange('trade_notifications', checked)}
                    disabled={savingPrefs}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Shield className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Risk Notifications</p>
                      <p className="text-sm text-muted-foreground">Risk rule triggers, kill switch events</p>
                    </div>
                  </div>
                  <Switch
                    checked={preferences.risk_notifications}
                    onCheckedChange={(checked) => handlePreferenceChange('risk_notifications', checked)}
                    disabled={savingPrefs}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Cpu className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Strategy Notifications</p>
                      <p className="text-sm text-muted-foreground">Strategy start/stop, signal generation</p>
                    </div>
                  </div>
                  <Switch
                    checked={preferences.strategy_notifications}
                    onCheckedChange={(checked) => handlePreferenceChange('strategy_notifications', checked)}
                    disabled={savingPrefs}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Daily Summary</p>
                      <p className="text-sm text-muted-foreground">Receive a daily portfolio summary</p>
                    </div>
                  </div>
                  <Switch
                    checked={preferences.daily_summary}
                    onCheckedChange={(checked) => handlePreferenceChange('daily_summary', checked)}
                    disabled={savingPrefs}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
