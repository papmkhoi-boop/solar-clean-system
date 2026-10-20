# TAI LIEU TONG HOP DU AN VE SINH TAM PIN MAT TROI SU DUNG TRI TUE NHAN TAO

## 1. Ten de tai

**Nghien cuu va xay dung he thong tu dong ve sinh tam pin mat troi su dung tri tue nhan tao, ung dung mang CNN voi kien truc EfficientNet-B0 de nhan dien muc do ban tren tung o nho cua tam pin va dieu khien PLC thuc hien ve sinh tu dong.**

Du an huong den viec ket hop thi giac may tinh, mo hinh hoc sau va he thong dieu khien cong nghiep de giam nhan cong kiem tra, tang hieu suat phat dien cua tam pin mat troi va phat hien som cac bat thuong tren be mat tam pin.

## 2. Boi canh va ly do thuc hien

Tam pin mat troi khi hoat dong ngoai troi thuong bi anh huong boi bui ban, la cay, phan chim, nuoc dong, vet bam va cac yeu to moi truong khac. Nhung yeu to nay lam giam luong anh sang chieu vao te bao quang dien, tu do lam giam cong suat phat dien. Neu viec kiem tra va ve sinh chi thuc hien thu cong, he thong se ton nhieu nhan luc, kho kiem soat lien tuc va khong phat hien kip thoi nhung khu vuc bi ban cuc bo.

Vi vay, du an duoc xay dung de giai quyet bai toan:

- Tu dong quan sat be mat tam pin bang camera.
- Dung AI de phan tich anh chup cua tam pin.
- Chia tam pin thanh tung o nho de xac dinh khu vuc nao sach, khu vuc nao ban.
- Tinh ty le dien tich ban dua tren so o bi ban.
- Tu dong gui lenh den PLC khi can ve sinh.
- Mo rong trong tuong lai de nhan dien la cay, phan chim va vet nut vo tren tam pin.

## 3. Muc tieu cua du an

Muc tieu tong quat cua du an la xay dung mot he thong giam sat va ve sinh tam pin mat troi co kha nang hoat dong tu dong, trong do AI dong vai tro phan tich hinh anh, con PLC dong vai tro dieu khien thiet bi chap hanh.

Muc tieu cu the:

- Xay dung phan mem desktop de ket noi camera, chay mo hinh AI va dieu khien PLC.
- Su dung mo hinh CNN EfficientNet-B0 de phan loai tung vung nho tren tam pin.
- Trien khai mo hinh AI sang dinh dang TensorFlow Lite de chay nhe hon tren may tinh dieu khien.
- Chia anh tam pin thanh 32 o nho, moi o duoc dua vao model de nhan dien.
- Phan loai tung o thanh cac trang thai hien tai: `sach`, `ban`, `nopanel`.
- Tinh ty le patch ban tren tong so patch hop le de uoc luong dien tich ban.
- Khi phat hien tam pin can ve sinh, phan mem gui tin hieu dieu khien den PLC Siemens S7.
- Xay dung giao dien web va ung dung di dong de giam sat tu xa, xem camera, xem ket qua AI, cau hinh nguong va kich ve sinh thu cong.
- Chuan bi mo rong nhan dien them `la cay`, `phan chim`, `tam pin nut vo`.

## 4. Tong quan he thong

He thong hien tai gom cac khoi chinh:

1. **Camera giam sat**

   Camera chup hoac lay khung hinh cua be mat tam pin. Anh dau vao co the duoc xoay, chuan hoa huong va resize de phu hop voi bo chia patch cua AI.

2. **Khoi xu ly anh va AI**

   Anh tam pin duoc tien xu ly, chia thanh cac o nho, sau do tung o duoc dua vao model EfficientNet-B0 da convert sang TensorFlow Lite. Model tra ve xac suat cua tung lop, tu do he thong xac dinh o do la sach, ban hay khong phai tam pin.

3. **Khoi ra quyet dinh**

   Phan mem tinh so o ban, so o sach, so o khong phai tam pin. Dua tren ty le o ban va nguong cau hinh, he thong quyet dinh co can ve sinh hay khong.

