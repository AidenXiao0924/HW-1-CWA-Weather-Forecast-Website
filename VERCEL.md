# Vercel deployment

Import AidenXiao0924/taiwan-weather, select FastAPI and keep the repository root.
Set DATA_MODE=live and CWA_API_KEY in Vercel environment variables. Never upload .env.
index.py exposes the same application as the local backend:app entrypoint.

SQLite on Vercel is an ephemeral per-instance cache in the temporary directory.
Requests refresh expired cache; new instances fetch data again. No persistent history
or always-running background task is provided. Local SQLite behavior is unchanged.

Without WINDY_API_KEY the map uses OpenStreetMap; CWA stations and forecasts still work.
A Windy Testing key is not licensed for production. Confirm the appropriate Windy
plan and domain restrictions before enabling Windy on the production site.

Verify /api/health, the station map and the seven-day forecast after deployment.
