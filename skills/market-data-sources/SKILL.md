---
name: market-data-sources
description: Sổ tra nguồn dữ liệu thị trường VN và JP đã KIỂM CHỨNG thật — endpoint nào chạy, endpoint nào không và vì sao, cạm bẫy của từng nguồn. Đọc TRƯỚC khi đi tìm nguồn cho một trường dữ liệu mới, để khỏi dò lại từ đầu.
---

# Nguồn dữ liệu thị trường — đã kiểm chứng

Mỗi dòng dưới đây là **kết quả thử thật**, không phải phỏng đoán. Ghi cả nguồn
đã LOẠI và lý do, vì phần lớn thời gian dò nguồn bị đốt vào việc thử lại những
thứ người trước đã thử và bỏ.

Kiểm lần cuối: **2026-09-20**. Endpoint web đổi mà không báo — thấy sai thì
sửa file này ngay, đừng để nó thành bản đồ cũ.

**Trước khi thêm bất kỳ nguồn nào**: đọc `robots.txt` và ghi lại chỉ thị thật
vào đây. CLAUDE.md §1.5 cấm scrape site có ToS cấm. Và không bao giờ né bot
protection (Cloudflare challenge, CSRF) — đó là ranh giới khác với scrape.

---

## 1. Việt Nam

### 1.1 VNDirect finfo — nguồn chính, không cần key

`https://api-finfo.vndirect.com.vn/v4/<resource>?q=<filter>&size=N`
Bộ lọc dạng `field:value~field2:value2`. robots: Cloudflare mặc định,
`User-agent: *  Allow: /` (có chặn `ClaudeBot`, xem §4).

| Resource | Cho gì | Dùng ở |
|---|---|---|
| `stock_prices` | giá/khối lượng từng mã theo `date` | `daily_update.py: fetch_breadth` |
| `foreigns` | `buyVal/sellVal/netVal` từng mã theo `tradingDate` | `daily_update.py: fetch_foreign` |
| `bonds` | metadata trái phiếu | — |

**Cạm bẫy đã sập:**

- `foreigns` trả cả dòng `type: "INDEX"` — **dòng tổng hợp cấp chỉ số**, không
  phải một mã. Cộng chung với từng mã là đếm hai lần cả thị trường: 2026-09-11
  các dòng INDEX thêm −8.831 tỷ, biến ròng −834 tỷ thành −10.575 tỷ. Số sai đó
  lớn hơn cả tổng GTGD phiên (16.123 tỷ). **Chỉ lấy `type == "STOCK"`.**
- `foreigns` trả chứng quyền **hai lần**, một lần `EW` một lần `CW` (287 mã
  trùng ở phiên trên). Giá trị 0 nên vô hại hôm đó, không phải mãi mãi.
- `stock_prices` dùng trường ngày là `date`; `foreigns` dùng `tradingDate`.
  Nhầm sẽ ra `totalElements: 0` chứ không báo lỗi.
- `stock_prices` **không có** trường khối ngoại; `bonds` **chỉ có trái phiếu
  doanh nghiệp**, không có giá, không có coupon. Không có type trái phiếu trong
  `stock_prices` (chỉ STOCK/ETF/IFC).

**Cổng kiểm nên dùng**: `a+d+u == totalElements` (breadth), `mua − bán == ròng`
(foreign), số mã không trùng, số dòng hợp lý so với quy mô sàn.

### 1.2 HNX — lợi suất trái phiếu Chính phủ

`POST https://www.hnx.vn/ModuleReportBonds/Bond_DauThau/Bond_KetQua_DauThau_Default`
body `p_keysearch=&p_pageIndex=1`, header `X-Requested-With: XMLHttpRequest` +
`Referer` trang đấu thầu. Trả **bảng HTML** `<table id="_tableDatas">`.
robots.txt: **404 — không tuyên bố hạn chế nào**.

Cột quan trọng (0-index): 1 `Đợt đấu thầu` · 5 `Kỳ hạn` · 7 `Ngày phát hành` ·
11 `GT trúng thầu` · 18 `Lãi suất trúng thầu`.

**Cạm bẫy:**