4. **Khoi dieu khien PLC**

   Khi AI ket luan can ve sinh, phan mem gui tin hieu den PLC Siemens S7 thong qua thu vien Snap7. PLC nhan tin hieu va dieu khien co cau ve sinh.

5. **Giao dien desktop**

   Giao dien desktop dung de khoi dong he thong, xem camera, xem ket qua nhan dien, xem ty le ban, ket noi PLC, doi camera, cau hinh chu ky chup anh va kich ve sinh thu cong.

6. **Web monitor FastAPI**

   Web monitor cho phep giam sat tu xa thong qua trinh duyet, co dang nhap, dang ky tai khoan, xem frame hien tai, xem snapshot, dieu khien start/stop, reconnect PLC, manual clean va cau hinh he thong.

7. **Ung dung di dong**

   Ung dung mobile duoc xay dung bang React Native / Expo de xem dashboard, monitor, control, trang thai thoi gian thuc, frame camera, snapshot va gui cac lenh dieu khien den backend.

So do luong xu ly tong quat:

```text
Camera -> Tien xu ly anh -> Chia thanh 32 o nho -> EfficientNet-B0 / TFLite
       -> Ket qua tung o -> Tinh ty le dien tich ban -> Ra quyet dinh
       -> Gui tin hieu PLC -> Co cau ve sinh hoat dong
```

## 5. Nhung phan da thuc hien trong du an

### 5.1. Model AI nhan dien tam pin sach / ban / khong co tam pin

He thong hien tai su dung file model `VeSinh.tflite` va file nhan `labels_3classes.txt`. File nhan hien co 3 lop:

```text
0 sach
1 ban
2 nopanel
```

Y nghia cac lop:

- `sach`: vung anh la be mat tam pin va khong can ve sinh.
- `ban`: vung anh la be mat tam pin co bui ban hoac vet bam, co kha nang can ve sinh.
- `nopanel`: vung anh khong phai la tam pin, dung de loai bo nhung phan anh ngoai vung can phan tich.

Viec co lop `nopanel` rat quan trong vi trong thuc te camera co the chup lech, khung hinh co the chua mot phan nen, khung sat, san nha hoac vung khong phai tam pin. Neu khong co lop nay, he thong co the tinh sai ty le ban.

### 5.2. Chia tam pin thanh tung o nho de tinh dien tich ban

Thay vi chi phan loai ca anh thanh "sach" hoac "ban", he thong duoc thiet ke theo huong chia anh thanh cac o nho. Cach nay giup danh gia duoc muc do ban theo tung khu vuc.

Cau hinh hien tai:

- Anh tam pin duoc resize ve khung tam thoi `896 x 1792` pixel.
- Anh duoc chia thanh `8 hang x 4 cot`.
- Tong cong co `32 patch`.
- Moi patch co kich thuoc `224 x 224` pixel.
- Moi patch duoc dua vao AI de phan loai rieng.

Vi moi patch dai dien cho mot phan dien tich cua tam pin, he thong co the uoc luong dien tich ban bang cong thuc:

```text
Ty le ban = So patch duoc AI nhan la ban / So patch hop le
```

Trong do:

- Patch hop le la patch thuoc ve tam pin, khong tinh patch `nopanel`.
- Neu co 32 patch, nhung 4 patch la `nopanel`, thi so patch hop le la 28.
- Neu trong 28 patch hop le co 7 patch bi ban, ty le ban la `7 / 28 = 25%`.

Neu biet dien tich thuc cua tam pin, co the quy doi tiep:

```text
Dien tich ban uoc tinh = Ty le ban x Tong dien tich tam pin
```

Vi du tam pin co dien tich 2 m2, ty le ban 25%, thi dien tich ban uoc tinh la 0.5 m2.

### 5.3. Tien xu ly anh truoc khi dua vao model

Moi patch truoc khi dua vao model se duoc tien xu ly de giup AI nhan dien on dinh hon:

