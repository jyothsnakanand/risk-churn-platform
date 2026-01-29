# Authentication & Authorization Guide

## Overview

This guide covers the most secure implementation of authentication and authorization for the Risk/Churn Scoring Platform.

## Recommended Architecture

### Authentication Strategy: OAuth 2.0 + JWT

**Why this approach?**
- Industry standard for API security
- Stateless authentication (scalable)
- Short-lived access tokens + refresh tokens
- Works seamlessly with React SPAs
- Supports SSO and social login providers

## Implementation Options

### Option 1: External Identity Provider (Most Secure) ⭐ RECOMMENDED

Use a dedicated identity provider service:

**Recommended Providers:**
1. **Auth0** - Easiest to implement, enterprise features
2. **AWS Cognito** - Good if already on AWS
3. **Okta** - Enterprise-grade, excellent RBAC
4. **Azure AD B2C** - Good for Microsoft ecosystems
5. **Keycloak** - Open-source, self-hosted option

**Advantages:**
- ✅ Battle-tested security
- ✅ Built-in MFA, password policies, breach detection
- ✅ Compliance (SOC 2, GDPR, HIPAA)
- ✅ No need to manage password hashing, token rotation
- ✅ Social login support (Google, GitHub, etc.)
- ✅ Audit logs and monitoring
- ✅ Advanced features (passwordless, biometrics)

**Implementation with Auth0 (Example):**

```python
# Backend: src/risk_churn_platform/api/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx

# Auth0 configuration
AUTH0_DOMAIN = "your-tenant.auth0.com"
API_AUDIENCE = "https://your-api-identifier"
ALGORITHMS = ["RS256"]

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Verify JWT token from Auth0."""
    token = credentials.credentials

    try:
        # Get Auth0 public key
        jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            jwks = await client.get(jwks_url)
            jwks = jwks.json()

        # Verify token
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key"
            )

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=ALGORITHMS,
            audience=API_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/"
        )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

# Role-based access control
def require_role(required_role: str):
    """Decorator to require specific role."""
    def role_checker(user: dict = Depends(get_current_user)) -> dict:
        user_roles = user.get("permissions", [])
        if required_role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_role}"
            )
        return user
    return role_checker

# Usage in routes
from fastapi import APIRouter

router = APIRouter()

@router.get("/predictions")
async def get_predictions(user: dict = Depends(get_current_user)):
    """Any authenticated user can view predictions."""
    return {"predictions": []}

@router.post("/models/deploy")
async def deploy_model(user: dict = Depends(require_role("admin"))):
    """Only admins can deploy models."""
    return {"status": "deployed"}
```

**Frontend (React):**

```typescript
// frontend/src/services/auth.ts
import { Auth0Client } from '@auth0/auth0-spa-js';

const auth0Client = new Auth0Client({
  domain: 'your-tenant.auth0.com',
  clientId: 'your-client-id',
  authorizationParams: {
    redirect_uri: window.location.origin,
    audience: 'https://your-api-identifier',
  },
  cacheLocation: 'localstorage',
  useRefreshTokens: true,
});

export const login = async () => {
  await auth0Client.loginWithRedirect();
};

export const logout = () => {
  auth0Client.logout({
    logoutParams: {
      returnTo: window.location.origin,
    },
  });
};

export const getAccessToken = async (): Promise<string | null> => {
  try {
    return await auth0Client.getTokenSilently();
  } catch (error) {
    console.error('Error getting token:', error);
    return null;
  }
};

export const getUser = async () => {
  return await auth0Client.getUser();
};

// Axios interceptor to add token to requests
import axios from 'axios';

axios.interceptors.request.use(
  async (config) => {
    const token = await getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);
```

### Option 2: Self-Implemented JWT (More Control, More Risk)

Only use if you have specific requirements that external providers can't meet.

**Implementation:**

