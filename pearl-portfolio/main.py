"""
Pearl-Invest Portfolio Service API
포트폴리오 분석 및 리밸런싱 서비스
"""

import os
import time
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import uvicorn

# ============= 설정 =============
SERVICE_NAME = "portfolio"
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8081"))
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://pearl-auth-internal:8080")

# ============= Prometheus 메트릭 =============
request_count = Counter(
    'portfolio_requests_total', 
    'Total requests to portfolio service',
    ['method', 'endpoint', 'status']
)
request_duration = Histogram(
    'portfolio_request_duration_seconds',
    'Request duration in portfolio service',
    ['method', 'endpoint']
)
rebalance_count = Counter(
    'portfolio_rebalance_total',
    'Total portfolio rebalances',
    ['strategy', 'status']
)

# ============= Enums =============
class AssetClass(str, Enum):
    STOCKS = "stocks"
    BONDS = "bonds"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    CASH = "cash"
    REAL_ESTATE = "real_estate"

class RebalanceStrategy(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

# ============= Pydantic 모델 =============
class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime
    uptime: float

class Asset(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass
    quantity: float
    current_price: float
    total_value: float
    allocation_percentage: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_percentage: float

class AssetAllocation(BaseModel):
    asset_class: AssetClass
    current_value: float
    current_percentage: float
    target_percentage: float
    difference: float

class PerformanceMetrics(BaseModel):
    total_return: float
    total_return_percentage: float
    daily_return: float
    daily_return_percentage: float
    monthly_return: float
    monthly_return_percentage: float
    yearly_return: float
    yearly_return_percentage: float
    sharpe_ratio: float
    volatility: float
    max_drawdown: float
    win_rate: float

class RiskMetrics(BaseModel):
    risk_level: RiskLevel
    beta: float
    var_95: float  # Value at Risk 95%
    expected_shortfall: float
    correlation_to_market: float
    diversification_ratio: float

class RebalanceRequest(BaseModel):
    strategy: RebalanceStrategy
    custom_allocations: Optional[Dict[AssetClass, float]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "strategy": "balanced",
                "custom_allocations": {
                    "stocks": 60,
                    "bonds": 30,
                    "cash": 10
                }
            }
        }

class RebalanceResponse(BaseModel):
    rebalance_id: str
    strategy: RebalanceStrategy
    current_allocations: List[AssetAllocation]
    target_allocations: List[AssetAllocation]
    required_trades: List[dict]
    estimated_cost: float
    status: str

class PortfolioAnalysis(BaseModel):
    total_value: float
    total_cost_basis: float
    total_pnl: float
    total_pnl_percentage: float
    assets: List[Asset]
    allocation: List[AssetAllocation]
    performance: PerformanceMetrics
    risk: RiskMetrics

class HistoricalData(BaseModel):
    date: date
    total_value: float
    daily_return: float
    cumulative_return: float

class Insight(BaseModel):
    type: str  # "risk", "opportunity", "rebalance", "performance"
    title: str
    description: str
    severity: str  # "info", "warning", "critical"
    action_required: bool

# ============= 임시 데이터베이스 =============
# 데모용 포트폴리오 데이터
PORTFOLIOS_DB: Dict[str, dict] = {
    "usr_001": {  # admin
        "assets": [
            {"symbol": "AAPL", "name": "Apple Inc.", "quantity": 100, "cost_basis": 15000, "asset_class": AssetClass.STOCKS},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "quantity": 50, "cost_basis": 125000, "asset_class": AssetClass.STOCKS},
            {"symbol": "BND", "name": "Vanguard Bond ETF", "quantity": 500, "cost_basis": 40000, "asset_class": AssetClass.BONDS},
            {"symbol": "GLD", "name": "SPDR Gold Trust", "quantity": 100, "cost_basis": 17000, "asset_class": AssetClass.COMMODITIES},
            {"symbol": "BTC", "name": "Bitcoin", "quantity": 0.5, "cost_basis": 20000, "asset_class": AssetClass.CRYPTO}
        ],
        "cash_balance": 50000,
        "created_at": datetime.now() - timedelta(days=365)
    },
    "usr_002": {  # trader
        "assets": [
            {"symbol": "TSLA", "name": "Tesla Inc.", "quantity": 200, "cost_basis": 40000, "asset_class": AssetClass.STOCKS},
            {"symbol": "NVDA", "name": "NVIDIA Corp.", "quantity": 100, "cost_basis": 45000, "asset_class": AssetClass.STOCKS},
            {"symbol": "ETH", "name": "Ethereum", "quantity": 10, "cost_basis": 30000, "asset_class": AssetClass.CRYPTO}
        ],
        "cash_balance": 20000,
        "created_at": datetime.now() - timedelta(days=180)
    }
}

