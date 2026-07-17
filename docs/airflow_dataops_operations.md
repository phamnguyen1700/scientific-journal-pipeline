# Vận Hành Airflow DataOps

Tài liệu này mô tả cách vận hành an toàn Scientific Journal Pipeline trên AWS EC2 với Airflow.

Mục tiêu hiện tại không phải crawl càng nhiều càng tốt. Mục tiêu là mỗi batch phải theo dõi được, khôi phục được, và dễ kiểm chứng trước khi tăng tải.

## Chiến Lược An Toàn Hiện Tại

DAG Airflow đang chạy theo cấu hình nhỏ:

```text
keywords: 6 seed keywords
per page: 10 works
max pages per keyword: 1
max works per run: khoảng 60
author enrich limit: 300
source enrich limit: 300
schedule: hằng tuần
```

Cấu hình này giữ API usage, tải EC2, và lượng ghi vào SQL Server ở mức nhỏ, đồng thời vẫn cho phép enrich author/source bắt kịp dữ liệu raw mới nhất.

## DAG OpenAlex Hiện Tại

DAG nằm tại:

```text
airflow/dags/openalex_works_sync_dag.py
```

DAG chạy command:

```bash
cd /opt/airflow && python -m src.jobs.sync.openalex_works \
  --keywords "artificial intelligence" "machine learning" "deep learning" \
    "computer vision" "natural language processing" "data mining" \
  --per-page 10 \
  --max-pages-per-keyword 1 \
  --page-delay-seconds 2 \
  --enrich-authors \
  --enrich-sources \
  --enrich-limit 300
```

Hành vi quan trọng:

- Mỗi keyword được truyền riêng.
- Mỗi keyword có một dòng riêng trong `ops.crawl_watermarks`.
- Mỗi lần chạy ghi log vào `ops.job_runs`.
- Dữ liệu raw giữ trong schema `raw`.
- Dữ liệu đã xử lý ghi vào schema `core`.
- Backend nên đọc từ `core`, không đọc trực tiếp từ `raw` hoặc `ops`.

## Keyword Parsing

CLI sync chấp nhận cả hai dạng:

```bash
--keywords "machine learning" "deep learning"
```

and:

```bash
--keywords "machine learning,deep learning"
```

Dạng đầu tiên được ưu tiên trong Airflow vì log hiển thị rõ số lượng keyword:

```text
OpenAlex works sync started: keywords=6
```

Nếu log hiển thị `keywords=1` trong khi giá trị chứa nhiều keyword phân tách bằng dấu phẩy, command trong DAG đang sai hoặc image cũ vẫn đang chạy.

## Deploy Sau Khi Có CI/CD

Hiện tại deploy đã được tự động hóa bằng GitHub Actions.

File workflow:

```text
.github/workflows/deploy.yml
```

Khi merge vào `main`, GitHub Actions sẽ SSH vào EC2 và chạy:

```bash
cd /opt/scientific-journal-pipeline
git pull origin main
docker compose up -d --build airflow-postgres airflow-init airflow-webserver airflow-scheduler
docker compose ps airflow-postgres airflow-webserver airflow-scheduler
curl http://localhost:8080/health
```

Nếu cần deploy thủ công, dùng cùng các lệnh trên sau khi SSH vào EC2.

Không dùng:

```bash
docker compose --profile airflow up -d --build
```

vì có thể kéo thêm service `sqlserver` và gây conflict container name nếu SQL Server container cũ đang chạy.

## Lệnh Airflow Thường Dùng

Liệt kê container:

```bash
docker ps
```

Kiểm tra DAG:

```bash
docker exec -it scientific-journal-airflow-scheduler airflow dags list
docker exec -it scientific-journal-airflow-scheduler airflow dags list-import-errors
```

Re-serialize DAG nếu UI chưa thấy DAG mới:

```bash
docker exec -it scientific-journal-airflow-scheduler airflow dags reserialize
docker compose --profile airflow restart airflow-webserver airflow-scheduler
```

Trigger DAG thủ công:

```bash
docker exec -it scientific-journal-airflow-scheduler airflow dags trigger openalex_works_sync
```

Liệt kê DAG runs:

```bash
docker exec -it scientific-journal-airflow-scheduler airflow dags list-runs -d openalex_works_sync
```

Đọc task log trên EC2:

```bash
find airflow/logs -type f | grep 'dag_id=openalex_works_sync' | sort | tail -1
tail -160 "$(find airflow/logs -type f | grep 'dag_id=openalex_works_sync' | sort | tail -1)"
```

## Log Healthy Kỳ Vọng

Một run thành công thường có log:

```text
OpenAlex works sync started: keywords=6
[1/6] Sync keyword: artificial intelligence
[2/6] Sync keyword: machine learning
...
OpenAlex works sync completed. Total changed raw works: <number>
Command exited with return code 0
Marking task as SUCCESS
```

Nếu `keywords=1` nhưng text chứa cả sáu keyword, dừng lại và sửa command trong DAG trước khi tin batch đó.

