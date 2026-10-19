# Deployment

The website is a static Vite application. Charts and shot events are generated
ahead of time, so production hosting does not need Python or an API server.

## Build

```bash
python scripts/export_web_data.py
cd web
npm ci
npm run build
npm run preview
```

Deploy `web/dist/` to Netlify, Vercel, Cloudflare Pages, or GitHub Pages. The Vite
base path is relative, so the same build works at a custom domain or repository
subpath. Re-run the exporter whenever the source season files change.

## Data and attribution

The deployed artifact includes derived NBA Stats shot records. Confirm the source's
terms before public or commercial redistribution. Publish code, inclusion rules,
schemas, and reproducible download instructions even when raw third-party records
cannot be redistributed.
