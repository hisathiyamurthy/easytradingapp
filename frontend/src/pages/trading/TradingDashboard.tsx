import { useState, useEffect } from 'react';
import { Button, Card, CardContent, CardHeader, CardTitle, CardDescription, Badge, Input, Label, Select, SelectContent, SelectItem, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui';
import { usePositions, useOrders, useTradeHistory, usePlaceOrder } from '@/hooks/useTrading';

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(value || 0);
}

export function TradingDashboard() {
  const { data: positions, isLoading: positionsLoading, error: positionsError, refetch: refetchPositions } = usePositions();
    const { data: orders, isLoading: ordersLoading, error: ordersError } = useOrders();
    const { data: trades, isLoading: tradesLoading } = useTradeHistory();
    const placeOrderMutation = usePlaceOrder();

  const [orderForm, setOrderForm] = useState({
    symbol: 'RELIANCE',
    side: 'buy',
    orderType: 'market',
    productType: 'MIS',
    quantity: 1,
    price: '',
    triggerPrice: '',
  });

  const [activeTab, setActiveTab] = useState('positions');
  const [orderError, setOrderError] = useState<string | null>(null);
  const [orderSuccess, setOrderSuccess] = useState<string | null>(null);

  const totalValue = positions?.reduce((acc: number, p: any) => acc + ((p.current_price || 0) * (p.quantity || 0)), 0) || 0;
  const totalPnl = positions?.reduce((acc: number, p: any) => acc + (p.unrealized_pnl || 0), 0) || 0;

  const handlePlaceOrder = async () => {
    setOrderError(null);
    setOrderSuccess(null);
    
    try {
      await placeOrderMutation.mutateAsync({
        symbol: orderForm.symbol,
        side: orderForm.side,
        order_type: orderForm.orderType,
        quantity: parseInt(orderForm.quantity.toString()),
        price: orderForm.price ? parseFloat(orderForm.price) : undefined,
        trigger_price: orderForm.triggerPrice ? parseFloat(orderForm.triggerPrice) : undefined,
        product: orderForm.productType,
        transaction_type: orderForm.side.toUpperCase(),
      });
      setOrderSuccess(`${orderForm.side.toUpperCase()} order placed successfully!`);
      setOrderForm({ ...orderForm, quantity: 1, price: '', triggerPrice: '' });
      refetchPositions();
    } catch (error: any) {
      setOrderError(error.message || 'Order failed. Please try again.');
      console.error('Order failed:', error);
    }
  };

  if (positionsLoading) {
    return <div className="p-8 text-center">Loading trading data...</div>;
  }
  
  if (positionsError || ordersError) {
    return (
      <div className="p-8 text-center text-red-600">
        <p>Error loading data: {positionsError || ordersError}</p>
        <p className="text-sm mt-2">Please make sure you are logged in.</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Trading Dashboard</h1>
          <p className="text-sm text-muted-foreground">Monitor your positions and place trades</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Portfolio Value</p>
            <p className="text-2xl font-bold">{formatCurrency(totalValue)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Unrealized P&L</p>
            <p className={`text-2xl font-bold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {totalPnl >= 0 ? '+' : ''}{formatCurrency(totalPnl)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Open Positions</p>
            <p className="text-2xl font-bold">{positions?.length || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Pending Orders</p>
            <p className="text-2xl font-bold">{orders?.length || 0}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Quick Trade</CardTitle>
            <CardDescription>Place a new order</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Symbol</Label>
              <Select value={orderForm.symbol} onValueChange={(v: string) => setOrderForm({ ...orderForm, symbol: v })}>
                <SelectContent>
                  <SelectItem value="RELIANCE">RELIANCE</SelectItem>
                  <SelectItem value="TCS">TCS</SelectItem>
                  <SelectItem value="INFY">INFY</SelectItem>
                  <SelectItem value="HDFCBANK">HDFCBANK</SelectItem>
                  <SelectItem value="ICICIBANK">ICICIBANK</SelectItem>
                  <SelectItem value="SBIN">SBIN</SelectItem>
                  <SelectItem value="WIPRO">WIPRO</SelectItem>
                  <SelectItem value="MARUTI">MARUTI</SelectItem>
                  <SelectItem value="BHARTIARTL">BHARTIARTL</SelectItem>
                  <SelectItem value="TITAN">TITAN</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex space-x-2">
              <Button
                className="flex-1"
                variant={orderForm.side === 'buy' ? 'default' : 'outline'}
                onClick={() => setOrderForm({ ...orderForm, side: 'buy' })}
              >
                Buy
              </Button>
              <Button
                className="flex-1"
                variant={orderForm.side === 'sell' ? 'destructive' : 'outline'}
                onClick={() => setOrderForm({ ...orderForm, side: 'sell' })}
              >
                Sell
              </Button>
            </div>

            <div className="space-y-2">
              <Label>Order Type</Label>
              <Select value={orderForm.orderType} onValueChange={(v: string) => setOrderForm({ ...orderForm, orderType: v, triggerPrice: '' })}>
                <SelectContent>
                  <SelectItem value="market">Market (MKT)</SelectItem>
                  <SelectItem value="limit">Limit (L)</SelectItem>
                  <SelectItem value="stop_loss">Stop Loss (SL)</SelectItem>
                  <SelectItem value="stop_loss_limit">Stop Loss Limit (SL-L)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Product Type</Label>
              <Select value={orderForm.productType} onValueChange={(v: string) => setOrderForm({ ...orderForm, productType: v })}>
                <SelectContent>
                  <SelectItem value="MIS">MIS (Intraday)</SelectItem>
                  <SelectItem value="CNC">CNC (Delivery)</SelectItem>
                  <SelectItem value="NRML">NRML (Overnight)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Quantity</Label>
              <Input
                type="number"
                min="1"
                value={orderForm.quantity}
                onChange={(e: any) => setOrderForm({ ...orderForm, quantity: parseInt(e.target.value) || 1 })}
              />
            </div>

            {(orderForm.orderType === 'limit' || orderForm.orderType === 'stop_loss_limit') && (
              <div className="space-y-2">
                <Label>Price</Label>
                <Input
                  type="number"
                  placeholder="Limit price"
                  value={orderForm.price}
                  onChange={(e: any) => setOrderForm({ ...orderForm, price: e.target.value })}
                />
              </div>
            )}

            {(orderForm.orderType === 'stop_loss' || orderForm.orderType === 'stop_loss_limit') && (
              <div className="space-y-2">
                <Label>Trigger Price</Label>
                <Input
                  type="number"
                  placeholder="Trigger price for SL"
                  value={orderForm.triggerPrice}
                  onChange={(e: any) => setOrderForm({ ...orderForm, triggerPrice: e.target.value })}
                />
              </div>
            )}

            {orderError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {orderError}
              </div>
            )}

            {orderSuccess && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
                {orderSuccess}
              </div>
            )}

            <Button
              className="w-full"
              variant={orderForm.side === 'buy' ? 'default' : 'destructive'}
              onClick={handlePlaceOrder}
              disabled={placeOrderMutation.isPending}
            >
              {placeOrderMutation.isPending ? 'Placing Order...' : `${orderForm.side === 'buy' ? 'Buy' : 'Sell'} ${orderForm.symbol}`}
            </Button>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Portfolio</CardTitle>
              <div className="flex space-x-2">
                <Button variant={activeTab === 'positions' ? 'default' : 'outline'} size="sm" onClick={() => setActiveTab('positions')}>
                  Positions ({positions?.length || 0})
                </Button>
                <Button variant={activeTab === 'orders' ? 'default' : 'outline'} size="sm" onClick={() => setActiveTab('orders')}>
                  Orders ({orders?.length || 0})
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {activeTab === 'positions' && (
              positions?.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No open positions</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Qty</TableHead>
                      <TableHead className="text-right">Avg Price</TableHead>
                      <TableHead className="text-right">Current</TableHead>
                      <TableHead className="text-right">P&L</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {positions?.map((position: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{position.symbol}</TableCell>
                        <TableCell>{position.quantity}</TableCell>
                        <TableCell className="text-right">{formatCurrency(position.average_price)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(position.current_price)}</TableCell>
                        <TableCell className={`text-right ${(position.unrealized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(position.unrealized_pnl)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )
            )}

            {activeTab === 'orders' && (
              orders?.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No pending orders</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orders?.map((order: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{order.symbol}</TableCell>
                        <TableCell>{order.transaction_type}</TableCell>
                        <TableCell className="text-right">{order.quantity}</TableCell>
                        <TableCell className="text-right">{order.price ? formatCurrency(order.average_price) : 'Market'}</TableCell>
                        <TableCell>
                          <Badge variant={order.status === 'COMPLETE' ? 'success' : 'warning'}>
                            {order.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default TradingDashboard;
