---
name: vn-market-mechanics
description: Luật chơi riêng của thị trường chứng khoán Việt Nam và điều chúng LÀM ĐỔI cách đọc số — biên độ trần/sàn, chu kỳ thanh toán T+2, dư nợ margin chỉ có theo quý, room ngoại. Mỗi mục có nguồn và trạng thái. Đọc TRƯỚC khi diễn giải breadth/ADR, dòng tiền ngoại, margin hay thanh khoản của thị trường VN.
---

# Cơ chế thị trường VN — và nó làm đổi cách đọc số thế nào

Đây **không** phải bài giới thiệu chứng khoán. Mỗi mục ở đây có mặt vì hệ thống
này đang hiển thị một con số mà luật chơi VN làm cho nó **có nghĩa khác** với
trực giác quen thuộc từ thị trường Mỹ/Nhật.

Trạng thái mỗi mục: **確定** (có nguồn, đã đối chiếu) · **要確認** (chưa xác
minh được tới nơi). **Không dùng 要確認 như sự thật.**

---

## 0. Luật của chính file này

Mọi con số ở đây phải có **nguồn + ngày**. Thấy một mục không có → coi như
chưa có. Đây là pillar `SD` áp cho tri thức, không chỉ cho dữ liệu.

Tôi (Claude) **không được thêm mục vào file này từ trí nhớ**. Thị trường VN
thay đổi quy định thường xuyên, và một con số nhớ mang máng trông y hệt một con
số đã kiểm.

---

## 1. Biên độ dao động — và vì sao `ceil`/`floor` mạnh hơn ADR

**確定** · Quyết định **352/QĐ-SGDHCM**, hiệu lực **2021-07-05**
· đối chiếu 2 nguồn độc lập (tra cứu 2026-09-29)

| | HOSE |
|---|---|
| biên độ thường | **±7%** so với giá tham chiếu |
| ngày giao dịch **đầu tiên** của mã mới niêm yết | **±20%** |
| ngày giao dịch **không hưởng quyền** trả cổ tức bằng cổ phiếu | **±20%** |
| lô chẵn khớp lệnh | 100 cp |
| khối lượng tối đa một lệnh lô chẵn | 500.000 cp |

HNX **±10%**, UPCoM **±15%** — nhiều nguồn môi giới nhất quán, nhưng tôi
**chưa tra được quyết định gốc của HNX** → *要確認*.

### Điều này làm đổi cách đọc

`live.json → breadth` đang đếm `ceil` và `floor` (phiên 2026-09-25: `ceil: 8,
floor: 3`). Ở một thị trường **có biên độ**, trần/sàn không phải "một phiên
tăng mạnh" — nó là **cầu bị cắt ngang**. Lệnh mua còn đó nhưng không có giá
nào cao hơn để khớp.

Hệ quả: **breadth và ADR ĐÁNH GIÁ THẤP một phiên nhiều mã trần.** Số mã tăng
đếm mỗi mã một phiếu, dù mã đó tăng 0,2% hay bị chặn ở 7%. Nên `ceil`/`floor`
là thông tin **cộng thêm**, không thừa — và đáng hiển thị cạnh ADR chứ không
chỉ nằm trong JSON.

### Bẫy trộn hai tập hợp

Một mã đang ở ngày đầu niêm yết, hoặc ngày không hưởng quyền cổ tức cổ phiếu,
có biên độ **20%** chứ không phải 7%. Đếm nó vào cùng một ô "số mã trần" là
**trộn hai đại lượng khác nhau dùng chung một tên** — đúng kiểu lỗi mà
`data-integrity-pillars` §8 mô tả: chúng lệch vài phần trăm, đủ nhỏ để không ai nghi.

Hệ thống hiện **không tách hai loại này**. Đây là giới hạn đã biết, cần nói ra
chỗ hiển thị chứ không lặng lẽ gộp.

---

## 2. Chu kỳ thanh toán T+2 — và vì sao dòng tiền ngoại là tín hiệu CHẬM

**確定** · VSDC ban hành quy chế **2022-08-19**, áp dụng từ **2022-08-29**
· nguồn báo tài chính, *chưa đọc trực tiếp văn bản VSDC* (tra cứu 2026-09-29)

Nhà đầu tư giao dịch được chứng khoán từ **chiều ngày T+2**. Trước 2022 là
sáng T+3; giai đoạn 2012–2022 rút ngắn ba lần.

### Điều này làm đổi cách đọc

