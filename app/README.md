# PitchMe app

The phone app, built with Expo SDK 57, React Native 0.86 and expo-router.
TypeScript is strict.

```
app/
  src/
    app/              routes: the file name is the route
      (tabs)/         Home, Playbook and Profile, with our own tab bar
    components/
      ui/             the UI kit: Screen, Text, Button, fields, cards, logo
      motion/         Rise (entrance), Pulse and Spinner (ambient), GrowBar (data)
    constants/        theme, fonts, score bands, motion, deal choices
    hooks/            theme, reduced motion, useRequest, back navigation
    lib/
      api/            typed API client
      storage.ts      the sign-in, in the Keychain or Keystore
  scripts/            use-lan-ip.sh, make_icons.py
```

## Setup

You need Node 20.19.4, 22.13, 24.3 or later (the range React Native 0.86 supports).

```bash
cd app
npm install
cp .env.example .env
scripts/use-lan-ip.sh     # sets EXPO_PUBLIC_API_URL to this computer's LAN IP
```

On a phone, `localhost` is the phone, so the API URL must use the computer's
LAN IP. Run `scripts/use-lan-ip.sh` again when you change networks, and
restart Metro after any change to `.env`.

## Run

The live call needs native WebRTC, so the app does not run in Expo Go. It
runs in a development build: a build of this app with the Expo dev client.

1. Make a development build once, and again after a change to native
   packages or `app.json`. With EAS (run `npx eas init` first, to link the
   project to your Expo account):

   ```bash
   npx eas build --profile development --platform android
   ```

   Or build on this computer, if it has Android Studio or Xcode:

   ```bash
   npx expo run:android
   ```

2. Start the backend (`make practice` in `backend/`).
3. Start Metro and open the app on the phone:

   ```bash
   npm start                 # or: npx expo start --port 8083
   ```

The web build (`npm run web`) shows the screens, but it has no live call.

## Screens and sign-in

| Route                             | Who sees it       | What it is                              |
| --------------------------------- | ----------------- | --------------------------------------- |
| `/`                               | signed out        | Landing                                 |
| `/login`                          | signed out        | Sign in                                 |
| `/onboard`                        | signed out        | Step 1: about you, and the account      |
| `/onboard/voice`                  | during onboarding | Step 2: voice sample                    |
| `/onboard/playbook`               | during onboarding | Step 3: playbook upload                 |
| `/home`, `/playbook`, `/profile`  | signed in         | The tabs                                |
| `/profile/edit`, `/profile/voice` | signed in         | Edit details, record a new voice sample |

`AuthProvider` (`src/hooks/use-auth.tsx`) holds the sign-in state, and the
root layout shows screens by it with `Stack.Protected`. Screens do not
navigate after sign-in or sign-out: the state changes, and the layout moves
the user to the first screen they may see.

- **Auto login:** a saved token is checked once at launch, behind the splash
  screen. Only a rejected token signs the user out. With no network, the
  token is kept and each screen offers to try again.
- **401:** when the API rejects the token later, the client clears it and
  the user lands on sign-in with the reason.
- **Onboarding:** sign-up opens steps 2 and 3. Both can be skipped, and both
  can be done later from Profile and the Playbook tab.

## API client

`src/lib/api` follows the API schemas in `backend/server/schemas`. Keep the
two in step.

- There is no mock mode. With no `EXPO_PUBLIC_API_URL`, every call fails
  with a clear message, so the app never shows data that is not real.
- Every failure is an `ApiError` with a `code` and a `message` the user can
  act on. A 422 also has `fields`: what to change in each field.
- When the API rejects the saved token, the client clears it and calls the
  `onSignedOut` listeners. A wrong password on the sign-in form does not
  sign anyone out.
- Uploads go straight to storage through a presigned URL, then the API
  confirms them.

## Design

- Plum and Sage, in light and dark. There is no red: the lowest score band is
  "Needs work", and every band pill shows its label.
- Newsreader for headings and numbers, IBM Plex Sans for text.
- Three kinds of motion: entrance, ambient (only for live things) and data.
  All of them respect the system's reduce motion setting.
- The app coaches. Copy says what to do next, never that something was bad.

The app icons come from `scripts/make_icons.py`, which draws the logo. Run it
with Python and Pillow after a change to the mark.

## Checks

```bash
npm run check    # type check, lint, format check and tests: what CI runs
npm run format   # apply the code style
```

One test reads `backend/ai/rehearsal/deal.py`, so the deal choices in the app
cannot drift from the keys the API takes.
