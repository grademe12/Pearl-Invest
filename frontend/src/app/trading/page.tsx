'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign,
  ShoppingCart,
  Activity,
  RefreshCw,
  ArrowUpCircle,
  ArrowDownCircle,
  AlertCircle
} from 'lucide-react';

// API 설정
const API_URL = process.env.NEXT_PUBLIC_TRADING_API_URL || 'http://192.168.45.85:30081';

// 타입 정의
interface Position {
  symbol: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  pnl: number;
  pnl_percentage: number;
}

interface PortfolioSummary {
  total_value: number;
  cash_balance: number;
  positions_value: number;
  daily_pnl: number;
  daily_pnl_percentage: number;
  positions: Position[];
}

interface Order {
  order_id: string;
  symbol: string;
  side: 'buy' | 'sell';
  order_type: 'market' | 'limit' | 'stop_loss' | 'stop_limit';
  quantity: number;
  price?: number;
  status: 'pending' | 'filled' | 'partially_filled' | 'cancelled' | 'rejected';
  created_at: string;
  filled_at?: string;
  filled_quantity: number;
  average_fill_price?: number;
}

interface Transaction {
  transaction_id: string;
  order_id: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
  fee: number;
  timestamp: string;
}

interface MarketData {
  symbol: string;
  last_price: number;
  bid: number;
  ask: number;
  volume: number;
  daily_change: number;
  daily_change_percentage: number;
}

