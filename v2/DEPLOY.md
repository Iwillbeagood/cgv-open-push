# 배포 가이드 — Oracle Cloud Always Free (24시간 무료)

이 앱을 Oracle Cloud의 **평생 무료(Always Free)** VM에서 Docker로 상시 실행하는 방법.
앱은 가벼워서(평소 CPU~0%, 5분마다 크롤링) 무료 사양으로 충분하다.

## 1. Oracle Cloud 계정 + 무료 VM 만들기

1. https://www.oracle.com/kr/cloud/free/ 에서 가입 (카드 등록 필요하지만 Always Free 리소스는 **과금 안 됨**).
2. 콘솔 → **Compute → Instances → Create Instance**
   - **Image**: Ubuntu 22.04 (또는 24.04)
   - **Shape**: `VM.Standard.A1.Flex` (Ampere ARM) — **1 OCPU / 6GB RAM** 정도로 지정 (Always Free 한도: 4 OCPU·24GB)
     - A1이 용량 부족이면 `VM.Standard.E2.1.Micro`(AMD, 1GB)도 가능. 이땐 RAM이 빠듯하니 아래 "저사양 팁" 참고.
   - **SSH 키**: 콘솔에서 키페어 생성 후 private key 저장(로컬 `~/.ssh/`).
3. 생성되면 **Public IP** 확인.

## 2. 포트 8000 열기 (2군데 모두)

**(a) Oracle 보안 목록(Security List) 인그레스 규칙 추가**
- 콘솔 → 인스턴스의 VCN → Security List → **Add Ingress Rule**
  - Source CIDR: **본인 집 IP/32** (권장, 예: `123.45.67.89/32`) — 이 앱은 로그인이 없으므로 전체 공개(`0.0.0.0/0`)는 비권장.
  - Protocol: TCP, Destination Port: `8000`

**(b) VM 내부 방화벽 (Ubuntu, iptables)**
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save   # 재부팅 후에도 유지
```

## 3. Docker 설치 (SSH 접속 후)

```bash
ssh -i ~/.ssh/<your_key> ubuntu@<PUBLIC_IP>

# Docker + compose 설치
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # 또는 재로그인
```

## 4. 코드 올리기

**방법 A — 로컬 맥북에서 rsync (git 불필요, 권장)**
로컬(맥북)에서:
```bash
cd ~/Documents/python/cgv-open-push
rsync -av --exclude '.venv' --exclude 'node_modules' --exclude 'dist' \
  --exclude '*.db' --exclude '.git' \
  v2/ ubuntu@<PUBLIC_IP>:~/cgv-open-push/
```

**방법 B — 본인 GitHub 비공개 저장소에 올린 뒤 clone**
```bash
# VM에서
git clone https://github.com/<you>/<repo>.git cgv-open-push
```

## 5. 실행

```bash
cd ~/cgv-open-push        # (방법 A면 v2 내용이 여기에 있음)
docker compose up -d --build   # 최초 빌드는 몇 분 소요(Chromium 다운로드)
docker compose logs -f          # "폴러 시작 (주기 300s)" 뜨면 정상
```

- 접속: `http://<PUBLIC_IP>:8000`
- 데이터(SQLite)는 `cgv-data` 볼륨에 영속. 재시작/재부팅해도 구독 유지.
- 부팅 시 자동 시작: compose에 `restart: unless-stopped` 이미 설정됨. VM이 켜지면 컨테이너도 자동 실행.

## 폴링 주기 바꾸기
`docker-compose.yml`의 `CGV_POLL_INTERVAL`(초) 수정 후 `docker compose up -d`.

## 저사양(E2.1.Micro, 1GB RAM) 팁
- 스왑 2GB 추가:
  ```bash
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  ```

## 보안 메모
- 이 앱은 인증이 없다. 반드시 **보안 목록 Source를 본인 IP로 제한**하거나, 더 안전하게는 **Tailscale(무료)** 로 사설 접속만 허용하는 것을 권장.
- Slack Webhook URL은 브라우저(localStorage)에만 저장되고 서버 코드/이미지에는 없다.
