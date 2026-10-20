# Đánh giá bản (4) và hướng dẫn AI chỉnh sửa bài báo Solar Clean

Ngày rà soát: 09/10/2026.

**Tệp đầu vào duy nhất để chỉnh sửa:** `bai_bao_khoa_hoc_solar_clean_tnu (4).docx`.

Đường dẫn bản tác giả cung cấp: `C:\Users\ADMIN\Downloads\bai_bao_khoa_hoc_solar_clean_tnu (4).docx`.

SHA-256 của bản đã kiểm tra: `bb8b28d499e4d5d03d3adb8ce9c1ce5ca2c181952546ee1371a6f38913aecd9a`.

## 1. Kết luận đánh giá

Bản (4) tiến bộ về độ gọn và cách trình bày kết quả, nhưng **chưa nên nộp nguyên trạng**. Điểm cần tập trung là tính nhất quán giữa mô tả, lưu đồ, logic PLC và bằng chứng đo; không cần viết lại toàn bộ bài. Các kết quả nên tiếp tục được định vị là đánh giá nguyên mẫu và quan sát bước đầu trên một tấm pin 50 W.

Đã kiểm tra toàn văn, ba phương trình Word, bảng số liệu, bảy hình, thay đổi so với bản (3), và toàn bộ tám trang PDF xuất bằng Microsoft Word từ bản sao. Chưa được cung cấp chương trình PLC, mã xử lý ảnh, dữ liệu huấn luyện, nhật ký đo hoặc ảnh cấu hình bộ sạc. Vì vậy, “chưa có bằng chứng để xác minh” trong báo cáo này **không đồng nghĩa với kết luận hệ thống không hoạt động hoặc số liệu sai**. Đây không phải kiểm toán đầy đủ từng tài liệu tham khảo.

### Những điểm đã tốt hơn, cần giữ

- PDF hiện có **8 trang**, không còn lỗi 9 trang của bản (3). Số trang phù hợp chưa có nghĩa toàn bộ định dạng đã đạt.
- Trung bình sáu chênh lệch công suất là **17,1167 W → 17,1 W**; độ lệch chuẩn mẫu là **11,1808 W → 11,2 W**. Hai số mới thêm tính đúng.
- Tóm tắt Việt–Anh thống nhất về trung bình 17,1 W và vẫn nêu giới hạn do chưa đo bức xạ, nhiệt độ.
- Đã mô tả diện tích bẩn là đại lượng quy đổi theo lưới, không phải diện tích bẩn đo chính xác bằng quang trắc.
- Mục 2.1 vẫn nêu vị trí PZEM-017 ở phía PV trước bộ sạc. Không nhận xét nhầm rằng bản (4) đã xóa vị trí đo.
- Mục 3.4 đã bỏ dải điện áp 17,2–18,0 V, suy luận dòng điện và tuyên bố sai số đối chuẩn của bản (3). Không tự động chèn lại các nội dung này nếu thiếu hồ sơ.
- Tài liệu [19] nay có trích dẫn trong thân bài. Không còn lỗi “tài liệu [19] mồ côi”, nhưng cách đưa CLAHE vào bài cần cân nhắc ở S08.
- Phần kinh tế đã thận trọng hơn: không còn kết luận chắc chắn về tính khả thi kinh tế hay tỷ lệ điện tự dùng dưới 1%.
- Ba phương trình vẫn tồn tại dưới dạng đối tượng toán học Word; phần trích văn bản đơn thuần chỉ hiện số (1)–(3) không có nghĩa công thức bị mất.

## 2. Quy tắc bắt buộc cho AI nhận việc

