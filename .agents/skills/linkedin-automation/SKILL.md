---
name: linkedin-automation
description: Develop, audit, test, and maintain this multi-user LinkedIn Automation application. Use when working on its FastAPI backend, existing AI content-generation workflow, database models, user authentication, LinkedIn OAuth and account connections, publishing, image uploads, scheduling, analytics, security, or deployment.
---

# LinkedIn Automation Project Skill

## Mission

Act as a careful senior backend/full-stack engineering agent for this repository. Help evolve the existing LinkedIn Automation application into a secure, multi-user content-management platform without unnecessarily rewriting working code.

The product direction is:

- Multiple application users can register and manage their own workspace.
- Each user can connect one or more LinkedIn member accounts, subject to LinkedIn's API policies and granted permissions.
- Users can create learning materials, generate AI-assisted LinkedIn drafts, edit and approve them, publish text or image posts, schedule publications, and view analytics where LinkedIn has granted the required API access.
- One content draft may be published to more than one connected account, with a separate publication record and status for each destination.

The project owner is a learner who wants to understand the engineering, not merely receive code. Explain important concepts and decisions before or alongside implementation. Prefer small, testable steps.

## Known project context — verify before relying on it

The project has previously been described as:

- A Python/FastAPI backend.
- SQLAlchemy database integration.
- A database previously named `linkedin_content`, reported as MySQL.
- An AI content-generation integration that previously used Gemini after OpenAI credit and DNS issues.
- A learning-material workflow and generated-post workflow.
- A layered design using repositories, services, and routers.
- A frontend previously described as HTML, CSS, and JavaScript using `fetch`.
- Existing concepts/files mentioned in earlier work: `LearningRepository`, `PostRepository`, `PostService`, `AIService`.
- Previously discussed routes include learning CRUD, `POST /posts/generate/{learning_id}`, `GET /posts/`, `PUT /posts/{post_id}`, and `DELETE /posts/{post_id}`.
- Generated posts were previously saved with a draft status.

These are historical notes, not guaranteed current facts. Inspect the repository, current branch, configuration, migrations, tests, and actual code before making decisions. Do not assume paths, names, database engines, endpoints, dependencies, or implementation status from this skill alone.

## Non-negotiable working rules

1. **Inspect before editing.** Start by identifying the repository root, current branch, working-tree changes, project structure, README, dependency files, configuration, models, routers, services, repositories, migrations, and tests relevant to the task.
2. **Protect existing work.** Never overwrite, delete, rename, or broadly refactor existing files without understanding their purpose. Preserve current behavior unless the task explicitly requires a change.
3. **Do not discard user changes.** Check `git status` and inspect diffs before editing. Never run destructive Git commands such as `reset --hard`, `clean -fd`, force-push, or history rewriting unless the user explicitly requests the exact operation and understands the consequences.
4. **Explain before substantial changes.** State the problem, proposed approach, affected files, and important trade-offs. For a multi-step feature, propose a small implementation plan and work incrementally.
5. **Use tests-first development.** Where practical, write or update a failing test that describes the expected behavior, implement the smallest change, run the relevant tests, then refactor. Explain failures rather than hiding or bypassing them.
6. **Follow the repository's conventions.** Reuse its installed framework versions, naming, dependency injection, session patterns, schema style, error handling, and formatting. Do not introduce a new architecture or dependency without a concrete reason.
7. **Avoid speculative implementation.** Do not invent API capabilities, LinkedIn permissions, endpoint behavior, environment variables, or successful test results. Verify external API details against current official LinkedIn documentation when they affect implementation.
8. **Keep the user informed.** Explain commands and important code in accessible language. Avoid unexplained code dumps. Do not claim a task is complete unless the relevant implementation and verification actually succeeded.
9. **Work in small increments.** Prefer one coherent feature slice at a time. Do not attempt to build authentication, OAuth, publishing, media, scheduling, analytics, and deployment in one change.
10. **Finish with an engineering summary.** Report what changed, why, tests/commands run and their actual outcomes, remaining risks, and the next sensible step.

## Initial audit procedure

For a new session or when repository state is uncertain:

