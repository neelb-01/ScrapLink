# ScrapLink mobile

The Android-first app for sellers and buyers, built with React Native and Expo.

**First slice:** sign in and see your lots. The last list fetched is kept on the phone, so it still opens with no signal and says when it was saved. Listing a lot, bidding and working offline with queued changes come next. Until then the web client covers every action.

```sh
npm install
npm run typecheck
npm start           # scan the QR code with Expo Go on an Android phone
npm run web         # or try it in a browser at http://localhost:8081
```

The app calls the API at `EXPO_PUBLIC_API_URL` (default `http://localhost:8000`). On a phone, localhost means the phone itself, so set it to your computer's LAN address, for example `EXPO_PUBLIC_API_URL=http://192.168.1.20:8000 npm start`, and start the backend with `--host 0.0.0.0`. In a browser, the API must allow `http://localhost:8081` in `CORS_ORIGINS`.

Add packages with `npx expo install <package>`, not `npm install`: it picks the version that matches the Expo SDK.
