"""
Pearl-Invest Trading Service API
거래 및 주문 관리 서비스
"""

import os
import time
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import uvicorn

# ============= 설정 =============
SERVICE_NAME = "trading"
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8082"))
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://pearl-auth-internal:8080")

# ============= Prometheus 메트릭 =============
request_count = Counter(
    'trading_requests_total', 
    'Total requests to trading service',
    ['method', 'endpoint', 'status']
)
request_duration = Histogram(
    'trading_request_duration_seconds',
    'Request duration in trading service',
    ['method', 'endpoint']
)
order_count = Counter(
    'trading_orders_total',
    'Total orders placed',
    ['order_type', 'side', 'status']
)

# ============= Enums =============
class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LIMIT = "stop_limit"

class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

# ============= Pydantic 모델 =============
class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime
    uptime: float

class Position(BaseModel):
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    pnl: float
    pnl_percentage: float

class OrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    side: OrderSide
    order_type: OrderType
    quantity: int = Field(..., gt=0)
    price: Optional[float] = Field(None, gt=0)
    stop_price: Optional[float] = Field(None, gt=0)
    
    @validator('price')
    def price_required_for_limit(cls, v, values):
        if values.get('order_type') in [OrderType.LIMIT, OrderType.STOP_LIMIT] and v is None:
            raise ValueError('Price is required for limit orders')
        return v

class OrderResponse(BaseModel):
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float]
    status: OrderStatus
    created_at: datetime
    filled_at: Optional[datetime]
    filled_quantity: int
    average_fill_price: Optional[float]

class Transaction(BaseModel):
    transaction_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    fee: float
    timestamp: datetime

class PortfolioSummary(BaseModel):
    total_value: float
    cash_balance: float
    positions_value: float
    daily_pnl: float
    daily_pnl_percentage: float
    positions: List[Position]

class MarketData(BaseModel):
    symbol: str
    last_price: float
    bid: float
    ask: float
    volume: int
    daily_change: float
    daily_change_percentage: float

# ============= 임시 데이터베이스 =============
# 데모용 포트폴리오 데이터
PORTFOLIOS: Dict[str, dict] = {
    "usr_001": {  # admin
        "cash_balance": 100000.0,
        "positions": {
            "AAPL": {"quantity": 100, "avg_price": 150.0},
            "GOOGL": {"quantity": 50, "avg_price": 2500.0},
            "TSLA": {"quantity": 75, "avg_price": 200.0}
        }
    },
    "usr_002": {  # trader
        "cash_balance": 50000.0,
        "positions": {
            "MSFT": {"quantity": 200, "avg_price": 300.0},
            "AMZN": {"quantity": 30, "avg_price": 3000.0}
        }
    }
}

# 주문 내역
ORDERS: List[dict] = []
TRANSACTIONS: List[dict] = []

# 가상의 시장 데이터
MARKET_PRICES = {
    "AAPL": 155.0,
    "GOOGL": 2600.0,
    "TSLA": 220.0,
    "MSFT": 320.0,
    "AMZN": 3200.0,
    "NVDA": 450.0,
    "META": 350.0
}

# ============= 유틸리티 함수 =============
def generate_order_id() -> str:
    return f"ORD-{int(time.time())}-{random.randint(1000, 9999)}"

def generate_transaction_id() -> str:
    return f"TXN-{int(time.time())}-{random.randint(1000, 9999)}"

def get_market_price(symbol: str) -> float:
    """현재 시장 가격 조회 (시뮬레이션)"""
    base_price = MARKET_PRICES.get(symbol, 100.0)
    # 약간의 랜덤 변동 추가
    return base_price * (1 + random.uniform(-0.01, 0.01))

def calculate_pnl(positions: dict, symbol: str) -> tuple[float, float]:
    """손익 계산"""
    if symbol not in positions:
        return 0.0, 0.0
    
    position = positions[symbol]
    current_price = get_market_price(symbol)
    cost_basis = position["quantity"] * position["avg_price"]
    current_value = position["quantity"] * current_price
    pnl = current_value - cost_basis
    pnl_percentage = (pnl / cost_basis) * 100 if cost_basis > 0 else 0
    
    return pnl, pnl_percentage