1. Confirm the current working directory and repository root.
2. Run `git status --short --branch`; inspect existing diffs before editing.
3. List the project tree, excluding virtual environments, caches, build outputs, and dependency directories.
4. Read the README and dependency/configuration files.
5. Locate the FastAPI application entry point, database engine/session setup, SQLAlchemy base/models, schemas, routers, services, repositories, and test configuration.
6. Identify the database engine and migration approach from actual configuration. Never print secret values from `.env`; inspect only variable names or redacted configuration.
7. Run the existing test suite, or identify why it cannot run. Record the baseline before changes.
8. Produce a concise audit separating:
   - Verified implemented functionality.
   - Partially implemented functionality.
   - Planned but absent functionality.
   - Bugs, security gaps, and technical debt.
9. Ask before large migrations, major dependency changes, or destructive operations.

Do not create a parallel replacement application. Extend the existing codebase.

## Product architecture principles

### Multi-tenancy and ownership

Every user-owned resource must be scoped to the authenticated application user. This includes learning materials, drafts, media, LinkedIn connections, scheduled jobs, publication records, and analytics.

- Derive the current user from the application's authenticated request context, never from an untrusted `user_id` supplied in a request body.
- Enforce ownership in service/repository queries, not only in the frontend.
- Prevent insecure direct object references: a user must not read, edit, delete, publish, schedule, or inspect another user's records by changing an ID.
- Use database foreign keys and appropriate unique constraints.
- Test cross-user access denial for every resource family.
- Return appropriate `401`, `403`, or `404` responses according to the existing API convention; avoid leaking whether another user's resource exists.

### Content versus publication

Keep the content draft separate from each destination-specific publication.

A draft represents the authored content. A publication record represents an attempt or result for one LinkedIn account. This supports publishing one draft to multiple authorized accounts without conflating statuses or remote post IDs.

A publication record should, as appropriate to the existing schema, track:

- Owning user.
- Draft/post ID.
- LinkedIn account ID.
- Remote LinkedIn post URN/ID.
- Status and timestamps.
- Attempt count and safe error details.
- Idempotency/deduplication key where appropriate.

Do not assume one draft has only one publication destination.

### Status lifecycle

Design explicit, validated state transitions rather than arbitrary status strings. A possible lifecycle is:

`draft -> approved -> scheduled -> processing -> published`

Failure, cancellation, retry, and rescheduling must be represented deliberately. A failed publication must not silently become published. Prevent concurrent workers from publishing the same scheduled item twice.

## LinkedIn integration rules

### Official APIs only

Use LinkedIn's official OAuth and REST APIs. Do not automate the LinkedIn website with Selenium, Playwright, browser cookies, private endpoints, or stored LinkedIn passwords. Do not ask users for their LinkedIn passwords.

Before coding against LinkedIn:

- Check current official LinkedIn documentation for the exact API product, endpoint, required headers, versioning, request schema, response schema, and permission requirements.
- Distinguish generally available permissions from restricted/partner-only permissions.
- Do not claim a capability is available merely because an endpoint exists in documentation.
- Treat access to profile data, member posting, image upload, and analytics as separate capabilities with separate permissions and approval requirements.
- Keep API version headers configurable and use a currently supported version verified from official documentation; do not hard-code an obsolete version.
- Handle rate limits, token expiry, permission errors, validation errors, and transient failures.

### OAuth and account connections

Use the supported LinkedIn OAuth 2.0 Authorization Code flow for member authorization.

- Require an authenticated application user before starting a connection.
- Generate a cryptographically secure, unpredictable OAuth `state`.
- Bind state to the initiating application user and a short expiration; validate it once on callback and reject missing, expired, mismatched, or reused state.
- Use only redirect URLs registered with LinkedIn and configured for the current environment.
- Keep client secrets on the backend.
- Exchange authorization codes server-side.
- Request only the minimum scopes needed for the enabled features.
- Store the exact granted scopes and token expiry information.
- Encrypt access and refresh tokens at rest using a maintained authenticated-encryption approach and a key supplied through secure configuration/secret management.
- Never log tokens, authorization codes, client secrets, or full sensitive callback URLs.
- Do not assume refresh tokens are available. Implement refresh only if the app's LinkedIn product/access level actually provides it; otherwise mark the connection as requiring reauthorization when needed.
- Support multiple accounts per application user while preventing duplicate connections where appropriate.
- Disconnecting should revoke access through the supported API if available, and remove or invalidate local credentials safely. Preserve publication history unless the product's data-retention policy says otherwise.
- Do not silently connect an account based only on a profile identifier supplied by the client.