- Chuyen anh sang anh xam.
- Lam mo nhe bang Gaussian Blur de giam nhieu.
- Tang tuong phan cuc bo bang CLAHE.
- Resize ve kich thuoc dau vao cua model la `224 x 224`.
- Chuyen anh xam thanh 3 kenh de phu hop voi model CNN.
- Chuan hoa gia tri pixel ve khoang `0 -> 1`.

Tien xu ly anh giup model giam anh huong cua anh sang moi truong, bong do, nhieu camera va su khac biet do dieu kien chup.

### 5.4. Suy luan AI bang TensorFlow Lite

Model duoc trien khai o dinh dang TensorFlow Lite, giup:

- Giam dung luong model.
- Chay nhe hon so voi TensorFlow day du.
- Phu hop hon voi may tinh dieu khien, may cong nghiep hoac he thong co tai nguyen han che.
- Tang kha nang dong goi thanh file chay doc lap.

Trong phan mem, neu co `tflite_runtime` thi he thong uu tien dung `tflite_runtime` vi nhe hon. Neu khong co, he thong fallback sang `tensorflow.lite`.

He thong cung co co che chay theo batch:

- Thay vi dua tung patch vao model mot cach rieng le, he thong co gang dua ca 32 patch vao model trong mot batch.
- Neu model ho tro batch input, toc do suy luan se nhanh hon.
- Neu khong ho tro, phan mem tu dong chay tung patch theo thu tu.

### 5.5. Ra quyet dinh ve sinh

Sau khi AI phan loai tung patch, he thong dem:

- So patch `ban`.
- So patch `sach`.
- So patch `nopanel`.
- So patch hop le.
- Do tin cay trung binh cua cac patch.

Nguong hien tai:

- Do tin cay toi thieu: `60%`.
- So patch hop le toi thieu: `10 patch`.
- Lop kich hoat ve sinh: `ban`.
- Ty le patch ban duoc tinh tren cac patch hop le.

He thong se kich ve sinh khi:

- Anh co du so patch hop le de ket luan day la tam pin.
- AI phat hien lop `ban`.
- Ty le patch ban dat nguong cai dat.
- PLC dang ket noi.
- Khong nam trong thoi gian cooldown.

### 5.6. Dieu khien PLC

Du an da tich hop PLC Siemens S7 thong qua thu vien Snap7.

Thong so trong phan mem desktop hien tai:

- PLC enabled: `True`.
- Dia chi IP PLC: `192.168.1.11`.
- Rack: `0`.
- Slot: `1`.
- Data block: `DB1`.
- Dia chi bit dieu khien: `DB1.DBX0.0`.
- Kich hoat bang cach set bit len `1`, sau do tra ve `0`.
- Co thoi gian cooldown de tranh kich lien tuc.

Nguyen ly dieu khien:

```text
AI phat hien can ve sinh
-> Phan mem doc DB1 tu PLC
-> Set bit DBX0.0 = 1
-> PLC nhan lenh va kich co cau ve sinh
-> Phan mem dua bit DBX0.0 ve 0
```

Cach truyen tin hieu dang xung `1 -> 0` phu hop voi nhieu bai toan dieu khien cong nghiep vi PLC chi can bat canh len hoac doc trang thai bit de bat dau chu trinh ve sinh.

### 5.7. Che do chup anh dinh ky va luu snapshot

He thong co che do snapshot:

- Chup anh theo chu ky.
- Chu ky mac dinh: `600 giay`, tuong duong 10 phut.
- Luu anh vao thu muc `snapshots`.
- Tao anh debug co ve luoi patch va thong tin ket qua AI.

Che do nay phu hop voi he thong thuc te vi tam pin khong can phai phan tich lien tuc tung frame nhu video an ninh. Viec chay AI theo chu ky giup giam tai CPU, giam nhiet, giam loi kich nham va van dam bao phat hien bui ban theo thoi gian.

### 5.8. Giao dien desktop

Phan mem desktop da co cac chuc nang:

- Dang nhap he thong.
- Hien thi camera.
- Khoi tao va nap model AI.
- Hien thi ket qua phan loai.
- Hien thi ty le patch ban.
- Hien thi so lan da ve sinh.
- Ket noi va ket noi lai PLC.
- Kich ve sinh thu cong.
- Doi camera truc tiep.
- Cai dat nguong ban.
- Cai dat chu ky AI / chu ky snapshot.
- Quan ly tai khoan nguoi dung.
- Luu snapshot va hien thi anh phan tich.