1. Làm trên bản sao của bản (4), không ghi đè bản tác giả đưa. Không lấy bản (2)/(3) làm nguồn chỉnh sửa chính.
2. Giữ nguyên các số đo trong Bảng 6 và các kết quả AI, trừ khi tác giả cung cấp dữ liệu gốc chứng minh cần sửa. Có thể tính lại thống kê từ dữ liệu có sẵn, phải ghi rõ công thức và ý nghĩa.
3. Không tự thêm số đo điện áp, dòng điện, độ chính xác cảm biến, timestamp, cấu hình sạc, checkpoint, ca thử PLC hoặc kết quả thực nghiệm.
4. Tách ba loại việc: **sửa biên tập ngay**, **đối chiếu hồ sơ rồi sửa**, **thực nghiệm bổ sung nếu muốn nâng mức kết luận**. Không biến thí nghiệm đề xuất thành thí nghiệm đã hoàn thành.
5. Các câu mẫu dưới đây chỉ được dùng khi phù hợp dữ liệu và triển khai thực tế. Với nội dung cần xác minh, lập danh sách câu hỏi cho tác giả thay vì điền dữ kiện phỏng đoán vào bài.
6. Bảo toàn ảnh thực nghiệm và biểu đồ dữ liệu. Được chỉnh nhãn hoặc vẽ lại lưu đồ cần sửa; phải lưu bản gốc và ghi rõ thay đổi. Không chỉnh các con số hiển thị trên ảnh chụp màn hình để chúng khớp bảng.
7. Không chuyển “ghi cờ DB”, “đã cấu hình” hoặc “có sơ đồ thiết kế” thành “đã kiểm chứng cơ cấu vật lý”, “an toàn đã được bảo đảm” hay “thử nghiệm thành công”.
8. Không yêu cầu đúng 8 trang bằng mọi giá. Dùng giới hạn và định dạng của template TNU áp dụng cho lần nộp; không thu nhỏ chữ tùy tiện để ép trang.

## 3. Danh sách sửa theo thứ tự ưu tiên

| Mã | Vị trí | Vấn đề cần xử lý | Cách xử lý chính |
|---|---|---|---|
| S01 | Hình 2; Mục 2.1, 2.5, 3.3 | Lưu đồ chưa có vòng kiểm chứng sau làm sạch | Đối chiếu logic rồi vẽ lại |
| S02 | Mục 2.1, 3.4; Bảng 2, 6 | Cấu hình sạc và quy trình tạo số đo chưa đủ để tái lập | Cần thông tin thiết bị, cấu hình, nhật ký |
| S03 | Mục 3.1; Hình 5 | Quy nguyên nhân loss và khẳng định tổng quát hóa quá mạnh; nhãn Loss sai | Sửa ngay; checkpoint cần log |
| S04 | Công thức (3); Mục 2.2, 3.3; Bảng 5 | Thiếu định nghĩa NFO; điều kiện nghiệm thu và giới hạn lặp chưa thống nhất | Sửa ký hiệu; đối chiếu PLC |
| S05 | Mục 3.4; Tóm tắt; Bảng 6 | SD, tỷ lệ phần trăm và ảnh hưởng thời tiết cần diễn giải đúng | Sửa cách diễn giải, xác minh timestamp |
| S06 | Mục 2.3, 3.1, 3.6 | Đơn vị độc lập, tập tăng cường và khoảng tin cậy | Làm rõ phạm vi; không bịa phân tích mới |
| S07 | Mục 3.5; Hình 7 | Ảnh giao diện thiếu liên hệ với phiên đo | Xác định nguồn ảnh và chú thích |
| S08 | Mục 2.2, 2.4, 3.1 | CLAHE; “song song” và thời gian 1,1 s | Sửa theo mã thực tế |
| S09 | Mục 3.6 | Giả định sản lượng ngày và các kịch bản điện tự dùng | Tách giả định khỏi số đo |
| S10 | Trang 2–5; tài liệu tham khảo; bản nộp | Chú thích, tiêu đề bị tách; bảng khó đọc; kiểm tra trích dẫn và ẩn danh | Chỉnh bố cục và xuất PDF kiểm tra |

## 4. Hướng dẫn chi tiết từng phần

