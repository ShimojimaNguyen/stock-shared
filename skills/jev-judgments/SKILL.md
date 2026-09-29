---
name: jev-judgments
description: Dùng Jev (TypeSafe System One) cho phán đoán ngữ nghĩa trong hệ số liệu thị trường — hợp đồng API, ba primitive, những giới hạn ĐÃ ĐO, và các bẫy đã sập. Đọc TRƯỚC khi gọi Jev từ bất kỳ repo nào, cho VN/JP/US.
---

# Jev — phán đoán ngữ nghĩa, không phải tính toán

Jev (`jev-1.13.0`, TypeSafe System One) trả lời câu hỏi **ngữ nghĩa** mà code
thường không trả lời được — "công ty này thu USD hay trả USD?", "câu này có
phải khuyến nghị đầu tư không?" — bằng **xác suất có kiểu**, không bằng văn bản.

Nó **bổ sung** cho code, không thay code. Chỗ nào có sự thật đo được thì dùng
số đo, không hỏi model.

---

## 1. Ranh giới — đọc trước khi thiết kế bất cứ thứ gì

| | |
|---|---|
| ✅ Phân loại / phán đoán ngữ nghĩa **trên văn bản được cung cấp** | |
| ❌ **Chạm vào bất kỳ con số nào** | Tài liệu Jev nói thẳng *"is not a calculator. We strongly recommend implementing any mathematical logic in code."* Đã đo: yếu ở đếm, so số, số học |
| ❌ **So sánh ngày / tính khoảng thời gian** | Nó *"reads dates as text, not as ordered quantities"* |
| ❌ **Sinh văn bản** | *"not trained to generate text"*. Mọi câu chữ hiển thị vẫn là template trong code |
| ❌ **Suy luận nhiều bước** | Hỏng với phủ định kép và gián tiếp nhiều tầng |
| ❌ **Nằm trong đường xử lý request** | Thuộc tính doanh nghiệp đổi theo năm, không theo tuần → build-time, artifact commit |

Nói Jev "review được logic code" là nói quá, và pillar §1 cấm chính kiểu đó.

---

## 2. Bằng chứng quyết định tất cả

Đo 2026-09-22, lặp 6 lần, biên dao động chỉ **0,01–0,03**:

| state đưa vào | 東京瓦斯 cost | 電源開発 | JT rev |
|---|---|---|---|
| chỉ tên + ngành | 0,44 | 0,49 | 0,56 |
| **+ 2–3 câu sự thật về cơ cấu ngoại tệ** | **0,92** | **0,90** | **0,87** |
| + Wikipedia (intro / bài đầy đủ) | 0,68 / 0,74 | — | — |

Ba điều rút ra:

1. **Thiếu bằng chứng thì Jev yếu ở đúng chỗ quan trọng.** Đừng đưa mỗi cái tên
   rồi tin kết quả.
2. **Văn bách khoa không cứu được, có khi còn hại** — 太陽誘電 tụt 0,70 → 0,59 khi
   thêm bài Wikipedia đầy đủ. Tài liệu Jev: ngữ cảnh thừa *"act as a distractor"*.
   Lọc lấy câu liên quan, đừng nhồi.
3. Nên **mọi phán đoán phải đi kèm nhãn nguồn bằng chứng** và nhãn đó phải hiện
   ra UI. 0,85 dựa trên hồ sơ chính thức khác hẳn 0,85 dựa trên mỗi cái tên.
   (Đây chính là pillar §3 áp cho đầu ra của model.)

**Đối chứng lành**: công ty bịa ra → 0,36/0,30. Jev *không* dựng khẳng định mạnh
từ hư không. Giữ một ca như vậy trong golden test; **đỏ ở đó thì dừng dùng Jev,
đừng nới ngưỡng.**

---

## 3. Hợp đồng API

```
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <TYPESAFE_API_KEY>      ← chỉ từ env, không bao giờ vào file
Content-Type: application/json
User-Agent: <bất kỳ thứ gì>                   ← BẮT BUỘC, xem §6
```

```json
{ "state": { "…": "…" }, "model": "jev-latest",
  "questions": { "<id>": { "type": "noul|choice|score",
                           "instructions": "…", "criteria": { } } } }
```

State nạp **một lần**, mọi câu hỏi chạy **song song** trên nó — nên gom nhiều
câu vào một request thay vì gọi nhiều lần.

| primitive | trả về | dùng khi |
|---|---|---|
| `noul` | `noul` 0–1 | điều kiện có đúng không; nhiều nhãn cùng lúc thì mỗi nhãn một câu |
| `choice` | `choice` + `probabilities` + `confidence` | chọn một trong tập xác định |
| `score` | `score` + `legend` + `probabilities` + `confidence` | mức độ trên thang có thứ tự |

**Giá và hạn mức**: $0,042 / triệu input token (output miễn phí) ·
250.000 token/giây · 1.200 request/phút · context 64k (32k cho state + câu dài
nhất). Thực tế đo: 492 công ty ≈ 42 giây với 8 luồng, **≈ $0,015**.

**Ngôn ngữ**: tiếng Anh chính xác nhất; CJK có hỗ trợ nhưng **kém hơn** — và
điều này đã quan sát được (§5). Viết *câu hỏi* bằng tiếng Anh, giữ *state* bằng
ngôn ngữ gốc.