# 가상의 시장 가격
MARKET_PRICES = {
    "AAPL": 155.0,
    "GOOGL": 2600.0,
    "TSLA": 220.0,
    "NVDA": 450.0,
    "BND": 82.0,
    "GLD": 180.0,
    "BTC": 45000.0,
    "ETH": 3000.0
}

# 목표 할당 전략
ALLOCATION_STRATEGIES = {
    RebalanceStrategy.CONSERVATIVE: {
        AssetClass.STOCKS: 30,
        AssetClass.BONDS: 50,
        AssetClass.COMMODITIES: 10,
        AssetClass.CASH: 10
    },
    RebalanceStrategy.BALANCED: {
        AssetClass.STOCKS: 60,
        AssetClass.BONDS: 30,
        AssetClass.COMMODITIES: 5,
        AssetClass.CASH: 5
    },
    RebalanceStrategy.AGGRESSIVE: {
        AssetClass.STOCKS: 80,
        AssetClass.CRYPTO: 10,
        AssetClass.COMMODITIES: 5,
        AssetClass.CASH: 5
    }
}

# ============= 유틸리티 함수 =============
def get_current_price(symbol: str) -> float:
    """현재 가격 조회 (시뮬레이션)"""
    base_price = MARKET_PRICES.get(symbol, 100.0)
    return base_price * (1 + random.uniform(-0.02, 0.02))

def calculate_performance_metrics(portfolio: dict) -> PerformanceMetrics:
    """성과 지표 계산 (시뮬레이션)"""
    total_value = sum(
        get_current_price(asset["symbol"]) * asset["quantity"]
        for asset in portfolio["assets"]
    ) + portfolio["cash_balance"]
    
    total_cost = sum(asset["cost_basis"] for asset in portfolio["assets"]) + portfolio["cash_balance"]
    total_return = total_value - total_cost
    
    return PerformanceMetrics(
        total_return=total_return,
        total_return_percentage=(total_return / total_cost) * 100,
        daily_return=total_return * 0.01,  # 시뮬레이션
        daily_return_percentage=random.uniform(-2, 2),
        monthly_return=total_return * 0.05,
        monthly_return_percentage=random.uniform(-5, 8),
        yearly_return=total_return * 0.15,
        yearly_return_percentage=random.uniform(5, 20),
        sharpe_ratio=random.uniform(0.5, 2.0),
        volatility=random.uniform(10, 25),
        max_drawdown=random.uniform(-20, -5),
        win_rate=random.uniform(0.4, 0.7)
    )

def calculate_risk_metrics(portfolio: dict) -> RiskMetrics:
    """리스크 지표 계산 (시뮬레이션)"""
    # 간단한 리스크 레벨 결정
    total_crypto = sum(
        1 for asset in portfolio["assets"] 
        if asset.get("asset_class") == AssetClass.CRYPTO
    )
    
    if total_crypto > 1:
        risk_level = RiskLevel.VERY_HIGH
    elif len(portfolio["assets"]) > 5:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.HIGH
    
    return RiskMetrics(
        risk_level=risk_level,
        beta=random.uniform(0.8, 1.5),
        var_95=random.uniform(-10000, -5000),
        expected_shortfall=random.uniform(-15000, -8000),
        correlation_to_market=random.uniform(0.6, 0.95),
        diversification_ratio=random.uniform(0.5, 0.9)
    )