```python
# Backend: src/risk_churn_platform/api/auth.py
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration
SECRET_KEY = "your-secret-key-from-environment"  # MUST be in env vars
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    roles: list[str] = []

class User(BaseModel):
    username: str
    email: str
    roles: list[str]
    disabled: bool = False

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using Argon2."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password using Argon2."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        token_data = TokenData(
            username=username,
            roles=payload.get("roles", [])
        )

    except JWTError:
        raise credentials_exception

    # Get user from database
    user = await get_user_from_db(token_data.username)

    if user is None:
        raise credentials_exception

    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user

async def get_user_from_db(username: str) -> Optional[User]:
    """Get user from database."""
    # Implement your database lookup here
    # This is a placeholder
    pass

# Login endpoint
from fastapi import APIRouter

router = APIRouter()

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint."""
    user = await authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    refresh_token = create_refresh_token(
        data={"sub": user.username}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/token/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token."""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        username = payload.get("sub")
        user = await get_user_from_db(username)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        access_token = create_access_token(
            data={"sub": user.username, "roles": user.roles}
        )

        return {"access_token": access_token, "token_type": "bearer"}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

async def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password."""
    user = await get_user_from_db(username)

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
```

## Role-Based Access Control (RBAC)

### Define Roles and Permissions

```python
# src/risk_churn_platform/api/rbac.py
from enum import Enum
from typing import List

class Role(str, Enum):
    ADMIN = "admin"
    DATA_SCIENTIST = "data_scientist"
    ANALYST = "analyst"
    VIEWER = "viewer"

class Permission(str, Enum):
    # Model permissions
    MODEL_VIEW = "model:view"
    MODEL_DEPLOY = "model:deploy"
    MODEL_DELETE = "model:delete"

    # Prediction permissions
    PREDICTION_VIEW = "prediction:view"
    PREDICTION_CREATE = "prediction:create"

    # Data permissions
    DATA_VIEW = "data:view"
    DATA_EXPORT = "data:export"

    # System permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"

# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, List[Permission]] = {
    Role.ADMIN: [
        Permission.MODEL_VIEW,
        Permission.MODEL_DEPLOY,
        Permission.MODEL_DELETE,
        Permission.PREDICTION_VIEW,
        Permission.PREDICTION_CREATE,
        Permission.DATA_VIEW,
        Permission.DATA_EXPORT,
        Permission.SYSTEM_ADMIN,
        Permission.SYSTEM_MONITOR,
    ],
    Role.DATA_SCIENTIST: [
        Permission.MODEL_VIEW,
        Permission.MODEL_DEPLOY,
        Permission.PREDICTION_VIEW,
        Permission.PREDICTION_CREATE,
        Permission.DATA_VIEW,
        Permission.DATA_EXPORT,
        Permission.SYSTEM_MONITOR,
    ],
    Role.ANALYST: [
        Permission.MODEL_VIEW,
        Permission.PREDICTION_VIEW,
        Permission.PREDICTION_CREATE,
        Permission.DATA_VIEW,
    ],
    Role.VIEWER: [
        Permission.MODEL_VIEW,
        Permission.PREDICTION_VIEW,
        Permission.DATA_VIEW,
    ],
}

def check_permission(user_roles: List[str], required_permission: Permission) -> bool:
    """Check if user has required permission."""
    for role in user_roles:
        if role in ROLE_PERMISSIONS:
            if required_permission in ROLE_PERMISSIONS[Role(role)]:
                return True
    return False

# Permission dependency
from fastapi import Depends, HTTPException, status

def require_permission(permission: Permission):
    """Require specific permission."""
    async def permission_checker(user: dict = Depends(get_current_user)):
        if not check_permission(user.get("roles", []), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}"
            )
        return user
    return permission_checker

# Usage
@router.post("/models/deploy")
async def deploy_model(
    user: dict = Depends(require_permission(Permission.MODEL_DEPLOY))
):
    """Deploy a model (requires MODEL_DEPLOY permission)."""
    pass
```

## Frontend Security Best Practices

### 1. Secure Token Storage