- **Đấu thầu trượt vẫn có dòng**: `GT trúng thầu = 0`, lãi suất hiện `0` hoặc
  rỗng. Đọc thẳng là công bố "lợi suất 30 năm = 0%". Phiên 2026-09-10 có 3/5 kỳ
  hạn như vậy. Chỉ nhận dòng `GT trúng thầu > 0` VÀ `lãi suất > 0`.
- **Chỉ trả 10 dòng gần nhất**, không nhận tham số phân trang nào (đã thử
  `p_pageIndex` / `pageIndex` / `p_currentpage` / `p_recordonpage` /
  `txtFromDate` — đều trả đúng 10 dòng đó). Nên phải **tích luỹ** qua nhiều
  ngày: xem `automation/vn_bond_yields.py`, khoá theo mã đợt.
- **TLS: HNX không gửi cert trung gian.** Python stdlib không dựng được chuỗi,
  mọi kết nối hỏng (`openssl` code 21). KHÔNG tắt verify — cert trung gian
  GlobalSign đóng gói sẵn ở `automation/certs/`, nạp qua
  `ctx.load_verify_locations(cafile=...)`. **Hết hạn 2027-07-16**, tải lại ở
  `http://secure.globalsign.com/cacert/gsgccr3evtlsca2025.crt`.
- Đây là lợi suất **sơ cấp**, chỉ đổi vào ngày đấu thầu → `quality = "proxy"`,
  không bao giờ `live`, và mỗi kỳ hạn mang ngày riêng.

### 1.3 Vietcombank — tỷ giá

`https://www.vietcombank.com.vn/api/exchangerates?date=YYYY-MM-DD` → JSON.
robots: `User-agent: *  Allow: /`.
Cũng có `https://portal.vietcombank.com.vn/UserControls/TVPortal.TyGia/pXML.aspx`
(XML, tự ghi "one request every 5 minutes").

**Cạm bẫy:** tham số `date` được **echo nguyên văn** vào trường `Date` của
response kể cả khi không có bảng mới — hỏi thứ Bảy vẫn trả bảng thứ Sáu nhưng
`Date` ghi thứ Bảy. **Chỉ `UpdatedDate` nói thật.**

**KHÔNG PHẢI tỷ giá trung tâm.** `usdVnd`/`usdVndCentral` là tỷ giá NHNN, một
đại lượng khác (25.463 vs VCB mua CK 25.730 / bán 26.110). Ghi chung một key sẽ
tạo bậc nhảy 1–2,5% vô hình trên biểu đồ lịch sử. Dùng key riêng `usdVndVcb`.

### 1.4 Đã LOẠI (đừng thử lại)

| Nguồn | Vì sao |
|---|---|
| **VBMA** `vbma.org.vn/vi/market-data/government-bond-yield` | Có đúng đường cong lợi suất, nhưng là Laravel+Angular sau **Cloudflare challenge + CSRF**. Lấy được = né bot protection. Không làm |
| **SBV / NHNN** | robots cho phép (`Disallow:` rỗng) và trang tải được **với UA trình duyệt thật** (UA đơn giản bị chặn). Nhưng chưa tìm ra trang tỷ giá trung tâm dạng máy đọc được |
| **TCBS** `apipubaws.tcbs.com.vn` | 403 |
| **FireAnt** `restv2.fireant.vn` | 401, cần bearer token của tài khoản |
| **SSI iBoard** `iboard-api.ssi.com.vn/statistics/charts/defaultAllStocks` | Chạy, nhưng chỉ có danh sách mã. TPCP ở đó chỉ là **6 hợp đồng tương lai**, không phải đường cong. Không tìm ra endpoint giá |
| **vnstock** (thư viện) | Không có module trái phiếu/lãi suất. `Trading.price_history` (lấy lịch sử nhiều mã 1 lần) báo **NotImplementedError** ở cả nguồn `VCI` lẫn `KBS` |
| **worldgovernmentbonds.com** | robots mở hoàn toàn, nhưng đường cong render bằng JS |

### 1.5 Hạn mức vnstock (pipeline phụ)

