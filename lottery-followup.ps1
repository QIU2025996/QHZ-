# 快乐8 追问触发脚本
# 用法：双击运行，输入追问内容，自动提交推送触发工作流

$ErrorActionPreference = "Stop"
Set-Location "F:\Agent"

# 检查分支
$branch = git branch --show-current
if ($branch -ne "feature/lottery-analysis-20260705") {
    Write-Host "当前分支: $branch"
    Write-Host "正在切换到 lottery 分支..."
    git checkout feature/lottery-analysis-20260705 2>&1 | Out-Null
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  快乐8 AI 协同分析 - 追问触发" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 显示当前问题
Write-Host "当前问题:" -ForegroundColor Yellow
Get-Content lottery_question.txt
Write-Host ""

# 输入追问
Write-Host "请输入你的追问（直接回车使用默认问题）:" -ForegroundColor Green
$question = Read-Host

if ([string]::IsNullOrWhiteSpace($question)) {
    $question = "基于上期分析规律，继续深入分析快乐8号码模式，给出下期推荐"
}

# 写文件
Set-Content -Path lottery_question.txt -Value $question -Encoding UTF8

# 显示最新期数
Write-Host ""
Write-Host "最新一期数据:" -ForegroundColor Yellow
Get-Content happy8_data.csv | Select-Object -Last 1

Write-Host ""
Write-Host "是否要添加新一期开奖号码？(y/N)" -ForegroundColor Green
$addNew = Read-Host

if ($addNew -eq "y" -or $addNew -eq "Y") {
    Write-Host "请输入期号（如 2026112）:" -ForegroundColor Green
    $period = Read-Host
    Write-Host "请输入日期（如 2026-05-02）:" -ForegroundColor Green
    $date = Read-Host
    Write-Host "请输入20个号码，用逗号分隔:" -ForegroundColor Green
    $nums = Read-Host

    $line = "$period,$date,$nums"
    Add-Content -Path happy8_data.csv -Value $line
    Write-Host "已添加: $line" -ForegroundColor Green
}

# Git 操作
Write-Host ""
Write-Host "提交并推送..." -ForegroundColor Yellow
git add happy8_data.csv lottery_question.txt
git commit -m "feat: update lottery question for follow-up analysis"
git push origin feature/lottery-analysis-20260705

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  推送成功！GitHub Actions 会自动触发" -ForegroundColor Green
Write-Host "  三个 AI 正在分析中，请刷新 PR 页面查看" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
