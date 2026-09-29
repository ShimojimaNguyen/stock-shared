"""PreToolUse (Bash `git commit`): chặn commit mang vi phạm pillar MỚI.

VÌ SAO TỒN TẠI
--------------
Bug thật: `(inp.flowYen ?? 0) > 0 ? … : "横ばい"` trong kiyohara biến "không
biết" thành lời khẳng định "đi ngang", ngay cạnh một con số đã hiện `—`. Nó
sống nhiều ngày và chỉ lộ ra khi `pillar_guard.py` được chạy TAY. Công cụ có
rồi; thứ thiếu là thời điểm nó tự chạy.

CHỈ SOÁT FILE TRONG COMMIT NÀY, KHÔNG SOÁT CẢ REPO
--------------------------------------------------
`vn-market-site` hiện có 15 vi phạm tầng grep ở bề mặt cũ. Chặn theo toàn repo
nghĩa là chặn mọi commit, kể cả commit đang đi sửa chính chỗ đó — và một cổng
luôn đỏ sẽ bị tắt trong vòng một ngày. Cổng bị tắt bảo vệ được 0 thứ.

Nên đây là bánh cóc: nợ cũ không chặn, thêm nợ mới thì chặn.

CHỈ TẦNG GREP, KHÔNG GỌI JEV: cổng phải chạy trong tích tắc và không tốn tiền,
không phụ thuộc mạng. Tầng Jev vẫn chạy tay hoặc trong CI.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys

COMMIT = re.compile(r"\bgit\s+(-[^\s]+\s+|--\S+\s+)*commit\b")


def load_guard():
    """Nạp pillar_guard từ stock-shared — DÙNG CHUNG bộ luật, không chép lại.

    Chép DETERMINISTIC sang đây là tạo bản thứ hai của cùng một bộ luật, và
    hai bản sẽ lệch nhau đúng như mọi lần trước."""
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools", "pillar_guard.py")
    if not os.path.isfile(p):
        return None
    spec = importlib.util.spec_from_file_location("pillar_guard", p)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001
        return None


try:
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
except Exception:  # noqa: BLE001
    sys.exit(0)

if (payload.get("tool_name") or "") != "Bash":
    sys.exit(0)
cmd = str((payload.get("tool_input") or {}).get("command") or "")
if not COMMIT.search(cmd):
    sys.exit(0)

def win_path(p: str) -> str:
    """`/c/x/y` → `C:\\x\\y`.

    Git Bash đưa đường dẫn kiểu POSIX, còn `git.exe` và Python trên Windows
    không hiểu nó: `git -C /c/tmp/x` trả `fatal: cannot change to …` và hook
    sẽ ÂM THẦM cho qua. Một cổng im lặng vì hỏng trông y hệt một cổng im lặng
    vì sạch — đúng kiểu hỏng mà docstring ở đầu file này nói tới.
    """
    m = re.match(r"^/([a-zA-Z])/(.*)$", p or "")
    return f"{m.group(1).upper()}:\\" + m.group(2).replace("/", "\\") if m else p


cwd = win_path(payload.get("cwd") or os.getcwd())
g = load_guard()
if g is None:
    sys.exit(0)

try:
    out = subprocess.run(["git", "-C", cwd, "diff", "--cached", "--name-only"],
                         capture_output=True, timeout=20)
    staged = [l for l in out.stdout.decode("utf-8", "replace").splitlines() if l.strip()]
except Exception:  # noqa: BLE001
    sys.exit(0)

hits = []
for rel in staged:
    if os.path.splitext(rel)[1] not in g.CODE_EXT:
        continue
    norm = rel.replace("\\", "/")
    if g.GENERATED.search(norm) or g.TEST_FILE.search(norm):
        continue
    full = os.path.join(cwd, rel)
    if not os.path.isfile(full):
        continue                      # file bị xoá trong commit này
    for i, line in g.code_lines(full):
        for name, pat, why, pillar in g.DETERMINISTIC:
            if re.search(pat, line, re.IGNORECASE):
                hits.append(f"  {rel}:{i}  [{pillar}] {name}\n      {line.strip()[:96]}")

if not hits:
    sys.exit(0)

body = "\n".join(hits[:12])
more = f"\n  … và {len(hits) - 12} chỗ nữa" if len(hits) > 12 else ""
sys.stdout.buffer.write(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": (
        f"{len(hits)} vi phạm pillar trong các file của chính commit này:\n\n"
        f"{body}{more}\n\n"
        "Bug thật đã đi qua đường này: `?? 0` biến 'không biết' thành khẳng "
        "định '横ばい' và sống nhiều ngày.\n\n"
        "Sửa, hoặc nếu chỗ đó thật sự hợp lệ thì miễn trừ KÈM LÝ DO:\n"
        "    // pillar-ok: <vì sao chỗ này 0 là 0 thật>\n"
        "Lý do nằm trong diff nên người review đọc được — khác hẳn một dòng "
        "tắt câm.\n\n"
        "Chỉ file trong commit này bị soát; nợ cũ của repo không chặn bạn."
    ),
}}, ensure_ascii=False).encode("utf-8"))
sys.exit(0)
