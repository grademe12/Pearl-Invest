'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  PieChart,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';

// API 설정
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://192.168.45.205:30082';

// 타입 정의
interface Asset {
  symbol: string;
  name: string;
  asset_class: string;
  quantity: number;
  current_price: number;
  total_value: number;
  allocation_percentage: number;
  cost_basis: number;
  unrealized_pnl: number;
  unrealized_pnl_percentage: number;
}

interface PerformanceMetrics {
  total_return: number;
  total_return_percentage: number;
  daily_return: number;
  daily_return_percentage: number;
  monthly_return: number;
  monthly_return_percentage: number;
  yearly_return: number;
  yearly_return_percentage: number;
  sharpe_ratio: number;
  volatility: number;
  max_drawdown: number;
  win_rate: number;
}

interface RiskMetrics {
  risk_level: string;
  beta: number;
  var_95: number;
  expected_shortfall: number;
  correlation_to_market: number;
  diversification_ratio: number;
}

interface PortfolioAnalysis {
  total_value: number;
  total_cost_basis: number;
  total_pnl: number;
  total_pnl_percentage: number;
  assets: Asset[];
  allocation: any[];
  performance: PerformanceMetrics;
  risk: RiskMetrics;
}

interface Insight {
  type: string;
  title: string;
  description: string;
  severity: string;
  action_required: boolean;
}

