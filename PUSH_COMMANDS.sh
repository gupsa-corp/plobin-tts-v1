#!/bin/bash

echo "🚀 GitHub 리포지토리에 코드 업로드 스크립트"
echo "============================================"

echo "1. 현재 Git 상태 확인..."
git status

echo ""
echo "2. 원격 저장소 확인..."
git remote -v

echo ""
echo "3. GitHub에 푸시 시도..."
git push -u origin master

echo ""
echo "✅ 업로드 완료!"
echo "리포지토리 URL: https://github.com/gupsa/plobin-tts-v1"