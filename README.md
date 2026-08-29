# Tactical Fitness Tracker V2

Multi-user Streamlit fitness tracker with Supabase Auth/Postgres and per-user Row Level Security.

## Files
- `app.py` — Streamlit app
- `supabase_schema.sql` — run once in Supabase SQL Editor
- `requirements.txt` — dependencies

## Streamlit Secrets
Add:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_PUBLISHABLE_OR_ANON_KEY"
```

Do not commit secrets.

## Supabase Auth
Enable Email provider. For username-only login used by this app, turn **Confirm email OFF**. Keep public sign-up ON if you want friends to create their own accounts.

## Deploy
Push the whole repository. In Streamlit Community Cloud choose the repository and `app.py` as the entrypoint, then add the two secrets above.
