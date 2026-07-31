from fastapi import Request, HTTPException
import os


def require_admin_token(request: Request):
    """Dependency that enforces ADMIN_API_TOKEN when set.

    If ADMIN_API_TOKEN env var is not set, this dependency is a no-op (allows access).
    If set, Authorization header must contain the token (supports 'Bearer <token>' or plain token).
    """
    token = os.environ.get("ADMIN_API_TOKEN")
    if not token:
        # no token configured — allow access
        return True

    auth = request.headers.get("Authorization") or ""
    provided = auth.split()[-1] if auth else ""
    if not provided or provided != token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True
