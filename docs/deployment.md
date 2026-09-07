# Deployment

## Environment variables

Copy `.env.example` to `.env` and set:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret key (required in production) |
| `DEBUG` | Set to `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `DATABASE_URL` | PostgreSQL connection string (recommended for production) |
| `EMAIL_BACKEND` | SMTP backend for account verification |
| `SECURE_SSL_REDIRECT` | `True` when behind HTTPS (default when `DEBUG=False`) |
| `SECURE_HSTS_SECONDS` | HSTS max-age (default 31536000) |

## Staging checklist

Use a staging environment that mirrors production before every release:

1. Deploy to a separate host (e.g. `staging.example.com`) with `DEBUG=False`.
2. Run migrations: `python manage.py migrate`.
3. Run the full test suite and smoke-test SketchMod (Check, Export, Save model).
4. Verify anonymous read-only model viewing on a public model.
5. Confirm media uploads (datasets, model covers) persist on the staging volume or bucket.
6. Test account signup, email verification, and Google OAuth if enabled.

## Production checklist

1. Set `DEBUG=False` and a strong `SECRET_KEY`.
2. Use PostgreSQL instead of SQLite for production workloads.
3. Run `python manage.py collectstatic` and serve static files via nginx or a CDN.
4. Serve `media/` from object storage or a protected volume — do not expose private datasets publicly.
5. Configure SMTP for django-allauth email verification.
6. Enable Google OAuth in Django admin (Social applications) if using social login.
7. Put the app behind HTTPS; production settings enable secure cookies and HSTS when `DEBUG=False`.
8. Add rate limiting on heavy endpoints (export zip, anonymous export) at the reverse proxy or application layer.

## Process layout

```
nginx / reverse proxy
  ├── staticfiles/  (collectstatic)
  ├── media/        (user uploads)
  └── gunicorn → config.wsgi
```

## Example gunicorn command

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

## Dataset and profile deep links

- Attach a dataset in SketchMod: `/sketchmod/?dataset=<dataset_id>` (requires login).
- Public user profile: `/accounts/u/<username>/` (when the user enables **Public profile** in Settings).

## Monitoring

- Use Django admin and in-app bug reports for user-reported issues.
- Consider Sentry or similar for unhandled exceptions in production (complements `bug_reports`).
