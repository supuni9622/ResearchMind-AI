# DB Session Management

## Simple direct, development method
            
            FastAPI

               │

               ▼

         PostgreSQL

Looks simple.But here's the problem...

1. Where does the database connection come from?
2. Who creates it?
3. Who closes it?
4. Who reconnects if PostgreSQL restarts?
5. Who shares it between requests?
6. Who cleans up resources when the application stops?

That's what these files are solving.

## Production Architecture
                FastAPI
                    │
                    ▼
              Dependency Injection
                    │
                    ▼
              Session Factory
                    │
                    ▼
          SQLAlchemy Engine
                    │
                    ▼
              PostgreSQL

Notice:
The route never talks directly to PostgreSQL. Everything goes through layers.