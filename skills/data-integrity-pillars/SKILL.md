---
name: data-integrity-pillars
description: Mười một pillar bắt buộc cho mọi hệ hiển thị số liệu thị trường — `—` chứ không `0`, kỳ dữ liệu + nguồn, nhãn tin cậy, chống look-ahead, ghi idempotent, cấm khuyến nghị. Trung lập thị trường và trung lập stack. Đọc TRƯỚC khi đụng vào bất cứ thứ gì hiển thị một con số, ở bất kỳ repo nào trong Stock/.
---

# Pillars — luật chung cho mọi hệ số liệu thị trường

File này nói **luật**. Skill engineering của từng repo nói **cơ chế** thực thi
luật đó trên stack cụ thể:

| repo | skill cơ chế |
|---|---|
| `vn-market-site` | `vn-dashboard-engineering` |
| `kiyohara` | `kiyohara-engineering` |

Khi mâu thuẫn: `CLAUDE.md` của repo > file này > skill engineering.

Mỗi pillar dưới đây **đã bị vi phạm ít nhất một lần trong các repo này**. Đó là
lý do chúng ở đây, không phải vì nghe hay.

---

## 0. Nguyên tắc nền

> **Một con số sai tệ hơn một ô trống.**

Người xem không có tài khoản ở đây, không đặt lệnh qua đây — nhưng họ ra quyết
định tiền bạc dựa trên số bạn hiển thị. Không chắc thì **DỪNG VÀ HỎI**, đừng đoán.

Và: **quy tắc viết ra không chặn được lỗi; chỉ cơ chế mới chặn được.** Khi có
thể, đưa kiểm tra vào code của công cụ (nó từ chối trả kết quả) hoặc vào test.
Ghi vào .md là tầng yếu nhất — dùng cho thứ không cơ chế hoá được.

---

## 1. Thiếu dữ liệu → `—`, không bao giờ `0`

`null` xuyên suốt, UI render `—`. **Cấm** `0`, `""`, `?? 0`, `|| 0` để lấp chỗ
trống.

`0` là một **khẳng định** về thị trường. `null` là thừa nhận không biết. Hai
thứ đó khác nhau và người đọc không phân biệt được nếu bạn trộn chúng.

Đã sập thật hai lần ở `vn-market-site`:
- `m: 0.0, yr: 0.0` hardcode render thành "+0,00" giả trên bảng lợi suất.
- `loadBreadth()` âm thầm dùng lại số mẫu PRNG seed cố định khi breadth stale —
  vì seed cố định, tỷ lệ ADR đứng yên ở đúng một số suốt một tháng.

Cạm bẫy JS đi kèm: **`null < 80` là `true`**. Mọi so sánh ngưỡng phải chặn null
trước. `?? 0` là cách vô hiệu hoá helper định dạng — cấm.

Hệ quả cho phép cộng: **tổng của toàn `null` phải là `null`, không phải `0`.**

---

## 2. Mọi số phải có kỳ dữ liệu + nguồn, **nhìn thấy được trên UI**

Có timestamp trong JSON mà không render ra đâu cả = lỗi. Đã xảy ra ở trang Thế
giới của `vn-market-site`.

Tách bạch hai khái niệm, đừng để cái này đóng vai cái kia:

| | nghĩa là gì |
|---|---|
| `asof` / `latestWeek` | **kỳ của dữ liệu** — ngày phiên, tuần giao dịch |
| `generatedAtIct` / `scannedAt` | **giờ script chạy** |

---

## 3. Mọi số phải có nhãn tin cậy

Tên khác nhau giữa các repo, luật giống nhau:

| repo | trường | các mức |
|---|---|---|
| `vn-market-site` | `quality` | `live` · `proxy` · `stale` · `missing` |
| `kiyohara` | `evidence` | `edinet` · `name_only` · `none` |

**Thêm field mới thì phải kèm nhãn tương ứng** — không có field "trần trụi"
không rõ độ tin cậy.

Nhãn phải hiện **cùng chỗ hiển thị**, không phải ở footer. Một con số proxy nằm
cạnh một con số live mà nhìn giống hệt nhau thì nhãn ở chân trang là vô dụng.

---

## 4. Cấm look-ahead bias

Mọi percentile/rolling phải **loại kỳ đang tính** khỏi tập lịch sử tham chiếu.
Chuẩn tham khảo: `compute_regime.py: history_excl_today` ở `vn-market-site`.

Đây là loại lỗi làm mọi chỉ báo trông tốt hơn thực tế, và không có triệu chứng
nào nhìn thấy được.

---

## 5. Ghi lịch sử idempotent theo kỳ

Chạy lại cùng một ngày/tuần phải **ghi đè đúng dòng đó**, không đẻ dòng trùng,
không đụng dòng của kỳ khác.

