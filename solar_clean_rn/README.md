# Solar Clean RN

React Native / Expo rewrite of the existing Flutter mobile app in `../solar_clean_app`.

## Scope

- Login / logout with saved session
- Register screen
- Dashboard with `Monitor` and `Control` tabs
- Realtime status with WebSocket plus polling fallback
- Current frame for mobile via `/api/current_frame`
- Snapshot preview, KPI cards, AI probability bars
- System control: start, stop, reconnect PLC, manual clean
- Settings control: PLC IP, camera id, snapshot interval, dirt threshold

## Stack

- Expo + React Native + TypeScript
- AsyncStorage for saved session cookie
- Same FastAPI backend contract used by the Flutter app

## Project structure

```text
solar_clean_rn/
|- App.tsx
|- assets/
|- src/
|  |- components/
|  |- context/
|  |- screens/
|  |- services/
|  `- types/
```

## Run

```bash
cd solar_clean_rn
npm install
npm run start
```

Then run on Android / iOS through Expo.

## Notes

- This rewrite intentionally uses `/api/current_frame` for the live camera preview because it is better suited for mobile than the MJPEG `/video_feed` endpoint.
- WebSocket is configured to send auth headers. If the backend only accepts cookie auth on a given platform build, polling still keeps the dashboard working.
- The app is pinned to `http://ctut.clean.id.vn` and no longer exposes server configuration in the login UI.