### S01 — Sửa Hình 2 để khớp đóng góp “chu trình khép kín”

**Quan sát đã xác nhận:** Hình 2 hiện kết thúc theo luồng PLC → động cơ/phun nước → Database & IoT → kết thúc chu kỳ. Chưa thể hiện thu ảnh sau làm sạch, đánh giá đạt/chưa đạt, làm sạch lần hai hoặc cảnh báo. Trong khi đó, đoạn dẫn Hình 2 và các Mục 2.5, 3.3 mô tả những chức năng này. Cả bảy tệp ảnh của bản (4) giống bản (3) từng byte; không phải chỉ thiếu trong phần trích chữ.

**Giao AI:** đối chiếu chương trình hoặc mô tả được tác giả xác nhận; bổ sung vòng sau làm sạch gồm thu ảnh → đánh giá điều kiện nghiệm thu → hoàn tất hoặc làm lại → giới hạn số lượt → cảnh báo. Thể hiện rõ xử lý khi đồng thời có lá, phân chim và bụi. Nhánh định vị viền chỉ chạy lúc khởi tạo/tái hiệu chỉnh phải phù hợp Mục 2.4.

Nếu chưa có chương trình để kiểm tra, có thể chuẩn bị lưu đồ dự thảo và đánh dấu cần tác giả xác nhận trong hồ sơ bàn giao; không gọi đó là sơ đồ triển khai đã kiểm chứng.

**Đạt khi:** Hình 2, luật (3), Bảng 5 và Mục 3.3 mô tả cùng một thuật toán; không chỉ thêm từ “khép kín” vào chú thích.

### S02 — Làm rõ phép đo PV và cấu hình sạc, không chỉ lược bỏ U/I

**Quan sát:** Bản (4) giữ cấu hình PV 50 W, Vmp 18,0 V, Voc 21,6 V; pin Li-ion 5S danh định 18,5 V, đầy 21,0 V; PWM CM3024Z; PZEM-017 phía PV. Bản này đã bỏ các chi tiết U/I và đối chuẩn ở Mục 3.4, nhưng điều đó chưa giải thích trạng thái tải trong các lần đo.