`live.json → foreign` là mua/bán ròng **của phiên hôm nay**. Nhưng khối lượng
đó **chưa thể quay vòng** cho tới chiều T+2. Nên:

- Một phiên khối ngoại bán ròng mạnh **không** đồng nghĩa với áp lực bán tiếp
  ngay phiên sau — hàng chưa về.
- Dòng tiền ngoại một phiên là **nhiễu**. `regime.json` đã đúng khi lấy
  *trung bình 5 phiên* cho điểm `positioning`, không lấy một phiên.

---

## 3. Margin — vì sao trường này `null`, và nó KHÔNG phải lỗi

**確定** về nhịp công bố · nhiều nguồn báo tài chính nhất quán (tra cứu 2026-09-29)

**Dư nợ margin toàn thị trường KHÔNG có số liệu hàng ngày.** Nó được tổng hợp
từ **báo cáo tài chính quý của hơn 70 công ty chứng khoán**, nên chỉ xuất hiện
theo quý, và trễ vài tuần sau khi quý kết thúc.

Mốc đã công bố:

| kỳ | dư nợ toàn thị trường |
|---|---|
| cuối 2025 | ~392.000 tỷ đồng |
| cuối Q1/2026 | ~405.000 tỷ đồng |
| cuối Q2/2026 | **435.000 tỷ đồng** (kỷ lục) |

### Điều này làm đổi thiết kế

`live.json → margin` đang là `null` và `quality.margin = "missing"`. Đó là
**kết quả đúng**, không phải việc còn dở: không tồn tại nguồn miễn phí cho một
con số margin hằng ngày.

Thiết kế trung thực là **một chỉ báo theo quý, có nhãn kỳ rõ ràng** — không
phải một ô trống trên bảng hằng ngày làm người đọc tưởng hệ thống hỏng. Nếu
sau này hiển thị, nó phải mang kỳ (`Q2/2026`) chứ không mang ngày phiên.

**要確認**: tỷ lệ cho vay ký quỹ tối đa (thường nhắc là 1:2, tức ký quỹ ban đầu
50%) — tôi **không tra được văn bản hiện hành** xác nhận con số và hiệu lực.
Đừng công bố tỷ lệ này cho tới khi có nguồn.

---

## 4. Room ngoại

**要確認** — chưa tra nguồn trong đợt này.

Biết chắc: có trần sở hữu nước ngoài theo ngành, và ngân hàng bị giới hạn thấp
hơn mặt bằng chung. **Không viết con số cụ thể vào đây cho tới khi có văn bản.**

`cashout-vn.json` có trường `foreignRoomWatch` — trước khi diễn giải nó, phải
lấp mục này.

---

## 5. Trước khi diễn giải một chỉ báo VN — bốn câu

1. Chỉ báo này có bị **biên độ** làm méo không? (breadth, ADR, biến động → có)
2. Nó đo **dòng tiền** hay **trạng thái**? Dòng tiền thì T+2 làm nó trễ.
3. Nguồn có **nhịp** nào? (hằng ngày / quý / không có) — nhịp sai thì ô trống
   không phải lỗi, mà là sự thật.
4. Con số tôi sắp nói có **nguồn trong file này** không? Không có → **không nói**.

---

## Nguồn

- Quyết định 352/QĐ-SGDHCM (HOSE, 2021-07-05) — biên độ, lô, khối lượng lệnh.
  Đối chiếu: [Vietstock](https://vietstock.vn/2021/07/quy-che-giao-dich-moi-tai-hose-duy-tri-bien-do-dao-dong-gia-7-va-lo-chan-100-cp-143-871725.htm)
- Chu kỳ thanh toán T+2 (VSDC, áp dụng 2022-08-29) —
  [VNDirect](https://support.vndirect.com.vn/hc/vi/articles/9816355920153-Chu-k%E1%BB%B3-thanh-to%C3%A1n-ch%E1%BB%A9ng-kho%C3%A1n)
- Dư nợ margin theo quý —
  [Tuổi Trẻ](https://tuoitre.vn/du-no-margin-vuot-380-000-ti-dong-loat-cong-ty-chung-khoan-dan-can-room-20251024112344674.htm) ·
  [Investing.com](https://vn.investing.com/news/stock-market-news/du-no-margin-lap-ky-luc-435000-ty-dong-trong-quy-ii2026-2668501)

Tra cứu ngày **2026-09-29**. Quy định VN đổi thường xuyên — mục nào quá một năm
không đối chiếu lại thì coi như *要確認*.
