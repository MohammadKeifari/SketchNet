# Deployment

## Environment variables

Copy `.env.example` to `.env` and set:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret key (required in production) |
| `DEBUG` | Set to `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `EMAIL_BACKEND` | SMTP backend for account verification |
| `SECURE_SSL_REDIRECT` | `True` when behind HTTPS (default when `DEBUG=False`) |
| `SECURE_HSTS_SECONDS` | HSTS max-age (default 31536000) |

## Checklist

1. Set `DEBUG=False` and a strong `SECRET_KEY`.
2. Use PostgreSQL instead of SQLite for production workloads.
3. Run `python manage.py collectstatic` and serve static files via nginx or a CDN.
4. Serve `media/` from object storage or a protected volume — do not expose private datasets publicly.
5. Configure SMTP for django-allauth email verification.
6. Enable Google OAuth in Django admin (Social applications) if using social login.
7. Put the app behind HTTPS; production settings enable secure cookies and HSTS when `DEBUG=False`.

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