```typescript
// frontend/src/services/tokenStorage.ts

/**
 * Token storage strategy:
 * - Access tokens: memory only (most secure)
 * - Refresh tokens: httpOnly cookie (recommended) or localStorage (less secure)
 */

class TokenService {
  private accessToken: string | null = null;

  // Store access token in memory only
  setAccessToken(token: string) {
    this.accessToken = token;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  clearAccessToken() {
    this.accessToken = null;
  }

  // Refresh token should be in httpOnly cookie (set by backend)
  // Never store refresh tokens in localStorage if possible
}

export const tokenService = new TokenService();
```

### 2. Protected Routes

```typescript
// frontend/src/components/ProtectedRoute.tsx
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string;
  requiredPermission?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  requiredPermission,
}) => {
  const { isAuthenticated, user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRole && !user?.roles?.includes(requiredRole)) {
    return <Navigate to="/unauthorized" replace />;
  }

  if (requiredPermission && !user?.permissions?.includes(requiredPermission)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};

// Usage in routes
<Route
  path="/admin"
  element={
    <ProtectedRoute requiredRole="admin">
      <AdminDashboard />
    </ProtectedRoute>
  }
/>
```

### 3. Auth Context Provider

```typescript
// frontend/src/context/AuthContext.tsx
import React, { createContext, useContext, useEffect, useState } from 'react';
import { getUser, getAccessToken, login, logout } from '../services/auth';

interface AuthContextType {
  user: any;
  isAuthenticated: boolean;
  loading: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const token = await getAccessToken();
      if (token) {
        const userData = await getUser();
        setUser(userData);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = () => {
    login();
  };

  const handleLogout = () => {
    logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        login: handleLogin,
        logout: handleLogout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

## Security Checklist

### Backend Security
- [ ] Use HTTPS only (enforce with HSTS headers)
- [ ] Implement rate limiting on auth endpoints
- [ ] Use Argon2 for password hashing (not bcrypt or MD5)
- [ ] Set secure JWT expiration times (15 min access, 7 day refresh)
- [ ] Validate JWT signature and claims
- [ ] Implement token rotation for refresh tokens
- [ ] Store secrets in environment variables (never in code)
- [ ] Use CSRF protection for cookie-based auth
- [ ] Implement account lockout after failed attempts
- [ ] Log all authentication events
- [ ] Sanitize user inputs
- [ ] Use parameterized queries to prevent SQL injection

### Frontend Security
- [ ] Store access tokens in memory only
- [ ] Use httpOnly cookies for refresh tokens
- [ ] Never log sensitive data to console
- [ ] Implement automatic token refresh
- [ ] Clear tokens on logout
- [ ] Set SameSite=Strict on cookies
- [ ] Implement CSP (Content Security Policy) headers
- [ ] Validate all user inputs
- [ ] Use XSS protection libraries
- [ ] Implement session timeout

### Network Security
- [ ] Enable CORS with specific origins
- [ ] Use TLS 1.3 for all connections
- [ ] Implement request signing for sensitive operations
- [ ] Use API rate limiting
- [ ] Implement IP whitelisting for admin endpoints

## Environment Variables

```bash
# .env.example
# Authentication
SECRET_KEY=your-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Auth0 (if using external provider)
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_AUDIENCE=https://your-api-identifier

# Security
ALLOWED_ORIGINS=http://localhost,https://yourdomain.com
RATE_LIMIT_PER_MINUTE=60
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30
```

## Recommended Approach

For the Risk/Churn Scoring Platform, I recommend:

1. **Use Auth0** (or similar provider) for authentication
2. **Implement RBAC** with 4 roles: Admin, Data Scientist, Analyst, Viewer
3. **Use JWT** with short-lived access tokens (15 min) and longer refresh tokens (7 days)
4. **Store access tokens in memory**, refresh tokens in httpOnly cookies
5. **Implement MFA** for admin accounts
6. **Add audit logging** for all authentication and authorization events

This provides enterprise-grade security without the overhead of building and maintaining your own auth system.

## Additional Resources

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OAuth 2.0 Security Best Practices](https://tools.ietf.org/html/draft-ietf-oauth-security-topics)
