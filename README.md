# Pearl-Invest Teleport Infrastructure v1.0

## 🎯 Overview

Pearl-Invest는 Teleport를 활용한 Zero Trust 접근 제어 시스템으로, Edge K3s Cluster에서 실행되는 마이크로서비스들을 안전하게 관리합니다.

### Architecture

```
Pearl-Invest Infrastructure
├── Cloud Control Plane (AWS EC2)
│   └── Teleport Cluster (teleport.pearlinvest.click)
└── Edge Cluster (Raspberry Pi)
    └── K3s Cluster
        ├── pearl-auth (인증 서비스)
        ├── pearl-trading (거래 서비스)
        └── pearl-portfolio (포트폴리오 서비스)
```

## 🚀 Features

- **Label 기반 접근 제어**: 서비스별 세분화된 권한 관리
- **세션 녹화 및 감사**: 모든 SSH 세션 자동 녹화 및 재생
- **Zero Trust Security**: 인증서 기반 보안 연결
- **Edge Computing**: 라즈베리파이 K3s 클러스터 활용
- **RBAC**: 역할 기반 접근 제어

## 📋 Prerequisites

- AWS EC2 인스턴스 (Ubuntu 22.04 LTS)
- 도메인 및 DNS 설정
- Raspberry Pi K3s Cluster
- Docker & Kubernetes 기본 지식

## 🔧 Installation

### 1. Teleport Cluster 설치 (AWS EC2)

```bash
# Teleport 설치
curl https://goteleport.com/static/install.sh | bash -s 14.0.0

# 설정 파일 생성
sudo teleport configure -o /etc/teleport.yaml \
  --cluster-name=teleport.pearlinvest.click \
  --public-addr=teleport.pearlinvest.click:443 \
  --acme-email=your-email@example.com \
  --acme

# 서비스 시작
sudo systemctl enable teleport
sudo systemctl start teleport

# Admin 사용자 생성
sudo tctl users add admin \
  --roles=editor,access,auditor \
  --logins=root,ubuntu,woosupar

# Edge Cluster 연결용 토큰 생성
sudo tctl tokens add --type=node --ttl=8760h
```

### 2. Edge Node 설정 (Raspberry Pi K3s)

각 마이크로서비스 Pod에 Teleport agent를 포함시킵니다.

#### Dockerfile
```dockerfile
FROM debian:slim
RUN apt-get update && apt-get install -y nginx supervisor curl
RUN curl https://goteleport.com/static/install.sh | bash -s 14.0.0
COPY teleport.yaml /etc/teleport.yaml
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
CMD ["/usr/bin/supervisord"]
```

#### teleport.yaml (각 서비스별)
```yaml
teleport:
  auth_token: "YOUR_JOIN_TOKEN"
  proxy_server: teleport.pearlinvest.click:443
  
ssh_service:
  enabled: yes
  labels:
    service: auth  # 또는 trading, portfolio
    env: production
```

#### Kubernetes Secret 설정
```bash
# 토큰을 Secret으로 저장
kubectl create secret generic teleport-token \
  --from-literal=token=YOUR_TOKEN \
  --from-literal=proxy=teleport.pearlinvest.click:443
```

## 👥 Role-Based Access Control

### 역할 정의

#### Developer Role (auth 서비스만 접근)
```yaml
kind: role
version: v7
metadata:
  name: developer
spec:
  allow:
    logins: ['ubuntu', 'woosupar']
    node_labels:
      'service': 'auth'
```

#### Trader Role (trading 서비스만 접근)
```yaml
kind: role
version: v7
metadata:
  name: trader
spec:
  allow:
    logins: ['ubuntu', 'woosupar']
    node_labels:
      'service': 'trading'
```

#### Admin Role (모든 서비스 접근)
```yaml
kind: role
version: v7
metadata:
  name: admin
spec:
  allow:
    logins: ['root', 'ubuntu', 'woosupar']
    node_labels:
      '*': '*'
```

### 사용자 생성 예시

