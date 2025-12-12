# Organization Management Service

Simple FastAPI service to create and manage organizations in a multi-tenant style using MongoDB.

Quick start (PowerShell):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# ensure MongoDB is running locally or set MONGO_URI
setx MONGO_URI "mongodb://localhost:27017"
	uvicorn app.main:app --port 8000
```

Docker (recommended for quick local run):

```powershell
docker compose up --build -d
```

This will start a MongoDB container and the FastAPI app (exposed on port 8000). The app is configured to connect to `mongodb://mongo:27017` inside the compose network.

Endpoints
- POST `/org/create` : create org with admin
- GET `/org/get?organization_name=...` : get org metadata
- PUT `/org/update` : update org (requires `Authorization: Bearer <token>`)
- DELETE `/org/delete?organization_name=...` : delete org (requires admin token)
- POST `/admin/login` : login admin, receive JWT

Notes
- Master DB defaults to `master_db` (change via `MASTER_DB_NAME` env var)
- JWT secret: set `JWT_SECRET` env var in production