### 5.9. Web monitor FastAPI

Du an da co module web monitor bang FastAPI. Vai tro cua web monitor la giup nguoi dung giam sat va dieu khien he thong tu xa qua trinh duyet.

Chuc nang chinh:

- Dang nhap / dang xuat.
- Dang ky tai khoan.
- Admin duyet tai khoan.
- Xem trang thai he thong.
- Xem frame hien tai qua API `/api/current_frame`.
- Xem video feed qua `/video_feed`.
- Xem ket qua AI, ty le ban, trang thai PLC.
- Start / stop he thong.
- Kich ve sinh thu cong tu xa.
- Doi PLC IP.
- Reconnect PLC.
- Doi camera id.
- Doi nguong ty le ban.
- Doi chu ky snapshot.
- Xem snapshot da luu.
- Day trang thai real-time bang WebSocket.

FastAPI duoc chon vi co kha nang xu ly bat dong bo tot, phu hop voi viec cap nhat trang thai, gui frame camera va dieu khien tu xa.

### 5.10. Ung dung di dong

Du an co ban ung dung di dong React Native / Expo trong thu muc `solar_clean_rn`.

Chuc nang chinh:

- Dang nhap / dang xuat.
- Luu phien dang nhap.
- Man hinh dashboard.
- Tab Monitor de xem trang thai va hinh anh.
- Tab Control de dieu khien he thong.
- Lay frame hien tai tu backend.
- Xem snapshot preview.
- Xem KPI va thanh xac suat AI.
- Gui lenh start, stop, reconnect PLC, manual clean.
- Cai dat PLC IP, camera id, chu ky snapshot va nguong ban.
- Dung WebSocket de cap nhat realtime, co polling fallback neu WebSocket khong kha dung.

## 6. Giai thich cu the ve AI model

### 6.1. CNN la gi?

CNN la viet tat cua **Convolutional Neural Network**, nghia la mang no-ron tich chap. Day la mot loai mo hinh hoc sau duoc thiet ke dac biet cho bai toan xu ly anh.

Neu con nguoi nhin vao mot buc anh va nhan ra vet ban bang mat, CNN se hoc cach nhan ra cac dac trung hinh anh nhu:

- Canh, duong vien, goc canh.
- Vung sang toi.
- Ket cau be mat.
- Vet mo, vet bui, vet dam.
- Mau sac va hinh dang bat thuong.
- Su khac nhau giua be mat tam pin sach va be mat co vat can.

CNN khong can nguoi lap trinh tung quy tac nhu "neu pixel toi hon thi la ban". Thay vao do, CNN hoc tu du lieu anh da gan nhan. Neu du lieu huan luyen co nhieu anh tam pin sach va ban, model se tu hoc ra mau hinh nao thuong tuong ung voi `sach`, mau hinh nao thuong tuong ung voi `ban`.

### 6.2. EfficientNet-B0 la gi?

EfficientNet-B0 la mot kien truc CNN hien dai, duoc thiet ke de dat do chinh xac cao trong khi van tiet kiem so tham so va tai nguyen tinh toan. Chu "Efficient" the hien muc tieu cua kien truc nay: hieu qua hon, nhe hon, nhung van co kha nang nhan dien tot.

EfficientNet-B0 thuong duoc su dung lam model nen cho cac bai toan phan loai anh. Trong du an nay, EfficientNet-B0 duoc dung de nhan dien tung patch nho cua tam pin.

Ly do phu hop voi du an:

- Dau vao chuan cua EfficientNet-B0 la anh kich thuoc `224 x 224`, trung voi kich thuoc patch dang su dung.
- Model co kich thuoc vua phai, phu hop de convert sang TensorFlow Lite.
- Co the tan dung transfer learning, nghia la dung model da hoc dac trung anh tong quat roi huan luyen lai cho bai toan tam pin.
- Toc do nhanh hon nhieu kien truc CNN lon, phu hop cho he thong giam sat thuc te.

