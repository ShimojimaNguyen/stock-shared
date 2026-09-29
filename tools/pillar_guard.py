"""Kiểm pillars — hai tầng: grep tất định, rồi Jev cho thứ grep không bắt được.

    py tools/pillar_guard.py --repo ../kiyohara
    py tools/pillar_guard.py --repo ../vn-market-site --no-jev   # chỉ tầng grep
    py tools/pillar_guard.py --selftest                          # đo lại ngưỡng

VÌ SAO HAI TẦNG
---------------
Phần lớn pillars grep được: `?? 0`, `|| 0`, `Math.random`, hex rời. Code bắt
được thì KHÔNG hỏi model — rẻ hơn, tất định, và không cần mạng.

Còn pillar "cấm nội dung khuyến nghị mua/bán" thì grep **không bắt hết được**:
"nên mua" thì grep ra, nhưng "nhà đầu tư có thể cân nhắc tích lũy dần ở vùng
giá này" thì không, mà nó vẫn là khuyến nghị. Chỗ đó mới gọi Jev.

NGƯỠNG ĐƯỢC ĐO, KHÔNG ĐƯỢC ĐOÁN (2026-09-24, n=5 mỗi mẫu)
---------------------------------------------------------
  chuỗi sạch  → cao nhất 0,08   (dao động ≤ 0,01)
  câu khuyến nghị → thấp nhất 0,21   (ca tiếng Nhật, dao động 0,21–0,23)
  34 chuỗi THẬT lấy từ hai repo → cao nhất 0,10
  => ngưỡng 0,15: cách chuỗi thật 0,05, cách câu bẩn 0,06

Bản đầu đặt 0,25 dựa trên MỘT lần đo mỗi mẫu, và ca tiếng Nhật lần đó ra 0,28.
Đo lại 5 lần thì nó nằm ở 0,21–0,23 — ngưỡng 0,25 sẽ bỏ sót. Chính `--selftest`
bắt được. Một lần đo không phải một phép đo.

Biên hẹp nhất vẫn là ca tiếng Nhật, khớp cảnh báo CJK kém chính xác hơn trong
tài liệu Jev. Nên đây là LƯỚI THỨ HAI, không thay lưới grep — và với văn bản
tiếng Nhật thì lưới grep quan trọng hơn lưới này.

`--selftest` chạy lại chính phép đo đó. Lệch khỏi số trên nghĩa là model đã trôi
hoặc câu hỏi đã bị sửa — dừng lại xem, đừng nới ngưỡng.

KHÔNG MỞ RỘNG SANG REVIEW LOGIC CODE. Jev không đọc diff nhiều bước, không làm
số học. Xem skill `jev-judgments` §1.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

# Console Windows mặc định cp932 ở máy này, và báo cáo của công cụ đầy tiếng
# Việt + tiếng Nhật. Không ép UTF-8 thì `print` ném UnicodeEncodeError và
# CÔNG CỤ CHẾT GIỮA CHỪNG — người chạy thấy traceback, tưởng repo hỏng, trong
# khi thứ hỏng là cái máy in. Một cổng chết là một cổng không gác.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001  — stream bị thay thế/không hỗ trợ
        pass

JEV_URL = "https://api.typesafe.ai/v1/systemone"
# Bắt buộc: thiếu UA thì Cloudflare trả 403 "error code: 1010", trông như lỗi
# xác thực chứ không phải lỗi client. Xem skill jev-judgments §6.
UA = "stock-shared-pillar-guard/0.1"

# HAI MỨC, vì phép đo không cho phép một mức.
#   ≥ FAIL  : đủ chắc để chặn
#   ≥ WARN  : cao hơn hẳn mọi chuỗi thật (max 0,10) nên đáng người xem, nhưng
#             chưa đủ chắc để chặn — vùng này có cả câu hợp lệ lẫn câu không.
# Hệ quả phải nói thẳng: câu khuyến nghị TIẾNG NHẬT đo được 0,21–0,23, tức rơi
# vào vùng CẢNH BÁO chứ không bị chặn. Với văn bản tiếng Nhật, lưới grep tất
# định mới là lưới chính; lớp Jev chỉ là lưới phụ.
ADVICE_FAIL = 0.40
ADVICE_WARN = 0.15

ADVICE_QUESTION = {
    "advice": {
        "type": "noul",
        "instructions": (
            "Does this text from a market-data website tell the reader to buy, sell, "
            "or hold a security, or otherwise steer an investment decision? "
            "Describing what the data shows is NOT advice."
        ),
        "criteria": {
            "true": "It recommends an action, names a target price, or tells the "
                    "reader what they should do with a position",
            "false": "It only describes or explains data, methodology, or limitations",
        },
    }
}

# ---------------------------------------------------------------- tầng 1: grep

# (tên, regex, giải thích, pillar)
DETERMINISTIC = [
    ("null-lap-bang-0", r"\?\?\s*0\b|\|\|\s*0\b",
     "`?? 0` / `|| 0` biến 'không biết' thành 'bằng không'", "§1"),
    ("prng-fallback", r"Math\.random\s*\(|random\.seed\s*\(|np\.random\.seed\s*\(",
     "số ngẫu nhiên làm dữ liệu — đã từng thành sparkline giả", "§6"),
    ("khuyen-nghi-hien-nhien",
     r"nên mua|nên bán|giá mục tiêu|買い推奨|売り推奨|target price",
     "chuỗi khuyến nghị bắt được bằng grep", "§7"),
    ("hyphen-thay-dau-tru", r"[\"'>]-\d+[.,]\d+\s*%",
     "dùng hyphen thay U+2212 cho số âm", "§8"),
]

# Thư mục không bao giờ quét.
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".output", "__pycache__",
             "crewai_env", ".venv", "venv", ".claude", ".amazonq", "data",
             "public", "coverage", ".vercel", ".tanstack"}
CODE_EXT = {".ts", ".tsx", ".js", ".jsx", ".py", ".css"}

# File sinh tự động — vi phạm ở đó phải sửa ở script sinh, không sửa tại chỗ.
GENERATED = re.compile(r"routeTree\.gen\.|universe\.ts$|fx-roles\.ts$")

# File test: bỏ qua CẢ HAI tầng.
#   · tầng grep — test hay chứa chính chuỗi bị cấm để khẳng định nó bị cấm,
#     ví dụ `assert.doesNotMatch(all, /買い推奨/)`.
#   · tầng Jev — tên test là câu mô tả hành vi, không phải chữ người dùng đọc;
#     "buildTradeView: loại 銀行業, トヨタ both_in…" bị chấm 0,85 vì đọc như một
#     lời khuyên, trong khi nó không bao giờ lên màn hình.
TEST_FILE = re.compile(r"(^|[./])(test_|conftest)|[.\-_](test|spec|check)\.[a-z]+$")


def walk_code(repo: str):
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if os.path.splitext(f)[1] not in CODE_EXT:
                continue
            p = os.path.join(root, f)
            rel = p.replace("\\", "/")
            if GENERATED.search(rel) or TEST_FILE.search(rel):
                continue
            yield p


# Miễn trừ BẮT BUỘC nêu lý do:
#   const x = a ?? 0;  // pillar-ok: so sánh sắp xếp, không hiển thị
# Lý do nằm trong diff nên người review thấy được — khác hẳn một dòng tắt câm.
SUPPRESS = re.compile(r"(//|#|\{/\*)\s*pillar-ok:\s*(\S.*)")


PY_DOC = ('"' * 3, "'" * 3)


def code_lines(path: str):
    """Sinh (số dòng, nội dung) chỉ cho dòng CODE — bỏ hết comment.

    Phải theo dõi trạng thái khối `/* */` và docstring. Pillars được trích dẫn
    dày đặc trong comment của chính các repo này, và một comment nhiều dòng
    không phải dòng nào cũng bắt đầu bằng `*`. Bản đầu chỉ xét ký tự đầu dòng,
    nên báo động giả ngay trên dòng giải thích vì sao luật tồn tại.
    """
    try:
        raw = open(path, encoding="utf-8").read().splitlines()
    except (UnicodeDecodeError, OSError):
        return
    in_block = False
    py = path.endswith(".py")
    # Miễn trừ đặt trong KHỐI comment ngay trên dòng code, và khối đó có thể dài
    # nhiều dòng — lý do miễn trừ thường cần cả câu để giải thích. Chỉ nhìn đúng
    # một dòng trên là hụt: lần đầu làm vậy, mọi miễn trừ hai dòng đều trượt.
    pending = False

    for i, line in enumerate(raw, 1):
        t = line.strip()
        comment = False

        if py:
            if any(t.count(q) % 2 == 1 for q in PY_DOC):
                in_block = not in_block
                comment = True
            elif in_block or t.startswith("#"):
                comment = True
        else:
            if in_block:
                comment = True
                if "*/" in t:
                    in_block = False
            elif t.startswith(("/*", "{/*")) and "*/" not in t:
                in_block = True
                comment = True
            elif t.startswith(("//", "*")) or (t.startswith("{/*") and "*/" in t):
                comment = True

        if comment:
            if SUPPRESS.search(line):
                pending = True
            continue
        if not t:                    # dòng trống cắt mạch miễn trừ
            pending = False
            continue
        if pending or SUPPRESS.search(line):
            # Miễn trừ giữ hiệu lực tới HẾT CÂU LỆNH, không chỉ dòng đầu. Một
            # biểu thức `.reduce(...)` xuống dòng thì dòng chứa `?? 0` không
            # phải dòng đầu — lần đầu làm vậy, mọi miễn trừ cho câu lệnh nhiều
            # dòng đều trượt.
            pending = not t.endswith((";", "{", "}"))
            continue
        yield i, line


def grep_pass(repo: str) -> list[dict]:
    hits = []
    for p in walk_code(repo):
        for i, line in code_lines(p):
            if SUPPRESS.search(line):
                continue
            for name, pat, why, pillar in DETERMINISTIC:
                if re.search(pat, line, re.IGNORECASE):
                    hits.append({"file": os.path.relpath(p, repo), "line": i,
                                 "rule": name, "pillar": pillar, "why": why,
                                 "text": line.strip()[:100]})
    return hits


# ---------------------------------------------------------------- tầng 2: Jev

# Chuỗi hiển thị: đủ dài để là câu, có chữ tiếng Việt hoặc tiếng Nhật.
HUMAN = re.compile("[ăâđêôơưáàảãạíìỉĩịúùủũụéèẻẽẹóòỏõọýỳỷỹỵ"
                   "぀-ヿ一-龯]")   # kana + kanji
STRING_LIT = re.compile(r"[\"'`>]([^\"'`<>{}\n]{28,220})[\"'`<]")


# Chuỗi dành cho LẬP TRÌNH VIÊN, không phải cho người xem trang. Câu log kiểu
# "Đối chiếu 売買代金上位 trước khi nới dải" đọc như một lời khuyên và bị chấm
# 0,17 — nhưng nó không bao giờ lên màn hình người dùng.
DEV_STRING = re.compile(r"\b(log|console\.(log|warn|error|info)|print|logger\.\w+|"
                        r"describe|it|test|assert\w*)\s*\(")


def collect_strings(repo: str) -> list[tuple[str, int, str]]:
    out, seen = [], set()
    for p in walk_code(repo):
        for i, line in code_lines(p):
            if SUPPRESS.search(line) or DEV_STRING.search(line):
                continue
            for m in STRING_LIT.finditer(line):
                t = m.group(1).strip()
                if not HUMAN.search(t) or "http" in t or "className" in t:
                    continue
                if t in seen:
                    continue
                seen.add(t)
                out.append((os.path.relpath(p, repo), i, t))
    return out


def ask_jev(key: str, texts: list[str]) -> list[float]:
    """Một request mỗi chuỗi. State nhỏ nên rẻ; gom nhiều chuỗi vào một state
    sẽ khiến model phán đoán trên hỗn hợp, không phải trên từng câu."""
    out = []
    for t in texts:
        body = json.dumps({"state": {"ui_text": t}, "model": "jev-latest",
                           "questions": ADVICE_QUESTION}).encode()
        req = urllib.request.Request(
            JEV_URL, data=body,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json", "User-Agent": UA})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
            out.append(d["answers"]["advice"]["noul"])
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:80]
            if e.code == 403 and "1010" in detail:
                raise SystemExit(
                    "Jev trả 403 / Cloudflare 1010 — thiếu hoặc bị chặn User-Agent, "
                    "KHÔNG phải lỗi khoá. Xem skill jev-judgments §6.")
            raise SystemExit(f"Jev HTTP {e.code}: {detail}")
    return out


# ---------------------------------------------------------------- selftest

CLEAN_SAMPLES = [
    "Tuần này tiền có vào công ty qua xuất / nhập không. USDJPY Yahoo + dòng ròng TOPIX.",
    "Dòng ròng ≠ tiền về tài khoản. Đây là close×volume có dấu trên thị trường thứ cấp.",
    "Dữ liệu chỉ để tham khảo và nghiên cứu. Không phải khuyến nghị mua bán.",
    "貿易の円換算と市場資金の両面で、会社／株へ資金が入った。",
    "Ngành Bất động sản đang ở góc phần tư Leading (RS-Ratio 104,2 · RS-Momentum 101,8).",
    "Thiếu dữ liệu breadth nên cột ADR hiển thị —.",
]
ADVICE_SAMPLES = [
    "Với định giá hiện tại, nhà đầu tư có thể cân nhắc tích lũy dần ở vùng giá này.",
    "Nhóm ngân hàng đang hấp dẫn hơn mặt bằng chung, đáng để ưu tiên trong danh mục.",
    "この水準なら仕込み時と考えられる。",
    "Rủi ro đã phản ánh phần lớn vào giá, khả năng hồi phục trong quý tới là cao.",
    "Chúng tôi đánh giá cao tiềm năng tăng giá của mã này trong 6 tháng tới.",
    "Nếu thủng mốc 1.200 điểm thì nên giảm tỷ trọng.",
]


def selftest(key: str) -> int:
    clean = ask_jev(key, CLEAN_SAMPLES)
    advice = ask_jev(key, ADVICE_SAMPLES)
    # Chuỗi sạch không được chạm cả ngưỡng CẢNH BÁO — đó là biên phải giữ.
    fp = [(v, t) for v, t in zip(clean, CLEAN_SAMPLES) if v >= ADVICE_WARN]
    # Câu khuyến nghị tối thiểu phải vào vùng cảnh báo. Không đòi phải ≥ FAIL:
    # đã đo, ca tiếng Nhật chỉ đạt 0,21–0,23.
    fn = [(v, t) for v, t in zip(advice, ADVICE_SAMPLES) if v < ADVICE_WARN]
    blocked = sum(1 for v in advice if v >= ADVICE_FAIL)

    print(f"ngưỡng: cảnh báo ≥ {ADVICE_WARN} · chặn ≥ {ADVICE_FAIL}")
    print(f"  sạch   n={len(clean)}  cao nhất {max(clean):.2f}  "
          f"trung bình {sum(clean)/len(clean):.3f}  → báo động giả: {len(fp)}")
    print(f"  bẩn    n={len(advice)} thấp nhất {min(advice):.2f}  "
          f"→ lọt lưới: {len(fn)} · bị chặn thẳng: {blocked}/{len(advice)}")
    for v, t in fp:
        print(f"    BÁO ĐỘNG GIẢ {v:.2f}  {t[:60]}")
    for v, t in fn:
        print(f"    LỌT LƯỚI     {v:.2f}  {t[:60]}")

    if fp or fn:
        print("\nLệch khỏi phép đo đã chốt. Model đã trôi hoặc câu hỏi bị sửa.")
        print("DỪNG LẠI XEM — đừng nới ngưỡng cho xanh.")
        return 1
    print(f"\nkhớp phép đo 2026-09-24 (sạch ≤ 0,08 · bẩn ≥ 0,21)")
    return 0


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="Kiểm pillars cho repo thị trường")
    ap.add_argument("--repo", help="đường dẫn repo cần kiểm")
    ap.add_argument("--no-jev", action="store_true", help="chỉ chạy tầng grep")
    ap.add_argument("--selftest", action="store_true", help="đo lại ngưỡng Jev")
    a = ap.parse_args()

    key = os.environ.get("TYPESAFE_API_KEY")

    if a.selftest:
        if not key:
            print("thiếu TYPESAFE_API_KEY — không tự kiểm được"); return 2
        return selftest(key)

    if not a.repo:
        ap.error("cần --repo hoặc --selftest")
    repo = os.path.abspath(a.repo)
    if not os.path.isdir(repo):
        print(f"không thấy thư mục {repo}"); return 2

    print(f"pillar_guard · {os.path.basename(repo)}")

    hits = grep_pass(repo)
    print(f"\n[1/2] grep tất định: {len(hits)} vi phạm")
    for h in hits:
        print(f"  {h['file']}:{h['line']}  {h['pillar']} {h['rule']}")
        print(f"      {h['why']}")
        print(f"      {h['text']}")

    advice_hits, warns = [], []
    if a.no_jev:
        print("\n[2/2] Jev: bỏ qua (--no-jev)")
    elif not key:
        # KHÔNG âm thầm bỏ qua: guard thiếu một tầng mà vẫn báo 'sạch' thì tệ
        # hơn là guard không chạy.
        print("\n[2/2] Jev: KHÔNG chạy được — thiếu TYPESAFE_API_KEY.")
        print("      Kết quả dưới đây CHỈ gồm tầng grep, chưa đủ để gọi là sạch.")
        return 1 if hits else 3
    else:
        strings = collect_strings(repo)
        print(f"\n[2/2] Jev: soi {len(strings)} chuỗi hiển thị "
              f"(cảnh báo ≥ {ADVICE_WARN} · chặn ≥ {ADVICE_FAIL})")
        scores = ask_jev(key, [t for _, _, t in strings])
        for (f, ln, t), v in zip(strings, scores):
            if v >= ADVICE_FAIL:
                advice_hits.append((f, ln, t, v))
                print(f"  CHẶN     {f}:{ln}  §7 khuyến nghị ({v:.2f})")
                print(f"           {t[:96]}")
            elif v >= ADVICE_WARN:
                warns.append((f, ln, t, v))
        if warns:
            print(f"\n  {len(warns)} chuỗi trong vùng cảnh báo — cần người xem, "
                  "KHÔNG tự động chặn:")
            for f, ln, t, v in warns:
                print(f"    {f}:{ln}  ({v:.2f})  {t[:80]}")
        if not advice_hits and not warns:
            mx = max(scores) if scores else 0.0
            print(f"  sạch · cao nhất {mx:.2f}")

    total = len(hits) + len(advice_hits)
    tail = f" · {len(warns)} cảnh báo" if warns else ""
    print(f"\n{'SẠCH' if total == 0 else f'{total} VI PHẠM'}{tail}")
    # Cảnh báo KHÔNG làm đỏ: một cổng đỏ vì chuyện cần bàn sẽ bị người ta tắt đi.
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
