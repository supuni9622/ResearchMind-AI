from pydantic import BaseModel


class CallbackRequest(BaseModel):
    code: str
    redirect_uri: str
    code_verifier: str | None = None  # Required for PKCE flows


class TokenResponse(BaseModel):
    id_token: str
    access_token: str
    refresh_token: str | None = None
    token_type: str
    expires_in: int
