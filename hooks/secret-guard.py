"""PreToolUse (Write/Edit): chặn ghi thứ trông như khoá API vào file.

VÌ SAO TỒN TẠI
--------------
`CLAUDE.md §1.5` cấm hardcode API key. Ngày 2026-09-21 một khoá TypeSafe thật
đi qua cửa sổ chat, và suốt phiên đó thứ duy nhất ngăn nó rơi vào một file là
kỷ luật của người đang gõ. Kỷ luật không phải cơ chế.

Chặn ở tầng ghi file, không ở tầng commit: một khoá đã nằm trong working tree
là đã rò — `.gitignore` chỉ giấu nó khỏi git, không giấu khỏi OneDrive đang
đồng bộ thư mục này lên mây.

PHẠM VI CÓ CHỦ ĐÍCH HẸP: chỉ bắt mẫu khoá có tiền tố rõ ràng và đủ dài. Một
guard bắt bừa sẽ bị tắt, và một guard bị tắt bảo vệ được 0 thứ. Biến môi
trường (`os.environ[...]`, `${...}`, `process.env`) và chuỗi ví dụ rõ ràng
được cho qua.
"""
from __future__ import annotations

import json
import re
import sys

# Mỗi mẫu: (tên dịch vụ, regex). Chỉ những tiền tố KHÔNG thể là văn xuôi.
PATTERNS = [
    ("TypeSafe",  re.compile(r"\bapikey_[0-9a-f]{20,}")),
    # Anthropic TRƯỚC OpenAI: `sk-ant-…` cũng khớp `sk-…`, và mẫu nào khớp
    # trước thì đặt tên cho thông báo. Sai tên dịch vụ trong một cảnh báo bảo
    # mật làm người đọc đi tìm nhầm chỗ.
    ("Anthropic", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{24,}")),
    ("OpenAI",    re.compile(r"\bsk-(?!ant-)[A-Za-z0-9_-]{32,}")),
    ("xAI",       re.compile(r"\bxai-[A-Za-z0-9]{32,}")),
    ("GitHub",    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("AWS",       re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google",    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}")),
    ("Slack",     re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{20,}")),
]

# Chuỗi cho thấy đây là chỗ ĐỌC khoá, không phải chỗ nhúng khoá.
SAFE = re.compile(
    r"os\.environ|getenv|process\.env|\$\{|\$env:|<YOUR_|xxx+|\.\.\.|"
    r"example|placeholder|REDACTED|\bENV\b",
    re.IGNORECASE,
)

try:
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
except Exception:  # noqa: BLE001
    sys.exit(0)

if (payload.get("tool_name") or "") not in ("Write", "Edit", "NotebookEdit"):
    sys.exit(0)

ti = payload.get("tool_input") or {}
# Write dùng `content`; Edit dùng `new_string`; NotebookEdit dùng `new_source`.
blob = "\n".join(
    str(ti.get(k) or "") for k in ("content", "new_string", "new_source")
)
if not blob:
    sys.exit(0)

for service, pat in PATTERNS:
    for m in pat.finditer(blob):
        # Cùng dòng có dấu hiệu đọc-từ-env thì bỏ qua.
        start = blob.rfind("\n", 0, m.start()) + 1
        end = blob.find("\n", m.end())
        line = blob[start: end if end != -1 else len(blob)]
        if SAFE.search(line):
            continue
        tok = m.group(0)
        masked = tok[:10] + "…" + tok[-4:]
        path = str(ti.get("file_path") or "?")
        sys.stdout.buffer.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"Chuỗi trông như khoá {service} ({masked}) sắp được ghi vào "
                f"`{path}`.\n\n"
                "Khoá chỉ đọc từ biến môi trường — `os.environ[\"X_API_KEY\"]`, "
                "`process.env.X`, hoặc GitHub Actions secret. Thư mục này nằm "
                "trong OneDrive và đang đồng bộ lên mây, nên một khoá trong "
                "working tree là đã rò, kể cả khi `.gitignore` giấu nó khỏi git."
                "\n\nNếu đây là chuỗi ví dụ, viết nó dạng `apikey_<REDACTED>` "
                "hoặc kèm chữ `example` trên cùng dòng."
            ),
        }}, ensure_ascii=False).encode("utf-8"))
        sys.exit(0)

sys.exit(0)
