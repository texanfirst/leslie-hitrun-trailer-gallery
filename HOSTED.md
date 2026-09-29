# Hosted gallery

Public HTTPS URL (Vercel production): **https://leslie-hitrun-gallery.vercel.app/**

- Project: `leslie-hitrun-gallery` on Vercel Hobby, Rick's `ricks-projects-9f4757da` team scope.
- Static deploy from this directory; no build step. The site was verified with 75 companies / 234 images.
- Redeploy after changes: `git add -A && git commit -m "Update gallery" && git push origin main` (the linked Vercel project redeploys from `main`). Or use `npx vercel@latest deploy --prod` after logging into the Vercel CLI.
- The URL is public and unlisted (no login/password); anyone who has the link can open it, and the URL is guessable from the project name. The GitHub source repository is public.
- Search, Eliminate, and Maybe run in the browser. Eliminate/Maybe state is stored in `localStorage`, so it is per-device/browser and does not sync between Leslie's and Rick's phones/computers.
- The lineup-only disclaimer remains visible in the page header.
