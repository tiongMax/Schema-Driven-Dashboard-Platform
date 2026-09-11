# Schema Studio frontend

A small React + TypeScript + Vite interface for the schema-driven dashboard API.

## Run locally

Start the FastAPI service first:

```powershell
cd backend
uv run uvicorn main:app --reload
```

Then start the frontend in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite development server proxies `/api` requests
to `http://localhost:8000`, so no backend CORS change is required.

For a production build, set `VITE_API_URL` to the deployed backend origin and run
`npm run build`.
