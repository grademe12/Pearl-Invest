"""
Pearl-Invest Auth Service API
인증 및 사용자 관리 서비스
"""

import os
import time
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import uvicorn

# ============= 설정 =============
SERVICE_NAME = "auth"
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8080"))
JWT_SECRET = os.getenv("JWT_SECRET", "pearl-invest-secret-key-change-in-production")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

# ============= Prometheus 메트릭 =============
request_count = Counter(
    'auth_requests_total', 
    'Total requests to auth service',
    ['method', 'endpoint', 'status']
)
request_duration = Histogram(
    'auth_request_duration_seconds',
    'Request duration in auth service',
    ['method', 'endpoint']
)
login_attempts = Counter(
    'auth_login_attempts_total',
    'Total login attempts',
    ['status']  # success/failure
)

# ============= Pydantic 모델 =============
class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime
    uptime: float

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds
    user_id: str
    username: str
    roles: List[str]

class UserProfile(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: Optional[str]
    roles: List[str]
    created_at: datetime
    last_login: Optional[datetime]

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

# ============= 임시 데이터베이스 (실제로는 DB 사용) =============
# 데모용 사용자 데이터
USERS_DB: Dict[str, dict] = {
    "admin": {
        "user_id": "usr_001",
        "password": "admin123",  # 실제로는 해시 저장
        "email": "admin@pearlinvest.com",
        "full_name": "Admin User",
        "roles": ["admin", "trader", "viewer"],
        "created_at": datetime.now(),
        "last_login": None
    },
    "trader": {
        "user_id": "usr_002",
        "password": "trader123",
        "email": "trader@pearlinvest.com",
        "full_name": "Trader Kim",
        "roles": ["trader", "viewer"],
        "created_at": datetime.now(),
        "last_login": None
    },
    "viewer": {
        "user_id": "usr_003",
        "password": "viewer123",
        "email": "viewer@pearlinvest.com",
        "full_name": "Viewer Lee",
        "roles": ["viewer"],
        "created_at": datetime.now(),
        "last_login": None
    }
}

# 활성 토큰 저장 (실제로는 Redis 사용)
ACTIVE_TOKENS: Dict[str, dict] = {}

# ============= 유틸리티 함수 =============
def generate_token() -> str:
    """안전한 랜덤 토큰 생성"""
    return secrets.token_urlsafe(32)

def create_access_token(user_data: dict) -> tuple[str, datetime]:
    """액세스 토큰 생성"""
    token = generate_token()
    expiry = datetime.now() + timedelta(hours=JWT_EXPIRY_HOURS)
    
    ACTIVE_TOKENS[token] = {
        "user_id": user_data["user_id"],
        "username": user_data.get("username"),
        "roles": user_data.get("roles", []),
        "expires_at": expiry
    }
    
    return token, expiry

def verify_token(token: str) -> Optional[dict]:
    """토큰 검증"""
    if token in ACTIVE_TOKENS:
        token_data = ACTIVE_TOKENS[token]
        if datetime.now() < token_data["expires_at"]:
            return token_data
        else:
            # 만료된 토큰 제거
            del ACTIVE_TOKENS[token]
    return None

# ============= 의존성 =============
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """현재 인증된 사용자 가져오기"""
    token = credentials.credentials
    user_data = verify_token(token)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_data

# ============= FastAPI 앱 설정 =============
start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🔐 Starting Auth Service on port {SERVICE_PORT}")
    yield
    print(f"👋 Shutting down Auth Service")

app = FastAPI(
    title="Pearl-Auth API",
    version="2.0.0",
    description="Authentication and User Management Service",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인으로
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

# ============= 헬스체크 & 메트릭 엔드포인트 =============

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """헬스체크 엔드포인트"""
    return HealthResponse(
        status="healthy",
        service=SERVICE_NAME,
        timestamp=datetime.now(),
        uptime=time.time() - start_time
    )

@app.get("/metrics", response_class=Response, tags=["Metrics"])
async def metrics():
    """Prometheus 메트릭 엔드포인트"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ============= 인증 엔드포인트 =============

@app.post("/auth/register", response_model=TokenResponse, tags=["Authentication"])
async def register(request: RegisterRequest):
    """새 사용자 등록"""
    # 중복 확인
    if request.username in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # 새 사용자 생성
    new_user = {
        "user_id": f"usr_{len(USERS_DB) + 1:03d}",
        "password": request.password,  # 실제로는 해시 처리
        "email": request.email,
        "full_name": request.full_name,
        "roles": ["viewer"],  # 기본 역할
        "created_at": datetime.now(),
        "last_login": None
    }
    
    USERS_DB[request.username] = new_user
    
    # 자동 로그인
    token, expiry = create_access_token({
        **new_user,
        "username": request.username
    })
    
    return TokenResponse(
        access_token=token,
        expires_in=JWT_EXPIRY_HOURS * 3600,
        user_id=new_user["user_id"],
        username=request.username,
        roles=new_user["roles"]
    )

@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
async def login(request: LoginRequest):
    """사용자 로그인"""
    # 사용자 확인
    user = USERS_DB.get(request.username)
    
    if not user or user["password"] != request.password:
        login_attempts.labels(status="failure").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # 로그인 시간 업데이트
    user["last_login"] = datetime.now()
    
    # 토큰 생성
    token, expiry = create_access_token({
        **user,
        "username": request.username
    })
    
    login_attempts.labels(status="success").inc()
    
    return TokenResponse(
        access_token=token,
        expires_in=JWT_EXPIRY_HOURS * 3600,
        user_id=user["user_id"],
        username=request.username,
        roles=user["roles"]
    )

@app.post("/auth/logout", tags=["Authentication"])
async def logout(current_user: dict = Depends(get_current_user)):
    """사용자 로그아웃"""
    # 토큰 무효화 (실제로는 토큰을 찾아서 제거)
    tokens_to_remove = []
    for token, data in ACTIVE_TOKENS.items():
        if data["user_id"] == current_user["user_id"]:
            tokens_to_remove.append(token)
    
    for token in tokens_to_remove:
        del ACTIVE_TOKENS[token]
    
    return {"message": "Successfully logged out"}

@app.post("/auth/refresh", response_model=TokenResponse, tags=["Authentication"])
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """토큰 갱신"""
    # 현재 사용자 정보로 새 토큰 생성
    username = current_user["username"]
    user = USERS_DB.get(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    token, expiry = create_access_token({
        **user,
        "username": username
    })
    
    return TokenResponse(
        access_token=token,
        expires_in=JWT_EXPIRY_HOURS * 3600,
        user_id=user["user_id"],
        username=username,
        roles=user["roles"]
    )

# ============= 사용자 관리 엔드포인트 =============

@app.get("/user/profile", response_model=UserProfile, tags=["User Management"])
async def get_profile(current_user: dict = Depends(get_current_user)):
    """현재 사용자 프로필 조회"""
    username = current_user["username"]
    user = USERS_DB.get(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserProfile(
        user_id=user["user_id"],
        username=username,
        email=user["email"],
        full_name=user.get("full_name"),
        roles=user["roles"],
        created_at=user["created_at"],
        last_login=user.get("last_login")
    )

@app.put("/user/profile", response_model=UserProfile, tags=["User Management"])
async def update_profile(
    email: Optional[EmailStr] = None,
    full_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """사용자 프로필 업데이트"""
    username = current_user["username"]
    user = USERS_DB.get(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 업데이트
    if email:
        user["email"] = email
    if full_name:
        user["full_name"] = full_name
    
    return UserProfile(
        user_id=user["user_id"],
        username=username,
        email=user["email"],
        full_name=user.get("full_name"),
        roles=user["roles"],
        created_at=user["created_at"],
        last_login=user.get("last_login")
    )

@app.post("/user/change-password", tags=["User Management"])
async def change_password(
    request: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user)
):
    """비밀번호 변경"""
    username = current_user["username"]
    user = USERS_DB.get(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 현재 비밀번호 확인
    if user["password"] != request.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # 비밀번호 변경
    user["password"] = request.new_password
    
    return {"message": "Password changed successfully"}

@app.get("/user/sessions", tags=["User Management"])
async def get_active_sessions(current_user: dict = Depends(get_current_user)):
    """현재 활성 세션 조회"""
    user_sessions = []
    for token, data in ACTIVE_TOKENS.items():
        if data["user_id"] == current_user["user_id"]:
            user_sessions.append({
                "expires_at": data["expires_at"],
                "is_current": data.get("username") == current_user.get("username")
            })
    
    return {"sessions": user_sessions, "total": len(user_sessions)}

# ============= 관리자 전용 엔드포인트 =============

@app.get("/admin/users", tags=["Admin"])
async def list_users(current_user: dict = Depends(get_current_user)):
    """모든 사용자 목록 조회 (관리자 전용)"""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    users = []
    for username, user_data in USERS_DB.items():
        users.append({
            "username": username,
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "roles": user_data["roles"],
            "created_at": user_data["created_at"],
            "last_login": user_data.get("last_login")
        })
    
    return {"users": users, "total": len(users)}

@app.get("/admin/stats", tags=["Admin"])
async def get_stats(current_user: dict = Depends(get_current_user)):
    """서비스 통계 (관리자 전용)"""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return {
        "total_users": len(USERS_DB),
        "active_sessions": len(ACTIVE_TOKENS),
        "service_uptime": time.time() - start_time,
        "roles_distribution": {
            "admin": sum(1 for u in USERS_DB.values() if "admin" in u["roles"]),
            "trader": sum(1 for u in USERS_DB.values() if "trader" in u["roles"]),
            "viewer": sum(1 for u in USERS_DB.values() if "viewer" in u["roles"])
        }
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