Tier khách = **20 request/phút**, vượt là vnstock **tự dừng tiến trình** (không
phải ném exception bắt được). Giãn 3,2s giữa các lần gọi là an toàn. API key
miễn phí (vnstocks.com/login) nâng lên 60/phút — chưa cấu hình.

#### CÀI ĐẶT: vnstock không còn trên PyPI (đo 2026-09-29)

```bash
pip install --extra-index-url https://vnstocks.com/api/simple vnstock vnai
```

Thiếu `--extra-index-url` thì pip báo **`No matching distribution found`**, và
thông báo đó trông như lỗi mạng chứ không như "gói đã dời kho".

| kiểm | kết quả |
|---|---|
| `pypi.org/pypi/vnstock/json` | **404** |
| `pypi.org/pypi/vnai/json` | **404** |
| `pypi.org/pypi/pandas/json` | 200 — *đối chứng: PyPI và mạng bình thường* |
| `pypi.org/pypi/vnstock3/json` | 200 — gói **khác**, đừng nhầm |
| github.com/thinh-vu/vnstock | 200, còn hoạt động, release v4.0.9 (27/09) |

Giải thật đã kiểm (`--dry-run --ignore-installed`): **39 gói** ·
`vnstock 4.0.9` + `vnai 2.6.2` từ kho vnstocks · `pandas`/`numpy`/`requests` từ PyPI.
Không cần API key để **cài**; tier khách vẫn chạy được không khoá.

**Hậu quả thật**: workflow `vn-vnstock-update` đỏ từ 2026-09-25 (lần xanh cuối
09-24) đúng ở bước cài, và ba trang `regime` / `cashout` / `sector-flows` phục
vụ số liệu 5 ngày tuổi mà không trang nào nói ra — vì lúc đó chỉ 1/7 trang biết
tính độ tươi.

> Bài học đo lường: `pip install --dry-run` **không** chứng minh được gì khi gói
> đã có sẵn trên máy — nó trả "0 gói sẽ cài" và trông như thành công. Phải thêm
> `--ignore-installed` mới là giải lại từ đầu như CI.

Lớp `Vnstock()` đã **ngừng hỗ trợ từ 2025-08-31**, khuyến nghị chuyển
`vnstock.api`. Cả 3 script pipeline phụ còn dùng lớp cũ.

---

## 2. Nhật Bản

### 2.1 Yahoo Finance JP — xếp hạng GTGD ⭐ nguồn tốt nhất tìm được

`https://finance.yahoo.co.jp/stocks/ranking/tradingValueHigh?market=all&page=N`

robots: `User-agent: *` chỉ chặn `/cm/personal/...`, `/portfolio`, `/my` —
trang ranking **được phép**. Không khai `Crawl-delay`.

- **50 dòng/trang**, phân trang bằng `&page=N` (trang 1 không cần tham số).
- Cột: `順位` là **`<th>`**, còn lại **4 `<td>`**: `名称・コード・市場` /
  `取引値` / `前日比` / `売買代金`. Đòi ≥5 `<td>` sẽ ra 0 dòng — lỗi tôi đã mắc.
- `売買代金` là **yên, chính xác tới đồng** (vd `1,818,861,709,000`).
- Mỗi dòng có nhãn thị trường (`東証PRM`/`東証STD`/`東証GRT`) → lọc Prime được
  ngay từ `market=all`, không cần request riêng.
- Có `__PRELOADED_STATE__` nhúng nếu muốn parse JSON thay vì HTML.

**Đã đo độ hội tụ (2026-09-18, market=all):**

| Trang | Số mã | Luỹ kế | % tổng |
|---|---|---|---|
| 1 | 50 | 6,56兆円 | 58% |
| 10 | 500 | 10,42兆円 | 93% |
| **20** | **1.000** | **11,02兆円** | **98,2%** |
| 35 | 1.750 | 11,22兆円 | ~100% |

→ **20 trang là điểm dừng hợp lý**: 98,2% tổng GTGD, ~26 giây ở giãn cách 1,3s.
Đi tiếp 15 trang nữa chỉ thêm 1,8%.

Cùng dữ liệu này phục vụ được cả tổng GTGD, nhóm mã dẫn dắt, và (nếu có bảng
mã→ngành) cả phân rã theo ngành.

