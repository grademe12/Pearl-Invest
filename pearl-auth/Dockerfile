# 멀티스테이지 빌드로 이미지 크기 최소화
# Stage 1: Builder
FROM python:3.11-slim AS builder

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 빌드 도구 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# --- 🔻 변경점 1: venv 생성 및 PATH 설정 ---
# 가상 환경 생성
RUN python -m venv /opt/venv
# 가상 환경을 활성화하기 위해 PATH 환경 변수 설정
ENV PATH="/opt/venv/bin:$PATH"

# pip 업그레이드
RUN pip install --upgrade pip

# 의존성 파일 복사
COPY requirements.txt .

# --- 🔻 변경점 2: venv에 의존성 설치 ---
# 가상 환경에 의존성 설치 (--user 플래그 제거)
RUN pip install --no-cache-dir -r requirements.txt


# Stage 2: Runtime
FROM python:3.11-slim

# 보안을 위한 non-root 사용자 생성
RUN useradd -m -u 1000 appuser

# 작업 디렉토리 설정
WORKDIR /app

# --- 🔻 변경점 3: venv 통째로 복사 ---
# builder 스테이지에서 생성된 가상 환경 전체를 복사
COPY --from=builder /opt/venv /opt/venv

# 애플리케이션 코드 복사
COPY --chown=appuser:appuser . .

# --- 🔻 변경점 4: PATH 환경변수 다시 설정 ---
# 최종 이미지에서도 가상 환경의 PATH를 설정
ENV PATH="/opt/venv/bin:$PATH"

# 사용자 전환
USER appuser

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# 포트 노출
EXPOSE 8080

# 애플리케이션 실행 (venv의 uvicorn이 실행됨)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