def generate_rebalance_id() -> str:
    return f"REB-{int(time.time())}-{random.randint(1000, 9999)}"

# ============= 의존성 =============
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Auth 서비스와 연동하여 사용자 검증 (간단 버전)"""
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # 데모: 토큰에서 사용자 ID 추출
    return {
        "user_id": "usr_001",
        "username": "admin",
        "roles": ["viewer", "trader"]
    }

# ============= FastAPI 앱 설정 =============
start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"💼 Starting Portfolio Service on port {SERVICE_PORT}")
    yield
    print(f"👋 Shutting down Portfolio Service")

app = FastAPI(
    title="Pearl-Portfolio API",
    version="2.0.0",
    description="Portfolio Analysis and Rebalancing Service",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 메트릭 미들웨어
@app.middleware("http")
async def track_metrics(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

# ============= 헬스체크 & 메트릭 =============

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="healthy",
        service=SERVICE_NAME,
        timestamp=datetime.now(),
        uptime=time.time() - start_time
    )

@app.get("/metrics", response_class=Response, tags=["Metrics"])
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ============= 포트폴리오 분석 엔드포인트 =============

@app.get("/portfolio/analysis", response_model=PortfolioAnalysis, tags=["Portfolio"])
async def get_portfolio_analysis(current_user: dict = Depends(get_current_user)):
    """포트폴리오 종합 분석"""
    user_id = current_user["user_id"]
    portfolio = PORTFOLIOS_DB.get(user_id)
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # 자산별 현재 가치 계산
    assets = []
    total_value = portfolio["cash_balance"]
    total_cost_basis = portfolio["cash_balance"]
    
    asset_class_values = {}
    
    for asset_data in portfolio["assets"]:
        current_price = get_current_price(asset_data["symbol"])
        current_value = current_price * asset_data["quantity"]
        total_value += current_value
        total_cost_basis += asset_data["cost_basis"]
        
        pnl = current_value - asset_data["cost_basis"]
        pnl_percentage = (pnl / asset_data["cost_basis"]) * 100 if asset_data["cost_basis"] > 0 else 0
        
        asset_class = asset_data.get("asset_class", AssetClass.STOCKS)
        asset_class_values[asset_class] = asset_class_values.get(asset_class, 0) + current_value
        
        assets.append(Asset(
            symbol=asset_data["symbol"],
            name=asset_data["name"],
            asset_class=asset_class,
            quantity=asset_data["quantity"],
            current_price=current_price,
            total_value=current_value,
            allocation_percentage=0,  # 나중에 계산
            cost_basis=asset_data["cost_basis"],
            unrealized_pnl=pnl,
            unrealized_pnl_percentage=pnl_percentage
        ))
    
    # Cash 추가
    asset_class_values[AssetClass.CASH] = portfolio["cash_balance"]
    
    # 할당 비율 계산
    for asset in assets:
        asset.allocation_percentage = (asset.total_value / total_value) * 100
    
    # 자산 클래스별 할당
    allocations = []
    target_allocation = ALLOCATION_STRATEGIES[RebalanceStrategy.BALANCED]
    
    for asset_class in AssetClass:
        current_value = asset_class_values.get(asset_class, 0)
        current_percentage = (current_value / total_value) * 100 if total_value > 0 else 0
        target_percentage = target_allocation.get(asset_class, 0)
        
        allocations.append(AssetAllocation(
            asset_class=asset_class,
            current_value=current_value,
            current_percentage=current_percentage,
            target_percentage=target_percentage,
            difference=current_percentage - target_percentage
        ))
    
    # 성과 및 리스크 지표
    performance = calculate_performance_metrics(portfolio)
    risk = calculate_risk_metrics(portfolio)
    
    total_pnl = total_value - total_cost_basis
    
    return PortfolioAnalysis(
        total_value=total_value,
        total_cost_basis=total_cost_basis,
        total_pnl=total_pnl,
        total_pnl_percentage=(total_pnl / total_cost_basis) * 100 if total_cost_basis > 0 else 0,
        assets=assets,
        allocation=allocations,
        performance=performance,
        risk=risk
    )

@app.get("/portfolio/assets", response_model=List[Asset], tags=["Portfolio"])
async def get_assets(
    asset_class: Optional[AssetClass] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """자산 목록 조회"""
    user_id = current_user["user_id"]
    portfolio = PORTFOLIOS_DB.get(user_id)
    
    if not portfolio:
        return []
    
    assets = []
    total_value = sum(
        get_current_price(a["symbol"]) * a["quantity"] 
        for a in portfolio["assets"]
    ) + portfolio["cash_balance"]
    
    for asset_data in portfolio["assets"]:
        if asset_class and asset_data.get("asset_class") != asset_class:
            continue
            
        current_price = get_current_price(asset_data["symbol"])
        current_value = current_price * asset_data["quantity"]
        pnl = current_value - asset_data["cost_basis"]
        
        assets.append(Asset(
            symbol=asset_data["symbol"],
            name=asset_data["name"],
            asset_class=asset_data.get("asset_class", AssetClass.STOCKS),
            quantity=asset_data["quantity"],
            current_price=current_price,
            total_value=current_value,
            allocation_percentage=(current_value / total_value) * 100,
            cost_basis=asset_data["cost_basis"],
            unrealized_pnl=pnl,
            unrealized_pnl_percentage=(pnl / asset_data["cost_basis"]) * 100
        ))
    
    return assets

@app.get("/portfolio/performance", response_model=PerformanceMetrics, tags=["Portfolio"])
async def get_performance(current_user: dict = Depends(get_current_user)):
    """수익률 및 성과 지표"""
    user_id = current_user["user_id"]
    portfolio = PORTFOLIOS_DB.get(user_id)
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    return calculate_performance_metrics(portfolio)

@app.get("/portfolio/risk", response_model=RiskMetrics, tags=["Portfolio"])
async def get_risk_metrics(current_user: dict = Depends(get_current_user)):
    """리스크 지표"""
    user_id = current_user["user_id"]
    portfolio = PORTFOLIOS_DB.get(user_id)
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    return calculate_risk_metrics(portfolio)

@app.post("/portfolio/rebalance", response_model=RebalanceResponse, tags=["Portfolio"])
async def rebalance_portfolio(
    request: RebalanceRequest,
    current_user: dict = Depends(get_current_user)
):
    """포트폴리오 리밸런싱 시뮬레이션"""
    if "trader" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trader role required for rebalancing"
        )
    
    user_id = current_user["user_id"]
    portfolio = PORTFOLIOS_DB.get(user_id)
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # 현재 할당 계산
    total_value = sum(
        get_current_price(a["symbol"]) * a["quantity"]
        for a in portfolio["assets"]
    ) + portfolio["cash_balance"]
    
    asset_class_values = {}
    for asset in portfolio["assets"]:
        ac = asset.get("asset_class", AssetClass.STOCKS)
        current_value = get_current_price(asset["symbol"]) * asset["quantity"]
        asset_class_values[ac] = asset_class_values.get(ac, 0) + current_value
    asset_class_values[AssetClass.CASH] = portfolio["cash_balance"]
    
    # 목표 할당 결정
    if request.strategy == RebalanceStrategy.CUSTOM:
        if not request.custom_allocations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom allocations required for custom strategy"
            )
        target_allocation = request.custom_allocations
    else:
        target_allocation = ALLOCATION_STRATEGIES.get(
            request.strategy,
            ALLOCATION_STRATEGIES[RebalanceStrategy.BALANCED]
        )
    
    # 현재 및 목표 할당 계산
    current_allocations = []
    target_allocations = []
    required_trades = []
    
    for asset_class in AssetClass:
        current_value = asset_class_values.get(asset_class, 0)
        current_pct = (current_value / total_value) * 100
        target_pct = target_allocation.get(asset_class, 0)
        target_value = (target_pct / 100) * total_value
        
        current_allocations.append(AssetAllocation(
            asset_class=asset_class,
            current_value=current_value,
            current_percentage=current_pct,
            target_percentage=target_pct,
            difference=current_pct - target_pct
        ))
        
        target_allocations.append(AssetAllocation(
            asset_class=asset_class,
            current_value=target_value,
            current_percentage=target_pct,
            target_percentage=target_pct,
            difference=0
        ))
        
        # 필요한 거래 계산
        value_diff = target_value - current_value
        if abs(value_diff) > 100:  # $100 이상 차이날 때만
            required_trades.append({
                "asset_class": asset_class.value,
                "action": "buy" if value_diff > 0 else "sell",
                "amount": abs(value_diff)
            })
    
    rebalance_count.labels(
        strategy=request.strategy.value,
        status="simulated"
    ).inc()
    
    return RebalanceResponse(
        rebalance_id=generate_rebalance_id(),
        strategy=request.strategy,
        current_allocations=current_allocations,
        target_allocations=target_allocations,
        required_trades=required_trades,
        estimated_cost=sum(t["amount"] * 0.001 for t in required_trades),  # 0.1% 수수료
        status="simulated"
    )

@app.get("/portfolio/insights", response_model=List[Insight], tags=["Portfolio"])
async def get_insights(current_user: dict = Depends(get_current_user)):
    """포트폴리오 인사이트 및 추천"""
    insights = []
    
    # 리밸런싱 필요 여부
    insights.append(Insight(
        type="rebalance",
        title="리밸런싱 권장",
        description="현재 포트폴리오가 목표 할당에서 10% 이상 벗어났습니다.",
        severity="warning",
        action_required=True
    ))
    
    # 리스크 경고
    insights.append(Insight(
        type="risk",
        title="높은 변동성 감지",
        description="최근 30일 변동성이 평균보다 50% 높습니다.",
        severity="info",
        action_required=False
    ))
    
    # 수익 기회
    insights.append(Insight(
        type="opportunity",
        title="수익 실현 기회",
        description="AAPL 포지션이 20% 이상 수익을 기록했습니다.",
        severity="info",
        action_required=False
    ))
    
    return insights

@app.get("/portfolio/history", response_model=List[HistoricalData], tags=["Portfolio"])
async def get_historical_data(
    days: int = Query(30, le=365),
    current_user: dict = Depends(get_current_user)
):
    """과거 포트폴리오 가치 추이"""
    history = []
    base_value = 100000  # 시작 가치
    
    for i in range(days):
        date_point = date.today() - timedelta(days=days-i)
        daily_return = random.uniform(-0.03, 0.03)
        base_value *= (1 + daily_return)
        
        history.append(HistoricalData(
            date=date_point,
            total_value=base_value,
            daily_return=daily_return * 100,
            cumulative_return=((base_value - 100000) / 100000) * 100
        ))
    
    return history

# ============= 관리자 엔드포인트 =============

@app.get("/admin/portfolio-stats", tags=["Admin"])
async def get_portfolio_stats(current_user: dict = Depends(get_current_user)):
    """포트폴리오 서비스 통계"""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    total_aum = sum(
        sum(get_current_price(a["symbol"]) * a["quantity"] for a in p["assets"]) + p["cash_balance"]
        for p in PORTFOLIOS_DB.values()
    )
    
    return {
        "total_portfolios": len(PORTFOLIOS_DB),
        "total_aum": total_aum,
        "average_portfolio_value": total_aum / len(PORTFOLIOS_DB) if PORTFOLIOS_DB else 0,
        "service_uptime": time.time() - start_time
    }

# ============= 에러 핸들러 =============

@app.exception_handler(404)
async def not_found(request, exc):
    return {"error": "Endpoint not found", "service": SERVICE_NAME}

@app.exception_handler(500)
async def internal_error(request, exc):
    return {"error": "Internal server error", "service": SERVICE_NAME}

# ============= 메인 실행 =============

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=True  # 개발 모드에서만
    )