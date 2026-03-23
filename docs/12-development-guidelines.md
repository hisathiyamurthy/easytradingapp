# Developer Onboarding Guide

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Running the Application

```bash
# Clone and navigate to project
cd /home/sathiya/easytradingapp

# Start all services
docker compose up -d

# Access the application
# Frontend: http://localhost:5300
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Default Credentials
- **Admin:** hisathiyamurthy@gmail.com / Zero@123
- **Database:** postgres / postgres (internal)
- **Redis:** (internal)

---

## Project Structure

### Frontend (`frontend/`)
- React + TypeScript + Vite
- Tailwind CSS for styling
- Pages in `src/pages/`

### Backend (`backend/`)
- FastAPI (Python)
- SQLAlchemy ORM
- PostgreSQL database

### Key Files
- `docker-compose.yml` - Service orchestration
- `frontend/src/App.tsx` - Main app with routing
- `backend/main.py` - FastAPI application
- `agents.md` - AI agent guidelines

---

## Common Tasks

### Adding a New Feature

1. **Backend:** Add endpoint in `backend/api/v1/endpoints/`
2. **Schema:** Add Pydantic model in `backend/schemas/`
3. **Database:** Add model in `backend/models/`
4. **Frontend:** Add page in `frontend/src/pages/`
5. **API:** Add service in `frontend/src/services/`

### Running Tests

```bash
# Backend tests (if available)
cd backend && pytest

# Frontend tests (if available)
cd frontend && npm test

# E2E tests
cd tests/e2e && npx playwright test
```

### Building for Production

```bash
docker compose build
docker compose up -d
```

---

## Important Notes

### Authentication
- JWT tokens stored in localStorage as `token` (not `access_token`)
- Role stored in user object under `role` key
- Check user role: `JSON.parse(localStorage.getItem('user')).role`

### API Endpoints
- All protected endpoints require `Authorization: Bearer <token>`
- Admin endpoints require `role: "admin"`

### Environment Variables
- Frontend: `VITE_API_URL` (set in docker-compose.yml)
- Backend: See `.env` file

---

## Key Locations

| Component | Location |
|-----------|----------|
| Auth Logic | `backend/core/security.py` |
| NLP Parser | `backend/strategy_engine/nl_parser.py` |
| API Routes | `backend/api/v1/endpoints/` |
| Frontend Pages | `frontend/src/pages/` |
| UI Components | `frontend/src/components/ui/` |

---

## Need Help?

1. Check `docs/` folder for detailed documentation
2. Review `agents.md` for AI agent guidelines
3. Check `BUG_TRACKER.md` for known issues

---

*Last Updated: March 2026*