export default function TradingPage() {
  const [token, setToken] = useState<string>('');
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [markets, setMarkets] = useState<MarketData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('portfolio');

  // Order Form State
  const [orderForm, setOrderForm] = useState({
    symbol: '',
    side: 'buy',
    order_type: 'market',
    quantity: '',
    price: ''
  });

  // 토큰 로드
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
      setToken(savedToken);
      fetchTradingData(savedToken);
    } else {
      setError('Please login first');
    }
  }, []);

  // 거래 데이터 가져오기
  const fetchTradingData = async (authToken: string) => {
    setLoading(true);
    setError('');

    try {
      // 포트폴리오
      const portfolioRes = await fetch(`${API_URL}/trading/portfolio`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      if (portfolioRes.ok) {
        const portfolioData = await portfolioRes.json();
        setPortfolio(portfolioData);
      }

      // 주문 내역
      const ordersRes = await fetch(`${API_URL}/trading/orders?limit=20`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      if (ordersRes.ok) {
        const ordersData = await ordersRes.json();
        setOrders(ordersData);
      }

      // 거래 내역
      const transactionsRes = await fetch(`${API_URL}/trading/transactions?limit=20`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      if (transactionsRes.ok) {
        const transactionsData = await transactionsRes.json();
        setTransactions(transactionsData);
      }

      // 시장 데이터
      const marketsRes = await fetch(`${API_URL}/trading/markets`);
      if (marketsRes.ok) {
        const marketsData = await marketsRes.json();
        setMarkets(marketsData);
      }

    } catch (err) {
      setError('Failed to load trading data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 주문 실행
  const handlePlaceOrder = async () => {
    if (!orderForm.symbol || !orderForm.quantity) {
      alert('Please fill in all required fields');
      return;
    }

    try {
      const orderData: any = {
        symbol: orderForm.symbol,
        side: orderForm.side,
        order_type: orderForm.order_type,
        quantity: parseInt(orderForm.quantity)
      };

      if (orderForm.order_type === 'limit' && orderForm.price) {
        orderData.price = parseFloat(orderForm.price);
      }

      const response = await fetch(`${API_URL}/trading/order`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(orderData)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Order failed');
      }

      const result = await response.json();
      alert(`Order placed successfully! Order ID: ${result.order_id}`);
      
      // 데이터 새로고침
      fetchTradingData(token);
      
      // 폼 리셋
      setOrderForm({
        symbol: '',
        side: 'buy',
        order_type: 'market',
        quantity: '',
        price: ''
      });

    } catch (err: any) {
      alert(err.message || 'Failed to place order');
    }
  };

  // 주문 취소
  const handleCancelOrder = async (orderId: string) => {
    try {
      const response = await fetch(`${API_URL}/trading/order/${orderId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Cancel failed');
      
      alert('Order cancelled successfully');
      fetchTradingData(token);
    } catch (err) {
      alert('Failed to cancel order');
    }
  };

  // 숫자 포맷
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('en-US').format(value);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="animate-spin h-8 w-8 mx-auto mb-4" />
          <p>Loading trading data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Trading Dashboard</h1>
        <Button onClick={() => fetchTradingData(token)} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      {portfolio && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Value</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.total_value)}</div>
              <p className="text-xs text-muted-foreground">
                Positions: {formatCurrency(portfolio.positions_value)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Cash Balance</CardTitle>
              <ShoppingCart className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.cash_balance)}</div>
              <p className="text-xs text-muted-foreground">
                Available for trading
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Daily P&L</CardTitle>
              {portfolio.daily_pnl >= 0 ? 
                <TrendingUp className="h-4 w-4 text-green-600" /> : 
                <TrendingDown className="h-4 w-4 text-red-600" />
              }
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${portfolio.daily_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(portfolio.daily_pnl)}
              </div>
              <p className="text-xs text-muted-foreground">
                {formatPercent(portfolio.daily_pnl_percentage)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Orders</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {orders.filter(o => o.status === 'pending').length}
              </div>
              <p className="text-xs text-muted-foreground">
                Total orders: {orders.length}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="trade">Trade</TabsTrigger>
          <TabsTrigger value="orders">Orders</TabsTrigger>
          <TabsTrigger value="transactions">History</TabsTrigger>
          <TabsTrigger value="markets">Markets</TabsTrigger>
        </TabsList>

        {/* Portfolio Tab */}
        <TabsContent value="portfolio" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Current Positions</CardTitle>
            </CardHeader>
            <CardContent>
              {portfolio && portfolio.positions.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2">Symbol</th>
                        <th className="text-right p-2">Quantity</th>
                        <th className="text-right p-2">Avg Price</th>
                        <th className="text-right p-2">Current Price</th>
                        <th className="text-right p-2">P&L</th>
                        <th className="text-right p-2">P&L %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {portfolio.positions.map((position, idx) => (
                        <tr key={idx} className="border-b hover:bg-gray-50">
                          <td className="p-2 font-medium">{position.symbol}</td>
                          <td className="p-2 text-right">{position.quantity}</td>
                          <td className="p-2 text-right">{formatCurrency(position.avg_price)}</td>
                          <td className="p-2 text-right">{formatCurrency(position.current_price)}</td>
                          <td className={`p-2 text-right ${position.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(position.pnl)}
                          </td>
                          <td className={`p-2 text-right ${position.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatPercent(position.pnl_percentage)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-4">No positions</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trade Tab */}
        <TabsContent value="trade" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Place Order</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="symbol">Symbol</Label>
                  <Select 
                    value={orderForm.symbol} 
                    onValueChange={(value) => setOrderForm({...orderForm, symbol: value})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select symbol" />
                    </SelectTrigger>
                    <SelectContent>
                      {markets.map(market => (
                        <SelectItem key={market.symbol} value={market.symbol}>
                          {market.symbol}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="side">Side</Label>
                  <Select 
                    value={orderForm.side} 
                    onValueChange={(value) => setOrderForm({...orderForm, side: value})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="buy">Buy</SelectItem>
                      <SelectItem value="sell">Sell</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="order_type">Order Type</Label>
                  <Select 
                    value={orderForm.order_type} 
                    onValueChange={(value) => setOrderForm({...orderForm, order_type: value})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="market">Market</SelectItem>
                      <SelectItem value="limit">Limit</SelectItem>
                      <SelectItem value="stop_loss">Stop Loss</SelectItem>
                      <SelectItem value="stop_limit">Stop Limit</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="quantity">Quantity</Label>
                  <Input
                    type="number"
                    placeholder="Enter quantity"
                    value={orderForm.quantity}
                    onChange={(e) => setOrderForm({...orderForm, quantity: e.target.value})}
                  />
                </div>

                {(orderForm.order_type === 'limit' || orderForm.order_type === 'stop_limit') && (
                  <div className="col-span-2">
                    <Label htmlFor="price">Price</Label>
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="Enter price"
                      value={orderForm.price}
                      onChange={(e) => setOrderForm({...orderForm, price: e.target.value})}
                    />
                  </div>
                )}
              </div>

              {/* Market Info */}
              {orderForm.symbol && markets.find(m => m.symbol === orderForm.symbol) && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {orderForm.symbol} - Last: {formatCurrency(markets.find(m => m.symbol === orderForm.symbol)!.last_price)} | 
                    Bid: {formatCurrency(markets.find(m => m.symbol === orderForm.symbol)!.bid)} | 
                    Ask: {formatCurrency(markets.find(m => m.symbol === orderForm.symbol)!.ask)}
                  </AlertDescription>
                </Alert>
              )}

              <Button 
                onClick={handlePlaceOrder}
                className={`w-full ${orderForm.side === 'buy' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}`}
              >
                {orderForm.side === 'buy' ? (
                  <ArrowUpCircle className="h-4 w-4 mr-2" />
                ) : (
                  <ArrowDownCircle className="h-4 w-4 mr-2" />
                )}
                Place {orderForm.side.toUpperCase()} Order
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Orders Tab */}
        <TabsContent value="orders" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Order History</CardTitle>
            </CardHeader>
            <CardContent>
              {orders.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2">Time</th>
                        <th className="text-left p-2">Symbol</th>
                        <th className="text-left p-2">Side</th>
                        <th className="text-left p-2">Type</th>
                        <th className="text-right p-2">Qty</th>
                        <th className="text-right p-2">Price</th>
                        <th className="text-left p-2">Status</th>
                        <th className="text-center p-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orders.map((order) => (
                        <tr key={order.order_id} className="border-b hover:bg-gray-50">
                          <td className="p-2 text-xs">
                            {new Date(order.created_at).toLocaleString()}
                          </td>
                          <td className="p-2 font-medium">{order.symbol}</td>
                          <td className="p-2">
                            <Badge variant={order.side === 'buy' ? 'default' : 'destructive'}>
                              {order.side}
                            </Badge>
                          </td>
                          <td className="p-2 text-sm">{order.order_type}</td>
                          <td className="p-2 text-right">{order.quantity}</td>
                          <td className="p-2 text-right">
                            {order.average_fill_price ? 
                              formatCurrency(order.average_fill_price) : 
                              order.price ? formatCurrency(order.price) : 'Market'
                            }
                          </td>
                          <td className="p-2">
                            <Badge variant={
                              order.status === 'filled' ? 'default' :
                              order.status === 'pending' ? 'secondary' :
                              order.status === 'cancelled' ? 'outline' :
                              'destructive'
                            }>
                              {order.status}
                            </Badge>
                          </td>
                          <td className="p-2 text-center">
                            {order.status === 'pending' && (
                              <Button
                                size="sm"
                                variant="destructive"
                                onClick={() => handleCancelOrder(order.order_id)}
                              >
                                Cancel
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-4">No orders yet</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Transactions Tab */}
        <TabsContent value="transactions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Transaction History</CardTitle>
            </CardHeader>
            <CardContent>
              {transactions.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2">Time</th>
                        <th className="text-left p-2">Symbol</th>
                        <th className="text-left p-2">Side</th>
                        <th className="text-right p-2">Quantity</th>
                        <th className="text-right p-2">Price</th>
                        <th className="text-right p-2">Total</th>
                        <th className="text-right p-2">Fee</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx) => (
                        <tr key={tx.transaction_id} className="border-b hover:bg-gray-50">
                          <td className="p-2 text-xs">
                            {new Date(tx.timestamp).toLocaleString()}
                          </td>
                          <td className="p-2 font-medium">{tx.symbol}</td>
                          <td className="p-2">
                            <Badge variant={tx.side === 'buy' ? 'default' : 'destructive'}>
                              {tx.side}
                            </Badge>
                          </td>
                          <td className="p-2 text-right">{tx.quantity}</td>
                          <td className="p-2 text-right">{formatCurrency(tx.price)}</td>
                          <td className="p-2 text-right">{formatCurrency(tx.quantity * tx.price)}</td>
                          <td className="p-2 text-right text-red-600">{formatCurrency(tx.fee)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-4">No transactions yet</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Markets Tab */}
        <TabsContent value="markets" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Market Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">Symbol</th>
                      <th className="text-right p-2">Last Price</th>
                      <th className="text-right p-2">Change</th>
                      <th className="text-right p-2">Change %</th>
                      <th className="text-right p-2">Volume</th>
                      <th className="text-right p-2">Bid</th>
                      <th className="text-right p-2">Ask</th>
                    </tr>
                  </thead>
                  <tbody>
                    {markets.map((market) => (
                      <tr key={market.symbol} className="border-b hover:bg-gray-50">
                        <td className="p-2 font-medium">{market.symbol}</td>
                        <td className="p-2 text-right">{formatCurrency(market.last_price)}</td>
                        <td className={`p-2 text-right ${market.daily_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {market.daily_change >= 0 ? '+' : ''}{formatCurrency(market.daily_change)}
                        </td>
                        <td className={`p-2 text-right ${market.daily_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatPercent(market.daily_change_percentage)}
                        </td>
                        <td className="p-2 text-right">{formatNumber(market.volume)}</td>
                        <td className="p-2 text-right">{formatCurrency(market.bid)}</td>
                        <td className="p-2 text-right">{formatCurrency(market.ask)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}