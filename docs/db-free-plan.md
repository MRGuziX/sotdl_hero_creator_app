# Database-free character creation

User decision (2026-10-06): replace production PostgreSQL/local SQLite with the flow
**create hero → preview filled PDF → download PDF**. Keep fixes in focused commits.

Status: implemented, committed and locally verified. Completion evidence is saved in
[repair-progress.md](repair-progress.md). Deployment remains a separate, unverified step.

1. Add authenticated browser-carried state and detached, atomic domain transitions.
   Preserve deterministic undo, validation, progression and supplement filtering.
2. Connect stateless HTTP/browser requests, keep only a per-tab browser draft, and
   return PDF bytes directly. Preview/download the same browser Blob; remove database
   adapters, server-side saved-character listing and database-specific tests/tooling.
3. Verify manual/random workflows, reload, undo, request failures, parallel tabs,
   PDF bytes/rendering and Blob cleanup. Update deployment instructions and CI.

Additional verification-driven repairs: preserve the previous draft on payload-size
errors; losslessly compact multi-page spell exports; run full Chromium for real PDF
viewer checks; exclude development files and old local saves from Vercel uploads.

Only a stable `SECRET_KEY` is required in production. No database URL, schema setup,
database cleanup job or persistent server filesystem is needed. Tokens are signed,
not encrypted, and sent in request bodies rather than URLs. Possession of a token
grants access to that character. Versions describe a local branch, not a global lock.
Old database saves are not migrated; nothing is deleted from any existing database.
Preview deployments must still be verified on Vercel before claiming deployment success.
