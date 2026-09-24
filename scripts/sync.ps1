# Phát hành skill/agent chung sang mức user, để mọi repo trên máy này thấy.
#
#   pwsh scripts/sync.ps1            chép (mặc định)
#   pwsh scripts/sync.ps1 -Check     chỉ báo lệch, không chép
#   pwsh scripts/sync.ps1 -Prune     xoá thứ đã bỏ khỏi repo nhưng còn ở đích
#
# VÌ SAO CHÉP CHỨ KHÔNG SYMLINK: thư mục này nằm trong OneDrive. OneDrive xử lý
# symlink không nhất quán giữa các máy, và một symlink gãy làm skill biến mất
# trong im lặng — kiểu hỏng tệ nhất cho một bộ luật.

param(
  [switch]$Check,
  [switch]$Prune
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Dest = if ($env:CLAUDE_HOME) { $env:CLAUDE_HOME } else { Join-Path $HOME '.claude' }
$Mode = if ($Check) { 'check' } elseif ($Prune) { 'prune' } else { 'copy' }
$script:Changed = 0

function Test-SameTree($a, $b) {
  if (-not (Test-Path $b)) { return $false }
  $fa = Get-ChildItem -Recurse -File $a | Sort-Object FullName
  $fb = Get-ChildItem -Recurse -File $b | Sort-Object FullName
  if ($fa.Count -ne $fb.Count) { return $false }
  for ($i = 0; $i -lt $fa.Count; $i++) {
    if ($fa[$i].Name -ne $fb[$i].Name) { return $false }
    $ha = (Get-FileHash $fa[$i].FullName -Algorithm SHA256).Hash
    $hb = (Get-FileHash $fb[$i].FullName -Algorithm SHA256).Hash
    if ($ha -ne $hb) { return $false }
  }
  return $true
}

function Sync-One($kind) {
  $src = Join-Path $Root $kind
  $dst = Join-Path $Dest $kind
  if (-not (Test-Path $src)) { return }
  if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Force $dst | Out-Null }

  foreach ($item in Get-ChildItem $src) {
    $target = Join-Path $dst $item.Name

    if ($item.PSIsContainer) {
      # skill = thư mục có SKILL.md. Thiếu file đó thì KHÔNG chép: một thư mục
      # rỗng ở đích trông như skill đã cài nhưng không có nội dung.
      if (-not (Test-Path (Join-Path $item.FullName 'SKILL.md'))) {
        Write-Host "  BỎ QUA  $kind/$($item.Name) — không có SKILL.md"
        continue
      }
      if (-not (Test-SameTree $item.FullName $target)) {
        $script:Changed++
        if ($Mode -eq 'check') { Write-Host "  LỆCH    $kind/$($item.Name)" }
        else {
          if (Test-Path $target) { Remove-Item -Recurse -Force $target }
          Copy-Item -Recurse $item.FullName $target
          Write-Host "  cập nhật $kind/$($item.Name)"
        }
      }
    } else {
      $same = (Test-Path $target) -and
              ((Get-FileHash $item.FullName -Algorithm SHA256).Hash -eq
               (Get-FileHash $target -Algorithm SHA256).Hash)
      if (-not $same) {
        $script:Changed++
        if ($Mode -eq 'check') { Write-Host "  LỆCH    $kind/$($item.Name)" }
        else { Copy-Item -Force $item.FullName $target; Write-Host "  cập nhật $kind/$($item.Name)" }
      }
    }
  }

  if ($Mode -eq 'prune') {
    foreach ($item in Get-ChildItem $dst) {
      # `synced/` là của Anthropic, không phải của repo này — không bao giờ đụng.
      if ($item.Name -eq 'synced') { continue }
      if (-not (Test-Path (Join-Path $src $item.Name))) {
        Remove-Item -Recurse -Force $item.FullName
        Write-Host "  xoá     $kind/$($item.Name) (đã bỏ khỏi stock-shared)"
      }
    }
  }
}

Write-Host "stock-shared -> $Dest  (chế độ: $Mode)"
Sync-One 'skills'
Sync-One 'agents'

if ($Mode -eq 'check') {
  if ($script:Changed -gt 0) {
    Write-Error "$($script:Changed) mục lệch. Chạy 'pwsh scripts/sync.ps1' để phát hành."
    exit 1
  }
  Write-Host 'khớp — không có gì lệch'
} else {
  Write-Host "xong · $($script:Changed) mục đã cập nhật"
}
