#!/usr/bin/env bash
# Phát hành skill/agent chung sang mức user, để mọi repo trên máy này thấy.
#
#   bash scripts/sync.sh            chép (mặc định)
#   bash scripts/sync.sh --check    chỉ báo lệch, không chép — dùng trong CI/hook
#   bash scripts/sync.sh --prune    xoá thứ đã bỏ khỏi repo nhưng còn ở đích
#
# VÌ SAO CHÉP CHỨ KHÔNG SYMLINK: thư mục này nằm trong OneDrive. OneDrive xử lý
# symlink không nhất quán giữa các máy, và một symlink gãy sẽ làm skill biến mất
# trong im lặng — đúng kiểu hỏng tệ nhất cho một bộ luật.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${CLAUDE_HOME:-$HOME/.claude}"
MODE="copy"
for a in "$@"; do
  case "$a" in
    --check) MODE="check" ;;
    --prune) MODE="prune" ;;
    *) echo "tham số lạ: $a" >&2; exit 2 ;;
  esac
done

changed=0
missing=0

sync_one() {           # $1 = skills|agents
  local kind="$1" src="$ROOT/$1" dst="$DEST/$1"
  [ -d "$src" ] || return 0
  mkdir -p "$dst"

  for item in "$src"/*; do
    [ -e "$item" ] || continue
    local name; name="$(basename "$item")"
    local target="$dst/$name"

    if [ -d "$item" ]; then
      # skill = thư mục có SKILL.md. Thiếu file đó thì KHÔNG chép: một thư mục
      # rỗng ở đích trông như skill đã cài nhưng không có nội dung.
      if [ ! -f "$item/SKILL.md" ]; then
        echo "  BỎ QUA  $kind/$name — không có SKILL.md"
        continue
      fi
      if [ ! -d "$target" ] || ! diff -rq "$item" "$target" >/dev/null 2>&1; then
        changed=$((changed+1)); missing=$((missing+1))
        if [ "$MODE" = "check" ]; then echo "  LỆCH    $kind/$name"
        else rm -rf "$target"; cp -r "$item" "$target"; echo "  cập nhật $kind/$name"; fi
      fi
    else
      if ! cmp -s "$item" "$target"; then
        changed=$((changed+1)); missing=$((missing+1))
        if [ "$MODE" = "check" ]; then echo "  LỆCH    $kind/$name"
        else cp "$item" "$target"; echo "  cập nhật $kind/$name"; fi
      fi
    fi
  done

  if [ "$MODE" = "prune" ]; then
    for item in "$dst"/*; do
      [ -e "$item" ] || continue
      local name; name="$(basename "$item")"
      # `synced/` là của Anthropic, không phải của repo này — không bao giờ đụng.
      [ "$name" = "synced" ] && continue
      if [ ! -e "$src/$name" ]; then
        rm -rf "$item"; echo "  xoá     $kind/$name (đã bỏ khỏi stock-shared)"
      fi
    done
  fi
}

echo "stock-shared → $DEST  (chế độ: $MODE)"
sync_one skills
sync_one agents

if [ "$MODE" = "check" ]; then
  if [ "$changed" -gt 0 ]; then
    echo "$changed mục lệch. Chạy 'bash scripts/sync.sh' để phát hành." >&2
    exit 1
  fi
  echo "khớp — không có gì lệch"
else
  echo "xong · $changed mục đã cập nhật"
fi
