"""Kiểm mọi artifact dữ liệu theo `contract/envelope.schema.json`.

VÌ SAO TỒN TẠI
--------------
Đo 2026-09-30 trên 6 artifact đang chạy: sáu cái có sáu kiểu metadata khác
nhau (tốt nhất khai đủ kỳ/nguồn/quality/unit, kém nhất chỉ có một dấu thời
gian). Không thể viết MỘT hàm trả lời "số này của kỳ nào, từ đâu, tin được
bao nhiêu" cho cả ba thị trường. Phong bì sửa điều đó; công cụ này cưỡng chế.

MỘT CÔNG CỤ CHO BA STACK
------------------------
vn-market-site viết bằng Python stdlib, kiyohara bằng TypeScript,
jp_stock_undervaluation bằng CrewAI. Chia sẻ CODE qua ba runtime đó sẽ hỏng.
Nhưng artifact đều là JSON — nên một công cụ Python đọc được hết. Đó là lý do
kiến trúc chọn chia sẻ HỢP ĐỒNG chứ không chia sẻ THƯ VIỆN.

TỰ VIẾT BỘ KIỂM, KHÔNG DÙNG `jsonschema`
----------------------------------------
Pipeline chính cố tình stdlib-only để chạy nhẹ trong CI, và thêm dependency
vào đó là quyết định có chủ đích. Bộ kiểm dưới đây phủ đúng phần JSON Schema
mà envelope dùng: required · type · enum · const · pattern · minLength ·
minItems · minProperties · minimum/maximum · properties ·
additionalProperties (bool hoặc schema) · items.

Gặp từ khoá LẠ thì BÁO chứ không bỏ qua im lặng — một bộ kiểm lặng lẽ không
kiểm gì trông y hệt một bộ kiểm thấy mọi thứ đều đúng.

  py tools/validate.py --all
  py tools/validate.py --repo kiyohara
  py tools/validate.py --file ../vn-market-site/public/data/live.json
"""
from __future__ import annotations

import argparse
import glob
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
SCHEMA_PATH = os.path.join(ROOT, "contract", "envelope.schema.json")

# Từ khoá `_doc` là chú thích của chúng ta, không phải JSON Schema — bỏ qua.
KNOWN = {
    "$schema", "$id", "title", "_doc", "type", "required", "properties",
    "additionalProperties", "items", "enum", "const", "pattern", "minLength",
    "minItems", "minProperties", "minimum", "maximum",
}

TYPES = {
    "object": dict, "array": list, "string": str, "number": (int, float),
    "integer": int, "boolean": bool, "null": type(None),
}


def validate(node, schema: dict, path: str, errs: list[str]) -> None:
    unknown = set(schema) - KNOWN
    if unknown:
        # Không im lặng: một từ khoá mình chưa cài nghĩa là một luật KHÔNG
        # được kiểm, và người viết schema đang tưởng nó có hiệu lực.
        errs.append(f"{path}: schema dùng từ khoá validate.py chưa cài: {sorted(unknown)}")

    if "const" in schema and node != schema["const"]:
        errs.append(f"{path}: phải đúng bằng {schema['const']!r}, nhận {node!r}")
        return
    if "enum" in schema and node not in schema["enum"]:
        errs.append(f"{path}: phải thuộc {schema['enum']}, nhận {node!r}")
        return
    if "type" in schema:
        want = TYPES[schema["type"]]
        # bool là con của int trong Python — 'integer' không được nhận True.
        if isinstance(node, bool) and schema["type"] in ("integer", "number"):
            errs.append(f"{path}: cần {schema['type']}, nhận boolean")
            return
        if not isinstance(node, want):
            errs.append(f"{path}: cần {schema['type']}, nhận {type(node).__name__}")
            return

    if isinstance(node, str):
        if "pattern" in schema and not re.search(schema["pattern"], node):
            errs.append(f"{path}: {node!r} không khớp mẫu {schema['pattern']}")
        if "minLength" in schema and len(node) < schema["minLength"]:
            errs.append(f"{path}: cần ≥{schema['minLength']} ký tự, có {len(node)}")

    if isinstance(node, (int, float)) and not isinstance(node, bool):
        if "minimum" in schema and node < schema["minimum"]:
            errs.append(f"{path}: {node} < tối thiểu {schema['minimum']}")
        if "maximum" in schema and node > schema["maximum"]:
            errs.append(f"{path}: {node} > tối đa {schema['maximum']}")

    if isinstance(node, list):
        if "minItems" in schema and len(node) < schema["minItems"]:
            errs.append(f"{path}: cần ≥{schema['minItems']} phần tử, có {len(node)}")
        if "items" in schema:
            for i, it in enumerate(node):
                validate(it, schema["items"], f"{path}[{i}]", errs)

    if isinstance(node, dict):
        for k in schema.get("required", []):
            if k not in node:
                errs.append(f"{path}: THIẾU trường bắt buộc `{k}`")
        if "minProperties" in schema and len(node) < schema["minProperties"]:
            errs.append(f"{path}: cần ≥{schema['minProperties']} khoá, có {len(node)}")
        props = schema.get("properties", {})
        for k, v in node.items():
            if k in props:
                validate(v, props[k], f"{path}.{k}", errs)
            else:
                ap = schema.get("additionalProperties")
                if ap is False:
                    errs.append(f"{path}: khoá lạ `{k}` (schema cấm thêm trường)")
                elif isinstance(ap, dict):
                    validate(v, ap, f"{path}.{k}", errs)


