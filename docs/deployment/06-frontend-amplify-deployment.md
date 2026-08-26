# ResearchMind --- Frontend Deployment with AWS Amplify

## Purpose

The frontend is independently deployed from the backend.

Current location:

``` text
apps/web
```

Technology:

-   Next.js 15;
-   React 19;
-   TypeScript;
-   Tailwind.

The current Next.js configuration uses:

``` text
output: "standalone"
```

Keep this initially.

## Decision

Use:

``` text
AWS Amplify Hosting
```

Do not run the frontend on ECS/Fargate.

Reason:

``` text
Frontend → Amplify
Backend  → ECS/Fargate
```

This gives independent deployment and avoids using container compute
just to serve the UI.

## Architecture

``` text
GitHub
  ↓
AWS Amplify
  ↓
Next.js frontend
  ↓ HTTPS
Application ALB
  ↓
ECS/Fargate FastAPI
```

Authentication:

``` text
Frontend
  ↓
Cognito Hosted UI
  ↓
Authentication callback
```

## Environment variables

Configure production values for:

``` text
NEXT_PUBLIC_API_URL
NEXT_PUBLIC_BASE_URL
NEXT_PUBLIC_REDIRECT_URI
```

These are public browser configuration, not secrets.

## Cognito

Update the existing Cognito configuration with the deployed frontend
URLs:

``` text
Allowed callback URLs
Allowed logout URLs
```

Do not introduce a second authentication system.

## Build strategy

Keep the existing standalone Next.js build first.

Do not switch to static export merely for hosting convenience.

The goal is to deploy the already-verified frontend implementation with
minimal application changes.

## CI/CD

``` text
Developer
   ↓
GitHub
   ↓
Amplify build
   ↓
Next.js deployment
   ↓
Amplify hosting/CDN
```

Frontend deployments remain independent from backend ECS deployments.

## Backend integration

The browser talks only to the public API endpoint:

``` text
Amplify frontend
      ↓
HTTPS
      ↓
ALB
      ↓
ECS/Fargate API
```

The frontend never directly accesses:

-   RDS;
-   Valkey;
-   SQS;
-   workers;
-   internal MCP services.

## Cost strategy

The frontend should not force the backend to remain running.

The intended model is:

``` text
Amplify frontend
    ↓
remains available

ECS backend
    ↓
apply → test/demo → destroy
```

This supports the project's very low persistent-cost target while
keeping the full production architecture reproducible.
