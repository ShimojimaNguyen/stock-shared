# stock-shared

Lớp chung cho bốn repo phân tích thị trường đứng cạnh nhau trong `Stock/`:
`vn-market-site`, `kiyohara`, `jp-market-dashboard`, `jp_stock_undervaluation`.

**Mỗi thứ trong đây được định nghĩa đúng một lần.** Trước khi thêm gì vào repo
con, hỏi: cái này có phải luật riêng của stack đó không? Nếu không — nó thuộc
về đây.

---

## Vì sao tồn tại

Bốn repo là bốn git repo độc lập, không có repo cha. Hệ quả đo được trước khi
lập repo này:

- `financial-analyst-review` và `financial-data-verification` — 230 dòng luật
  tài chính **hoàn toàn trung lập thị trường** — chỉ nằm trong `vn-market-site`.
  Ba repo còn lại không nhìn thấy, nên không thể áp dụng.
- `vn-dashboard-engineering` và `kiyohara-engineering` nói lại **cùng một bộ
  nguyên tắc** cho hai stack khác nhau, và đã bắt đầu lệch nhau.
- Kiến thức về Jev bị nhốt trong `kiyohara/CLAUDE.md`.

---

## Cách phát hành

Claude Code chỉ nhận skill ở `.claude/skills/<tên>/SKILL.md` — **đúng một cấp**.
Nên submodule đặt tại `.claude/skills/shared/` sẽ *không* được nhận diện. Cách
làm ở đây: giữ nguồn sự thật trong git repo này, rồi **sync sang mức user**.

```powershell
pwsh scripts/sync.ps1        # Windows
```
```bash
bash scripts/sync.sh         # Git Bash / macOS / Linux
```

Sync chép `skills/*` → `~/.claude/skills/` và `agents/*` → `~/.claude/agents/`.
Sau đó **mọi** repo trên máy này thấy chúng, không repo con nào giữ bản sao.

`--check` để xem lệch mà không chép. `--prune` để xoá thứ đã bỏ khỏi repo.

### Khi chưa sync

Skill sẽ vắng mặt. Agent phụ thuộc nó phải **dừng lại và báo**, không được chạy
tiếp trong im lặng — một agent mất bộ luật của nó thì nguy hiểm hơn một agent
không chạy.

---

## Nội dung

### `skills/`

| skill | vai trò |
|---|---|
| `data-integrity-pillars` | Pillars phát triển: `—` chứ không `0`, as-of + nguồn, nhãn tin cậy, look-ahead, idempotent. **Đọc trước mọi việc đụng số.** |
| `financial-analyst-review` | Pillars phân tích: soi *định nghĩa*, không soi số học. DCF, PER point-in-time, 連結/個別. |
| `financial-data-verification` | Quy trình kiểm số so với định nghĩa chuẩn: đơn vị, đẳng thức, thứ bậc nguồn, đối chiếu độc lập. |
| `jev-judgments` | Dùng Jev (TypeSafe System One) cho phán đoán ngữ nghĩa — hợp đồng, giới hạn đã đo, các bẫy. |
| `market-data-sources` | Sổ tra nguồn dữ liệu đã KIỂM CHỨNG: cái nào chạy, cái nào không và vì sao. |
| `agent-memory` | Ba tầng bộ nhớ và cách đọc/ghi Obsidian vault. |

### `agents/`

| agent | vai trò |
|---|---|
| `pillar-auditor` | Soát pillars, trung lập thị trường, **chỉ đọc**. Chạy được ở bất kỳ repo nào — khác với `vn-frontend-reviewer` (chỉ VN) và `kiyohara-review` (chỉ kiyohara). |

### `tools/`

| công cụ | vai trò |
|---|---|
| `pillar_guard.py` | Kiểm pillars hai tầng: grep tất định + Jev cho thứ grep không bắt được (câu khuyến nghị diễn đạt vòng). |

---

## Ranh giới

**Thuộc về đây**: luật đúng cho mọi thị trường và mọi stack.

**KHÔNG thuộc về đây**: 7 entry Vite của VN, bẫy base path GitHub Pages, cổng
scanner của kiyohara, `alignToWeeks`, bộ đọc OLE2/BIFF8. Những thứ đó ở lại
skill engineering của từng repo.

Phép thử: *"luật này có còn đúng nếu ngày mai thêm một thị trường thứ tư và một
stack khác không?"* Có → vào đây. Không → ở lại repo con.
