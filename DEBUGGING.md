# Nexus for Google: Debugging & Triage Guide

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