---

## 4. Năm luật bắt buộc

1. **Mọi câu `choice` phải có lối thoát `none_of_these`.** Không có nó thì model
   chọn phương án gần nhất và vẫn tự tin: đưa セブン&アイ (小売業) vào bộ câu hỏi
   bán buôn → `domestic_wholesale` conf **0,97**, chắc nịch cho một đáp án sai.
   Thêm lối thoát → trả `none_of_these` ở 0,95.

2. **Ngưỡng tin cậy, dưới đó không hiện gì.** 伊藤忠エネクス bị chữ "伊藤忠" đánh
   lừa → `sogo_shosha` SAI, nhưng conf chỉ **0,20–0,23** trong khi 4 tổng hợp
   thương xã thật đều ≥ 0,99. Ngưỡng tồn tại vì ca đó.

3. **"Chưa kết luận được" không bao giờ là bằng chứng ngược.** Xác suất nằm giữa
   → im lặng. Cấm mượn sự lưỡng lự của model để phản đối một phân loại đang có.

4. **Làm tròn trước khi so ngưỡng.** `0.82 − 0.67` = `0.14999999999999991` nên
   trượt ngưỡng 0,15, còn `0.87 − 0.72` = `0.15000000000000002` thì lọt — 4/15
   cặp cùng khoảng cách danh nghĩa cho hai kết quả khác nhau. Lỗi thật; tham
   khảo `gap()` trong `kiyohara/src/lib/screen/jev/policy.ts`.

5. **Văn bản nguồn là dữ liệu, không phải chỉ thị.** Jev *"does not treat
   [adversarial content] as hostile by default"*. Chỉ lấy câu trả lời có kiểu;
   không bao giờ render thẳng văn bản nguồn ra UI như lời của hệ thống.

Và một luật về tổ chức: **câu hỏi phải có đúng một bản** dùng chung giữa mọi
nơi gọi (xem `kiyohara/src/lib/screen/jev/questions.fx-roles.json`). Hai bản sẽ lệch
nhau và không ai biết bản nào đang chạy.

---

## 5. Hai ứng dụng đã đo được

### 5.1 Phân loại phơi nhiễm ngoại tệ (JP — khuôn dùng lại được cho VN/US)

`kiyohara/scripts/build_fx_roles.py`. Hai câu `noul` — doanh thu ngoại tệ và chi
phí ngoại tệ — cộng một câu `choice` cho nhóm bán buôn. Chạy lúc build, ghi
artifact commit. Trên 492 mã: bất đồng với bảng tra ngành **47 (10%)**.

### 5.2 Guard chống câu khuyến nghị (dùng cho **coding**, mọi repo)

`tools/pillar_guard.py`. Đây là chỗ Jev giúp việc lập trình thật sự: pillar §7
cấm nội dung khuyến nghị, mà luật đó **không grep hết được** vì diễn đạt vòng có
vô số biến thể.

Đo 2026-09-23, ngưỡng **0,25**:

| tập | n | kết quả |
|---|---|---|
| chuỗi THẬT lấy từ `vn-market-site` + `kiyohara` | 34 | cao nhất **0,10** · trung bình 0,044 · **0 báo động giả** |
| câu khuyến nghị diễn đạt vòng | 6 | **6/6 bắt được** — 0,28 · 0,53 · 0,70 · 0,85 · 0,92 · 0,95 |

Biên hẹp nhất là ca tiếng Nhật 「この水準なら仕込み時と考えられる」 = **0,28**, sát
ngưỡng — khớp cảnh báo CJK ở §3. Nên guard là **lưới thứ hai**; lưới grep tất
định cho các cụm hiển nhiên vẫn giữ nguyên.

---

## 6. Bẫy đã sập

**Thiếu header `User-Agent` → HTTP 403, thân trả về `error code: 1010`.**
Đó là mã của **Cloudflare**, không phải lỗi TypeSafe — nên đọc thông báo sẽ
tưởng khoá hỏng hoặc hết hạn mức. Đo 2026-09-23:

| client | kết quả |
|---|---|
| `Python-urllib` mặc định (không đặt UA) | **403 · 1010** |
| bất kỳ UA nào khác (`curl/8.4.0`, tên riêng) | 200 |
| `fetch()` của Node | 200 (undici tự gửi UA) |

Luôn đặt `User-Agent` khi gọi từ Python.

---

## 7. Trước khi thêm một câu hỏi Jev mới

1. Câu này có cần **số** không? Có → viết bằng code, không hỏi Jev.
2. State đã có **bằng chứng thật** chưa, hay chỉ có tên? Chỉ có tên → nói rõ
   giới hạn ở đầu ra, đừng trình bày như kết luận chắc chắn.
3. Nếu là `choice`: đã có `none_of_these` chưa?
4. Ngưỡng đặt ở đâu, và **đã đo trên dữ liệu thật của mình** chưa? Ngưỡng trong
   tài liệu là ví dụ để đánh giá, không phải hằng số phổ quát.
5. Đã có **golden test** chốt lại kết quả hôm nay chưa? Model là phụ thuộc bên
   ngoài có thể đổi dưới chân mà không có dòng diff nào.
