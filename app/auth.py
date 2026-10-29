from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from uuid import UUID
from app.config import settings

# Inicjalizacja schematu bezpieczeństwa dla tokena Bearer
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Zależność FastAPI, która wyodrębnia i weryfikuje token JWT z nagłówka Authorization.
    Zwraca słownik zawierający dane użytkownika (np. sub, email).
    """
    token = credentials.credentials
    
    # Obsługa Mock Auth na potrzeby lokalnego testowania i ewaluacji
    if token == "mock-jwt-token-active":
        return {
            "id": UUID("98bc203e-d9a2-4a0b-90f7-111fbfa251bd"),
            "email": "mock-user@lojiparse.com",
            "role": "authenticated"
        }
        
    try:
        # Dekodowanie tokena przy użyciu sekretu Supabase (JWT Secret) i algorytmu HS256
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}  # Supabase może używać niestandardowej audycji
        )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token JWT jest niepoprawny (brak sub lub email)",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return {
            "id": UUID(user_id),
            "email": email,
            "role": payload.get("role")
        }
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Błąd autoryzacji tokenu: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
