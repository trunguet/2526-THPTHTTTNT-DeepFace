# Frontend Admin/User Review

Pham vi: `frontend/admin`, `frontend/user`, va cac file dung chung trong `frontend/shared`.

## Yeu diem cua ban cu

1. Link dieu huong bi gay

- `frontend/admin/index.html` tro toi `dashboard.html` nhung file that la `index.html`.
- Nhieu trang tro toi `settings.html` va `login.html` nhung ban cu chua co file.
- Logout dung `/login.html`, khi chay moi frontend trong container rieng se de gay route.

2. Cau hinh API bi lap va khong phu hop vanilla JS

- Nhieu file tung dung `process.env.REACT_APP_API_BASE_URL`, bien nay khong ton tai trong browser neu khong co bundler.
- Moi module tu viet base URL rieng, kho doi moi truong khi demo bang Docker.

3. Dashboard admin dung mock data cung

- So lieu dashboard khong phan anh backend.
- Khi giang vien test, dashboard van hien so ao nen kho danh gia he thong end-to-end.

4. Filter lam mat du lieu goc

- `manage_list.js`, `view_logs.js`, `check_history.js` filter truc tiep tren mang hien tai.
- Sau khi filter nhieu lan, du lieu bi thu hep dan va phai fetch lai moi khoi phuc.

5. Render du lieu API chua an toan

- Nhieu cho ghep chuoi vao `innerHTML` tu API.
- Neu backend tra ve chuoi co HTML/script, frontend co nguy co XSS.

6. UX loi va trang thai loading con mong

- Loi backend chi hien thong bao chung chung.
- Khi backend chua implement endpoint, nguoi dung khong biet loi do frontend hay backend.
- Camera xin quyen ngay khi load page, gay trai nghiem hoi dot ngot.

7. Thieu man hinh cau hinh va phien demo

- De bai yeu cau docker-compose chay duoc de giang vien danh gia nhanh.
- Neu backend auth chua xong, frontend can co phien demo/toi thieu de test luong UI.

## Cai thien da lam

1. Them API client dung chung

- File: `frontend/shared/api.js`
- Chuc nang: base URL, token, request JSON/FormData, parse loi, health check, normalize list, escape HTML.
- Admin/user co wrapper rieng: `frontend/admin/api.js`, `frontend/user/api.js`.

2. Sua route va them trang thieu

- Them `frontend/admin/settings.html`
- Them `frontend/admin/login.html`
- Them `frontend/user/login.html`
- Sua logout ve route tuong doi `./login.html`.

3. Dashboard admin lay du lieu tu API

- File moi: `frontend/admin/dashboard.js`
- Lay `/api/employees`, `/api/access-logs`, `/api/access-logs/alerts`.
- Neu backend chua san sang, hien loi ro tren bang hoat dong.

4. Quan ly nhan vien tot hon

- File: `frontend/admin/manage_list.js`
- Tach `allEmployees` va `visibleEmployees`.
- Search khong lam mat du lieu goc.
- Render text API qua `DeepFaceAPI.escapeHTML`.
- Delete dung API client, thong bao loi cu the.

5. Log va canh bao tot hon

- File: `frontend/admin/view_logs.js`
- Tach `allLogs` va `visibleLogs`.
- Filter ngay/trang thai khong mutate du lieu goc.
- Render alert/log an toan hon.
- Auto refresh giu nguyen.

6. User history tot hon

- File: `frontend/user/check_history.js`
- Ho tro empty state khi chua co `employee_id`.
- Filter date/month khong lam mat du lieu goc.
- Export CSV theo du lieu dang hien thi.

7. Face scan than thien hon

- File: `frontend/user/face_scan.js`
- Khong xin quyen camera ngay khi load.
- Chi xin quyen khi bam khoi dong.
- Hien ro truong hop backend chua implement API nhan dien.

## Huong cai thien tiep theo

1. Can backend chot contract API

Frontend nen thong nhat schema voi backend:

- `GET /api/employees` tra list nhan vien: `id`, `employee_id`, `full_name`, `email`, `department`, `image_url`, `status`.
- `POST /api/employees/upload-image` tra `image_url`.
- `POST /api/employees` tra record nhan vien vua tao.
- `POST /api/employees/{id}/extract-embedding` tra trang thai job queue.
- `POST /api/access/verify-face` tra `status: allowed | denied | stranger`, `confidence`, `employee_name`, `message`.
- `GET /api/access-logs` tra log co `timestamp`, `status`, `camera_location`.
- `GET /api/access-logs/alerts` tra alert co `image_url`, `confidence`, `timestamp`.

2. Nen them trang sua nhan vien

Hien tai nut "Sua" chi thong bao can backend. Khi backend co `PUT /api/employees/{id}`, nen them:

- `frontend/admin/edit_employee.html`
- `frontend/admin/edit_employee.js`
- Load thong tin nhan vien theo ID.
- Sua email/phong ban/trang thai.
- Doi anh va trigger re-embedding neu can.

3. Nen them trang cau hinh camera

Theo use case "kiem soat truy cap cong ty", admin nen quan ly:

- Ten camera.
- Vi tri camera.
- Loai cong: vao/ra.
- Trang thai bat/tat.

4. Nen them UX cho background jobs

Khi upload anh va extract embedding, frontend nen hien tien trinh:

- Upload anh.
- Tao employee.
- Day job extract embedding vao queue.
- Poll job status den khi indexed vao Qdrant.

5. Nen them demo data fallback co kiem soat

Chi dung khi backend chua xong:

- Bat/tat bang localStorage hoac settings.
- Ghi ro trong README la demo mode.
- Khong de demo data gia lam sai ket qua khi cham.

6. Nen them test nhe cho frontend

Khong can framework lon, toi thieu:

- Smoke test bang Playwright: admin/user/login/settings/index tra 200.
- Kiem tra console khong co `ReferenceError`.
- Kiem tra nut start camera ton tai va API URL dung port Docker.

## Noi dung nen trinh bay trong bao cao

- Frontend admin quan ly nhan vien, xem log, xem canh bao, cau hinh backend.
- Frontend user co scan camera, xem lich su, export CSV.
- Frontend da tach API client dung chung, san sang ket noi backend Docker.
- Diem con thieu nam o backend/contract: auth that, CRUD that, queue embedding, vector indexing, face verification.
