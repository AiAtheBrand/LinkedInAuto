# LinkedIn Automation Platform

A multi-user backend and API service for drafting, managing, and publishing authentic technical content to LinkedIn with AI assistance.

Built with **FastAPI**, **SQLAlchemy**, and **Pydantic**, following a strict layered architecture:
`Routers -> Services -> Repositories -> Models`.

---

## Key Features

1. **Multi-Tenancy & Workspace Isolation**:
   - Secure registration and login with PBKDF2-HMAC-SHA256 password hashing.
   - User-scoped workspaces: All learning notes, post drafts, LinkedIn connections, and publication records are isolated to the authenticated user.
   - Prevents Insecure Direct Object References (IDOR) at repository and service levels.

2. **Learning Journey to LinkedIn Draft Workflow**:
   - Record software engineering learnings: topic, category, problem encountered, lessons learned, and project context.
   - Generate conversational, authentic LinkedIn post drafts via integrated AI services (`Groq`).
   - Edit, refine, and approve drafts.

3. **Official LinkedIn OAuth 2.0 Integration**:
   - Authorization Code Flow with user-bound, cryptographically random, short-lived, single-use CSRF `state` tokens.
   - Multi-account connectivity: Connect multiple LinkedIn member profiles per application user.
   - **Encryption at rest**: LinkedIn access and refresh tokens are encrypted in the database using authenticated ciphertext before storage.

4. **Decoupled Content vs. Destination Publications**:
   - Content drafts are kept separate from destination-specific publication attempts.
   - Publish a single draft across one or more authorized LinkedIn accounts.
   - Tracks individual publication records with statuses: `draft`, `approved`, `scheduled`, `processing`, `published`, `failed`.
   - Records remote LinkedIn post URNs, timestamps, attempt counts, and error messages.

5. **Durable Scheduling**:
   - Schedule publications for future dates/times.
   - Background worker service for atomic job claiming, preventing race conditions or duplicate publications across workers.

---

## Architecture & Data Model

```mermaid
erDiagram
    USERS ||--o{ LEARNINGS : owns
    USERS ||--o{ POSTS : owns
    USERS ||--o{ LINKEDIN_ACCOUNTS : connects
    USERS ||--o{ PUBLICATIONS : owns
    USERS ||--o{ OAUTH_STATES : generates
    LEARNINGS ||--o{ POSTS : "source of"
    POSTS ||--o{ PUBLICATIONS : publishes
    LINKEDIN_ACCOUNTS ||--o{ PUBLICATIONS : "destination account"

    USERS {
        int id PK
        string email UK
        string hashed_password
        string full_name
        boolean is_active
        datetime created_at
    }

    LEARNINGS {
        int id PK
        int user_id FK
        string topic
        string category
        text problem
        text what_i_learned
        string project
        text lesson
        datetime created_at
    }

    POSTS {
        int id PK
        int user_id FK
        int learning_id FK
        text content
        string status
        datetime created_at
    }

    LINKEDIN_ACCOUNTS {
        int id PK
        int user_id FK
        string linkedin_member_urn
        string name
        string email
        text encrypted_access_token
        datetime token_expires_at
        string scopes
        datetime created_at
    }

    PUBLICATIONS {
        int id PK
        int user_id FK
        int post_id FK
        int linkedin_account_id FK
        string status
        string linkedin_post_urn
        text error_message
        int attempt_count
        datetime scheduled_at
        datetime published_at
        datetime created_at
    }
```

---

## API Endpoints

### 1. Authentication (`/auth`)
- `POST /auth/register` - Register a new application user.
- `POST /auth/login` - Authenticate and receive a Bearer access token.
- `GET /auth/me` - Retrieve current authenticated user profile.

### 2. Learning Material (`/learning`)
- `POST /learning/` - Create a new learning entry.
- `GET /learning/` - List learning entries for current user.
- `GET /learning/{learning_id}` - Retrieve a specific learning entry.
- `PUT /learning/{learning_id}` - Update a learning entry.
- `DELETE /learning/{learning_id}` - Delete a learning entry.

### 3. Posts & AI Generation (`/posts`)
- `POST /posts/generate/{learning_id}` - Generate an AI-assisted LinkedIn post draft from a learning entry.
- `GET /posts/` - List post drafts for current user.
- `GET /posts/{post_id}` - Retrieve a specific post draft.
- `PUT /posts/{post_id}` - Update post draft content.
- `DELETE /posts/{post_id}` - Delete a post draft.

### 4. LinkedIn Connections (`/linkedin`)
- `GET /linkedin/oauth/authorize` - Initiate OAuth flow and receive LinkedIn authorization URL with secure state.
- `POST /linkedin/oauth/callback` - Complete OAuth callback with authorization code.
- `GET /linkedin/accounts` - List connected LinkedIn profiles.
- `DELETE /linkedin/accounts/{account_id}` - Disconnect a LinkedIn profile.

### 5. Publications & Scheduling (`/publications`)
- `POST /publications/publish` - Publish a post immediately to a specified LinkedIn account.
- `POST /publications/schedule` - Schedule a post for future automated publishing.
- `GET /publications/` - List publication history and status records.
- `GET /publications/{publication_id}` - Get status details for a specific publication.

---

## Testing

The project includes an automated test suite verifying models, repositories, services, auth flows, LinkedIn integrations, and multi-tenant isolation:

```bash
# Run all tests
python -m unittest discover -s tests -v
```

All 37 automated tests run against an in-memory SQLite database without requiring live external network sockets.

---

## Environment Configuration

Create a `.env` file in the root directory:

```env
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/linkedin_content
SECRET_KEY=your-secure-random-secret-key-at-least-32-chars
GROQ_API_KEY=your-groq-api-key
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
LINKEDIN_REDIRECT_URI=http://127.0.0.1:8000/linkedin/oauth/callback
LINKEDIN_API_VERSION=202401
```

---

## Running the Application

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Start API server
uvicorn app.main:app --reload
```