### 2.2 Yahoo chart API — giá/khối lượng từng mã, không cần key

`https://query1.finance.yahoo.com/v8/finance/chart/{ma}.T?range=5d&interval=1d`

Bắt buộc có `User-Agent`, nếu không trả "Edge: Too Many Requests". Hậu tố `.T`
cho JP, `.VN` cho VN, không hậu tố cho US. Đã dùng trong
`daily_update.py: fetch_yahoo_quote` và `jp_value_screen_graph/tools/market_data.py`.

`close × volume` = GTGD của mã đó (Toyota 2026-09-18: 3.025 × 46.568.200 =
1.409 億円).

**`v7/finance/quote?symbols=A,B,C` (lấy nhiều mã 1 request) trả HTTP 401** —
cần auth, không dùng được. Nên mỗi mã một request.

### 2.2b Yahoo JP trang từng mã — PER / PBR / EPS / BPS ⭐ nguồn duy nhất đủ bốn

`https://finance.yahoo.co.jp/quote/{code}.T` · không cần khoá · cần `User-Agent`

Đã thử **bốn** nguồn cho định giá từng mã (2026-09-29):

| nguồn | kết quả |
|---|---|
| Yahoo US `v7/finance/quote` | **401** |
| Yahoo US `v10/quoteSummary` (4 module) | **401 cả bốn** |
| Kabutan `/stock/?code=` | 200 nhưng **không có EPS/BPS**, và robots khai `Crawl-delay: 3` → 492 mã ≈ 25 phút |
| **Yahoo JP `/quote/{code}.T`** | 200, **có đủ** giá · PER · PBR · EPS · BPS |

`robots.txt` cho phép `/quote/` (chỉ chặn `/portfolio`, `/my`, `/cm/*`, ảnh tin),
**không khai crawl-delay**.

**⛔ KHÔNG LẤY HÀNG LOẠT — đã đo, nguồn chặn sau ~85 mã.**

Chạy thật 492 mã, nghỉ 150ms: **50 mã đầu OK, rồi HTTP 500 liên tục** cho
407 mã còn lại. Độ phủ 17,3%.

Và đó là **chặn kéo dài, không phải cửa sổ tần suất**:

| thử lại sau khi bị chặn | kết quả |
|---|---|
| ngay lập tức, 3 mã | 500 · 500 · 500 |
| nghỉ 60 giây, 3 mã | 500 · 500 · 500 |
| giãn 3 giây/request, 6 mã | 500 × 6 |

Nghĩa là một lần quét hàng loạt làm **mất nguồn cho mọi việc khác**, kể cả tra
một mã lẻ. Thời gian chặn chưa biết — và đừng dò bằng cách gọi thêm.

**Chỉ dùng cho tra lẻ vài mã.** Muốn phủ cả universe thì dùng §2.3b
(Kabutan `/stock/finance`) — đã thử và chạy được.

*Chi phí mỗi mã, nếu vẫn cần biết*: 62,6KB truyền (gzip; 490KB sau giải nén —
đừng nhầm hai con số, tôi đã nhầm một lần và suýt loại nguồn vì tưởng nặng 250MB).

**Cách đọc**: dữ liệu nằm trong JSON nhúng có **dấu nháy escape** — gỡ `\"`
trước, rồi tìm `"per":{…}`, `"pbr"`, `"eps"`, `"bps"`, `"price"`.

**Hai bẫy, cả hai đã cắn:**

1. **`"isLock":true` + `"value":"000.00"`** — trường sau tường phí. Đọc thẳng
   sẽ ra **PER = 0**, trông như một mã cực rẻ. Mọi trường có `isLock` phải
   thành `null`.
2. **Dấu phẩy ngăn nghìn.** `"value":"3,150.60"` — regex `[^",]+` cắt ở dấu
   phẩy và trả `3`. Không ném lỗi, chỉ ra một con số nhỏ **hợp lý**.

**Kiểm ngay tại nguồn**: `price/eps ≈ per` và `price/bps ≈ pbr`. Đo trên 12 mã:
**0 mã lệch quá 3%** (Toyota 0,01%). Đây là đường tính thứ hai mà `SD §8` đòi,
và nó cũng chính là thứ phát hiện lỗi dấu phẩy ở trên.

