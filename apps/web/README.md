# ResearchMind Web

Next.js 15 frontend for the ResearchMind AI Research Intelligence Platform.

---

## Overview

The web app provides the user-facing interface for ResearchMind:

- **Sign in** via AWS Cognito Hosted UI (Authorization Code flow)
- **Upload documents** — PDF, DOCX, TXT, Markdown
- **Research chat** — ask questions, receive AI-generated answers with cited sources
- **Dashboard** — overview of your knowledge base and research sessions

The frontend talks exclusively to the FastAPI backend at `apps/api`. It never handles passwords or talks to AWS directly — Cognito auth is brokered through the backend.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS v3 |
| Fonts | Fraunces · Inter · Geist Mono (Google Fonts) |
| Auth | AWS Cognito Hosted UI |
| State | React Context (auth) + local component state |

---

## Prerequisites

- Node.js 22 LTS
- npm (bundled with Node)
- ResearchMind backend running at `http://localhost:8000`

---

## Setup

### 1. Install dependencies

```bash
cd apps/web
npm install
```

### 2. Configure environment

```bash
cp .env.local.example .env.local
```

The example file is pre-filled with the development Cognito app client values. Only edit if you are using a different Cognito user pool or a different backend URL.

```env
NEXT_PUBLIC_COGNITO_DOMAIN=https://us-east-19chs0pt6p.auth.us-east-1.amazoncognito.com
NEXT_PUBLIC_COGNITO_CLIENT_ID=1r4at7v1s9nr9jqots6gl15ht
NEXT_PUBLIC_REDIRECT_URI=http://localhost:3000/auth/callback
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BASE_URL=http://localhost:3000
```

### 3. Start the dev server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Available Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start dev server with Turbopack hot reload |
| `npm run build` | Production build |
| `npm run start` | Serve a production build locally |
| `npm run lint` | ESLint |
| `npm run type-check` | TypeScript check without emitting files |

---

## Project Structure

```
src/
├── app/
│   ├── layout.tsx              # Root layout — fonts, metadata, body
│   ├── globals.css             # Tailwind base + CSS custom properties
│   ├── page.tsx                # Landing / sign-in page
│   ├── auth/
│   │   └── callback/
│   │       └── page.tsx        # Cognito callback — exchanges code for tokens
│   └── (app)/                  # Auth-gated route group
│       ├── layout.tsx          # Auth guard + sidebar shell
│       ├── dashboard/
│       │   └── page.tsx        # Overview and quick actions
│       ├── documents/
│       │   └── page.tsx        # Upload zone and document list
│       └── research/
│           └── page.tsx        # Research chat interface
├── components/
│   ├── auth/
│   │   └── login-button.tsx    # Sign-in button (redirects to Cognito)
│   └── layout/
│       └── sidebar.tsx         # App sidebar with nav and user info
├── hooks/
│   └── use-auth.tsx            # Auth context — user state, logout
└── lib/
    ├── auth.ts                 # Cognito URL builders, token storage
    └── api.ts                  # Typed API client for the backend
```

---

## Authentication Flow

```
Browser
  │
  │  1. Click "Sign in" → buildLoginUrl() → redirect to Cognito Hosted UI
  ▼
AWS Cognito
  │
  │  2. User authenticates → Cognito issues authorization code
  │     Redirects to: http://localhost:3000/auth/callback?code=XXX
  ▼
/auth/callback
  │
  │  3. POST /api/v1/auth/callback  { code, redirect_uri }
  ▼
FastAPI backend  →  Cognito token endpoint
  │
  │  4. Returns { id_token, access_token, refresh_token, expires_in }
  ▼
Frontend
  │
  │  5. Stores id_token in sessionStorage
  │     All API requests: Authorization: Bearer <id_token>
  ▼
Protected routes (dashboard, documents, research)
```

Token storage uses `sessionStorage` during development (clears when the tab closes). For production, replace with `httpOnly` cookies via Next.js server actions.

---

## Environment Variables

All variables are prefixed with `NEXT_PUBLIC_` and are embedded at build time. They are visible in the browser bundle — do not store secrets here.

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_COGNITO_DOMAIN` | Cognito Hosted UI base URL |
| `NEXT_PUBLIC_COGNITO_CLIENT_ID` | Cognito app client ID |
| `NEXT_PUBLIC_REDIRECT_URI` | OAuth callback URL registered in Cognito |
| `NEXT_PUBLIC_API_URL` | ResearchMind FastAPI backend base URL |
| `NEXT_PUBLIC_BASE_URL` | Frontend base URL, used for Cognito logout redirect |

---

## Connecting to the Backend

The backend must be running before sign-in or document upload will work.

```bash
# From the repo root
./scripts/dev.sh
```

This starts FastAPI at `http://localhost:8000`. Swagger UI is available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Adding New Pages

All pages inside `src/app/(app)/` are automatically auth-gated by the route group layout. Create a new folder with a `page.tsx` and it will appear behind the sign-in wall with the sidebar already rendered.

```
src/app/(app)/
└── your-feature/
    └── page.tsx
```

Add a nav entry in [src/components/layout/sidebar.tsx](src/components/layout/sidebar.tsx) to make it reachable from the sidebar.