### 6.3. EfficientNet-B0 hoat dong nhu the nao?

Mot cach de hieu don gian:

```text
Anh patch 224x224
-> Cac lop convolution trich xuat dac trung co ban
-> Cac khoi MBConv hoc dac trung sau hon
-> Gop thong tin toan anh
-> Lop phan loai
-> Xac suat: sach / ban / nopanel
```

Cac thanh phan quan trong:

- **Convolution**: quet cac bo loc tren anh de phat hien dac trung.
- **Depthwise separable convolution**: giam so phep tinh so voi convolution thong thuong.
- **MBConv block**: khoi xu ly chinh cua EfficientNet, giup model hoc dac trung tot nhung van nhe.
- **Squeeze-and-Excitation**: giup model tu hoc kenh dac trung nao quan trong hon.
- **Activation function**: giup model hoc quan he phi tuyen trong anh.
- **Softmax output**: bien ket qua cuoi thanh xac suat cua tung lop.

Vi du voi mot patch, model co the tra ve:

```text
sach:    0.08
ban:     0.89
nopanel: 0.03
```

Khi do he thong lay lop co xac suat cao nhat la `ban`, voi do tin cay 89%.

### 6.4. Vi sao khong chi nhan dien ca tam pin mot lan?

Neu chi dua ca anh tam pin vao AI va hoi "tam pin nay sach hay ban", he thong chi biet ket qua tong quat. Cach nay co nhieu han che:

- Khong biet vung nao bi ban.
- Khong uoc luong duoc dien tich ban.
- Vet ban nho co the bi bo qua.
- Neu mot goc anh co vat can, model co the ket luan sai cho ca tam pin.

Vi vay, du an chon cach chia thanh cac patch nho. Loi ich:

- Nhan dien cuc bo tot hon.
- Tinh duoc ty le dien tich ban.
- De hien thi truc quan tren anh bang luoi o.
- Co the mo rong de biet la cay, phan chim, vet nut nam o khu vuc nao.
- Giam rui ro do camera chup lech vi co lop `nopanel` de loai bo patch khong hop le.

### 6.5. Transfer learning trong du an

Transfer learning la cach dung mot model da duoc huan luyen truoc tren tap anh lon, sau do huan luyen tiep cho bai toan rieng.

Trong du an nay, cach tiep can phu hop la:

1. Lay EfficientNet-B0 da pretrained.
2. Thay lop phan loai cuoi thanh so lop cua du an.
3. Huan luyen tren du lieu tam pin da gan nhan.
4. Kiem tra do chinh xac tren tap validation va test.
5. Convert model sang `.tflite`.
6. Dua model vao phan mem desktop de chay thuc te.

Loi ich:

- Can it du lieu hon so voi huan luyen tu dau.
- Model hoc nhanh hon.
- Tan dung duoc dac trung anh tong quat nhu canh, ket cau, vung sang toi.
- Phu hop voi bai toan thuc te khi viec thu thap du lieu ban dau con han che.

### 6.6. Dau ra cua model va cach he thong su dung

Model khong truc tiep dieu khien PLC. Model chi tra ve ket qua nhan dien cho tung patch. Phan mem moi la noi ra quyet dinh cuoi cung.

Quy trinh:

```text
Model AI -> Xac suat tung lop cua moi patch
Phan mem -> Dem so patch ban va tinh ty le
Bo quy tac -> So sanh voi nguong
PLC -> Nhan lenh ve sinh neu thoa dieu kien
```

Cach tach rieng AI va bo quy tac giup he thong de bao tri hon:

- Neu model can nang cap, chi thay file `.tflite`.
- Neu nguong ve sinh can thay doi, chi doi cau hinh.
- Neu PLC thay doi dia chi, chi doi thong so ket noi.
- Neu them chuc nang moi, co the bo sung lop va bo quy tac uu tien.

## 7. Chuc nang hien tai cua he thong

### 7.1. Nhan dien be mat tam pin bi ban

He thong da co kha nang phat hien cac patch bi ban tren tam pin. Khi so patch ban dat dieu kien, he thong ket luan tam pin can ve sinh.

