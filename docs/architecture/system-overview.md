As we've started implementing real infrastructure, I recommend a small update to the repository structure:

apps/api/app/
├── ai/                 # AI orchestration, RAG, agents, evaluation
├── infrastructure/     # External systems (AWS, storage, messaging, etc.)
├── db/                 # Database infrastructure
├── api/                # HTTP layer
├── services/           # Application/business services
└── ...

This keeps a clean separation:

AI = intelligence and orchestration
Infrastructure = external dependencies
Services = business workflows
API = transport layer
