"""Một lệnh trả lời: có sản phẩm dữ liệu nào đang chết mà không ai biết không?

VÌ SAO TỒN TẠI
--------------
Ngày 2026-09-29 tôi phát hiện `regime.json`, `cashout-vn.json`, `sector-flows.json`
đứng yên ở 24/09 — **năm ngày, ba phiên**, workflow đỏ hai lần, và không chỗ
nào nói ra. Tôi tìm ra nó bằng cách mở từng file đọc `asof`, rồi gọi API
GitHub xem workflow, rồi so `main` với `origin/main`. Một chuỗi thao tác tay.

Lần sau tôi sẽ không nhớ làm chuỗi đó. Nên nó thành lệnh này.

BỐN CÂU HỎI, VÀ VÌ SAO PHẢI ĐỦ CẢ BỐN
-------------------------------------
Đợt hỏng vừa rồi chỉ lộ ra khi ghép đủ bốn mảnh — thiếu mảnh nào cũng ra kết
luận sai:

  1. artifact có cũ quá nhịp đã khai không?   → thấy TRIỆU CHỨNG
  2. workflow sinh ra nó lần cuối xanh khi nào? → thấy NGUYÊN NHÂN
  3. local và origin có lệch nhau không?        → bản vá có thật sự lên CI chưa
  4. lớp chung trên máy có cũ không?            → agent có đang chạy theo luật cũ

Chỉ nhìn (1) sẽ tưởng nguồn dữ liệu hỏng. Chỉ nhìn (2) sẽ tưởng đã sửa xong
— tôi suýt kết luận thế, cho tới khi (3) cho thấy bản vá vào lúc 29/09 còn
lần chạy đỏ cuối là 28/09: **bản vá chưa từng được CI chạy thử.**

KHÔNG ĐOÁN
----------
Không đọc được `asof` → in `—` và tính là KHÔNG BIẾT, không tính là tươi.
Không gọi được API GitHub → nói rõ là không kiểm được, không báo xanh.
Một công cụ giám sát báo xanh vì nó mù thì tệ hơn không có công cụ.

  py tools/check.py --all
  py tools/check.py --repo vn-market-site
  py tools/check.py --all --no-net      (bỏ qua phần cần mạng)
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

# Console Windows ở máy này là cp932, báo cáo thì đầy tiếng Việt. Không ép
# UTF-8 thì `print` ném UnicodeEncodeError và công cụ chết giữa chừng — đúng
# lỗi đã xảy ra với `pillar_guard.py`.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK = os.path.dirname(ROOT)

# Ngân sách độ trễ, tính bằng PHIÊN (bỏ thứ Bảy/Chủ Nhật), theo `cadence`.
#
# `daily` = 2 chứ không phải 1: pipeline chạy sau giờ đóng cửa, nên sáng hôm
# sau artifact mang `asof` của phiên trước là BÌNH THƯỜNG. Đặt 1 sẽ báo động
# mỗi sáng, và một cổng luôn đỏ sẽ bị tắt trong vòng một ngày.
#
# ⚠ Không có lịch nghỉ lễ VN/JP ở đây. Tết hoặc Golden Week sẽ báo động giả.
# Đây là giới hạn đã biết — xem CLAUDE.md §1.2; đừng hardcode bảng nghỉ lễ.
BUDGET_SESSIONS = {"daily": 2, "weekly": 7, "monthly": 25, "manual": None}

OK, WARN, BAD, UNK = "ok", "cũ", "HỎNG", "?"


# ------------------------------------------------------------------ tiện ích

def sessions_between(d: dt.date, today: dt.date) -> int:
    """Số phiên (ngày trong tuần) từ `d` tới `today`, không tính `d`.

    Thứ Sáu → thứ Hai ra 1, không phải 3. Không biết ngày nghỉ lễ."""
    if d >= today:
        return 0
    n, cur = 0, d
    while cur < today:
        cur += dt.timedelta(days=1)
        if cur.weekday() < 5:
            n += 1
    return n


def parse_date(v) -> dt.date | None:
    if not isinstance(v, str):
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v)
    return dt.date(int(m[1]), int(m[2]), int(m[3])) if m else None


def artifact_date(path: str) -> tuple[dt.date | None, str]:
    """Kỳ dữ liệu của một artifact + nói rõ đọc được từ trường nào.

    Ưu tiên `asof`/`date` (ngày PHIÊN) hơn `generatedAtIct` (giờ script chạy).
    Hai thứ đó khác nhau, và lẫn lộn chúng chính là lỗi mà CLAUDE.md §1.2 nói:
    một script chạy hôm nay vẫn có thể ghi ra dữ liệu của tuần trước."""
    try:
        if path.endswith((".ts", ".js")):
            # Artifact do script sinh ra dạng mã nguồn (universe.ts, fx-roles.ts).
            # Chúng khai kỳ bằng một hằng số, không phải JSON.
            txt = open(path, encoding="utf-8").read(200_000)
            m = re.search(r'(?:SNAPSHOT|AS_OF|ASOF|GENERATED_AT|_DATE)\s*=\s*"'
                          r'(\d{4}-\d{2}-\d{2})', txt)
            if m:
                return dt.date(*map(int, m[1].split("-"))), "hằng số trong mã"
            return None, "file .ts không khai hằng số ngày nào"
        if path.endswith(".jsonl"):
            last = None
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        last = line
            if not last:
                return None, "file rỗng"
            row = json.loads(last)
            # `week` là của JP (tuần 投資部門別), `issue_date` của đấu thầu
            # TPCP. Mỗi nguồn gọi kỳ dữ liệu một tên; danh sách này phải phủ
            # HẾT, vì một tên thiếu ở đây biến thành một dòng "?" trông vô hại.
            for k in ("date", "asof", "week", "auctionDate", "issue_date"):
                if (d := parse_date(row.get(k))):
                    return d, f"dòng cuối .{k}"
            # Nêu ĐÍCH DANH các trường trông như ngày mà không đọc được —
            # "không có trường ngày" là câu vô dụng, người đọc phải đi mở file.
            #
            # Và tuyệt đối không đoán: `investor.jsonl` của jp-market-dashboard
            # có `fileStamp: "260902"` trông y hệt YYMMDD. Nó KHÔNG phải vậy —
            # `26`+`09`+`02` là năm 2026, tháng 9, TUẦN 2, khớp với
            # `week: "09/07～09/11"`. Đọc như YYMMDD ra 2026-09-02, sớm 5 ngày
            # và trông hoàn toàn hợp lý. Thà mù mà biết mình mù.
            cand = [k for k in row
                    if re.search(r"date|week|stamp|time|at$|asof", k, re.I)]
            return None, ("dòng cuối không có trường ngày đọc được"
                          + (f" · thấy {', '.join(f'{k}={row[k]!r}' for k in cand[:3])}"
                             if cand else ""))
        with open(path, encoding="utf-8") as f:
            j = json.load(f)
        if not isinstance(j, dict):
            return None, "không phải object"
        for k in ("asof", "date", "week", "latestWeek", "fetchedAt",
                  "generatedAtIct", "generatedAtJst", "scannedAt"):
            if (d := parse_date(j.get(k))):
                return d, f".{k}"
        return None, "không có trường ngày nào nhận ra được"
    except FileNotFoundError:
        return None, "KHÔNG TỒN TẠI"
    except Exception as e:  # noqa: BLE001
        return None, f"đọc lỗi: {type(e).__name__}"


def git(repo: str, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, timeout=30)
        return r.stdout.decode("utf-8", "replace").strip() if r.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


def gh_api(url: str):
    h = {"User-Agent": "stock-check", "Accept": "application/vnd.github+json"}
    # Không đăng nhập thì GitHub cho 60 lần/giờ — 5 repo × nhiều workflow là
    # vượt ngay. Có token thì 5000. Chỉ đọc từ env, không bao giờ ghi ra đâu.
    if (tok := os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")):
        h["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=25) as f:
        return json.load(f)


# ------------------------------------------------------------------ các kiểm

def check_freshness(reg: dict, today: dt.date, only: str | None) -> list[dict]:
    out = []
    for name, p in reg["products"].items():
        if name.startswith("_"):
            continue
        repo = p.get("repo")
        if only and repo != only:
            continue
        budget = BUDGET_SESSIONS.get(p.get("cadence"), None)
        base = os.path.join(STOCK, repo)
        for pat in p.get("artifacts", []):
            paths = sorted(glob.glob(os.path.join(base, pat)))
            if not paths:
                out.append({"product": name, "file": pat, "state": BAD,
                            "age": None, "why": "KHÔNG TỒN TẠI"})
                continue
            # Với glob (history/*.jsonl) chỉ xét file MỚI NHẤT — các năm cũ
            # đứng yên là đúng, báo động ở đó là báo động giả.
            for path in ([paths[-1]] if "*" in pat else paths):
                d, why = artifact_date(path)
                rel = os.path.relpath(path, base).replace("\\", "/")
                if d is None:
                    out.append({"product": name, "file": rel, "state": UNK,
                                "age": None, "why": why})
                    continue
                age = sessions_between(d, today)
                state = OK if (budget is None or age <= budget) else (
                    BAD if age > (budget or 0) * 2 else WARN)
                out.append({"product": name, "file": rel, "state": state, "age": age,
                            "why": f"{why} = {d} · nhịp {p.get('cadence')} "
                                   f"(ngân sách {budget if budget is not None else '—'} phiên)"})
    return out


def check_git(reg: dict, only: str | None) -> list[dict]:
    out = []
    for name in reg["repos"]:
        if only and name != only:
            continue
        repo = os.path.join(STOCK, name)
        if not os.path.isdir(os.path.join(repo, ".git")):
            out.append({"repo": name, "state": UNK, "why": "không phải git repo"})
            continue
        url = git(repo, "remote", "get-url", "origin")
        if not url:
            # Không phải lỗi vặt: lớp chung là nguồn sự thật cho MỌI repo còn
            # lại, và nó chỉ tồn tại trên một cái máy.
            out.append({"repo": name, "state": BAD,
                        "why": "KHÔNG CÓ REMOTE — chỉ tồn tại trên máy này"})
            continue
        branch = git(repo, "branch", "--show-current") or "?"
        git(repo, "fetch", "-q", "origin")
        ahead = git(repo, "rev-list", "--count", f"origin/{branch}..{branch}")
        behind = git(repo, "rev-list", "--count", f"{branch}..origin/{branch}")
        dirty = bool(git(repo, "status", "--porcelain"))
        bits = []
        if ahead and ahead != "0":
            bits.append(f"{ahead} commit CHƯA đẩy")
        if behind and behind != "0":
            bits.append(f"{behind} commit chưa kéo về")
        if dirty:
            bits.append("có thay đổi chưa commit")
        out.append({"repo": name, "url": url, "branch": branch,
                    "state": WARN if bits else OK,
                    "why": " · ".join(bits) if bits else f"{branch} khớp origin, sạch"})
    return out


def check_ci(reg: dict, only: str | None) -> list[dict]:
    """Workflow lần cuối XANH khi nào — và bản vá mới nhất đã được chạy chưa.

    Câu thứ hai mới là câu quan trọng: một repo có commit sửa CI nhưng chưa
    có lần chạy nào SAU commit đó thì chưa sửa xong, nó chỉ chưa được thử."""
    out = []
    for name in reg["repos"]:
        if only and name != only:
            continue
        repo = os.path.join(STOCK, name)
        url = git(repo, "remote", "get-url", "origin") or ""
        m = re.search(r"github\.com[:/]+([^/]+)/([^/.]+)", url)
        if not m:
            continue
        slug = f"{m[1]}/{m[2]}"
        try:
            wfs = gh_api(f"https://api.github.com/repos/{slug}/actions/workflows")["workflows"]
        except urllib.error.HTTPError as e:
            # Mã số là thứ sửa được: 403 = hết hạn mức 60 lần/giờ cho gọi
            # không đăng nhập (chờ, hoặc đặt GITHUB_TOKEN); 404 = repo riêng
            # tư, cần token. Một dòng "HTTPError" trơ trụi thì không ai biết
            # phải làm gì — tôi đã nhận đúng dòng đó và phải đi đo lại bằng tay.
            hint = {403: "hết hạn mức 60 lần/giờ (không đăng nhập) — đặt GITHUB_TOKEN",
                    401: "token sai", 404: "repo riêng tư hoặc sai tên — cần GITHUB_TOKEN"}
            out.append({"repo": name, "wf": "(tất cả)", "state": UNK,
                        "why": f"API GitHub trả {e.code}"
                               + (f" · {hint[e.code]}" if e.code in hint else "")})
            continue
        except Exception as e:  # noqa: BLE001
            out.append({"repo": name, "wf": "(tất cả)", "state": UNK,
                        "why": f"không gọi được API GitHub: {type(e).__name__}"})
            continue
        for w in wfs:
            if w.get("state") != "active" or "/" not in w.get("path", ""):
                continue
            try:
                runs = gh_api(f"https://api.github.com/repos/{slug}/actions/workflows"
                              f"/{w['id']}/runs?per_page=15")["workflow_runs"]
            except Exception:  # noqa: BLE001
                continue
            if not runs:
                continue
            last = runs[0]
            green = next((r for r in runs if r["conclusion"] == "success"), None)
            state = OK if last["conclusion"] == "success" else BAD
            why = (f'lần cuối {last["created_at"][:10]} → {last["conclusion"]} '
                   f'({last["event"]})')
            if state == BAD:
                why += (f' · xanh gần nhất {green["created_at"][:10]}'
                        if green else " · CHƯA TỪNG XANH trong 15 lần gần đây")
            out.append({"repo": name, "wf": w["name"][:52], "state": state, "why": why,
                        "last_run_at": last["created_at"]})
    return out


def check_shared() -> dict:
    sh = os.path.join(ROOT, "scripts", "sync.sh")
    if not os.path.isfile(sh):
        return {"state": UNK, "why": "không thấy scripts/sync.sh"}
    try:
        r = subprocess.run(["bash", sh, "--check"], capture_output=True, timeout=90, cwd=ROOT)
        txt = r.stdout.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return {"state": UNK, "why": f"không chạy được sync.sh: {type(e).__name__}"}
    lech = [l.strip() for l in txt.splitlines() if "LỆCH" in l or "BỎ QUA" in l]
    return ({"state": WARN, "why": f"{len(lech)} mục lệch: " + " · ".join(lech[:4])}
            if lech else {"state": OK, "why": "~/.claude khớp stock-shared"})


# ------------------------------------------------------------------ in ra

MARK = {OK: "  ok  ", WARN: " CŨ   ", BAD: " HỎNG ", UNK: "  ?   "}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--no-net", action="store_true", help="bỏ kiểm CI và fetch git")
    a = ap.parse_args()
    if not a.all and not a.repo:
        ap.error("cần --all hoặc --repo <tên>")

    reg = json.load(open(os.path.join(ROOT, "registry.json"), encoding="utf-8"))
    today = dt.date.today()
    print(f"check · {today} · registry v{reg.get('version')}"
          + (f" · chỉ {a.repo}" if a.repo else " · 5 repo"))

    bad = warn = unk = 0

    print("\n[1/4] Độ tươi artifact — có cũ quá nhịp đã khai không?")
    rows = check_freshness(reg, today, a.repo)
    for r in sorted(rows, key=lambda x: (x["state"] != BAD, x["state"] != WARN, x["file"])):
        age = "—" if r["age"] is None else f'{r["age"]}p'
        print(f'  {MARK[r["state"]]} {age:>4}  {r["product"]:<12} {r["file"]:<38} {r["why"]}')
        bad += r["state"] == BAD; warn += r["state"] == WARN; unk += r["state"] == UNK

    print("\n[2/4] Git — bản vá đã lên remote chưa?")
    if a.no_net:
        print("  (bỏ qua: --no-net)")
    else:
        for r in check_git(reg, a.repo):
            print(f'  {MARK[r["state"]]}       {r["repo"]:<24} {r["why"]}')
            bad += r["state"] == BAD; warn += r["state"] == WARN; unk += r["state"] == UNK

    print("\n[3/4] CI — workflow lần cuối xanh khi nào?")
    if a.no_net:
        print("  (bỏ qua: --no-net)")
    else:
        rows = check_ci(reg, a.repo)
        if not rows:
            print("  (không repo nào có remote GitHub đọc được)")
        for r in sorted(rows, key=lambda x: x["state"] != BAD):
            print(f'  {MARK[r["state"]]}       {r["repo"]:<18} {r["wf"]:<40} {r["why"]}')
            bad += r["state"] == BAD; warn += r["state"] == WARN; unk += r["state"] == UNK

    print("\n[4/4] Lớp chung — ~/.claude có khớp stock-shared không?")
    s = check_shared()
    print(f'  {MARK[s["state"]]}       {s["why"]}')
    bad += s["state"] == BAD; warn += s["state"] == WARN; unk += s["state"] == UNK

    print(f"\n{bad} HỎNG · {warn} cũ · {unk} không kiểm được")
    if unk:
        print("  'không kiểm được' KHÔNG phải 'ổn'. Mỗi dòng ? là một chỗ công cụ này mù.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
