# Database Migrations

Thu muc nay danh cho migration schema sau nay.

Trong MVP hien tai, cach tao bang nhanh la dung SQLAlchemy metadata:

```powershell
docker compose run --rm backend python -m app.db.init_db
```

Lenh nay doc cac model trong `backend/app/models/` va tao nhung bang chua ton tai trong PostgreSQL.

Seed user demo sau khi tao bang:

```powershell
docker compose run --rm backend python -m app.db.seed
```

Khi schema bat dau thay doi thuong xuyen hoac can deploy nghiem tuc, chuyen sang Alembic de co version migration ro rang.