**Kỳ khác nhau**: PER/EPS thường là 会社予想, PBR/BPS là 実績 — trang ghi trong
`subText`. Đừng trộn dự phóng với thực hiện trong cùng một bảng.

Dùng ở `kiyohara/scripts/fetch_snapshots.ts`.

### 2.3b Kabutan `/stock/finance` — giá · PER · PBR · EPS ⭐ nguồn phủ nổi cả universe

`https://kabutan.jp/stock/finance?code={code}` · không cần khoá · cần `User-Agent`

Đây là câu trả lời cho khoảng trống mà §2.2b để lại: Yahoo JP đủ trường nhưng
chặn sau ~85 mã; trang này thiếu BPS nhưng **cho quét cả universe**.

| | |
|---|---|
| robots.txt (đọc thật 2026-09-29) | chỉ `Disallow: /94446337/` và `/search*`; **`Crawl-delay: 3`** |
| đo thật | 27,5KB truyền/mã → 492 mã ≈ 13,5MB, ≈ 25 phút ở nhịp 3s |
| chặn? | **không** — 18 mã liên tiếp ở nhịp 3s, 18/18 HTTP 200 |
| có | `price` · `PER` · `PBR` · `EPS` · **niên độ** · dấu thời gian `<time>` |
| **không có** | **BPS** |

**Đối chiếu chéo với Yahoo JP trên 12 mã trùng** (cùng ngày, 2026-09-29):

| trường | lệch tối đa |
|---|---|
| giá | **0,00%** — khớp 12/12 tới từng yên |
| PBR | 1,19% |
| PER | 1,75% · EPS 1,52% |

Và `lệch PER ≈ lệch EPS` ở **từng dòng** → lệch **có hệ thống** do cơ sở số cổ
phiếu khác nhau (Kabutan dùng `修正1株益`, đã điều chỉnh chia tách), không phải
nhiễu. Nên **đừng trộn hai nguồn vào một bảng** — mỗi bản ghi phải mang
`source` của chính nó. Ngoại lệ lớn nhất đã thấy: `7203` lệch 3,6% (275,1 vs
265,55) — ghi lại, chưa giải thích được.

**Bốn bẫy, cả bốn đã cắn:**

1. **Trang không in chữ "EPS"/"BPS"** — nhãn là `修正1株益`. Grep "EPS" ra 0 kết
   quả và tôi suýt kết luận trang không có dữ liệu. Nó có.
2. **~26 `<table>`, không cái nào có `id`.** Bảng 通期業績 phải nhận diện bằng
   tiêu đề: chỉ nó có **đủ ba** chữ `経常益` + `修正` + `発表日`. Các bảng
   財務指標 / 過去最高 / 半期 / 四半期 đều thiếu ít nhất một.
3. **`<time datetime>` ở đầu trang là của bảng chỉ số** (日経平均, 米ドル円…),
   không phải của mã. Phải lấy `<time>` **sát trước** chữ `前日比`.
4. **Ô trống in `－`, không phải `0`** — mã lỗ hoặc chưa có dự phóng. Đọc
   thành 0 cho ra PER 0, trông như mã cực rẻ. Cùng loại bẫy `isLock` của
   Yahoo, chỉ khác ký tự.

**Niên độ khác nhau giữa các mã** — đã thấy `2026.08`, `2026.12`, `2027.06`,
`2027.03`. Trường `fiscalPeriod` phải đi kèm từng dòng; gộp chung một kỳ là sai.

**Cột của bảng 通期業績**: 決算期 · 売上高 · 営業益 · 経常益 · 最終益 ·
**修正1株益** · 修正1株配 · 発表日 → EPS là `<td>` thứ **5** (index 4).

**Hàng 予想 thắng hàng 実績**: PER trang in ra được tính từ đúng hàng dự phóng —
kiểm trên `7203`: `2881,5 / 275,1 = 10,47` → trang in `10,5`. ✓