Ket qua hien thi gom:

- Lop du doan.
- Do tin cay.
- Ty le patch ban.
- So patch ban / so patch hop le.
- So patch `nopanel`.
- Anh debug co ve khung tung patch.

### 7.2. Tu dong kich ve sinh

Khi AI ket luan can ve sinh, phan mem gui xung den PLC. PLC se chay chu trinh ve sinh theo logic dieu khien da lap trinh o PLC.

He thong co them:

- Dieu kien PLC phai ket noi.
- Cooldown de tranh kich lien tuc.
- Che do manual clean de nguoi van hanh kich thu cong khi can.

### 7.3. Giam sat tu xa

Nguoi dung co the giam sat qua:

- Giao dien desktop tai may dieu khien.
- Web monitor trong trinh duyet.
- Ung dung di dong React Native.

Nguoi dung co the xem:

- Trang thai he thong.
- Trang thai PLC.
- Hinh anh camera.
- Anh snapshot moi nhat.
- Ty le ban.
- So lan ve sinh.
- Chu ky snapshot.
- Nguong kich hoat.

### 7.4. Quan ly tai khoan

He thong co chuc nang dang ky, dang nhap va duyet tai khoan. Admin co the quan ly tai khoan nguoi dung. Dieu nay giup phan quyen khi dua he thong vao moi truong van hanh co nhieu nguoi truy cap.

## 8. Chuc nang sap phat trien

Ngoai viec nhan dien `sach`, `ban`, `nopanel`, du an se mo rong them cac chuc nang nhan dien chuyen sau:

### 8.1. Nhan dien la cay tren tam pin

La cay la vat can thuong gap khi tam pin lap ngoai troi, dac biet gan cay xanh. La cay co the che mot phan be mat tam pin, tao bong va lam giam hieu suat phat dien.

Chuc nang du kien:

- AI nhan dien patch co la cay.
- He thong danh dau vi tri la cay tren anh.
- Tinh ty le khu vuc bi la cay che phu.
- Neu phat hien la cay, he thong tu dong kich PLC ve sinh.

Quy tac dieu khien:

```text
Neu phat hien la cay -> Tu dong ve sinh
```

### 8.2. Nhan dien phan chim

Phan chim la dang ban cuc bo nhung anh huong manh den hieu suat vi co the che kin mot hoac nhieu cell nho. Phan chim cung co tinh bam dinh cao, can duoc xu ly som.

Chuc nang du kien:

- AI nhan dien patch co phan chim.
- Phan biet phan chim voi bui ban thong thuong.
- Uu tien ve sinh khi phat hien phan chim.
- Luu anh snapshot lam bang chung bao tri.

Quy tac dieu khien:

```text
Neu phat hien phan chim -> Tu dong ve sinh
```

### 8.3. Nhan dien tam pin nut vo

Vet nut vo la loi nghiem trong hon bui ban, vi day la dau hieu hu hong vat ly cua tam pin. Neu chi ve sinh ma khong canh bao, co the khong giai quyet duoc van de va co the lam tang rui ro hu hong.

Chuc nang du kien:

- AI nhan dien patch co vet nut, vet vo, duong ran hoac bat thuong vat ly.
- Danh dau vi tri vet nut tren anh.
- Gui canh bao den nguoi van hanh.
- Khong xem vet nut la ly do ve sinh thong thuong.
- Luu snapshot de doi ngu bao tri kiem tra.

Quy tac dieu khien:

```text
Neu phat hien vet nut / vo -> Canh bao nguoi van hanh
```

Trong truong hop co vet nut, nen uu tien canh bao va kiem tra thu cong. Tuy tung co cau thuc te, co the tam dung chu trinh ve sinh doi voi tam pin do de tranh lam vet nut nang hon.

### 8.4. De xuat bo lop moi cho model

Khi mo rong, model co the co cac lop:

```text
0 sach
1 bui_ban
2 la_cay
3 phan_chim
4 nut_vo
5 nopanel
```

Hoac co the tach thanh hai nhom:

