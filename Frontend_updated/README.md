# SamadhanSetu — React Frontend

Civic problem resolution portal for Jharkhand (Citizen / Government / Industry / University).
Built with React 19 + Vite + React Router. Hindi/English bilingual UI.

## Run locally

```bash
npm install
npm run dev
```

Then open the printed local URL (usually http://localhost:5173).

## Build for production

```bash
npm run build
npm run preview
```

## Project structure

```
src/
  components/
    layout/    -> TopBar, Sidebar, DashboardLayout, ProtectedRoute, navConfig
    shared/    -> FileUploadField, VoiceRecorder, McqOption, TrackingStepper
  context/     -> AuthContext, LanguageContext, ToastContext, ProblemsContext
  data/        -> mockData.js (seed problems, past projects, institutions)
  i18n/        -> translations.js (Hindi + English strings)
  pages/
    HomePage.jsx           -> hero + unified login/signup
    citizen/                -> Problems list, Add Problem (uploads+voice), Feedback
    government/             -> Verification & Allocation, Analytics
    industry/                -> Active Collaborations (+ shared PastProjectsPage)
    university/              -> Faculty Challenges, Student Dashboard (+ shared PastProjectsPage)
  services/
    uploadService.js  -> mock upload stub, swap in a real API call here later
  styles/
    theme.css   -> design tokens (colors, buttons, cards, badges, forms)
    layout.css  -> page layout, hero, sidebar, uploads, responsive rules
```

## Login / roles

There's no real backend — any email/password works. Pick a role on the
signup tab (Citizen, Government, Industry, University) to see that
role's dashboard. Session resets on page refresh (by design, per the
mock-auth setup chosen for this build).

## Wiring a real backend later

- **File/video/photo/document uploads**: see the comment block at the
  top of `src/services/uploadService.js` — swap the body of `uploadFile`
  for a real `fetch`/`FormData` POST and keep the same return shape.
- **Voice notes**: `VoiceRecorder.jsx` already records real audio via the
  browser's MediaRecorder API and hands the blob to `uploadVoiceNote`,
  which reuses `uploadFile` under the hood.
- **Auth**: replace `AuthContext.login` with a real API call; the rest
  of the app only depends on the `user` object shape it already returns.
- **Problems data**: `ProblemsContext` currently holds everything in
  React state seeded from `mockData.js` — swap its actions for API calls
  when a backend exists.