## Query Kiểm Tra Database

Chạy trong SSMS sau một test run:

```sql
USE scientific_journal_tracking_db;

SELECT COUNT(*) AS total_papers
FROM core.papers;

SELECT COUNT(*) AS total_authors
FROM core.authors;

SELECT COUNT(*) AS total_journals
FROM core.journals;

SELECT COUNT(*) AS total_paper_authors
FROM core.paper_authors;

SELECT TOP 20
    job_name,
    status,
    records_in,
    records_out,
    records_failed,
    started_at,
    finished_at,
    error_message
FROM ops.job_runs
ORDER BY started_at DESC;

SELECT
    source_entity,
    scope_type,
    scope_value,
    last_cursor,
    last_from_updated_date,
    last_to_updated_date,
    last_processed_record_id,
    updated_at
FROM ops.crawl_watermarks
ORDER BY updated_at DESC;
```

Kiểm tra duplicate source mappings:

```sql
SELECT source_record_id, COUNT(*) AS total
FROM core.author_source_mappings
GROUP BY source_record_id
HAVING COUNT(*) > 1;
```

Query này nên trả về 0 dòng.

## Vì Sao Số Authors Có Thể Lớn Hơn Papers

Điều này bình thường:

```text
99 papers * about 4 authors per paper = about 396 authors
```

Quan hệ dữ liệu:

```text
core.papers          1 paper row
core.authors         many author rows
core.paper_authors   paper-author relationship rows
```

Rủi ro cần theo dõi không phải là "authors > papers". Rủi ro thật là duplicate source mappings hoặc raw backlog tăng mãi nhưng không được xử lý.

## Quy Tắc Enrichment

Author/source enrichment chọn các record pending từ mapping hiện có.

Với batch nhỏ:

```text
crawl up to 60 works
enrich up to 300 authors
enrich up to 300 sources
```

Điều này nghĩa là enrich step có thể xử lý cả record mới và một phần backlog cũ. Nếu backlog lớn hơn limit, một số record vẫn pending cho lần chạy sau. Điều này không làm hỏng dữ liệu, nhưng có nghĩa là một số record chưa enrich đầy đủ.

## Vấn Đề Data Quality Đã Biết

Một số OpenAlex sources có thể fail khi process vì metadata vi phạm constraint hiện tại của `core.journals`, ví dụ constraint về năm xuất bản.

Không nới constraint tùy tiện trong DAG vận hành. Giữ raw record bị fail, log lỗi, và xử lý trong giai đoạn Data Quality sau.

## Hướng Scale

Không gộp tất cả nguồn vào một DAG lớn.

Dùng DAG tách theo từng nguồn:

```text
OpenAlex DAG
  ingest
  process
  enrich authors
  enrich sources
  validate

Crossref DAG
  ingest
  process
  validate

Semantic Scholar DAG
  ingest
  process
  validate

Canonical Merge DAG
  match duplicate papers
  resolve source priority
  update canonical core
  validate core
```

Layering khuyến nghị:

```text
source API
raw.<source>_*
normalized/staging layer
quality checks
core canonical tables
mart tables for analytics and backend views
```

Backend nên đọc từ `core` hoặc sau này là `mart`, không đọc bảng `raw` theo từng source.

## Khi Nào Tăng Volume

Chỉ tăng volume sau vài lần chạy thành công khi:

- Airflow task status là success.
- `ops.job_runs.records_failed` thấp và đã hiểu nguyên nhân.
- `ops.crawl_watermarks` dịch chuyển đúng.
- Duplicate mapping checks trả về 0 dòng.
- Raw pending backlog ổn định hoặc giảm.
- CPU, memory, disk của EC2 và response SQL Server vẫn chấp nhận được.

Tăng dần theo gợi ý:

```text
Step 1: per-page 10, max-pages 1, weekly
Step 2: per-page 25, max-pages 1, weekly
Step 3: per-page 25, max-pages 2, weekly
Step 4: per-page 50, max-pages 2, weekly
```

Nếu raw author/source backlog tăng, tăng enrich limit trước khi tăng crawl volume.

## Backup Sau Khi Airflow Ổn Định

Sau khi xác minh một Airflow run thành công, tạo backup có tên:

```sql
BACKUP DATABASE scientific_journal_tracking_db
TO DISK = '/var/opt/mssql/backup/scientific_journal_tracking_db_airflow_ready.bak'
WITH INIT, COMPRESSION, STATS = 10;
```

Copy backup ra khỏi SQL Server container:

```bash
docker exec -it scientific-journal-sqlserver mkdir -p /var/opt/mssql/backup
docker cp scientific-journal-sqlserver:/var/opt/mssql/backup/scientific_journal_tracking_db_airflow_ready.bak /opt/scientific-journal/scientific_journal_tracking_db_airflow_ready.bak
ls -lh /opt/scientific-journal/*.bak
```

Không commit backup vào Git.
