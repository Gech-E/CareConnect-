# CareConnect patient app

Expo + React Native client for the existing FastAPI backend.

## Getting started

1. Start the backend and infrastructure as described in the repository README.
2. Copy `.env.example` to `.env` and set `EXPO_PUBLIC_API_URL`.
   - Android emulator: `http://10.0.2.2:8005/api/v1`
   - iOS simulator: `http://localhost:8005/api/v1`
   - Physical device: use your computer's LAN IP and a trusted development network.
3. Run `npm install` and `npm start`.
4. Run `npm run typecheck`.

The app includes directory, clinician detail, available slots, sign-in/registration, and appointment booking.
Only test with synthetic users. Telehealth service-area validation, clinician credential review, consent and verification require completed backend enforcement before a public pilot.
