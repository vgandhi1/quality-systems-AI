# Deployment Guide — GradeVision

## GitHub Setup & Deployment

### 1. Create GitHub Repository

Visit: https://github.com/new

**Repository Details:**
- **Owner**: vgandhi1
- **Repository name**: `GradeVision`
- **Description**: `Production-grade AI-powered return merchandise inspection system for e-commerce and industrial damage assessment`
- **Visibility**: Public ✓
- **Initialize**: None (we already have a local repo)

**Click**: "Create repository"

---

### 2. Push to GitHub

After creating the repo on GitHub, run these commands:

```bash
cd C:\Users\Vinay\Documents\Scap-management\GradeVision

# Add GitHub remote
git remote add origin https://github.com/vgandhi1/GradeVision.git

# Rename branch to main (optional but recommended)
git branch -M main

# Push all commits
git push -u origin main
```

---

### 3. Add Repository Metadata

Go to: https://github.com/vgandhi1/GradeVision/settings

#### **Repository Settings**

- **Description**: 
  ```
  AI-powered return merchandise inspection for e-commerce and industrial damage assessment
  ```

- **Homepage URL**: 
  ```
  (Leave empty or add your docs URL)
  ```

#### **Topics** (click "Add topics")

Add these tags for discoverability:
- `ai`
- `computer-vision`
- `damage-detection`
- `e-commerce`
- `fastapi`
- `inspection`
- `machine-learning`
- `return-merchandise`
- `yolov5`

#### **Visibility**
- ✓ Public

---

### 4. Create GitHub Release (Optional)

After pushing, create a release:

```bash
git tag -a v0.1.0 -m "Initial release: Production-grade inspection system"
git push origin v0.1.0
```

Then visit GitHub and create a release from the tag with notes.

---

## Local Development

### Setup

```bash
# Clone the repo
git clone https://github.com/vgandhi1/GradeVision.git
cd GradeVision

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Clone YOLOv5
git clone https://github.com/ultralytics/yolov5.git

# Setup environment
cp .env.example .env
# Edit .env with your SECRET_KEY
```

### Run Locally

```bash
# Start server
uvicorn app.main:app --reload

# Visit
http://localhost:8000
```

**Default login:**
- Email: `admin@gradevisio n.com`
- Password: `admin@123`

---

## Docker Deployment

### Build & Run

```bash
# Build image
docker build -t gradevisio n:latest .

# Run container
docker run -p 8000:8000 \
  -e SECRET_KEY="your-secret-key-here" \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/artifacts:/app/artifacts \
  gradevisio n:latest

# Or use docker-compose
docker-compose up --build
```

### Push Image to Docker Hub (Optional)

```bash
# Login
docker login

# Tag image
docker tag gradevisio n:latest vgandhi1/gradevisio n:latest

# Push
docker push vgandhi1/gradevisio n:latest
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Change `SECRET_KEY` in `.env` (min 32 characters, random)
- [ ] Switch `DATABASE_URL` to PostgreSQL (from SQLite)
- [ ] Set `DEBUG=False` in config
- [ ] Enable HTTPS/TLS on your server
- [ ] Configure environment variables on hosting platform
- [ ] Set up logging and monitoring
- [ ] Add rate limiting middleware
- [ ] Create database backups strategy
- [ ] Set up automated certificate renewal (if self-hosted)

### Example: Deploy to AWS EC2

```bash
# 1. SSH into instance
ssh -i key.pem ubuntu@your-instance-ip

# 2. Clone repo
git clone https://github.com/vgandhi1/GradeVision.git
cd GradeVision

# 3. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
git clone https://github.com/ultralytics/yolov5.git

# 4. Setup environment
cp .env.example .env
# Edit .env with production values

# 5. Run with Gunicorn (production ASGI server)
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker

# 6. (Optional) Use systemd/supervisor for process management
```

### Example: Deploy to Heroku

```bash
# 1. Login to Heroku
heroku login

# 2. Create app
heroku create vgandhi1-gradevisio n

# 3. Add buildpacks
heroku buildpacks:add heroku/python

# 4. Set environment variables
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set DATABASE_URL="postgresql://..."

# 5. Deploy
git push heroku main

# 6. Check logs
heroku logs --tail
```

---

## Database Migrations (Production)

For PostgreSQL, use Alembic for migrations:

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Run migrations
alembic upgrade head
```

---

## Monitoring & Logging

### Recommended Tools

- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Error Tracking**: Sentry
- **Performance**: New Relic or DataDog

### Basic Logging Setup (Python)

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

---

## Continuous Integration / Continuous Deployment

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - run: pip install -r requirements.txt
      - run: pytest  # Add tests

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to server
        run: |
          # Your deployment script here
```

---

## Support & Troubleshooting

### Common Issues

**Issue**: Database locked
```
Solution: Ensure SQLite isn't being accessed by multiple processes. 
Use PostgreSQL for production.
```

**Issue**: YOLOv5 model not found
```
Solution: Run `git clone https://github.com/ultralytics/yolov5.git`
Ensure path matches YOLOV5_MODEL_PATH in config.
```

**Issue**: Port 8000 already in use
```
Solution: uvicorn app.main:app --port 8001
Or kill process: lsof -i :8000 | kill -9 $PID
```

---

## Next Steps

1. ✅ Push to GitHub
2. ✅ Add topics & description
3. ⬜ Train custom YOLOv5 model
4. ⬜ Add inspector users
5. ⬜ Test with sample images
6. ⬜ Deploy to production
7. ⬜ Monitor & scale

---

For more info, see [README.md](README.md) and [CONSOLIDATION_NOTES.md](CONSOLIDATION_NOTES.md).