- Nhom can ve sinh: `bui_ban`, `la_cay`, `phan_chim`.
- Nhom can canh bao: `nut_vo`.
- Nhom loai bo: `nopanel`.
- Nhom binh thuong: `sach`.

Bang quyet dinh de nguoi doc de hieu:

| Ket qua AI | Hanh dong cua he thong |
|---|---|
| sach | Khong ve sinh |
| bui_ban | Ve sinh neu ty le vuot nguong |
| la_cay | Tu dong ve sinh |
| phan_chim | Tu dong ve sinh, uu tien cao |
| nut_vo | Canh bao, luu anh, thong bao bao tri |
| nopanel | Khong tinh vao dien tich tam pin |

### 8.5. Luu y khi mo rong model

Khi them la cay, phan chim va vet nut, nen can nhac bai toan co the co nhieu doi tuong trong cung mot patch. Vi du mot patch vua co bui ban vua co vet nut, hoac vua co la cay vua co phan chim.

Co hai huong ky thuat:

1. **Multi-class classification**

   Moi patch chi co mot nhan duy nhat. Cach nay don gian, de huan luyen va phu hop voi giai doan dau. Neu patch co nhieu doi tuong, chon nhan quan trong nhat theo muc uu tien.

2. **Multi-label classification**

   Mot patch co the co nhieu nhan cung luc. Cach nay phu hop hon khi du lieu phuc tap, nhung can nhieu du lieu va cach huan luyen phuc tap hon.

Trong giai doan mo rong ban dau, co the dung multi-class de don gian hoa. Sau khi co nhieu du lieu thuc te, co the nang cap sang multi-label hoac dung object detection/segmentation de dinh vi chinh xac hon tung vat the.

## 9. Du lieu can thu thap cho giai doan tiep theo

De model nhan dien tot hon, can thu thap du lieu thuc te trong nhieu dieu kien:

- Tam pin sach trong nhieu goc chup.
- Tam pin bi bui nhe, bui nang.
- Tam pin co la cay nho, la cay lon, nhieu la.
- Tam pin co phan chim o nhieu hinh dang va kich thuoc.
- Tam pin co vet nut nho, vet nut dai, vet vo ro.
- Anh co bong do, nang gat, troi am, anh thieu sang.
- Anh chup bi nghieng, bi lech, co nen ngoai tam pin.
- Anh sau khi ve sinh de so sanh truoc / sau.

Cach gan nhan nen thong nhat:

- Moi patch can co nhan ro rang.
- Neu patch khong phai tam pin thi gan `nopanel`.
- Neu patch co vat can can ve sinh thi gan theo loai vat can.
- Neu patch co vet nut thi gan `nut_vo` va uu tien cao hon nhan `ban`.

## 10. Danh gia model

Khi huan luyen va kiem tra model, nen su dung cac chi so:

- **Accuracy**: ty le du doan dung tong the.
- **Precision**: trong cac patch model bao la ban, bao nhieu patch that su ban.
- **Recall**: trong cac patch that su ban, model phat hien duoc bao nhieu.
- **F1-score**: can bang giua precision va recall.
- **Confusion matrix**: xem model hay nham lop nao voi lop nao.

Doi voi he thong ve sinh tu dong, can chu y:

- Neu model bao ban nham qua nhieu, PLC co the ve sinh khong can thiet.
- Neu model bo sot qua nhieu, tam pin bi ban nhung khong duoc ve sinh.
- Doi voi vet nut, uu tien recall cao vi bo sot vet nut co the gay rui ro bao tri.
- Doi voi phan chim va la cay, uu tien phat hien nhanh de kich ve sinh kip thoi.

## 11. Diem manh cua giai phap

- Ket hop AI va PLC thanh mot he thong tu dong hoan chinh.
- Dung model CNN EfficientNet-B0 phu hop voi bai toan phan loai anh.
- Trien khai model nhe bang TensorFlow Lite.
- Khong chi phan loai toan anh ma phan tich theo 32 patch, giup tinh duoc ty le dien tich ban.
- Co lop `nopanel` de tranh tinh sai khi camera chup lech hoac anh co vung ngoai tam pin.
- Co giao dien desktop, web va mobile de giam sat linh hoat.
- Co snapshot va anh debug de kiem tra lai ket qua AI.
- Co the mo rong de phat hien la cay, phan chim va tam pin nut vo.
- Co ket noi PLC thuc te de dieu khien co cau ve sinh.

