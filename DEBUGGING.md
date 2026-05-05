# Nexus for Google: Debugging & Triage Guide

## Blue-Green Symlink Architecture & Emergency Rollback
Nexus uses a Zero-Downtime deployment model based on symlinks.
- **Database Location:** The true database securely resides at `/home/frank/nexus/shared/data/nexus.db`. It is symlinked into each release's `backend` folder.
- **Emergency Rollback:** If a deployment breaks the backend, you can revert the system instantly by changing the `/current` symlink to point to an older release folder.

**Rollback Command Sequence:**
1. Run `./scripts/connect.ps1` (or `.sh`) to easily SSH into your VM.
2. Once connected, run:
```bash
ls -l /home/frank/nexus/releases/
ln -sfn /home/frank/nexus/releases/[PREVIOUS_RELEASE_DIR] /home/frank/nexus/current
sudo systemctl restart nexus.service
```

## Backend Triage
To watch live logs from the FastAPI backend service:
```bash
sudo journalctl -u nexus.service -f
```

## Database Inspection
To inspect the backend SQLite database (`backend/nexus.db`):
1. Run `gcloud compute config-ssh` on your local terminal.
2. Open VS Code Remote-SSH and connect using the generated GCP hostname.
3. Install the "SQLite Viewer" extension in VS Code.
4. Open the `backend/nexus.db` file to view the database visually.

## Frontend Triage
- **Deployments:** The `/exec` link is a cached, immutable snapshot of your deployment. Active UI development must use the `/dev` (Test Deployment) URL to see real-time changes.
- **Console Errors:** Use your browser's F12 Developer Tools Console to catch Javascript `ReferenceError` crashes or other unhandled exceptions.
- **Cache-Busting:** To force Google to bypass the inner iframe cache after a `clasp push`, append `?v=2` (or any random string) to the URL (e.g., `.../dev?v=2`).

## Environment Configuration (debug.gs)
Nexus features a centralized feature-flag and logging system. To change the app's verbosity or expose hidden developer tools:
1. Open the Google Apps Script editor.
2. Locate the `frontend/debug.gs` file.
3. Modify the `NEXUS_CONFIG` object (e.g., set `LOG_LEVEL` to 'DEBUG' or toggle `showRawPayloads` to `true` in `UI_FLAGS`).
4. Save and refresh your `/dev` UI deployment. The frontend will immediately adapt to these changes without requiring a redeployment.