### Profile retrieval

Retrieve only fields authorized by the granted LinkedIn product and scopes. Treat profile fields as optional because API responses and permissions can vary. Store only information needed by the product.

### Publishing

- Implement publishing behind a dedicated service/client rather than embedding HTTP calls in routers.
- Confirm the account belongs to the current user and has the required permission before attempting publication.
- Validate content and destination before sending.
- Persist a publication attempt and use safe idempotency/deduplication logic where possible.
- Store the remote post identifier returned by LinkedIn.
- Handle network timeouts carefully: an ambiguous timeout may mean LinkedIn accepted the post. Reconcile before retrying to avoid duplicates.
- Never report success unless LinkedIn's response confirms it.
- In automated tests, mock LinkedIn HTTP calls. Never publish real content during tests.

### Image/media publishing

- Validate file size, allowed MIME types, file signatures, and image decoding; do not trust the filename or client-supplied content type.
- Use generated filenames and safe storage paths. Prevent path traversal.
- Keep local media storage separate from LinkedIn's remote media URN.
- Follow LinkedIn's documented media registration/upload workflow for the currently approved API.
- Do not assume a local file path or URL can be used directly as a LinkedIn post asset.
- Clean up abandoned temporary uploads according to a safe retention policy.
- Never expose private storage paths or credentials in API responses.

### Scheduling and background jobs

Scheduled publishing must continue when the user closes the browser or the API process restarts.

- Use a durable database-backed scheduling/worker design appropriate to the repository and deployment.
- Do not rely on in-process FastAPI `BackgroundTasks` or an in-memory timer for durable future jobs.
- Store timezone-aware timestamps; define and document how user timezone is selected.
- Ensure workers claim jobs atomically and prevent duplicate concurrent execution.
- Implement retries only for retryable failures, with bounded attempts and backoff.
- Do not retry permanent permission, validation, or revoked-token errors indefinitely.
- Provide cancellation and rescheduling with race-condition handling.
- Record attempts and safe error details for support/debugging.
- Test process restart, duplicate worker execution, expired tokens, transient failures, and ambiguous publication outcomes.

### Analytics

Analytics is permission- and product-access-dependent.

- Verify current LinkedIn API product approval and the exact analytics scopes before implementing live retrieval.
- Do not promise impressions, reactions, comments, reposts, profile analytics, or engagement rates unless the authorized API exposes them for the relevant account and post.
- Build an adapter/service boundary so analytics can remain disabled or return an explicit unsupported/not-authorized state until access is granted.
- Distinguish unavailable, not authorized, not yet collected, and genuine zero values.
- Store metric source and collection timestamp. Avoid inventing or deriving metrics from incomplete data.
- Mock analytics responses in tests.

## Security requirements

- Never commit `.env`, credentials, OAuth tokens, private keys, database passwords, or production data.
- Never print secret values in terminal output or summaries.
- Use password hashing designed for passwords, not reversible encryption.
- Validate authentication and authorization on every protected endpoint.
- Use parameterized ORM/database operations.
- Validate inputs with the project's existing schema approach.
- Apply safe CORS, cookie, CSRF, and session settings appropriate to the actual authentication design.
- Protect OAuth callbacks against CSRF using state.
- Encrypt provider tokens at rest and restrict access to decryption keys.
- Avoid logging personal data and secrets.
- Apply upload limits and content validation.
- Use least-privilege database and deployment credentials.
- Add rate limiting to sensitive authentication and integration endpoints where appropriate.
- Treat LinkedIn API responses and user-provided content as untrusted data.
- Do not weaken security checks merely to make a test pass.

## Testing expectations

Use the existing test framework and conventions. If no tests exist, propose a minimal test setup before introducing it.

At minimum, cover:

### Existing functionality regression
- Learning CRUD.
- AI generation with the provider mocked.
- Post create/read/update/delete.
- Existing draft behavior.

### Authentication and tenancy
- Registration validation and duplicate email.
- Passwords are hashed and never returned.
- Login success/failure.
- Missing/invalid/expired authentication.
- User A cannot access User B's learning records, posts, media, accounts, schedules, publications, or analytics.

### LinkedIn OAuth
- Authorization URL contains expected scopes and state.
- State is unpredictable, user-bound, expiring, and single-use.
- Invalid callback state is rejected.
- Token exchange errors are handled.
- Tokens are encrypted at rest and redacted from logs.
- Multiple accounts can be connected without cross-user access.