## 12. Han che hien tai va huong cai tien

Han che hien tai:

- Anh dang duoc resize ve khung tam thoi roi chia patch, chua co buoc cat chinh xac vung tam pin bang ROI.
- Neu camera lap dat lech nhieu, ty le patch co the bi anh huong.
- Model hien tai moi co 3 lop, chua tach rieng la cay, phan chim va vet nut.
- Chua co co che phan biet muc do nghiem trong cua tung loai ban.
- Neu patch co nhieu doi tuong cung luc, multi-class co the chi chon duoc mot nhan.

Huong cai tien:

- Them buoc phat hien vung tam pin va can chinh phoi canh bang `warpPerspective`.
- Mo rong tap du lieu va so lop nhan dien.
- Huan luyen model moi voi cac lop `la_cay`, `phan_chim`, `nut_vo`.
- Them muc uu tien: vet nut canh bao cao nhat, phan chim ve sinh uu tien, la cay ve sinh ngay, bui ban ve sinh theo nguong.
- Them lich su su kien: thoi gian phat hien, anh minh chung, hanh dong PLC.
- Them thong bao tren mobile khi co vet nut hoac loi PLC.
- Danh gia model bang confusion matrix va bao cao do chinh xac.

## 13. Quy tac dieu khien de xuat sau khi mo rong

Bang logic uu tien:

| Do uu tien | Dieu kien AI | Hanh dong |
|---|---|---|
| 1 | Phat hien `nut_vo` | Canh bao ngay, luu anh, thong bao bao tri |
| 2 | Phat hien `phan_chim` | Tu dong ve sinh, luu su kien |
| 3 | Phat hien `la_cay` | Tu dong ve sinh, luu su kien |
| 4 | Ty le `bui_ban` vuot nguong | Tu dong ve sinh |
| 5 | Tam pin `sach` | Khong kich PLC |
| 6 | Qua nhieu `nopanel` | Bao camera lech hoac khong du anh tam pin |

Dang pseudo-code:

```text
Neu phat hien nut_vo:
    Gui canh bao
    Luu snapshot
    Khong uu tien ve sinh tu dong neu co nguy co lam nang vet nut
Nguoc lai neu phat hien phan_chim:
    Kich PLC ve sinh
Nguoc lai neu phat hien la_cay:
    Kich PLC ve sinh
Nguoc lai neu ty le bui_ban >= nguong:
    Kich PLC ve sinh
Nguoc lai:
    Khong ve sinh
```

## 14. Ket luan

Du an da xay dung duoc nen tang cho he thong ve sinh tam pin mat troi tu dong su dung tri tue nhan tao. Trong he thong nay, AI khong chi nhan dien tam pin sach hay ban mot cach tong quat, ma phan tich tung vung nho cua tam pin de tinh ty le dien tich ban. Ket qua AI duoc ket hop voi PLC Siemens S7 de kich hoat co cau ve sinh, tao thanh mot vong lap tu dong tu quan sat, phan tich, ra quyet dinh den dieu khien thuc te.

Mo hinh CNN EfficientNet-B0 la thanh phan cot loi cua phan nhan dien. Model duoc trien khai bang TensorFlow Lite de toi uu toc do va tai nguyen. Cach chia 32 patch giup he thong co kha nang danh gia cuc bo, uoc luong dien tich ban va mo rong de nhan dien cac doi tuong cu the nhu la cay, phan chim va vet nut vo.

Trong giai doan tiep theo, du an se nang cap model de nhan dien them la cay, phan chim va tam pin nut vo. Khi phat hien la cay hoac phan chim, he thong se tu dong ve sinh. Khi phat hien vet nut hoac vo, he thong se canh bao nguoi van hanh de kiem tra va bao tri. Huong phat trien nay giup he thong khong chi la thiet bi ve sinh tu dong, ma con tro thanh mot he thong giam sat tinh trang tam pin thong minh.