# ============= 의존성 =============
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Auth 서비스와 연동하여 사용자 검증 (간단 버전)"""
    # 실제로는 Auth 서비스 API 호출해야 함
    # 여기서는 데모용으로 간단히 처리
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # 데모: 토큰에서 사용자 ID 추출 (실제로는 Auth 서비스 호출)
    return {
        "user_id": "usr_001",  # 데모용
        "username": "admin",
        "roles": ["trader"]
    }

async def check_trader_role(current_user: dict = Depends(get_current_user)) -> dict:
    """트레이더 권한 확인"""
    if "trader" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trader role required"
        )
    return current_user

# ============= FastAPI 앱 설정 =============
start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"📈 Starting Trading Service on port {SERVICE_PORT}")
    yield
    print(f"👋 Shutting down Trading Service")

app = FastAPI(
    title="Pearl-Trading API",
    version="2.0.0",
    description="Trading and Order Management Service",
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

# ============= 거래 엔드포인트 =============

@app.get("/trading/portfolio", response_model=PortfolioSummary, tags=["Trading"])
async def get_portfolio(current_user: dict = Depends(get_current_user)):
    """포트폴리오 조회"""
    user_id = current_user["user_id"]
    portfolio = PORTFOLIOS.get(user_id, {"cash_balance": 0, "positions": {}})
    
    positions = []
    total_positions_value = 0
    total_pnl = 0
    
    for symbol, pos_data in portfolio["positions"].items():
        current_price = get_market_price(symbol)
        position_value = pos_data["quantity"] * current_price
        pnl, pnl_pct = calculate_pnl(portfolio["positions"], symbol)
        
        positions.append(Position(
            symbol=symbol,
            quantity=pos_data["quantity"],
            avg_price=pos_data["avg_price"],
            current_price=current_price,
            pnl=pnl,
            pnl_percentage=pnl_pct
        ))
        
        total_positions_value += position_value
        total_pnl += pnl
    
    total_value = portfolio["cash_balance"] + total_positions_value
    
    return PortfolioSummary(
        total_value=total_value,
        cash_balance=portfolio["cash_balance"],
        positions_value=total_positions_value,
        daily_pnl=total_pnl,
        daily_pnl_percentage=(total_pnl / total_value * 100) if total_value > 0 else 0,
        positions=positions
    )

@app.post("/trading/order", response_model=OrderResponse, tags=["Trading"])
async def place_order(
    order: OrderRequest,
    current_user: dict = Depends(check_trader_role)
):
    """주문 실행"""
    user_id = current_user["user_id"]
    portfolio = PORTFOLIOS.get(user_id, {"cash_balance": 0, "positions": {}})
    
    # 주문 검증
    if order.side == OrderSide.BUY:
        required_cash = order.quantity * (order.price or get_market_price(order.symbol))
        if required_cash > portfolio["cash_balance"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient funds"
            )
    elif order.side == OrderSide.SELL:
        position = portfolio["positions"].get(order.symbol, {})
        if position.get("quantity", 0) < order.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient position"
            )
    
    # 주문 생성
    order_id = generate_order_id()
    new_order = {
        "order_id": order_id,
        "user_id": user_id,
        "symbol": order.symbol,
        "side": order.side,
        "order_type": order.order_type,
        "quantity": order.quantity,
        "price": order.price,
        "status": OrderStatus.PENDING,
        "created_at": datetime.now(),
        "filled_at": None,
        "filled_quantity": 0,
        "average_fill_price": None
    }
    
    # 시장가 주문은 즉시 체결
    if order.order_type == OrderType.MARKET:
        fill_price = get_market_price(order.symbol)
        new_order["status"] = OrderStatus.FILLED
        new_order["filled_at"] = datetime.now()
        new_order["filled_quantity"] = order.quantity
        new_order["average_fill_price"] = fill_price
        
        # 포트폴리오 업데이트
        if order.side == OrderSide.BUY:
            portfolio["cash_balance"] -= order.quantity * fill_price
            if order.symbol not in portfolio["positions"]:
                portfolio["positions"][order.symbol] = {"quantity": 0, "avg_price": 0}
            
            pos = portfolio["positions"][order.symbol]
            total_cost = (pos["quantity"] * pos["avg_price"]) + (order.quantity * fill_price)
            pos["quantity"] += order.quantity
            pos["avg_price"] = total_cost / pos["quantity"]
            
        else:  # SELL
            portfolio["cash_balance"] += order.quantity * fill_price
            portfolio["positions"][order.symbol]["quantity"] -= order.quantity
        
        # 거래 기록
        TRANSACTIONS.append({
            "transaction_id": generate_transaction_id(),
            "order_id": order_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "price": fill_price,
            "fee": order.quantity * fill_price * 0.001,  # 0.1% 수수료
            "timestamp": datetime.now()
        })
    
    ORDERS.append(new_order)
    
    order_count.labels(
        order_type=order.order_type.value,
        side=order.side.value,
        status=new_order["status"].value
    ).inc()
    
    return OrderResponse(**new_order)

@app.get("/trading/orders", response_model=List[OrderResponse], tags=["Trading"])
async def get_orders(
    status: Optional[OrderStatus] = Query(None),
    symbol: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    current_user: dict = Depends(get_current_user)
):
    """주문 내역 조회"""
    user_orders = [o for o in ORDERS if o["user_id"] == current_user["user_id"]]
    
    if status:
        user_orders = [o for o in user_orders if o["status"] == status]
    if symbol:
        user_orders = [o for o in user_orders if o["symbol"] == symbol]
    
    # 최신순 정렬
    user_orders.sort(key=lambda x: x["created_at"], reverse=True)
    
    return [OrderResponse(**o) for o in user_orders[:limit]]

@app.delete("/trading/order/{order_id}", tags=["Trading"])
async def cancel_order(
    order_id: str,
    current_user: dict = Depends(check_trader_role)
):
    """주문 취소"""
    order = next((o for o in ORDERS if o["order_id"] == order_id and o["user_id"] == current_user["user_id"]), None)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order["status"] != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel filled or cancelled order"
        )
    
    order["status"] = OrderStatus.CANCELLED
    
    return {"message": "Order cancelled successfully", "order_id": order_id}

@app.get("/trading/transactions", response_model=List[Transaction], tags=["Trading"])
async def get_transactions(
    symbol: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    current_user: dict = Depends(get_current_user)
):
    """거래 내역 조회"""
    user_orders = [o["order_id"] for o in ORDERS if o["user_id"] == current_user["user_id"]]
    user_transactions = [t for t in TRANSACTIONS if t["order_id"] in user_orders]
    
    if symbol:
        user_transactions = [t for t in user_transactions if t["symbol"] == symbol]
    
    # 최신순 정렬
    user_transactions.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return [Transaction(**t) for t in user_transactions[:limit]]

# ============= 시장 데이터 =============

@app.get("/trading/market/{symbol}", response_model=MarketData, tags=["Market Data"])
async def get_market_data(symbol: str):
    """시장 데이터 조회"""
    if symbol not in MARKET_PRICES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Symbol not found"
        )
    
    current_price = get_market_price(symbol)
    base_price = MARKET_PRICES[symbol]
    
    return MarketData(
        symbol=symbol,
        last_price=current_price,
        bid=current_price * 0.999,
        ask=current_price * 1.001,
        volume=random.randint(1000000, 10000000),
        daily_change=current_price - base_price,
        daily_change_percentage=((current_price - base_price) / base_price) * 100
    )

@app.get("/trading/markets", response_model=List[MarketData], tags=["Market Data"])
async def get_all_markets():
    """전체 시장 데이터"""
    markets = []
    for symbol in MARKET_PRICES.keys():
        current_price = get_market_price(symbol)
        base_price = MARKET_PRICES[symbol]
        
        markets.append(MarketData(
            symbol=symbol,
            last_price=current_price,
            bid=current_price * 0.999,
            ask=current_price * 1.001,
            volume=random.randint(1000000, 10000000),
            daily_change=current_price - base_price,
            daily_change_percentage=((current_price - base_price) / base_price) * 100
        ))
    
    return markets

# ============= 관리자 엔드포인트 =============

@app.get("/admin/trading-stats", tags=["Admin"])
async def get_trading_stats(current_user: dict = Depends(get_current_user)):
    """거래 통계 (관리자용)"""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return {
        "total_orders": len(ORDERS),
        "total_transactions": len(TRANSACTIONS),
        "active_users": len(PORTFOLIOS),
        "order_stats": {
            "pending": sum(1 for o in ORDERS if o["status"] == OrderStatus.PENDING),
            "filled": sum(1 for o in ORDERS if o["status"] == OrderStatus.FILLED),
            "cancelled": sum(1 for o in ORDERS if o["status"] == OrderStatus.CANCELLED)
        },
        "service_uptime": time.time() - start_time
    }

# ============= 메인 실행 =============

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=True
    )