"""SessionStart: báo nếu lớp chung chưa được phát hành, hoặc đã cũ.

VÌ SAO TỒN TẠI
--------------
Toàn bộ luật dùng chung (pillar dữ liệu, luật tài chính, luật Jev, sổ nguồn)
sống trong `stock-shared/skills/` rồi được `scripts/sync.sh` chép sang
`~/.claude/skills/`. Bước chép đó chạy TAY.

Máy chưa sync — hoặc sync từ lâu rồi sửa tiếp bản gốc — thì agent gọi
`Skill(skill: "data-integrity-pillars")` sẽ nhận bản cũ, hoặc không nhận gì,
và **làm việc tiếp như thể không có luật nào**. Đó là kiểu hỏng tệ nhất: im
lặng, và trông y hệt lúc bình thường.

Hook này chỉ ĐỌC và BÁO. Không tự sync: phát hành một bộ luật là việc cần
người biết mình đang phát hành cái gì.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys


def sha(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def note(msg: str) -> None:
    sys.stdout.buffer.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": msg,
    }}, ensure_ascii=False).encode("utf-8"))
    sys.exit(0)


src_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_skills = os.path.join(src_root, "skills")
dst_skills = os.path.join(os.path.expanduser("~"), ".claude", "skills")

if not os.path.isdir(src_skills):
    sys.exit(0)   # không phải máy có stock-shared — im lặng

missing, stale = [], []
for name in sorted(os.listdir(src_skills)):
    s = os.path.join(src_skills, name, "SKILL.md")
    if not os.path.isfile(s):
        continue
    d = os.path.join(dst_skills, name, "SKILL.md")
    if not os.path.isfile(d):
        missing.append(name)
    elif sha(s) != sha(d):
        stale.append(name)

if not missing and not stale:
    sys.exit(0)

lines = ["LỚP CHUNG CHƯA ĐỒNG BỘ — luật dùng chung có thể đang thiếu hoặc cũ."]
if missing:
    lines.append(f"  · chưa phát hành: {', '.join(missing)}")
if stale:
    lines.append(f"  · bản gốc đã đổi, bản đang dùng còn cũ: {', '.join(stale)}")
lines += [
    "",
    "Chạy:  bash stock-shared/scripts/sync.sh      (hoặc pwsh scripts/sync.ps1)",
    "",
    "Trước khi sync xong, ĐỪNG dựa vào trí nhớ về các luật đó. Một bộ luật nhớ "
    "mang máng nguy hiểm hơn là không có luật — nó cho cảm giác đã kiểm rồi.",
]
note("\n".join(lines))