# --------------------------------------------------------------- kiểm ngữ cảnh

def cross_checks(env: dict, registry: dict, path: str) -> list[str]:
    """Những thứ JSON Schema không diễn đạt được, nhưng sai thì rất đắt."""
    out = []

    prod = env.get("product")
    if prod and prod not in registry.get("products", {}):
        out.append(f"product `{prod}` không có trong registry.json — "
                   f"một tên không ai khai là một tên sẽ trôi")

    per = env.get("period") or {}
    asof, gen = per.get("asof"), env.get("generatedAt")
    if isinstance(asof, str) and isinstance(gen, str) and asof > gen[:10]:
        # Kỳ dữ liệu nằm SAU lúc chạy = nhìn trộm tương lai, hoặc lẫn hai khái niệm.
        out.append(f"period.asof ({asof}) SAU generatedAt ({gen[:10]}) — "
                   f"kỳ dữ liệu không thể ở tương lai so với lúc chạy")

    cov = env.get("coverage")
    if cov:
        w, g = cov.get("wanted"), cov.get("got")
        if isinstance(w, int) and isinstance(g, int):
            if g > w:
                out.append(f"coverage.got ({g}) > wanted ({w})")
            if w and cov.get("pct") is not None:
                real = g / w * 100
                if abs(real - cov["pct"]) > 0.5:
                    out.append(f"coverage.pct {cov['pct']} ≠ got/wanted = {real:.1f} "
                               f"— đường tính thứ hai không khớp")

    for s in env.get("source") or []:
        if s.get("robots") == "cấm":
            out.append(f"nguồn `{s.get('name')}` khai robots='cấm' mà vẫn đang dùng")

    return out


# --------------------------------------------------------------- thu thập file

def artifacts_from_registry(registry: dict, only: str | None) -> list[tuple[str, str]]:
    out = []
    for name, p in registry.get("products", {}).items():
        if name.startswith("_"):
            continue
        repo = p.get("repo")
        if only and repo != only:
            continue
        for pat in p.get("artifacts", []):
            if not pat.endswith((".json", ".jsonl")):
                continue          # .ts sinh ra thì không mang phong bì JSON
            for f in sorted(glob.glob(os.path.join(STOCK, repo, pat))):
                out.append((name, f))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--file", default=None)
    a = ap.parse_args()
    if not (a.all or a.repo or a.file):
        ap.error("cần --all, --repo <tên> hoặc --file <đường dẫn>")

    schema = json.load(open(SCHEMA_PATH, encoding="utf-8"))
    registry = json.load(open(os.path.join(ROOT, "registry.json"), encoding="utf-8"))

    items = ([("(--file)", a.file)] if a.file
             else artifacts_from_registry(registry, a.repo))

    print(f"validate · phong bì {schema['title']} · {len(items)} artifact")
    n_ok = n_bad = n_none = 0
    for prod, f in items:
        rel = os.path.relpath(f, STOCK).replace("\\", "/")
        try:
            if f.endswith(".jsonl"):
                # .jsonl không mang phong bì: nó là chuỗi dòng, phong bì nằm ở
                # artifact JSON cùng sản phẩm. Ghi nhận chứ không bắt lỗi.
                n_none += 1
                print(f"   —      {rel}  (.jsonl — phong bì nằm ở artifact JSON cùng sản phẩm)")
                continue
            d = json.load(open(f, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            n_bad += 1
            print(f"   HỎNG   {rel}  đọc lỗi: {type(e).__name__}")
            continue

        if "_envelope" not in d:
            n_none += 1
            print(f"   THIẾU  {rel}  chưa có `_envelope`")
            continue

        errs: list[str] = []
        validate(d, schema, "", errs)
        errs += cross_checks(d["_envelope"], registry, rel)
        if errs:
            n_bad += 1
            print(f"   SAI    {rel}  ({len(errs)} lỗi)")
            for e in errs[:8]:
                print(f"            · {e}")
            if len(errs) > 8:
                print(f"            … và {len(errs) - 8} lỗi nữa")
        else:
            n_ok += 1
            env = d["_envelope"]
            print(f"   ok     {rel}  {env['market']}/{env['product']} · "
                  f"kỳ {env['period']['asof']} ({env['period']['kind']})")

    print(f"\n{n_ok} đạt · {n_bad} sai · {n_none} chưa có phong bì")
    if n_none:
        print("  'chưa có phong bì' KHÔNG phải 'đạt' — artifact đó vẫn chưa nói được "
              "kỳ nào, nguồn nào, tin được bao nhiêu.")
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
