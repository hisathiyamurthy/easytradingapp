import { useState, useEffect, useCallback } from 'react';
import { marketApi, Quote, IndexQuote, formatPrice, formatChange, getChangeColor } from '../services/marketApi';

export function useMarketQuote(symbol: string, exchange = 'NSE') {
  const [quote, setQuote] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQuote = useCallback(async () => {
    try {
      setLoading(true);
      const data = await marketApi.getQuote(symbol, exchange);
      setQuote(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch quote');
    } finally {
      setLoading(false);
    }
  }, [symbol, exchange]);

  useEffect(() => {
    fetchQuote();
  }, [fetchQuote]);

  return { quote, loading, error, refetch: fetchQuote };
}

export function useMultipleQuotes(symbols: string[], exchange = 'NSE') {
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQuotes = useCallback(async () => {
    if (symbols.length === 0) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const data = await marketApi.getQuotes(symbols, exchange);
      const quoteMap: Record<string, Quote> = {};
      data.forEach((q) => {
        quoteMap[q.symbol] = q;
      });
      setQuotes(quoteMap);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch quotes');
    } finally {
      setLoading(false);
    }
  }, [symbols.join(','), exchange]);

  useEffect(() => {
    fetchQuotes();
  }, [fetchQuotes]);

  return { quotes, loading, error, refetch: fetchQuotes };
}

export function useIndexQuote(index: string) {
  const [indexData, setIndexData] = useState<IndexQuote | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIndex = useCallback(async () => {
    try {
      setLoading(true);
      const data = await marketApi.getIndex(index);
      setIndexData(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch index');
    } finally {
      setLoading(false);
    }
  }, [index]);

  useEffect(() => {
    fetchIndex();
  }, [fetchIndex]);

  return { indexData, loading, error, refetch: fetchIndex };
}

export function useLivePrices(symbols: string[], interval = 5000, exchange = 'NSE') {
  const [prices, setPrices] = useState<Record<string, Quote>>({});
  const { quotes, loading, error, refetch } = useMultipleQuotes(symbols, exchange);

  useEffect(() => {
    if (quotes && Object.keys(quotes).length > 0) {
      setPrices(quotes);
    }
  }, [quotes]);

  useEffect(() => {
    const timer = setInterval(() => {
      refetch();
    }, interval);

    return () => clearInterval(timer);
  }, [interval, refetch]);

  return { prices, loading, error };
}

// Watchlist hook
export function useWatchlist() {
  const [symbols, setSymbols] = useState<string[]>(() => {
    const saved = localStorage.getItem('watchlist');
    return saved ? JSON.parse(saved) : ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'NIFTY'];
  });

  const addSymbol = (symbol: string) => {
    if (!symbols.includes(symbol)) {
      const updated = [...symbols, symbol];
      setSymbols(updated);
      localStorage.setItem('watchlist', JSON.stringify(updated));
    }
  };

  const removeSymbol = (symbol: string) => {
    const updated = symbols.filter((s) => s !== symbol);
    setSymbols(updated);
    localStorage.setItem('watchlist', JSON.stringify(updated));
  };

  return { symbols, addSymbol, removeSymbol };
}
