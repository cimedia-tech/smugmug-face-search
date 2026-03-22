# ============================================================
# SmugMug Face Search - Deployment & DB Maintenance Script
# Usage: .\deploy.ps1 -CommitMsg "Your commit message"
# ============================================================

param(
    [string]$CommitMsg = "Add face search by image upload"
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "`n▶ $msg" -ForegroundColor Cyan
}

function Write-Success($msg) {
    Write-Host "  ✓ $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "  ⚠ $msg" -ForegroundColor Yellow
}

# ── Step 1: Cancel stale indexing jobs ──────────────────────
Write-Step "Step 1: Cancel stale indexing jobs in Supabase"
Write-Warn "Run this SQL in your Supabase Dashboard → SQL Editor:"
Write-Host @"

  UPDATE indexing_jobs
  SET    status     = 'cancelled',
         updated_at = NOW()
  WHERE  status IN ('pending', 'running');

"@ -ForegroundColor DarkYellow
Read-Host "Press ENTER once you've run the SQL (or skip if not needed)"

# ── Step 2: Git commit & push ────────────────────────────────
Write-Step "Step 2: Git commit & push"

git add -A
if ($LASTEXITCODE -ne 0) { throw "git add failed" }
Write-Success "Staged all changes"

git commit -m $CommitMsg
if ($LASTEXITCODE -ne 0) { throw "git commit failed (nothing to commit?)" }
Write-Success "Committed: $CommitMsg"

git push
if ($LASTEXITCODE -ne 0) { throw "git push failed" }
Write-Success "Pushed to remote — Vercel deploy triggered"

# ── Step 3: Wait for Vercel ──────────────────────────────────
Write-Step "Step 3: Waiting for Vercel to deploy..."
Write-Warn "Monitor at: https://vercel.com/dashboard"
Read-Host "Press ENTER once Vercel deploy shows ✅ Ready"

# ── Step 4: Post-deploy SQL ──────────────────────────────────
Write-Step "Step 4: Post-deploy — create search_jobs table (if not exists)"
Write-Warn "Run this SQL in your Supabase Dashboard → SQL Editor:"
Write-Host @"

  -- Paste contents of: supabase_search_jobs.sql

"@ -ForegroundColor DarkYellow

$sqlPath = Join-Path $PSScriptRoot "supabase_search_jobs.sql"
if (Test-Path $sqlPath) {
    Write-Host "  SQL file ready at: $sqlPath" -ForegroundColor Gray
    Start-Process notepad $sqlPath    # opens SQL file for easy copy
}

Read-Host "Press ENTER once post-deploy SQL is done"

# ── Done ─────────────────────────────────────────────────────
Write-Host "`n🚀 Deployment complete!" -ForegroundColor Green