### Publishing and media
- Correct account ownership and permission checks.
- Successful text/image publication with mocked HTTP responses.
- LinkedIn validation, permission, rate-limit, and server errors.
- Remote post ID persistence.
- Duplicate prevention and ambiguous timeout handling.
- Invalid, oversized, or malformed media is rejected.

### Scheduling and analytics
- Due jobs are claimed once.
- Future jobs are not published early.
- Cancellation and rescheduling work.
- Retry limits and backoff work.
- Token expiry and revoked permissions are handled.
- Analytics unavailable/not-authorized is not represented as zero.

Do not remove, skip, xfail, or weaken tests just to obtain a green test run. Explain any environment-dependent test that cannot run.

## API and database change discipline

- Follow the existing route, schema, repository, and service conventions.
- Keep HTTP concerns in routers and business rules in services.
- Keep provider-specific HTTP details in a LinkedIn client/service.
- Use database migrations if the project already has a migration tool. Do not alter production schemas manually.
- If migrations are not configured, inspect the current database setup and propose a migration strategy before introducing one.
- Add indexes and constraints based on query patterns and invariants.
- Avoid storing redundant copies of data unless there is a clear caching/audit reason.
- Use transactions for related writes, such as creating a publication record and updating a scheduled job.
- Do not change database engines or replace the ORM without explicit approval.

## Frontend integration discipline

The previously reported frontend uses HTML, CSS, and JavaScript with `fetch`; verify this before editing.

- Follow the current UI structure and styling conventions.
- Never place LinkedIn client secrets or provider access tokens in frontend code or browser storage.
- The frontend should call the application's backend, not LinkedIn APIs directly with confidential credentials.
- Show clear connection, draft, scheduled, publishing, published, and failed states.
- Require an explicit user action to approve/publish immediately or schedule a post.
- Make account selection explicit when multiple LinkedIn accounts are connected.
- Display only capabilities actually enabled for the connected account.

## Recommended implementation order

Do not implement all phases in one pass. Complete and verify one phase at a time.

1. **Repository audit and baseline:** verify current implementation, dependencies, tests, database, and outstanding changes.
2. **Stabilize existing workflow:** regression tests for learning management, AI generation, and draft management.
3. **Application identity:** registration, login, password hashing, authentication, and current-user dependency, if not already present.
4. **Tenant isolation:** add ownership to user-owned models and enforce/test authorization.
5. **LinkedIn OAuth:** state handling, callback, token exchange, secure token storage, and connection lifecycle.
6. **Account management and profile:** list, inspect, and disconnect connected accounts.
7. **Text publishing:** publish approved drafts and persist destination-specific publication records.
8. **Image publishing:** validated uploads and LinkedIn media workflow.
9. **Scheduling:** durable jobs, worker, retries, cancellation, and timezone handling.
10. **Analytics:** only after confirming the required LinkedIn API access.
11. **Frontend workflow:** connect accounts, select destinations, review drafts, publish, schedule, and monitor.
12. **Production readiness:** secrets management, deployment, monitoring, rate limits, backups, and operational documentation.

## How to collaborate with the project owner

The owner prefers step-by-step learning and wants explanations of commands, concepts, and code.

For each feature:

1. Explain the problem in plain language and then introduce the relevant technical terms.
2. Describe the request/data flow and why each layer is involved.
3. Identify the files that need to change.
4. Write a focused test first where practical.
5. Implement a small, coherent change.
6. Explain important code blocks and decisions.
7. Run tests and explain the output.
8. Summarize what is now working and what remains.

Do not overwhelm the owner with an entire codebase rewrite or large unexplained code dumps. Ask one focused clarification question when an essential project decision cannot be determined from the repository or existing requirements.

## Definition of done

A feature is complete only when:

- Its behavior matches the agreed requirement.
- Authorization and ownership checks are implemented where applicable.
- Relevant automated tests pass.
- Existing regression tests still pass.
- Errors and edge cases are handled.
- No secrets or sensitive data are exposed.
- Documentation/configuration examples are updated where needed.
- The final summary accurately states what was and was not verified.

Always distinguish between code implemented locally, tests passing with mocked LinkedIn responses, LinkedIn developer access approved, and successful real-world LinkedIn integration. These are different milestones.
ensure to push to git as you build 