Phát hiện một kỳ quá khứ sai thì sửa trực tiếp dòng đó và **nói rõ lý do trong
commit message**.

---

## 6. Cấm dữ liệu bịa trông như thật

- Cấm `Math.random`, seed PRNG, hằng số "trông hợp lý" làm fallback.
  `worldEngine.js` từng có sparkline giả sinh bằng PRNG seed theo mã thị trường
  — đã gỡ.
- Preset/mẫu **buộc phải có** thì nhãn nằm **cùng chỗ hiển thị**.
- Fetch hỏng → bỏ mục đó và **đếm vào `failures`**, không suy ra, không lặng lẽ
  dùng kỳ trước thay thế.

---

## 7. Cấm nội dung khuyến nghị mua/bán

Hệ thống **mô tả dữ liệu, không tư vấn**. Cấm "nên mua", "giá mục tiêu",
「買い推奨」, và mọi phỏng đoán kiểu 「だろう」.

Luật này **không grep hết được** — diễn đạt vòng có vô số biến thể. Dùng
`tools/pillar_guard.py` (xem skill `jev-judgments`) làm lưới thứ hai.

---

## 8. Đơn vị tường minh + một đường đối chiếu cùng bậc

- Mọi số tiền phải có **đơn vị ngay cạnh nó** và làm tròn nhất quán trong cùng
  một bảng.
- Cấm cộng/so sánh khác đơn vị mà không quy đổi tường minh.

**Sai bậc đơn vị KHÔNG làm đổi thứ hạng**, nên nhìn danh sách không phát hiện
được. Đã xảy ra: ADTV lệch 1000× vì `close` tính bằng nghìn đồng.

Nên mỗi đại lượng phải có **ít nhất một phép đối chiếu với đường tính khác cùng
bậc độ lớn**. Ví dụ đã dựng: cổng `GROSS_*` của `kiyohara/scripts/scan.ts` đối
chiếu với bảng 売買代金 công bố của Yahoo JP.

---

## 9. Trình tự: phân tích → xác minh bằng lệnh → mới code

Không đảo thứ tự. "Xác minh" nghĩa là chạy `grep`/`Read`/một request thử, không
phải nhớ lại.

**Và kiểm chính phép kiểm trước khi tin nó.** Một phép dò trả "không tìm thấy"
chưa phải bằng chứng vắng mặt cho tới khi nó được chứng minh là bắt được thứ nó
phải bắt — cho nó dò một thứ chắc chắn có trước.

Đã suýt hỏng vì điều này: 285A キオクシア có turnover 7,9兆円/tuần trông vô lý và
regex dò bảng xếp hạng không thấy nó → gần như kết luận "nguồn hỏng". Thực tế
285A đứng **#1 toàn thị trường**; regex mới là thứ hỏng.

---

## 10. Artifact sinh tự động thì **commit**

Universe, kết quả quét, bảng phân loại — sinh ra rồi commit, để thay đổi **nhìn
thấy trong diff PR** thay vì âm thầm đổi dưới chân.

Đi kèm: **cấm sửa tay** file do script sinh. Sửa logic trong script.
Danh sách file nào được/không được sửa tay phải **liệt kê đủ mọi file** trong
thư mục dữ liệu — một file không có tên ở cả hai danh sách là một câu hỏi mở,
và lần sau sẽ có người đoán sai.

Chế độ thử của một script (`--limit N`) **không được ghi đè artifact
production**. Quét 20 mã vẫn cho độ phủ 20/20 = 100% nên nó lọt mọi cổng.

---

## 11. "Xong" = đã chạy thật

Không phải "đã viết xong". Tối thiểu:

- [ ] Build sạch (nếu đụng frontend)
- [ ] Test xanh, và có test **mới** cho hành vi mới
- [ ] Script liên quan chạy thật, output đúng schema cũ
- [ ] Thiếu dữ liệu hiện `—`, không `0`/`null`/`NaN` lọt ra DOM
- [ ] Số mới có nhãn tin cậy + kỳ dữ liệu + nguồn **render được**
- [ ] Mọi tổng kèm số phần tử đóng góp
- [ ] Không secret trong diff
- [ ] `py tools/pillar_guard.py --repo <repo>` sạch

---

## Trước khi gõ dòng code đầu tiên — bốn câu

1. Số này lấy từ đâu, ai sinh ra nó, kỳ nào? Chưa có nguồn → **dừng, hỏi**.
2. Trường nào có thể thiếu, thiếu thì hiện gì? (phải là `—`)
3. Có phép cộng nào không? Cộng đúng cùng một kỳ chưa, và đã công bố số phần tử
   đóng góp chưa?
4. Có đổi công thức tài chính / đổi schema nhiều nơi đọc / >3 file không?
   → **Plan mode**, chờ duyệt.
