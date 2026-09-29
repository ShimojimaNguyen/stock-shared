"""PreToolUse (Write/Edit/NotebookEdit): chặn sửa TAY file do script sinh ra.

VÌ SAO TỒN TẠI
--------------
`CLAUDE.md §1.5` đã cấm điều này bằng văn xuôi từ lâu. Văn xuôi không chặn
được gì. Hai bằng chứng từ chính repo này:

  · Danh sách "cấm sửa tay" được chép tay, và ngày 2026-09-22 phát hiện nó
    THIẾU 3 file: world-live.json, vn-insight.json, last-run.json. Một luật
    liệt kê thiếu là một luật cho phép nhầm.
  · Sửa tay một artifact thì lần chạy sau script ghi đè, và thay đổi biến mất
    trong im lặng — không ai biết là đã từng có.

Nên hook này KHÔNG mang danh sách riêng: nó đọc `registry.json`, chỗ mỗi sản
phẩm dữ liệu tự khai artifact của mình. Thêm một pipeline mới là tự động được
bảo vệ, không phải nhớ cập nhật hai nơi.

CÁCH DÙNG ĐÚNG khi thật sự cần sửa: sửa LOGIC trong script rồi chạy lại. Nếu
một dòng lịch sử quá khứ sai, sửa đúng dòng đó và nói rõ lý do trong commit.
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys


def deny(reason: str) -> None:
    # stdout.buffer + encode: console Windows là cp932, `json.dump(..., sys.stdout)`
    # sẽ làm hỏng tiếng Việt và hook biến thành im lặng.
    sys.stdout.buffer.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}, ensure_ascii=False).encode("utf-8"))
    sys.exit(0)


def load_registry() -> dict | None:
    """registry.json nằm ở stock-shared, cạnh repo đang mở."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in (os.path.join(here, "registry.json"),
              os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", ""), "..",
                           "stock-shared", "registry.json")):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001 — thiếu registry thì im lặng cho qua
            continue
    return None


try:
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
except Exception:  # noqa: BLE001
    sys.exit(0)

tool = payload.get("tool_name") or ""
if tool not in ("Write", "Edit", "NotebookEdit"):
    sys.exit(0)

path = str((payload.get("tool_input") or {}).get("file_path") or "")
if not path:
    sys.exit(0)
norm = path.replace("\\", "/")

reg = load_registry()
if not reg:
    sys.exit(0)   # không đoán khi không có nguồn sự thật

# Được phép sửa tay theo thiết kế — kiểm TRƯỚC, vì news.json nằm trong
# public/data nhưng không script nào sinh ra nó.
for ok in reg.get("hand_editable", []):
    if norm.endswith(ok.replace("\\", "/")):
        sys.exit(0)

for name, prod in (reg.get("products") or {}).items():
    for pat in prod.get("artifacts", []):
        pat = pat.replace("\\", "/")
        # so khớp phần đuôi: hook không biết repo được mở ở đường dẫn tuyệt đối nào
        if fnmatch.fnmatch(norm, "*/" + pat) or norm.endswith("/" + pat) or fnmatch.fnmatch(norm, "*" + pat):
            script = prod.get("script", "?")
            deny(
                f"'{pat}' là artifact do `{script}` sinh ra (sản phẩm `{name}` "
                f"trong stock-shared/registry.json) — CẤM sửa tay.\n\n"
                "Sửa tay sẽ bị ghi đè ở lần chạy sau và biến mất trong im lặng. "
                f"Hãy sửa LOGIC trong `{script}` rồi chạy lại.\n\n"
                "Nếu một dòng lịch sử quá khứ thật sự sai: sửa đúng dòng đó và "
                "nói rõ lý do trong commit message. Nếu file này lẽ ra được sửa "
                "tay, thêm nó vào `hand_editable` trong registry.json."
            )

sys.exit(0)
