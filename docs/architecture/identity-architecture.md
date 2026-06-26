# Identity Architecture

External Identity Provider
        │
        ▼
Authentication Provider
        │
        ▼
User Service
        │
        ▼
User Repository
        │
        ▼
ResearchMind User

ResearchMind does not own authentication.

ResearchMind owns application users.

Identity providers own:

- Passwords
- MFA
- OAuth
- JWT issuance

ResearchMind owns:

- Research Sessions
- Documents
- Reports
- Preferences
- Memory