```bash
# 개발자 (auth 서비스만)
sudo tctl users add lee --roles=developer --logins=ubuntu,woosupar

# 트레이더 (trading 서비스만)
sudo tctl users add kim --roles=trader --logins=ubuntu,woosupar

# 관리자 (모든 서비스)
sudo tctl users add admin --roles=admin --logins=root,ubuntu,woosupar
```

## 🎮 Usage

### CLI 접속
```bash
# 로그인
tsh login --proxy=teleport.pearlinvest.click --user=username

# 접근 가능한 노드 확인
tsh ls

# SSH 접속
tsh ssh ubuntu@pearl-auth
```

### 세션 녹화 재생
```bash
# 녹화된 세션 목록
tsh recordings ls

# 세션 재생
tsh play [SESSION_ID]
```

### Web UI 접속
브라우저에서 `https://teleport.pearlinvest.click` 접속

## 📁 Project Structure

```
pearl-invest-teleport/
├── cluster/
│   ├── teleport.yaml          # Cluster 설정
│   └── setup.sh               # 설치 스크립트
├── edge/
│   ├── Dockerfile             # Edge node 이미지
│   ├── teleport.yaml          # Node 설정 템플릿
│   ├── supervisord.conf       # Process 관리
│   └── k8s/
│       └── pearl-invest-msa.yaml  # K8s 배포 매니페스트
├── roles/
│   ├── developer.yaml         # 개발자 역할
│   ├── trader.yaml           # 트레이더 역할
│   └── admin.yaml            # 관리자 역할
└── README.md
```

## 🔍 Monitoring & Troubleshooting

### 로그 확인
```bash
# Cluster 로그
sudo journalctl -u teleport -f

# Pod 로그 (K3s)
kubectl logs -f deployment/pearl-auth
```

### 연결 상태 확인
```bash
# 노드 목록
sudo tctl nodes ls

# 토큰 목록
sudo tctl tokens ls

# 사용자 목록
sudo tctl users ls
```

### 일반적인 문제 해결

1. **세션 녹화가 표시되지 않을 때**
   ```bash
   sudo systemctl restart teleport
   ```

2. **노드가 연결되지 않을 때**
   ```bash
   # 토큰 재생성
   sudo tctl tokens add --type=node --ttl=8760h
   # K3s Secret 업데이트
   kubectl delete secret teleport-token
   kubectl create secret generic teleport-token --from-literal=token=NEW_TOKEN
   ```

3. **인증서 오류 발생 시**
   ```bash
   tsh logout
   tsh login --proxy=teleport.pearlinvest.click --user=username
   ```

## 📊 Performance Considerations

- EC2 인스턴스: t3.small 이상 권장
- 라즈베리파이: 4GB RAM 이상 권장
- 네트워크: 안정적인 인터넷 연결 필수
- 스토리지: 세션 녹화용 충분한 공간 확보

## 🔒 Security Best Practices

1. **정기적인 토큰 갱신**: 연 1회 이상
2. **최소 권한 원칙**: 필요한 서비스만 접근 허용
3. **2FA 필수 설정**: 모든 사용자에게 적용
4. **정기 감사**: 세션 녹화 주기적 검토
5. **백업**: 설정 파일 및 인증서 백업

## 🚧 Known Limitations (OSS Version)

- Web UI에서 타인 세션 재생 일부 제한
- 동적 권한 할당 불가
- OS 계정 수동 관리 필요
- Advanced RBAC 기능 제한

## 🗺️ Roadmap

- [ ] v1.1: 모니터링 대시보드 추가 (Grafana)
- [ ] v1.2: GitOps 워크플로우 구현 (ArgoCD)
- [ ] v1.3: 자동 백업 시스템 구축
- [ ] v2.0: Multi-cluster 지원

## 📝 License

MIT License

## 🤝 Contributing

Issues와 Pull Requests를 환영합니다!

## 📧 Contact

- Email: grademe12@gmail.com
- GitHub: [pearl-invest-teleport](https://github.com/yourusername/pearl-invest-teleport)

---

**Version**: 1.0.0  
**Last Updated**: 2024-09-06  
**Maintainer**: Pearl-Invest Team
