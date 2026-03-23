import { useEffect, useRef, useState, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface WebSocketMessage {
  type: string;
  channel: string;
  data: any;
  timestamp: string;
}

type MessageHandler = (message: WebSocketMessage) => void;

interface UseWebSocketOptions {
  channels?: string[];
  onMessage?: MessageHandler;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    channels = [],
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoReconnect = true,
    reconnectInterval = 5000,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const handlersRef = useRef<Map<string, Set<MessageHandler>>>(new Map());

  const getToken = useCallback(() => localStorage.getItem('token'), []);

  const connect = useCallback(() => {
    const token = getToken();
    if (!token) {
      console.warn('No token available for WebSocket');
      return;
    }

    const wsUrl = `${API_URL.replace('http', 'ws')}/ws?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      onConnect?.();

      // Subscribe to channels
      channels.forEach(channel => {
        ws.send(JSON.stringify({
          type: 'subscribe',
          channel,
        }));
      });
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastMessage(message);

        // Call general message handler
        onMessage?.(message);

        // Call channel-specific handlers
        const channelHandlers = handlersRef.current.get(message.channel);
        if (channelHandlers) {
          channelHandlers.forEach(handler => handler(message));
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      onDisconnect?.();

      if (autoReconnect) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      onError?.(error);
    };

    wsRef.current = ws;
  }, [channels, getToken, onConnect, onDisconnect, onMessage, onError, autoReconnect, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const subscribe = useCallback((channel: string, handler: MessageHandler) => {
    if (!handlersRef.current.has(channel)) {
      handlersRef.current.set(channel, new Set());
    }
    handlersRef.current.get(channel)?.add(handler);

    // Send subscription if connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        channel,
      }));
    }
  }, []);

  const unsubscribe = useCallback((channel: string, handler?: MessageHandler) => {
    const channelHandlers = handlersRef.current.get(channel);
    if (channelHandlers) {
      if (handler) {
        channelHandlers.delete(handler);
      } else {
        channelHandlers.clear();
      }
    }

    // Send unsubscription if connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'unsubscribe',
        channel,
      }));
    }
  }, []);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    send,
    subscribe,
    unsubscribe,
    connect,
    disconnect,
  };
}

// Hook for order updates
export function useOrderUpdates(onOrderUpdate: (order: any) => void) {
  return useWebSocket({
    channels: ['orders'],
    onMessage: (msg) => {
      if (msg.type === 'order_update') {
        onOrderUpdate(msg.data);
      }
    },
  });
}

// Hook for position updates
export function usePositionUpdates(onPositionUpdate: (position: any) => void) {
  return useWebSocket({
    channels: ['positions'],
    onMessage: (msg) => {
      if (msg.type === 'position_update') {
        onPositionUpdate(msg.data);
      }
    },
  });
}

// Hook for market data
export function useMarketDataUpdates(symbols: string[], onQuote: (quote: any) => void) {
  return useWebSocket({
    channels: symbols.map(s => `market:${s}`),
    onMessage: (msg) => {
      if (msg.type === 'quote') {
        onQuote(msg.data);
      }
    },
  });
}
