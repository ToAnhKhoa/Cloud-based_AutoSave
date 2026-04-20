# CloudSave Sync

CloudSave Sync is a standalone cloud synchronization engine designed to safely back up and manage local saved data (like video game save files or local configurations) directly to a remote production server. It accurately mirrors the intelligent sync behavior and disaster recovery of modern platforms like Steam Cloud. 

## Key Features
- **Smart Startup Sync**: Safely compares live timestamps between your local filesystem and the cloud. If conflicts are detected between your local PC and the Cloud backup, the app intelligently prompts you, protecting you from accidental or permanent file overwrites.
- **AI-Powered "Auto-Find"**: Don't know where a game's save directory is hidden? CloudSave utilizes a secure Gemini 2.5 Flash AI integration to automatically estimate and locate hidden local paths for thousands of unsupported or legacy games.
- **Auto-Learning Game Alias**: Features a centralized caching system to learn abbreviations globally. If one user maps "witcher 3" via the AI, subsequent users utilizing the same nickname will bypass the AI wait times, instantly locating the mapped path.
- **Snapshot Rollback (Disaster Recovery)**: Features tracked database routing for timeline-based snapshots. If your local save file corrupts, you can dynamically select a previous day's snapshot and roll back your cloud backup directly from the UI. 
- **Lightweight System Integration**: Features native settings to launch quietly in the Windows System Tray, register as a startup daemon on boot, and live-monitor directory changes with configurable debounce timings.

## How to Use
1. **Extract & Run**: Grab the latest packaged `.zip` release, extract it, and double-click `CloudSync_Client.exe`. (No python environment is required!)
2. **Register**: Provide your credentials. Your session securely authenticates with the external Azure backend.
3. **Map Software**: Inside the Dashboard, click `+ Add New App`. Type the name of the application, and use the `Auto-Find` AI tool to find the default directory, or browse to map it manually.
4. **Leave It Be**: CloudSave will immediately conduct an initial scan and upload your files! It tracks filesystem events in the background, updating the cloud server dynamically.

## Technical Architecture
- **Client Application**: Python utilizing `CustomTkinter` and `PyInstaller` for standalone Windows binary packaging. 
- **Production Backend**: Linux Azure Virtual Machine routing traffic through an NGINX reverse-proxy wrapper to a live Python `FastAPI` instance interacting with a dynamic SQLite tracking schema.