export default function PortfolioPage() {
  const [token, setToken] = useState<string>('');
  const [analysis, setAnalysis] = useState<PortfolioAnalysis | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  // 토큰 로드
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
      setToken(savedToken);
      fetchPortfolioData(savedToken);
    } else {
      setError('Please login first');
    }
  }, []);

  // 포트폴리오 데이터 가져오기
  const fetchPortfolioData = async (authToken: string) => {
    setLoading(true);
    setError('');

    try {
      // 포트폴리오 분석
      const analysisRes = await fetch(`${API_URL}/portfolio/analysis`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!analysisRes.ok) throw new Error('Failed to fetch portfolio');
      const analysisData = await analysisRes.json();
      setAnalysis(analysisData);

      // 인사이트
      const insightsRes = await fetch(`${API_URL}/portfolio/insights`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (insightsRes.ok) {
        const insightsData = await insightsRes.json();
        setInsights(insightsData);
      }

    } catch (err) {
      setError('Failed to load portfolio data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 숫자 포맷
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  // 리밸런싱 시뮬레이션
  const handleRebalance = async (strategy: string) => {
    try {
      const response = await fetch(`${API_URL}/portfolio/rebalance`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ strategy })
      });

      if (!response.ok) throw new Error('Rebalance failed');
      const data = await response.json();
      
      alert(`Rebalance simulation complete! Estimated cost: ${formatCurrency(data.estimated_cost)}`);
    } catch (err) {
      alert('Rebalance simulation failed');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="animate-spin h-8 w-8 mx-auto mb-4" />
          <p>Loading portfolio data...</p>
        </div>
      </div>
    );
  }

  if (error && !analysis) {
    return (
      <div className="container mx-auto p-8">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!analysis) {
    return null;
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Portfolio Dashboard</h1>
        <Button onClick={() => fetchPortfolioData(token)} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(analysis.total_value)}</div>
            <p className="text-xs text-muted-foreground">
              Cost Basis: {formatCurrency(analysis.total_cost_basis)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
            {analysis.total_pnl >= 0 ? 
              <TrendingUp className="h-4 w-4 text-green-600" /> : 
              <TrendingDown className="h-4 w-4 text-red-600" />
            }
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${analysis.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(analysis.total_pnl)}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatPercent(analysis.total_pnl_percentage)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Daily Return</CardTitle>
            <PieChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${analysis.performance.daily_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatPercent(analysis.performance.daily_return_percentage)}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(analysis.performance.daily_return)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Risk Level</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              <Badge variant={
                analysis.risk.risk_level === 'low' ? 'default' :
                analysis.risk.risk_level === 'medium' ? 'secondary' :
                'destructive'
              }>
                {analysis.risk.risk_level.toUpperCase()}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Beta: {analysis.risk.beta.toFixed(2)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Insights */}
      {insights.length > 0 && (
        <div className="space-y-2">
          {insights.map((insight, idx) => (
            <Alert key={idx} variant={insight.severity === 'warning' ? 'destructive' : 'default'}>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>{insight.title}:</strong> {insight.description}
              </AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="assets">Assets</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="rebalance">Rebalance</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Asset Allocation</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {analysis.allocation
                  .filter(a => a.current_percentage > 0)
                  .map((alloc, idx) => (
                    <div key={idx} className="flex justify-between items-center">
                      <span className="text-sm font-medium">{alloc.asset_class}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-32 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${alloc.current_percentage}%` }}
                          />
                        </div>
                        <span className="text-sm w-16 text-right">
                          {alloc.current_percentage.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="assets" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Holdings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">Symbol</th>
                      <th className="text-left p-2">Name</th>
                      <th className="text-right p-2">Quantity</th>
                      <th className="text-right p-2">Price</th>
                      <th className="text-right p-2">Value</th>
                      <th className="text-right p-2">P&L</th>
                      <th className="text-right p-2">%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.assets.map((asset, idx) => (
                      <tr key={idx} className="border-b hover:bg-gray-50">
                        <td className="p-2 font-medium">{asset.symbol}</td>
                        <td className="p-2">{asset.name}</td>
                        <td className="p-2 text-right">{asset.quantity}</td>
                        <td className="p-2 text-right">{formatCurrency(asset.current_price)}</td>
                        <td className="p-2 text-right">{formatCurrency(asset.total_value)}</td>
                        <td className={`p-2 text-right ${asset.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(asset.unrealized_pnl)}
                        </td>
                        <td className={`p-2 text-right ${asset.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatPercent(asset.unrealized_pnl_percentage)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Returns</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span>Daily</span>
                    <span className={analysis.performance.daily_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {formatPercent(analysis.performance.daily_return_percentage)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Monthly</span>
                    <span className={analysis.performance.monthly_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {formatPercent(analysis.performance.monthly_return_percentage)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Yearly</span>
                    <span className={analysis.performance.yearly_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {formatPercent(analysis.performance.yearly_return_percentage)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Risk Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span>Sharpe Ratio</span>
                    <span>{analysis.performance.sharpe_ratio.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Volatility</span>
                    <span>{analysis.performance.volatility.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max Drawdown</span>
                    <span className="text-red-600">{analysis.performance.max_drawdown.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Win Rate</span>
                    <span>{(analysis.performance.win_rate * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="rebalance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Portfolio Rebalancing</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Choose a rebalancing strategy to optimize your portfolio allocation.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="cursor-pointer hover:shadow-lg transition-shadow"
                      onClick={() => handleRebalance('conservative')}>
                  <CardHeader>
                    <CardTitle className="text-lg">Conservative</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      30% Stocks, 50% Bonds, 20% Others
                    </p>
                    <p className="text-xs mt-2">Low risk, stable returns</p>
                  </CardContent>
                </Card>

                <Card className="cursor-pointer hover:shadow-lg transition-shadow"
                      onClick={() => handleRebalance('balanced')}>
                  <CardHeader>
                    <CardTitle className="text-lg">Balanced</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      60% Stocks, 30% Bonds, 10% Others
                    </p>
                    <p className="text-xs mt-2">Moderate risk, balanced growth</p>
                  </CardContent>
                </Card>

                <Card className="cursor-pointer hover:shadow-lg transition-shadow"
                      onClick={() => handleRebalance('aggressive')}>
                  <CardHeader>
                    <CardTitle className="text-lg">Aggressive</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      80% Stocks, 10% Crypto, 10% Others
                    </p>
                    <p className="text-xs mt-2">High risk, maximum growth</p>
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}