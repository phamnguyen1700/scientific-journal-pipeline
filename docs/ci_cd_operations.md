# Hướng Dẫn CI/CD Cho Scientific Journal Pipeline

Tài liệu này ghi lại các bước đã triển khai CI/CD cho project, các lỗi đã gặp, cách debug, và trạng thái cuối cùng sau khi hoàn thành.

## 1. Mục Tiêu

Mục tiêu của CI/CD v1 là tự động hóa luồng kiểm tra và triển khai hiện tại nhưng vẫn giữ cách vận hành EC2 đang chạy ổn định.

Luồng hiện tại:

```text
feature branch
  -> Pull Request vào main
  -> CI kiểm tra
  -> merge vào main
  -> CD SSH vào EC2
  -> git pull origin main
  -> docker compose rebuild/restart Airflow
  -> kiểm tra Airflow /health
```

## 2. Nhánh Và Quy Ước

- `main` là nhánh deploy chính.
- Không push trực tiếp lên `main`.
- Mỗi thay đổi nên đi qua branch riêng và Pull Request.
- CI chạy trên Pull Request vào `main`.
- CD chạy khi có push/merge vào `main`.

Các branch đã dùng trong quá trình setup:

```text
setup-ci-cd
setup-cd
```

## 3. CI Đã Làm Gì

File workflow:

```text
.github/workflows/ci.yml
```

CI chạy trên:

```yaml
pull_request -> main
push -> main
```

Các bước CI:

```text
checkout source code
setup Python 3.12
cài requirements.txt
cài requirements-dev.txt
ruff check src airflow
python -m compileall src airflow
docker build Dockerfile chính
docker build airflow/Dockerfile
khởi tạo metadata DB tạm cho Airflow
airflow dags list
```

## 4. Vì Sao Dùng Ubuntu 24.04 Trong CI/CD

EC2 đang chạy:

```text
Ubuntu 24.04.4 LTS
Codename: noble
```

Vì vậy workflow dùng:

```yaml
runs-on: ubuntu-24.04
```

Không dùng `ubuntu-latest` để tránh GitHub tự đổi version runner trong tương lai.

## 5. Lỗi CI Đã Gặp Và Cách Sửa

### 5.1 Airflow Báo Chưa Khởi Tạo Database

Lỗi:

```text
ERROR: You need to initialize the database. Please run `airflow db init`.
```

Nguyên nhân:

```text
airflow dags list
```

được chạy trong container Airflow mới tinh, chưa có metadata database.

Cách sửa:

```bash
airflow db migrate && airflow dags list
```

Trong CI, bước validate DAG cần chạy migrate trước khi list DAG.

### 5.2 Docker Desktop Local Bị Kẹt Khi Build

Lỗi local:

```text
ERROR: got 3 SIGTERM/SIGINTs, forcing shutdown
```

Nguyên nhân:

- Docker Desktop đang tắt Docker Engine.
- Build Airflow image nặng và bị ngắt giữa chừng.

Cách xử lý:

- Không kết luận Dockerfile lỗi khi Docker Desktop bị shutdown.
- Vì hệ thống đã chạy ổn trên EC2, cho phép bỏ qua build local và để GitHub Actions build trên runner.

## 6. CD Đã Làm Gì

File workflow:

```text
.github/workflows/deploy.yml
```

CD chạy khi:

```yaml
push -> main
```

Các bước CD:

```text
tạo SSH key tạm từ GitHub Secrets
thêm EC2 host vào known_hosts
SSH vào EC2 bằng bash
cd /opt/scientific-journal-pipeline
git pull origin main
docker compose up -d --build airflow-postgres airflow-init airflow-webserver airflow-scheduler
docker compose ps airflow-postgres airflow-webserver airflow-scheduler
retry health check Airflow /health
```

CD v1 hiện tại build image trực tiếp trên EC2. Đây là hướng đơn giản, phù hợp với trạng thái deploy hiện tại.

## 7. GitHub Secrets Cần Có

Vào:

```text
GitHub Repository -> Settings -> Secrets and variables -> Actions
```

Tạo các secret:

```text
EC2_HOST
EC2_USER
EC2_PORT
EC2_SSH_KEY
```

Giá trị:

```text
EC2_HOST = public IP của EC2, ví dụ 54.255.167.114
EC2_USER = ubuntu
EC2_PORT = 22
EC2_SSH_KEY = toàn bộ nội dung private key .pem
```

Lưu ý:

- Ô value chỉ nhập giá trị, không nhập `EC2_HOST = ...`.
- `EC2_SSH_KEY` là nội dung file `.pem`, không phải đường dẫn file.
- Không paste private key vào chat hoặc commit vào Git.

## 8. Lỗi CD Đã Gặp Và Cách Sửa

### 8.1 Hostname Contains Invalid Characters

Lỗi:

```text
hostname contains invalid characters
```

Nguyên nhân:

Secret `EC2_HOST` bị nhập sai, ví dụ:

```text
EC2_HOST = 54.255.167.114
```

thay vì:

```text
54.255.167.114
```

Cách sửa:

Sửa secret để value chỉ chứa IP.

### 8.2 Container Name Conflict Với SQL Server

Lỗi:

```text
Conflict. The container name "/scientific-journal-sqlserver" is already in use
```

Nguyên nhân:

Lệnh ban đầu:

```bash
docker compose --profile airflow up -d --build
```

vô tình kéo cả service `sqlserver` vì service này không có profile. EC2 đã có container SQL Server đang chạy, nên Docker báo conflict.

Cách sửa:

Chỉ deploy các service Airflow:

```bash
docker compose up -d --build airflow-postgres airflow-init airflow-webserver airflow-scheduler
```

Không xóa SQL Server container vì đây là service đang giữ dữ liệu production.

### 8.3 Health Check Chạy Quá Sớm

Lỗi:

```text
curl: (56) Recv failure: Connection reset by peer
curl: (52) Empty reply from server
```

Nguyên nhân:

Airflow webserver container đã start nhưng process webserver bên trong chưa ready.

Cách sửa:

Thêm retry loop 30 lần, mỗi lần cách nhau 5 giây.

### 8.4 Curl In JSON Nhưng Workflow Vẫn Fail

Hiện tượng:

```text
{"metadatabase": {"status": "healthy"}, "scheduler": {"status": "healthy"}}
Error: Process completed with exit code 1
```

Nguyên nhân:

Health check ban đầu dựa vào exit code của `curl`, trong thời điểm Airflow vừa khởi động có thể có body response nhưng connection vẫn chưa ổn định.

Cách sửa:

Chuyển sang đọc HTTP status code:

```bash
http_code=$(curl -sS -o /tmp/airflow-health.json -w "%{http_code}" http://localhost:8080/health)
```

Chỉ pass khi:

```text
http_code=200
```

### 8.5 Script SSH In Healthy Nhưng Step Vẫn Exit 1

Hiện tượng:

```text
Airflow webserver is healthy.
Error: Process completed with exit code 1.
```

Nguyên nhân:

Script dùng `exit 0` ngay trong loop heredoc, khiến việc trả exit code qua SSH không rõ ràng trong bối cảnh script phức tạp.

Cách sửa:

Ép remote chạy bằng Bash:

```bash
ssh ... 'bash -s' << 'EOF'
```

Dùng biến:

```bash
healthy=0
```

Khi health check thành công:

```bash
healthy=1
break
```

Sau loop mới quyết định fail/pass rõ ràng.

### 8.6 Sai Indentation YAML

Lỗi:

```yaml
            - name: Deploy over SSH
```

Nguyên nhân:

Step `Deploy over SSH` bị thụt vào trong block `run` của step `Configure SSH`.

Cách sửa:

Đưa step về cùng cấp:

```yaml
      - name: Configure SSH
        run: |
          ...

      - name: Deploy over SSH
        run: |
          ...
```

## 9. Cách Kiểm Tra Sau Deploy

SSH vào EC2:

```bash
ssh scientific-journal-ec2
```

Hoặc:

```bash
ssh -i "D:\DE\SWP\scientific-journal-key.pem" ubuntu@54.255.167.114
```

Kiểm tra container:

```bash
cd /opt/scientific-journal-pipeline
docker compose ps airflow-postgres airflow-webserver airflow-scheduler
```

Kết quả mong muốn:

```text
airflow-postgres    Up ... (healthy)
airflow-webserver   Up ...
airflow-scheduler   Up ...
```

Kiểm tra Airflow health:

```bash
curl -i http://localhost:8080/health
```

Kết quả mong muốn:

```text
HTTP/1.1 200 OK
metadatabase: healthy
scheduler: healthy
```

`dag_processor` và `triggerer` có thể là `null` trong setup hiện tại. Đây không phải lỗi vì project chưa chạy triggerer riêng.

## 10. Trạng Thái Hoàn Thành

CI/CD v1 đã hoàn thành:

```text
CI: pass
CD: pass
EC2 Airflow: running
Airflow /health: HTTP 200
```

## 11. Giới Hạn Của CD v1

CD v1 vẫn build image trực tiếp trên EC2:

```text
GitHub Actions -> SSH EC2 -> git pull -> docker compose build/up
```

Ưu điểm:

- Dễ hiểu.
- Ít thay đổi.
- Phù hợp hệ thống đang chạy.

Nhược điểm:

- EC2 phải tự build image.
- Deploy lâu hơn.
- Rollback theo image tag chưa tốt.

Nâng cấp sau này:

```text
GitHub Actions build image
-> push GitHub Container Registry
-> EC2 pull image
-> docker compose up -d
```

Khi đó cần thêm `docker-compose.prod.yml` và tag image theo commit SHA.