**⛔ KHÔNG suy `BPS = giá / PBR`.** Đó là số vòng lại từ chính PBR, nên phép
kiểm đẳng thức sẽ luôn xanh và luôn vô nghĩa. BPS ở nguồn này là `null`, và
đẳng thức PBR phải ra **"không kiểm được"**.

Dùng ở `kiyohara/scripts/fetch_snapshots.ts --source kabutan` (mặc định).

### 2.3 Kabutan — các trang khác

robots: cho phép, chặn `/search*` và `/94446337/`, **`Crawl-delay: 3`** — phải
tôn trọng, giãn ≥3,2s.

- Trả **403 nếu không có User-Agent**, 200 nếu có.
- `https://kabutan.jp/themes/?industry=N&market=M` — danh sách mã theo ngành
  kèm PER/PBR. **15 dòng/trang**, chỉ `&page=N` có tác dụng (`&disp`/`&num`/
  `&limit`/`&rows` bị bỏ qua). Trang tự khai dân số dạng `「123銘柄」` — dùng
  làm cổng kiểm. Xem `jp_value_screen_graph/tools/sector_benchmark.py`.
- `https://kabutan.jp/warning/?mode=2_1` / `2_2` — xếp hạng **biến động giá**
  (không phải GTGD), 15 dòng/trang, có `株価` và `出来高`.
- Mã Nhật là **4 ký tự**, mã mới kết thúc bằng chữ cái (`285A`, `146A`).
  `\d{4}` sẽ bỏ sót chúng.
- Trang 日経平均 (`?code=0000`) hiện `出来高` nhưng `売買代金` là `－`.

### 2.4 JPX — chính thống nhưng khó máy đọc

robots: `User-Agent:*  Disallow:` — **cho phép toàn bộ**.

| Trang | Định dạng |
|---|---|
| `/markets/statistics-equities/investor-type/` 投資部門別売買状況 (tuần) | `.xls` **định dạng cũ** — stdlib không đọc được, `openpyxl` cũng không, phải `xlrd` |
| `/markets/statistics-equities/daily/` | PDF |
| `/markets/statistics-equities/misc/` | `.xlsx` |

Đây là **nguồn duy nhất** cho 投資部門別売買状況. Muốn dùng thì phải chấp nhận
thêm dependency đọc Excel.

---

## 3. Bài học chung về cạm bẫy

Bốn loại lỗi đã thực sự xảy ra, cả bốn đều cho ra số **trông hợp lý**:

1. **Dòng tổng hợp lẫn với dòng chi tiết** — `foreigns` type=INDEX. Luôn hỏi
   "mỗi dòng ở đây là một cái gì?" trước khi `sum()`.
2. **Sai bậc đơn vị** — `close` của vnstock là **nghìn đồng**, chia 1e9 thay vì
   1e6 làm ADTV nhỏ đi 1.000 lần. Thứ hạng KHÔNG đổi (sai số là hằng số) nên
   nhìn danh sách không phát hiện được. Luôn đối chiếu với một đường tính độc
   lập cùng bậc độ lớn.
3. **Phân trang dừng sớm** — lấy 15/123 mã rồi tính trung vị, số ra hoàn toàn
   hợp lý. Dừng theo con số **trang tự khai**, không theo số dòng parse được.
4. **Ô trống nghĩa là "trượt", không phải 0** — đấu thầu HNX trượt hiện `0`.

Và một loại thứ năm không phải lỗi dữ liệu mà lỗi đặt tên: **hai đại lượng khác
nhau dùng chung một key** (tỷ giá NHNN vs NHTM; GTGD 1 sàn khớp lệnh vs 3 sàn
toàn phiên). Chúng lệch vài phần trăm — đủ nhỏ để không ai nghi, đủ lớn để sai.

## 4. Về `ClaudeBot` trong robots.txt

Nhiều site (VBMA, VNDirect finfo, FireAnt — đều dùng Cloudflare) có
`User-agent: ClaudeBot  Disallow: /` trong khi `User-agent: *  Allow: /`.

Pipeline chạy dưới UA riêng của dự án từ GitHub Actions, **không phải ClaudeBot**
— chỉ thị đó nhắm vào crawler của Anthropic. Nhưng ghi lại để biết, và nếu có
nghi ngờ thì hỏi chủ dự án trước.
