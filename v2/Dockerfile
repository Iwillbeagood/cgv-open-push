# ---- 프론트엔드 빌드 ----
FROM node:20-slim AS web
WORKDIR /web
# 기본 Slack 웹훅(선택). git엔 안 두고 빌드 시에만 주입 → 빌드 산출물(JS)에 포함됨.
ARG VITE_DEFAULT_WEBHOOK=""
ENV VITE_DEFAULT_WEBHOOK=$VITE_DEFAULT_WEBHOOK
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- 백엔드 런타임 (Chromium 사전설치된 공식 Playwright 이미지) ----
# playwright CDN 단일스트림 다운로드가 느린 회선에서 자주 멈춰서,
# Chromium+OS의존성이 미리 깔린 MS 공식 이미지를 베이스로 사용(레지스트리 레이어=재시도/재개 가능).
# 태그의 v1.62.0은 requirements.txt의 playwright 버전과 반드시 일치해야 함.
FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy AS runtime
WORKDIR /app

# 파이썬 의존성 (playwright 브라우저는 이미지에 이미 포함)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/src ./src
COPY --from=web /web/dist ./static

ENV PYTHONPATH=/app/src \
    CGV_STATIC_DIR=/app/static \
    CGV_DB_PATH=/data/cgv_push.db \
    CGV_POLL_INTERVAL=300 \
    CGV_HEADLESS=1

VOLUME ["/data"]
EXPOSE 8000
CMD ["python", "-m", "cgv_push.main"]