Tài liệu CM3024Z mang nhãn JUTA công bố chế độ 12/24 V và các ngưỡng có thể đặt lại. Đây là căn cứ yêu cầu kiểm tra **đúng biến thể và cấu hình thực tế**, không đủ để kết luận bộ sạc của tác giả chắc chắn tương thích hoặc chắc chắn không tương thích với pin 5S. Nguồn: [CM3024Z Installation and Operation Manual, phần 3.10 và bảng thông số](https://www.emimikos.gr/shop/Documents/CM3024Z_Manual_En.pdf).

**Thông tin cần tác giả cung cấp:** ảnh nhãn/phiên bản bộ sạc, cấu hình điện áp đang dùng, sơ đồ PV–PZEM/shunt–bộ sạc–pin, trạng thái hoặc điện áp pin trong các lần thử nếu đã ghi nhận, và dữ liệu hình thành sáu cặp công suất.

**Giao AI:** mô tả đúng điểm đo, cách lấy công suất và cách chọn cửa sổ trung bình. Với dữ liệu 1 Hz, nói rõ cửa sổ trước làm sạch nằm ở đâu, cửa sổ sau nằm sau thời gian chờ ráo khoảng 5 phút như thế nào, có mẫu thiếu không và hệ thống ghi P trực tiếp hay tính P từ U/I. Không giả định trung bình của U nhân trung bình của I luôn bằng trung bình P.

Nếu không lưu U/I hoặc điện áp pin, ghi đó là giới hạn tái lập; không tạo bảng U/I từ công suất. Chỉ khôi phục tuyên bố sai số cảm biến/đối chuẩn khi có hồ sơ tương ứng.

**Đạt khi:** người đọc hiểu số liệu là công suất tại điểm làm việc với tải thực tế nào; không gọi là công suất cực đại đo được hoặc kết quả MPPT nếu chưa có phép đo đó.

### S03 — Sửa diễn giải Hình 5 và lựa chọn checkpoint

**Đoạn cần tìm:** “nhiều khả năng do phương sai mẫu kiểm định” và “nhằm bảo đảm độ khái quát tối ưu” tại Mục 3.1.

**Vấn đề:** đồ thị chưa chứng minh nguyên nhân dao động. Chọn checkpoint có validation loss thấp nhất cũng không bảo đảm tổng quát hóa tối ưu. Trong ảnh, nhãn “Độ Chệch (Loss)” không đúng thuật ngữ hàm mất mát.

**Có thể sửa ngay thành:**

> Hình 5 ghi nhận dao động của hàm mất mát kiểm định tại epoch 13. Nguyên nhân của dao động này chưa được phân tích trong nghiên cứu.

Chỉ khi log hoặc mã huấn luyện xác nhận mới thêm:

> Checkpoint được lựa chọn theo giá trị hàm mất mát nhỏ nhất trên tập kiểm định trong quá trình huấn luyện.

Xác định checkpoint này có đúng là mô hình dùng để tính 372/384 và triển khai hay không. Làm rõ cách đánh số epoch nếu đồ thị dùng 0–14 còn bài dùng 1–15; không tự đổi vị trí spike.

Đổi nhãn hình thành “Hàm mất mát (Loss)”, giữ nguyên dữ liệu, trục và đường biểu diễn. Ưu tiên xuất lại từ dữ liệu/source figure; nếu thiếu, chỉ sửa nhãn, không tái tạo đường cong bằng số giả.

**Đạt khi:** bỏ giải thích nguyên nhân chưa kiểm chứng và bảo đảm quá mức; nhãn trong ảnh được sửa thực sự.

### S04 — Thống nhất ký hiệu và trạng thái PLC

**Sửa ngay:** định nghĩa `NFO = Nleaf + Nbird` nếu hai loại này chính là toàn bộ lớp dị vật dùng trong luật. Công thức (3), Mục 3.3 và ghi chú Bảng 6 đang dùng NFO nhưng phần giải thích ký hiệu chưa định nghĩa.

**Đối chiếu logic thực tế rồi thống nhất:**

- Mục 3.3 ghi tối đa hai chu trình nhưng lại viết cảnh báo khi “vượt quá 2 chu trình”. Nếu ý định là sau hai lượt vẫn không đạt thì dừng, viết đúng như vậy; không để người đọc hiểu có lượt thứ ba. Đây là mơ hồ trong mô tả, chưa phải bằng chứng mã PLC lỗi.
- Mục 3.3 kiểm tra cả tỷ lệ bẩn và dị vật, còn GĐ 4 của Bảng 5 chỉ kiểm tra Csau. Cần cùng một điều kiện nghiệm thu hoặc giải thích điều kiện riêng theo chế độ; không tự bổ sung AND/OR khi chưa đối chiếu.
- Phân biệt 24 s quét khô, thời gian kiểm chứng AI, 30 s chu trình ướt và khoảng chờ 5 phút trước đo công suất. Không cộng thời gian chờ phép đo vào thời gian cơ cấu rồi gọi là cùng đại lượng.
- Sáu ca Bảng 6 đều đạt sau một lượt nên không chứng minh nhánh retry/cảnh báo. Giữ ranh giới “đã cấu hình” với “đã thử nghiệm”; chỉ gọi đã cấu hình nếu có chương trình hoặc xác nhận triển khai.
- Câu công tắc hành trình “bảo vệ độc lập với máy tính biên” cần được hiểu và mô tả theo sơ đồ đấu dây/logic PLC. Không suy rằng DB bit là phản hồi tiếp điểm hoặc đây là hệ thống an toàn đã được chứng nhận.

**Đạt khi:** mọi nơi dùng cùng giới hạn lượt, điều kiện kết thúc, đơn vị thời gian; ca thử thiếu được ghi rõ trong hạn chế hoặc hồ sơ bàn giao. Thử nhánh chưa đạt/lỗi truyền thông là việc bổ sung để nâng mức kết luận, không được viết như đã làm.

### S05 — Giữ số thống kê mới nhưng làm rõ ý nghĩa

Sáu ΔP là `16,0; 5,4; 5,0; 21,3; 20,2; 34,8 W`. Tính được trung bình 17,1 W và SD mẫu 11,2 W, dùng mẫu số `n − 1 = 5`. **Không cần sửa hai số này.**

**Câu gợi ý:**

> Trên sáu kịch bản khảo sát, chênh lệch công suất đo trước–sau có trung bình 17,1 W và độ lệch chuẩn mẫu 11,2 W, dao động 5,0–34,8 W. Độ lệch chuẩn mô tả sự phân tán giữa các kịch bản, không phải sai số đo hoặc độ lặp lại trong cùng điều kiện.

Tỷ lệ 40,8% là trung bình các `ΔP/Psau × 100%`, không phải phần trăm tăng so với Ptrước. Giữ mẫu số minh bạch; nên đổi cách gọi “mức tổn thất ban đầu” thành “chênh lệch tương đối so với công suất sau làm sạch”, vì bức xạ và nhiệt độ chưa được kiểm soát.

Câu “củng cố nhận định ... bức xạ ... chi phối” nên hạ thành nhận xét về yếu tố có thể ảnh hưởng. Psau khác nhau chưa tách được tác động bức xạ, nhiệt độ và tải nạp.

Các mốc 10:24, 11:33, 11:45–12:00 và khung 10:00–12:30 phải đối chiếu nhật ký. Chúng thay đổi giữa các phiên bản trước; không kết luận sai chỉ vì có thay đổi, nhưng không cho AI tự sửa giờ cho hợp lý. Nếu không có nhật ký giờ chi tiết, dùng mức mô tả thời tiết mà tác giả thực sự ghi nhận.

**Đạt khi:** abstract, Bảng 6, Mục 3.4 và kết luận không gọi 17,1 W hoặc 40,8% là hiệu quả nhân quả đã được tách riêng của làm sạch.

### S06 — Giữ giới hạn đúng của dữ liệu AI và khoảng tin cậy

Bản đã nêu chia 96/12/12 ảnh mẹ trước tăng cường và 125 ảnh YOLO kiểm thử phát sinh từ 12 ảnh gốc; đây là cải thiện cần giữ. Không diễn đạt 125 biến thể hoặc 384 ô là tương ứng 125/384 cảnh độc lập.

**Giao AI:** làm rõ phép biến đổi “góc chụp” là biến đổi hình học trên ảnh hay thu ảnh mới; nêu đúng quy trình, không tự thêm augmentation. Với các cảnh cùng phiên, chỉ nói tách ảnh mẹ nếu chưa chứng minh tách độc lập bối cảnh/ngày chụp. Làm rõ “1.250 dị vật” là số đối tượng gán nhãn hay “1.250 ảnh”; hai đơn vị này không mặc nhiên giống nhau.

Khoảng tin cậy 95,1–98,6% hiện đã gắn giả định các ô độc lập và nêu giới hạn nội cụm. Không coi đây là lỗi tính toán. Tuy nhiên, nếu chưa có dự đoán theo ảnh mẹ, có thể bỏ khoảng tin cậy khỏi phần kết quả chính, giữ 372/384, 96,9% và hạn chế 12 cảnh. Nếu muốn thay bằng ước lượng theo cụm, phải có dữ liệu dự đoán/gán nhãn theo từng ảnh mẹ và ghi rõ phương pháp; không tự phát sinh một khoảng tin cậy mới.

Bảng 4 dùng `mAPmask: 97,1%` nhưng chưa nói ngưỡng IoU. Đối chiếu log để xác định là mask mAP@0.5 hay mAP@0.5:0.95; không đoán theo trị số.

**Đạt khi:** đơn vị ảnh, đối tượng, ô và cảnh rõ ràng; chỉ số mask có định nghĩa; không có khẳng định độc lập mạnh hơn cách chia dữ liệu thực tế.

### S07 — Làm rõ Hình 7 và phạm vi minh họa IoT

Hình 7 vẫn hiển thị 19,88 V, 2,610 A, 51,8 W. Bản (4) đã bỏ dải 17,2–18,0 V trong văn bản, nên không tiếp tục kết luận còn mâu thuẫn với dải đó. Công suất ảnh khác các cặp Bảng 6 cũng chưa tự chứng minh sai số liệu vì có thể khác thời điểm hoặc loại dữ liệu.

**Giao AI:** xác minh ảnh từ phiên nào, là số đọc tức thời hay trung bình, dữ liệu thực hay chế độ trình diễn và có thuộc sáu ca Bảng 6 không. Chỉ khi xác nhận mới bổ sung chú thích phân biệt. Mục 3.5 có thể nêu cả U/I/P nếu đúng chức năng hiện có; không cần xóa U/I chỉ để tránh giải thích ảnh.

Giảm các ảnh phụ ít giá trị khoa học như màn hình đăng nhập nếu cần tăng kích thước đồ thị và các chỉ số chính. Bảo toàn nội dung ảnh đo, không sửa số 51,8 W thành 49,3 W hoặc 50 W.

**Đạt khi:** người đọc hiểu ảnh minh họa chức năng giao diện hay bằng chứng của một ca thử cụ thể; chữ và số cần thiết đọc được ở kích thước in.

### S08 — Làm rõ tiền xử lý CLAHE và cách đo độ trễ

Câu mới về không áp dụng CLAHE đã tạo vị trí trích dẫn [19], nhưng không nên giữ một thao tác không sử dụng chỉ để tránh tài liệu mồ côi. Đối chiếu mã: nếu thực tế không dùng CLAHE, có thể mô tả ngắn tiền xử lý thật; chỉ nêu lý do bảo toàn màu là lựa chọn thiết kế, không xem đó là lợi ích đã chứng minh bằng thí nghiệm đối chứng. Nếu bỏ cả thảo luận CLAHE, xóa tài liệu [19] không còn được dùng và đánh lại số trích dẫn toàn bài.

Mục 2.4 nói YOLO chạy “song song”, trong khi 995,1 + 106,8 = 1.101,9 ms. Phép cộng đúng nhưng không tự chứng minh đó là độ trễ của thực thi song song. Kiểm tra mã/lịch chạy: nếu tuần tự, đổi từ; nếu song song, dùng thời gian toàn chuỗi đã đo hoặc gọi 1,1 s là tổng thời gian các mô hình nếu chỉ có số thành phần. Nêu độ trễ có/không bao gồm thu ảnh, tiền xử lý, truyền PLC khi có căn cứ.

**Đạt khi:** lựa chọn tiền xử lý và cách gọi độ trễ khớp triển khai; không có số benchmark hoặc ablation do AI tự thêm.

### S09 — Làm rõ giả định điện tự dùng

Mục 3.6 đã bỏ kết luận kinh tế quá mức; giữ cách viết thận trọng này. Cần phân biệt số đo 33 W/14 W với thông số danh định hoặc ước lượng, và có căn cứ cho sản lượng 175–200 Wh/ngày. Nếu đây chỉ là kịch bản giả định thì gọi rõ là giả định dùng minh họa; nếu lấy từ nguồn hoặc mô phỏng thì dẫn nguồn/phương pháp thực tế.

112 Wh là 14 W × 8 h; 240 Wh là riêng PLC 10 W × 24 h. Hai cách tính có phần PLC trùng nhau nên không cộng thẳng thành tổng điện tự dùng ngày. Chưa bao gồm đầy đủ các khoảng hoạt động, bơm và động cơ thì không gọi là cân bằng năng lượng hoàn chỉnh.

**Đạt khi:** các phép tính đúng và phạm vi tính rõ; không tự tạo tỷ lệ tiết kiệm, thời gian hoàn vốn hay lợi ích ròng cho mảng 10–20 kWp.

### S10 — Sửa bố cục thực tế và hoàn thiện hồ sơ nộp

**Lỗi nhìn thấy trong PDF bản (4):**

- Bảng 3: chú thích bắt đầu cuối trang 4, phần cuối chú thích và bảng nằm đầu trang 5.
- Bảng 4: chú thích bắt đầu cuối cột trái trang 5, phần cuối chuyển lên đầu cột phải.
- Tiêu đề Mục 2.4 bị tách giữa hai cột trang 4: từ “huấn luyện” nằm đầu cột phải.
- Bảng 1 và Bảng 2 có ô hẹp, xuống dòng nhiều và giãn khoảng trắng khó đọc. Bảng 3–4 cũng cần kiểm tra độ rộng cột sau khi giữ chú thích liền bảng.
- Hình 7 thu nhỏ làm thông tin khó đọc. Ưu tiên chọn thành phần có giá trị thay vì ép toàn bộ giao diện vào một hình nhỏ.

**Giao AI:** dùng Keep with next cho chú thích với bảng/tiêu đề với đoạn sau; Keep lines together cho chính chú thích và tiêu đề; chỉnh độ rộng cột, căn trái nội dung nhiều chữ, rút gọn nhãn có giải thích. Không dùng chuỗi dấu cách để căn bố cục. Sau chỉnh phải xuất PDF lại bằng Word và xem từng trang, không lấy số trang trong metadata làm kết quả.

Kiểm tra nguồn chính thức cho [15], [17], [18]: đúng sản phẩm, phiên bản, năm, mã tài liệu và URL. Việc thêm URL hoặc rút gọn tên tạp chí chưa chứng minh thư mục đã chính xác. Trong lượt này liên kết Siemens mới thêm chưa đọc được, nên chưa xác nhận mã tài liệu phù hợp và cũng chưa kết luận liên kết sai. Kiểm tra trích dẫn hai chiều sau mọi lần đánh lại số; các ô NR ở Bảng 1 không được diễn giải thành kết luận công trình khác chắc chắn không có chức năng đó.

Bản (4) có tên tác giả, email và lời cảm ơn: bình thường đối với bản đầy đủ, nhưng cần tạo **bản phản biện ẩn danh riêng** nếu chuẩn bị nộp. Hướng dẫn TNU yêu cầu bài nộp không cung cấp thông tin tác giả; kiểm tra cả metadata, comment, tracked changes và nội dung ảnh. Giữ bản đầy đủ riêng. Nguồn: [Hướng dẫn gửi bài TNU JST](https://jst.tnu.edu.vn/jst/about/submissions).

**Đạt khi:** không còn chú thích/tiêu đề bị xé đôi; đúng template; hình, bảng đọc được; trích dẫn khớp; bản ẩn danh được kiểm tra riêng nếu có yêu cầu tạo hồ sơ nộp.

## 5. Thông tin cần xin tác giả, gom một lần

1. Ảnh nhãn và cấu hình CM3024Z; sơ đồ đấu PZEM/shunt; thông tin tải pin trong các ca đo đã ghi nhận.
2. Nhật ký sáu cặp công suất, cách chọn cửa sổ trước/sau và các timestamp thực có. Nếu chỉ lưu P, nói rõ chỉ có P.
3. Chương trình PLC hoặc bảng trạng thái/mapping: điều kiện nghiệm thu, bộ đếm lượt, nhánh cảnh báo, công tắc hành trình; các nhánh nào đã được thử.
4. Log huấn luyện/chọn checkpoint, dữ liệu nguồn Hình 5, định nghĩa mAPmask và mã đo độ trễ. Dự đoán theo ảnh mẹ chỉ cần nếu tính lại độ bất định theo cụm.
5. Nguồn phiên chụp Hình 7 và căn cứ của các số điện tự dùng/sản lượng ước tính.

AI tiếp tục sửa các lỗi biên tập độc lập trong lúc chờ. Nội dung chưa xác minh phải được ghi vào hồ sơ bàn giao, không được âm thầm điền bằng giả định. Không bắt tác giả tạo lại những log trước đây không lưu; nếu thiếu thì hạ mức kết luận hoặc nêu hạn chế thích hợp.

## 6. Prompt có thể gửi nguyên khối cho AI khác

> Hãy chỉnh sửa `bai_bao_khoa_hoc_solar_clean_tnu (4).docx` theo báo cáo này. Đọc bản (4), kiểm tra từng điểm S01–S10 còn tồn tại trước khi sửa; không sao chép nhận xét lỗi của bản cũ một cách máy móc. Làm trên bản sao. Ưu tiên nhất quán Hình 2–luật điều khiển–PLC, cấu hình đo công suất, diễn giải Hình 5 và ngắt chú thích/tiêu đề. Giữ nguyên số liệu gốc; số 17,1 W và SD mẫu 11,2 W đã tính đúng. Không bịa log, cấu hình, timestamp, ablation hay kết quả thử. Với phần thiếu bằng chứng, lập danh sách cần tác giả xác nhận và đưa phương án diễn đạt thận trọng; hoàn tất các chỉnh sửa độc lập trước. Không tự sửa con số trên ảnh thực nghiệm. Xuất Word bản chỉnh sửa và PDF kiểm tra, kèm bảng S01–S10: đã sửa gì, căn cứ nào, còn thiếu gì. Không tuyên bố bản thảo sẵn sàng nộp chỉ vì đủ 8 trang hoặc công cụ kiểm tra báo PASS.

## 7. Checklist nghiệm thu cho lượt sửa tiếp theo

- [ ] S01: Hình 2 thể hiện đúng vòng kiểm chứng và giới hạn lượt, đối chiếu được với mô tả/triển khai.
- [ ] S02: Mô tả điểm đo, tải và cửa sổ trung bình rõ; thông tin phần cứng chưa xác minh được liệt kê.
- [ ] S03: Bỏ quy nguyên nhân loss chưa có căn cứ, bỏ “bảo đảm độ khái quát tối ưu”; sửa nhãn Loss.
- [ ] S04: Định nghĩa NFO, thống nhất điều kiện đạt và tối đa hai chu trình; không nhập nhằng đã cấu hình/đã thử.
- [ ] S05: Giữ 17,1 W và SD mẫu 11,2 W; diễn giải đúng sáu kịch bản và mẫu số phần trăm.
- [ ] S06: Phân biệt ảnh mẹ/biến thể/ô/đối tượng; ghi rõ chỉ số mask; không tạo CI mới khi thiếu dữ liệu.
- [ ] S07: Hình 7 có nguồn và phạm vi minh họa phù hợp, không sửa số hiển thị.
- [ ] S08: CLAHE và cách chạy/đo độ trễ khớp mã thực tế hoặc có giới hạn rõ.
- [ ] S09: Điện tự dùng, sản lượng giả định và phạm vi tính không bị trộn lẫn/cộng trùng.
- [ ] S10: Xuất PDF mới, xem toàn bộ trang; không tách chú thích Bảng 3–4 và tiêu đề 2.4; kiểm tra trích dẫn và bản ẩn danh khi làm hồ sơ nộp.

**Sản phẩm AI sửa cần bàn giao:** bản Word mới, PDF đã kiểm tra trực quan, bảng thay đổi và danh sách vấn đề còn cần tác giả xác nhận. Chỉ đánh dấu “đã xác minh thực nghiệm” cho nội dung thật sự có bằng chứng tương ứng.
