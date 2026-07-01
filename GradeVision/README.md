# GradeVision — Production-Grade Return Merchandise Inspection

AI-powered intelligent inspection system for e-commerce returns, industrial materials, and damaged goods assessment.

## Features

✅ **Inspector Authentication** — JWT-based login for warehouse staff  
✅ **AI-Powered Detection** — YOLOv5 computer vision for damage detection  
✅ **Confidence Scoring** — Automatic verdict based on damage severity (Good / Minor / Moderate / Severe)  
✅ **Product Categorization** — Support for Clothing, Boxes, Electronics, Auto Components  
✅ **Audit Trail** — Full inspection logging with timestamps and inspector tracking  
✅ **Dashboard Analytics** — Statistics and trend analysis for QA teams  
✅ **RESTful API** — FastAPI with async support  

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Auth**: JWT (HS256), bcrypt password hashing
- **ML**: YOLOv5, PyTorch, OpenCV
- **Frontend**: Jinja2 templates, vanilla JS, CSS Grid
- **Docker**: Production-ready containerization

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env with your secret key (change SECRET_KEY for production)
```

### 3. Clone YOLOv5

```bash
git clone https://github.com/ultralytics/yolov5.git
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload
```

Visit: `http://localhost:8000`

**Default credentials:**
- Email: `admin@gradevisio n.com`
- Password: `admin@123`

## API Endpoints

### Authentication
- `POST /auth/login` — Get JWT token
- `POST /auth/register` — Register new inspector (admin only)
- `GET /auth/me` — Get current user info

### Inspection
- `POST /inspect` — Run detection on uploaded image → returns verdict + confidence

### Logs
- `GET /logs` — Inspector's inspection history
- `GET /logs/{id}` — Detailed inspection record
- `GET /logs/dashboard/stats` — Aggregated statistics

## Inspection Verdict Mapping

| Damage Confidence | Verdict | Recommendation |
|---|---|---|
| 0–15% | Good | Resellable as-is |
| 15–45% | Minor Damage | Refurbish / discount |
| 45–75% | Moderate Damage | Sell as parts |
| 75–100% | Severe Damage | Write off |

## Database Models

### Users
```sql
id | email | full_name | hashed_password | role (inspector/admin) | is_active | created_at
```

### Inspections
```sql
id | inspector_id | product_category | verdict | confidence | severity | 
recommendation | damage_regions (JSON) | result_image_path | raw_image_path | created_at
```

## Deployment

### Docker
```bash
docker-compose up --build
```

### Production Checklist
- [ ] Set strong `SECRET_KEY` in `.env`
- [ ] Use PostgreSQL instead of SQLite for production
- [ ] Enable HTTPS/TLS
- [ ] Set `debug=False`
- [ ] Add rate limiting and authentication scopes
- [ ] Set up logging and monitoring

## Directory Structure

```
GradeVision/
├── app/
│   ├── core/         # Config, security, database
│   ├── models/       # SQLAlchemy ORM models
│   ├── schemas/      # Pydantic request/response models
│   ├── routers/      # API endpoint routers
│   ├── services/     # Detection & grading logic
│   └── main.py       # FastAPI app entry point
├── gradeVision/      # ML training package (optional)
├── frontend/         # HTML templates & static assets
├── data/             # Runtime images directory
├── artifacts/        # Training outputs
└── yolov5/           # YOLOv5 model (cloned separately)
```

## Development

### Add a new inspection category

1. Update `product_category` options in `inspect.html`
2. Add category-specific logic in `app/services/grader.py`
3. Update training dataset for new category

### Integrate with YOLOv5

1. Train custom model: `python yolov5/train.py --data custom_data.yaml ...`
2. Copy best.pt to `yolov5/best.pt`
3. Update `YOLOV5_MODEL_PATH` in `.env`

## Support & Documentation

For issues, feature requests, or contributions, please refer to the project documentation.

---

**Built for e-commerce and warehouse operations. Production-ready. Scalable.**
