"""Kiểm tương phản WCAG 2.2 trên file design token — [U-3], [U-1].

VÌ SAO TỒN TẠI
--------------
Đo 2026-09-30 trên `vn-market-site/src/styles/tokens.css`: **25 cặp màu không
đạt 4.5:1**, và những màu trượt đang tô CHÍNH CÁC CON SỐ BIẾN ĐỘNG —
`--tang` (xanh tăng) 3.05 trên nền trắng, `--tc` (cam) 2.69, trượt cả ngưỡng
3.0. Người đọc trên màn hình mờ hoặc thị lực kém không đọc nổi.

Cùng phép đo trên `kiyohara/src/styles.css`: chỉ 3 cặp trượt, đều là nhãn phụ.
Hai repo cùng một đội, cùng một tuần — chênh nhau vì **không ai đo**.

TÍNH ĐƯỢC, KHÔNG CẦN TRÌNH DUYỆT
--------------------------------
Tương phản là một hàm thuần của hai mã màu. Không cần Playwright, không cần
axe-core, không cần cài gì — nên nó chạy được trong CI của một dự án phi lợi
nhuận, và chạy cho MỌI thị trường vì màu không phụ thuộc thị trường.

Đây đúng là phần "reusable 100%": công cụ chung, phần customize là danh sách
vai trò màu của từng repo, khai trong `registry.json`.

NGƯỠNG
------
WCAG 2.2 AA: chữ thường ≥ 4.5:1 · chữ lớn (≥18.66px đậm hoặc ≥24px) và
thành phần giao diện ≥ 3:1.
https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html

Một màu vừa làm chữ vừa làm nền ô thì phải TÁCH LÀM HAI token: `--x` cho chữ
(≥4.5) và `--x-fill` cho nền (≥3.0). Ép một mã màu gánh cả hai vai là lý do
bảng màu hiện tại không đạt.

  py tools/contrast.py --all
  py tools/contrast.py --file ../vn-market-site/src/styles/tokens.css
  py tools/contrast.py --all --suggest    # đề xuất mã màu đạt chuẩn, GIỮ NGUYÊN sắc
"""
from __future__ import annotations

import argparse
import colorsys
import json
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK = os.path.dirname(ROOT)

AA_TEXT = 4.5
AA_LARGE = 3.0


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_: str) -> float:
    h = hex_.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def ratio(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def parse_tokens(path: str) -> dict[str, str]:
    """Đọc mọi `--ten: #rrggbb` — hợp cả `:root {}` của CSS thường lẫn
    `@theme {}` của Tailwind v4. Hai repo dùng hai kiểu; công cụ không quan tâm."""
    t = open(path, encoding="utf-8", errors="replace").read()
    return dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;", t))


def fix(fg: str, bgs: list[str], target: float) -> str | None:
    """Mã màu gần nhất đạt `target` trên MỌI nền, GIỮ NGUYÊN sắc (hue).

    Chỉ đổi độ sáng. Đổi sắc là đổi NGHĨA — người dùng đã quen xanh = tăng,
    đỏ = giảm; một cổng a11y không được phép âm thầm đổi ngôn ngữ màu của
    sản phẩm. Nếu hạ hết mức vẫn không đạt thì trả None và nói ra, chứ không
    lặng lẽ trả về màu gần đúng."""
    h = fg.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    dark = luminance(max(bgs, key=luminance)) > 0.18   # nền sáng → phải làm tối chữ
    step = -0.005 if dark else 0.005
    cur = ll
    for _ in range(200):
        cur += step
        if not 0.0 <= cur <= 1.0:
            break
        rr, gg, bb = colorsys.hls_to_rgb(hh, cur, ss)
        cand = "#%02X%02X%02X" % (round(rr * 255), round(gg * 255), round(bb * 255))
        if all(ratio(cand, bg) >= target for bg in bgs):
            return cand
    return None


def audit(path: str, bg_names: list[str], suggest: bool) -> int:
    tok = parse_tokens(path)
    bgs = {k: tok[k] for k in bg_names if k in tok}
    if not bgs:
        print(f"   không tìm thấy token nền {bg_names} trong {path}")
        return 0
    fgs = {k: v for k, v in tok.items() if k not in bgs}

    worst: list[tuple[str, float, str]] = []
    print(f"   {'token chữ':22}{'hex':10}" + "".join(f"{b.replace('--color-', '').replace('--', ''):>13}" for b in bgs))
    for f, fh in sorted(fgs.items()):
        row = f"   {f:22}{fh:10}"
        lo = 99.0
        for bh in bgs.values():
            r = ratio(fh, bh)
            lo = min(lo, r)
            mark = "" if r >= AA_TEXT else ("△" if r >= AA_LARGE else "✗")
            row += f"{r:>10.2f}{mark:<3}"
        print(row)
        if lo < AA_TEXT:
            worst.append((f, lo, fh))

    if not worst:
        print("   → mọi token đạt 4.5:1 làm chữ thường")
        return 0

    print(f"\n   {len(worst)} token KHÔNG đạt {AA_TEXT}:1 làm chữ thường "
          f"(✗ = trượt cả {AA_LARGE}:1 của chữ lớn/thành phần UI)")
    if suggest:
        print(f"\n   Đề xuất — GIỮ NGUYÊN sắc, chỉ hạ độ sáng:")
        for f, lo, fh in sorted(worst, key=lambda x: x[1]):
            new = fix(fh, list(bgs.values()), AA_TEXT)
            if new is None:
                print(f"     {f:22} {fh} → không có biến thể nào cùng sắc đạt {AA_TEXT}:1; "
                      f"phải đổi cách dùng (chỉ làm nền, không làm chữ)")
            else:
                got = min(ratio(new, b) for b in bgs.values())
                print(f"     {f:22} {fh} ({lo:.2f})  →  {new} ({got:.2f})")
    return len(worst)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--file", default=None)
    ap.add_argument("--bg", default=None, help="tên token nền, cách nhau bằng dấu phẩy")
    ap.add_argument("--suggest", action="store_true")
    a = ap.parse_args()
    if not (a.all or a.file):
        ap.error("cần --all hoặc --file")

    reg = json.load(open(os.path.join(ROOT, "registry.json"), encoding="utf-8"))
    targets = []
    if a.file:
        bgs = (a.bg or "--bg,--surface,--fill").split(",")
        targets.append((a.file, a.file, bgs))
    else:
        for name, r in reg["repos"].items():
            if name.startswith("_"):
                continue          # `_doc`/`_ui_doc` là chú thích, không phải repo
            ui = r.get("ui")
            if not ui:
                continue
            p = os.path.join(STOCK, name, ui["tokens"])
            if os.path.isfile(p):
                targets.append((name, p, ui["backgrounds"]))

    if not targets:
        print("Không repo nào khai `ui.tokens` trong registry.json — "
              "chưa có gì để kiểm, và đó KHÔNG phải là 'đạt'.")
        return 1

    print(f"contrast · WCAG 2.2 AA · {len(targets)} bảng màu")
    total = 0
    for name, p, bgs in targets:
        print(f"\n[{name}] {os.path.relpath(p, STOCK)}")
        total += audit(p, bgs, a.suggest)
    print(f"\n{total} token không đạt 4.5:1 làm chữ thường")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
