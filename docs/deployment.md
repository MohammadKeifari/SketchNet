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
4. User uploads (`media/`) are served by Django with the same visibility rules as the app (covers/avatars that a viewer is allowed to see; private dataset files stay 404). nginx can still front `/media/` if you prefer.
5. Configure SMTP for django-allauth email verification.
6. Enable Google OAuth in Django admin (Social applications) if using social login.
7. Put the app behind HTTPS; production settings enable secure cookies and HSTS when `DEBUG=False`.
8. Add rate limiting on heavy endpoints (export zip, anonymous export) at the reverse proxy or application layer.

## SketchMod canvas.js

The left tool palette and default Input/Output nodes are created only after
`/static/sketchmod/js/canvas.js` parses. The right sidebar is HTML, so it still
renders when that script is truncated or cached stale.

After every deploy:

1. `git pull`
2. `python manage.py collectstatic --noinput`
3. Delete stale compressed copies if they exist:
   `rm -f staticfiles/sketchmod/js/canvas.js.gz staticfiles/sketchmod/js/canvas.js.br`
   then run `collectstatic` again.
4. Restart gunicorn.
5. Purge the Cloudflare cache for `/static/sketchmod/js/canvas.js` and `/sketchmod/`.
6. In Cloudflare: disable **Auto Minify (JavaScript)** and **Rocket Loader**.

Confirm origin is complete (must include `handleSave` at the end):

```bash
curl -sS https://sketchnet.site/static/sketchmod/js/canvas.js | tail -c 120
```

## Process layout

```
Cloudflare Tunnel (or nginx)
  └── gunicorn → config.wsgi
        ├── WhiteNoise staticfiles/
        └── Django /media/  (ACL-checked uploads)
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
