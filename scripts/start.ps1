# FastAPI Backend 启动脚本
# 使用方法: .\scripts\start.ps1

Write-Host "🚀 启动 LangChain Agent FastAPI 服务..." -ForegroundColor Green
Write-Host ""

# 切换到项目根目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# 检查 .env 文件
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  警告: .env 文件不存在" -ForegroundColor Yellow
    Write-Host "请创建 .env 文件并添加 OPENAI_API_KEY" -ForegroundColor Yellow
    Write-Host ""
}

# 显示环境信息
Write-Host "📦 使用 UV 虚拟环境" -ForegroundColor Cyan
Write-Host ""

# 启动服务
Write-Host "🌐 启动 FastAPI 服务在 http://localhost:8000" -ForegroundColor Green
Write-Host "📚 API 文档: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "❤️  健康检查: http://localhost:8000/health" -ForegroundColor Green
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
