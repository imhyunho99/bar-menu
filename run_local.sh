#!/bin/bash

# 종료 시 백그라운드 프로세스 자동 정리
trap 'kill $(jobs -p) 2>/dev/null' EXIT

echo "========================================="
echo "       bar-menu 로컬 실행 스크립트       "
echo "========================================="

# 백엔드 실행
echo "1. Django 백엔드 서버 기동 중 (Port: 8000)..."
cd backend/menu_project
../../venv/bin/python manage.py runserver 8000 &
BACKEND_PID=$!

# 프론트엔드 실행
echo "2. Next.js 프론트엔드 개발 서버 기동 중 (Port: 3000)..."
cd ../../frontend
npm run dev &
FRONTEND_PID=$!

echo "-----------------------------------------"
echo "서버 실행 완료! 브라우저에서 아래 주소로 접속해 주세요."
echo "▶ 프론트엔드 (고객 메뉴판): http://localhost:3000"
echo "▶ 백엔드 커스텀 관리자: http://localhost:8000/[restaurantSlug]/admin/login/"
echo "   (기존 데이터 예시 Slug: bid, cafe 등)"
echo "▶ Django 내장 DB 관리자: http://localhost:8000/admin/"
echo "-----------------------------------------"
echo "작업을 종료하려면 Ctrl + C 를 누르세요."

# 백그라운드 프로세스가 끝날 때까지 대기
wait
