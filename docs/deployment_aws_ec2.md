# Ghi Chú Triển Khai AWS EC2

Tài liệu này ghi lại trạng thái triển khai hiện tại của Scientific Journal Pipeline trên AWS EC2.

## Môi Trường Hiện Tại

- AWS EC2 Ubuntu 24.04
- Docker Compose
- SQL Server 2022 container
- Python pipeline container
- Airflow webserver và scheduler cho lịch chạy pipeline
- GitHub Actions CI/CD v1

Đường dẫn project trên EC2:

```text
/opt/scientific-journal-pipeline
```

Tài liệu liên quan:

- `docs/airflow_dataops_operations.md`: vận hành Airflow và DataOps.
- `docs/ci_cd_operations.md`: luồng CI/CD, lỗi đã gặp, và cách xử lý.

## Cấu Trúc Repository

```text
src/                    Mã nguồn pipeline
airflow/                Dockerfile, DAG, logs, plugins của Airflow
docs/                   Tài liệu bàn giao và vận hành
sql/database_ver7.sql   Script tạo database mới
Dockerfile              Image Python pipeline
docker-compose.yml      SQL Server, pipeline, Airflow services
.github/workflows/      CI/CD workflows
.env.example            Mẫu biến môi trường
requirements.txt        Dependencies runtime
requirements-dev.txt    Dependencies phục vụ dev/CI
```

## Khởi Tạo Database

Chạy `sql/database_ver7.sql` vào SQL Server bằng SSMS hoặc SQL Server client khác.

Script này tạo database, schemas, bảng `raw`, bảng `core`, bảng `ops`, constraints, và seed data cần thiết cho pipeline.

## User Runtime

- `sa`: chỉ dùng cho admin, migration, backup.
- `pipeline_user`: dùng cho Python pipeline, có quyền ghi vào `raw`, `core`, và `ops`.
- `backend_user`: dùng cho backend API, nên đọc từ `core` hoặc `mart` sau này.

## EC2 Security Group

Chỉ mở inbound theo IP cụ thể.

```text
22    SSH         IP cá nhân /32
1433  SQL Server  IP cá nhân và IP backend team /32
8080  Airflow     IP cá nhân /32 hoặc IP được phép truy cập UI
```

Không mở SQL Server với `0.0.0.0/0`.

## Test Local Trỏ Tới Cloud DB

Dùng `pipeline_user` trong `.env`, sau đó chạy:

```powershell
python -m src.jobs.sync.openalex_works --keywords "machine learning" --per-page 25 --max-pages-per-keyword 1 --page-delay-seconds 2 --enrich-authors --enrich-sources --enrich-limit 25
```

## Các Chế Độ Watermark

- `initial`: chưa có watermark, crawl keyword bình thường và không dùng mốc `updated-date` phía dưới.
- `resume`: lần chạy trước dừng khi còn cursor, tiếp tục cùng crawl window.
- `incremental`: crawl window trước đã hoàn thành, chạy tiếp từ `last_to_updated_date`.

## Mốc Backup

Backup cloud đầu tiên đã xác minh:

```text
scientific_journal_tracking_db_pipeline_ready.bak
```

Ý nghĩa: database đã sẵn sàng cho pipeline. Các bảng riêng cho backend có thể bổ sung sau.

Sau khi Airflow chạy ổn, backup mốc tiếp theo:

```text
scientific_journal_tracking_db_airflow_ready.bak
```

## CI/CD Hiện Tại

CI:

```text
.github/workflows/ci.yml
```

CD:

```text
.github/workflows/deploy.yml
```

Luồng deploy:

```text
merge vào main
-> GitHub Actions Deploy
-> SSH vào EC2
-> cd /opt/scientific-journal-pipeline
-> git pull origin main
-> docker compose up -d --build airflow-postgres airflow-init airflow-webserver airflow-scheduler
-> curl http://localhost:8080/health
```

Kiểm tra sau deploy:

```bash
cd /opt/scientific-journal-pipeline
docker compose ps airflow-postgres airflow-webserver airflow-scheduler
curl -i http://localhost:8080/health
```
