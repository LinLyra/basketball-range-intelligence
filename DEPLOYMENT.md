# Deployment

## Vercel — recommended

The repository is configured for zero-code Vercel deployment through `vercel.json`.

1. Open the Vercel dashboard and select **Add New → Project**.
2. Import `LinLyra/basketball-range-intelligence`.
3. Keep the repository root as the Root Directory. Do not select `web/`.
4. Vercel will read the install command, build command, output directory, and cache
   headers from `vercel.json`.
5. Select **Deploy**.

| Setting | Value |
| --- | --- |
| Framework | Vite |
| Install command | `npm --prefix web ci` |
| Build command | `npm --prefix web run build` |
| Output directory | `web/dist` |

No environment variables or server runtime are required. Subsequent pushes to
`main` can deploy automatically after the Vercel GitHub integration is enabled.

## Local production check

```bash
npm --prefix web ci
npm --prefix web run build
npm --prefix web run preview
```

## Data and attribution

The deployment contains derived NBA Stats shot-location records. Review source terms
before commercial redistribution. Code, inclusion rules, schemas, and reproducible
download instructions should remain available even when third-party raw data cannot
be redistributed.
