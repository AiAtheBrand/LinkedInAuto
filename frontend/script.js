const API_URL =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:8000"
        : "https://linkedinauto-edi2.onrender.com";

let currentUser = null;
let connectedLinkedInAccounts = [];
let connectedSocialAccounts = [];
let currentAccountFilter = "all";
let authMode = "login"; // 'login' or 'register'

/* =============================================================
   ERROR FORMATTING HELPER (PREVENTS [object Object])
   ============================================================= */

function getErrorMessage(error, fallback = "An unexpected error occurred.") {
    if (!error) return fallback;
    if (typeof error === "string") return error;

    // FastAPI 422 validation errors: array of error dicts
    if (Array.isArray(error)) {
        return error.map(e => {
            if (typeof e === "string") return e;
            if (e && e.msg) {
                const loc = Array.isArray(e.loc) ? e.loc.filter(l => l !== "body").join(".") : "";
                return loc ? `${loc}: ${e.msg}` : e.msg;
            }
            return JSON.stringify(e);
        }).join("; ");
    }

    if (typeof error === "object") {
        if (error.detail) {
            return getErrorMessage(error.detail, fallback);
        }
        if (error.message) return String(error.message);
        if (error.msg) return String(error.msg);
        if (error.error) return typeof error.error === "object" ? getErrorMessage(error.error, fallback) : String(error.error);
        try {
            return JSON.stringify(error);
        } catch {
            return fallback;
        }
    }

    return String(error);
}

/* =============================================================
   FORM VALIDATION HELPERS
   ============================================================= */

const EMAIL_REGEX = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$/;
const INSTAGRAM_HANDLE_REGEX = /^@?[a-zA-Z0-9._]{1,30}$/;

function isValidEmail(email) {
    if (!email || typeof email !== "string") return false;
    const trimmed = email.trim();
    return EMAIL_REGEX.test(trimmed);
}

function setFieldError(inputId, errorMsg) {
    const el = document.getElementById(inputId);
    const errEl = document.getElementById(`${inputId}-error`);
    if (el) el.classList.add("input-error");
    if (errEl) errEl.textContent = errorMsg || "";
}

function clearFieldError(inputId) {
    const el = document.getElementById(inputId);
    const errEl = document.getElementById(`${inputId}-error`);
    if (el) el.classList.remove("input-error");
    if (errEl) errEl.textContent = "";
}

function setupInputLiveValidation() {
    // Auth inputs
    const authEmail = document.getElementById("auth-email");
    const authPassword = document.getElementById("auth-password");
    const authFullname = document.getElementById("auth-fullname");

    if (authEmail) {
        authEmail.addEventListener("input", () => {
            const val = authEmail.value.trim();
            if (!val) {
                setFieldError("auth-email", "Email cannot be blank.");
            } else if (!isValidEmail(val)) {
                setFieldError("auth-email", "Please enter a valid email format (e.g. name@example.com).");
            } else {
                clearFieldError("auth-email");
            }
        });
    }

    if (authPassword) {
        authPassword.addEventListener("input", () => {
            const val = authPassword.value;
            if (!val || !val.trim()) {
                setFieldError("auth-password", "Password cannot be blank or contain only spaces.");
            } else if (val.length < 8) {
                setFieldError("auth-password", "Password must be at least 8 characters long.");
            } else {
                clearFieldError("auth-password");
            }
        });
    }

    if (authFullname) {
        authFullname.addEventListener("input", () => {
            clearFieldError("auth-fullname");
        });
    }

    // Learning form inputs
    ["topic", "category", "what_i_learned"].forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener("input", () => {
                if (input.value.trim()) clearFieldError(id);
            });
        }
    });

    // Facebook modal inputs
    ["fb-page-name", "fb-page-id", "fb-email", "fb-token"].forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener("input", () => {
                if (id === "fb-email" && input.value.trim()) {
                    if (!isValidEmail(input.value.trim())) {
                        setFieldError("fb-email", "Invalid email format.");
                        return;
                    }
                }
                clearFieldError(id);
            });
        }
    });

    // Instagram modal inputs
    ["ig-handle", "ig-name", "ig-email", "ig-token"].forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener("input", () => {
                if (id === "ig-handle" && input.value.trim()) {
                    if (!INSTAGRAM_HANDLE_REGEX.test(input.value.trim())) {
                        setFieldError("ig-handle", "Invalid handle. Letters, numbers, dots and underscores only.");
                        return;
                    }
                }
                if (id === "ig-email" && input.value.trim()) {
                    if (!isValidEmail(input.value.trim())) {
                        setFieldError("ig-email", "Invalid email format.");
                        return;
                    }
                }
                clearFieldError(id);
            });
        }
    });
}

/* =============================================================
   AUTHENTICATION & FETCH HELPERS
   ============================================================= */

function getToken() {
    return localStorage.getItem("auth_token");
}

function setToken(token) {
    if (token) {
        localStorage.setItem("auth_token", token);
    } else {
        localStorage.removeItem("auth_token");
    }
}

async function authFetch(endpoint, options = {}) {
    const token = getToken();
    const headers = { ...(options.headers || {}) };

    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            setToken(null);
            currentUser = null;
            updateUI();
            throw new Error("Session expired. Please log in again.");
        }

        return response;
    } catch (err) {
        if (err.message === "Failed to fetch" || err.name === "TypeError") {
            throw new Error(`Cannot reach backend at ${API_URL}. Ensure uvicorn server is running.`);
        }
        throw err;
    }
}

function switchAuthTab(mode) {
    authMode = mode;
    const tabLogin = document.getElementById("tab-login");
    const tabRegister = document.getElementById("tab-register");
    const nameGroup = document.getElementById("auth-name-group");
    const submitBtn = document.getElementById("auth-submit-btn");
    const msg = document.getElementById("auth-message");
    msg.textContent = "";

    clearFieldError("auth-email");
    clearFieldError("auth-password");
    clearFieldError("auth-fullname");

    if (mode === "register") {
        tabLogin.classList.remove("active");
        tabRegister.classList.add("active");
        nameGroup.style.display = "block";
        submitBtn.textContent = "Create Account";
    } else {
        tabRegister.classList.remove("active");
        tabLogin.classList.add("active");
        nameGroup.style.display = "none";
        submitBtn.textContent = "Sign In";
    }
}

async function handleAuthSubmit(event) {
    event.preventDefault();
    const emailInput = document.getElementById("auth-email");
    const passwordInput = document.getElementById("auth-password");
    const fullNameInput = document.getElementById("auth-fullname");
    const msg = document.getElementById("auth-message");
    const submitBtn = document.getElementById("auth-submit-btn");

    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const fullName = fullNameInput ? fullNameInput.value.trim() : "";

    // Client-side validation checks
    let hasError = false;

    if (!email) {
        setFieldError("auth-email", "Email address cannot be blank.");
        hasError = true;
    } else if (!isValidEmail(email)) {
        setFieldError("auth-email", "Please enter a valid email format (e.g. name@example.com).");
        hasError = true;
    } else {
        clearFieldError("auth-email");
    }

    if (!password || !password.trim()) {
        setFieldError("auth-password", "Password cannot be blank or contain only spaces.");
        hasError = true;
    } else if (password.length < 8) {
        setFieldError("auth-password", "Password must be at least 8 characters long.");
        hasError = true;
    } else {
        clearFieldError("auth-password");
    }

    if (hasError) {
        msg.style.color = "var(--danger)";
        msg.textContent = "Please fix the form errors highlighted above.";
        return;
    }

    msg.textContent = "";
    submitBtn.disabled = true;

    try {
        if (authMode === "register") {
            const res = await fetch(`${API_URL}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password, full_name: fullName || null })
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(getErrorMessage(data, "Registration failed"));
            }

            // Auto-login after registration
            const loginRes = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });
            const loginData = await loginRes.json();
            if (!loginRes.ok) throw new Error(getErrorMessage(loginData, "Login failed"));

            setToken(loginData.access_token);
            currentUser = loginData.user;
        } else {
            const res = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(getErrorMessage(data, "Invalid credentials"));
            }

            setToken(data.access_token);
            currentUser = data.user;
        }

        updateUI();
        loadAllData();
    } catch (err) {
        msg.style.color = "var(--danger)";
        msg.textContent = getErrorMessage(err.message);
    } finally {
        submitBtn.disabled = false;
    }
}

async function checkAuthSession() {
    const token = getToken();
    if (!token) {
        updateUI();
        return;
    }

    try {
        const res = await authFetch("/auth/me");
        if (res.ok) {
            currentUser = await res.json();
            updateUI();
            loadAllData();
        } else {
            currentUser = null;
            setToken(null);
            updateUI();
        }
    } catch {
        currentUser = null;
        setToken(null);
        updateUI();
    }
}

function logout() {
    setToken(null);
    currentUser = null;
    connectedLinkedInAccounts = [];
    connectedSocialAccounts = [];
    updateUI();
}

function updateUI() {
    const authSection = document.getElementById("auth-section");
    const appWorkspace = document.getElementById("app-workspace");
    const headerAuthArea = document.getElementById("auth-header-area");

    if (currentUser) {
        authSection.style.display = "none";
        appWorkspace.style.display = "block";
        headerAuthArea.innerHTML = `
            <div class="user-badge">
                <span class="user-name">👤 ${currentUser.full_name || currentUser.email}</span>
                <button class="btn btn-secondary btn-sm" onclick="logout()">Sign Out</button>
            </div>
        `;
    } else {
        authSection.style.display = "block";
        appWorkspace.style.display = "none";
        headerAuthArea.innerHTML = "";
    }
}

/* =============================================================
   SOCIAL ACCOUNTS MANAGEMENT (LINKEDIN, FACEBOOK, INSTAGRAM)
   ============================================================= */

function filterAccountsTab(platform, btnEl) {
    currentAccountFilter = platform;
    document.querySelectorAll(".filter-tab").forEach(tab => tab.classList.remove("active"));
    if (btnEl) btnEl.classList.add("active");
    renderSocialAccounts();
}

async function loadAllAccounts() {
    try {
        const [liRes, socialRes] = await Promise.all([
            authFetch("/linkedin/accounts"),
            authFetch("/social/accounts")
        ]);

        connectedLinkedInAccounts = liRes.ok ? await liRes.json() : [];
        connectedSocialAccounts = socialRes.ok ? await socialRes.json() : [];

        renderSocialAccounts();
    } catch (err) {
        const listEl = document.getElementById("social-accounts-list");
        if (listEl) listEl.innerHTML = `<p class="empty-text">${escapeHtml(getErrorMessage(err.message))}</p>`;
    }
}

function renderSocialAccounts() {
    const listEl = document.getElementById("social-accounts-list");
    if (!listEl) return;

    listEl.innerHTML = "";

    const combined = [
        ...connectedLinkedInAccounts.map(a => ({ ...a, platform: "linkedin" })),
        ...connectedSocialAccounts
    ];

    const filtered = currentAccountFilter === "all"
        ? combined
        : combined.filter(a => a.platform === currentAccountFilter);

    if (filtered.length === 0) {
        listEl.innerHTML = `<p class="empty-text">No ${currentAccountFilter === "all" ? "" : currentAccountFilter + " "}accounts connected. Click the buttons above to connect.</p>`;
        return;
    }

    filtered.forEach(acc => {
        const pill = document.createElement("div");
        pill.className = "account-pill";

        let avatarClass = "avatar-linkedin";
        let avatarText = "in";
        let isLinkedIn = acc.platform === "linkedin";

        if (acc.platform === "facebook") {
            avatarClass = "avatar-facebook";
            avatarText = "fb";
        } else if (acc.platform === "instagram") {
            avatarClass = "avatar-instagram";
            avatarText = "ig";
        }

        const subtitle = isLinkedIn
            ? (acc.email || acc.linkedin_member_urn)
            : (acc.account_identifier + (acc.email ? ` • ${acc.email}` : ""));

        const disconnectAction = isLinkedIn
            ? `disconnectLinkedInAccount(${acc.id})`
            : `disconnectSocialAccount(${acc.id}, '${acc.platform}')`;

        pill.innerHTML = `
            <div class="account-avatar ${avatarClass}">${avatarText}</div>
            <div class="account-info">
                <h4>${escapeHtml(acc.name)}</h4>
                <p title="${escapeHtml(subtitle)}">${escapeHtml(subtitle)}</p>
            </div>
            <button class="btn btn-danger btn-sm" onclick="${disconnectAction}">Disconnect</button>
        `;
        listEl.appendChild(pill);
    });
}

// Modal handling
function openConnectModal(platform) {
    const modal = document.getElementById(`modal-${platform}`);
    if (modal) modal.style.display = "flex";
}

function closeConnectModal(platform) {
    const modal = document.getElementById(`modal-${platform}`);
    if (modal) {
        modal.style.display = "none";
        const form = document.getElementById(platform === "facebook" ? "connect-fb-form" : "connect-ig-form");
        if (form) form.reset();
        const msg = document.getElementById(platform === "facebook" ? "fb-modal-msg" : "ig-modal-msg");
        if (msg) msg.textContent = "";
    }
}

// Facebook Form Submit
async function handleConnectFacebook(event) {
    event.preventDefault();
    const name = document.getElementById("fb-page-name").value.trim();
    const pageId = document.getElementById("fb-page-id").value.trim();
    const email = document.getElementById("fb-email").value.trim();
    const token = document.getElementById("fb-token").value.trim();
    const msg = document.getElementById("fb-modal-msg");
    const btn = document.getElementById("fb-submit-btn");

    let hasError = false;
    if (!name) { setFieldError("fb-page-name", "Page name cannot be blank."); hasError = true; } else { clearFieldError("fb-page-name"); }
    if (!pageId) { setFieldError("fb-page-id", "Page ID cannot be blank."); hasError = true; } else { clearFieldError("fb-page-id"); }
    if (email && !isValidEmail(email)) { setFieldError("fb-email", "Invalid email format."); hasError = true; } else { clearFieldError("fb-email"); }
    if (!token) { setFieldError("fb-token", "Access token cannot be blank."); hasError = true; } else { clearFieldError("fb-token"); }

    if (hasError) return;

    btn.disabled = true;
    msg.textContent = "";

    try {
        const res = await authFetch("/social/accounts", {
            method: "POST",
            body: JSON.stringify({
                platform: "facebook",
                name,
                account_identifier: pageId,
                email: email || null,
                access_token: token
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to connect Facebook page"));

        closeConnectModal("facebook");
        await loadAllAccounts();
        await loadPosts();
    } catch (err) {
        msg.style.color = "var(--danger)";
        msg.textContent = getErrorMessage(err.message);
    } finally {
        btn.disabled = false;
    }
}

// Instagram Form Submit
async function handleConnectInstagram(event) {
    event.preventDefault();
    const handle = document.getElementById("ig-handle").value.trim();
    const name = document.getElementById("ig-name").value.trim();
    const email = document.getElementById("ig-email").value.trim();
    const token = document.getElementById("ig-token").value.trim();
    const msg = document.getElementById("ig-modal-msg");
    const btn = document.getElementById("ig-submit-btn");

    let hasError = false;
    if (!handle) {
        setFieldError("ig-handle", "Instagram handle cannot be blank.");
        hasError = true;
    } else if (!INSTAGRAM_HANDLE_REGEX.test(handle)) {
        setFieldError("ig-handle", "Invalid handle. Letters, numbers, dots and underscores only.");
        hasError = true;
    } else {
        clearFieldError("ig-handle");
    }

    if (!name) { setFieldError("ig-name", "Display name cannot be blank."); hasError = true; } else { clearFieldError("ig-name"); }
    if (email && !isValidEmail(email)) { setFieldError("ig-email", "Invalid email format."); hasError = true; } else { clearFieldError("ig-email"); }
    if (!token) { setFieldError("ig-token", "Access token cannot be blank."); hasError = true; } else { clearFieldError("ig-token"); }

    if (hasError) return;

    btn.disabled = true;
    msg.textContent = "";

    try {
        const res = await authFetch("/social/accounts", {
            method: "POST",
            body: JSON.stringify({
                platform: "instagram",
                name,
                account_identifier: handle,
                email: email || null,
                access_token: token
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to connect Instagram account"));

        closeConnectModal("instagram");
        await loadAllAccounts();
        await loadPosts();
    } catch (err) {
        msg.style.color = "var(--danger)";
        msg.textContent = getErrorMessage(err.message);
    } finally {
        btn.disabled = false;
    }
}

async function startLinkedInOAuth() {
    try {
        const res = await authFetch("/linkedin/oauth/authorize");
        if (!res.ok) {
            const data = await res.json();
            throw new Error(getErrorMessage(data, "Failed to start OAuth"));
        }
        const data = await res.json();

        const authWindow = window.open(data.authorization_url, "_blank", "width=600,height=700");

        const timer = setInterval(async () => {
            if (authWindow && authWindow.closed) {
                clearInterval(timer);
                await loadAllAccounts();
                await loadPosts();
            }
        }, 1500);
    } catch (err) {
        alert("OAuth initiation failed: " + getErrorMessage(err.message));
    }
}

async function disconnectLinkedInAccount(accountId) {
    if (!confirm("Are you sure you want to disconnect this LinkedIn account?")) return;
    try {
        const res = await authFetch(`/linkedin/accounts/${accountId}`, { method: "DELETE" });
        if (!res.ok) {
            const data = await res.json();
            throw new Error(getErrorMessage(data, "Failed to disconnect"));
        }
        await loadAllAccounts();
        await loadPosts();
    } catch (err) {
        alert(getErrorMessage(err.message));
    }
}

async function disconnectSocialAccount(accountId, platform) {
    if (!confirm(`Are you sure you want to disconnect this ${platform} account?`)) return;
    try {
        const res = await authFetch(`/social/accounts/${accountId}`, { method: "DELETE" });
        if (!res.ok) {
            const data = await res.json();
            throw new Error(getErrorMessage(data, "Failed to disconnect"));
        }
        await loadAllAccounts();
        await loadPosts();
    } catch (err) {
        alert(getErrorMessage(err.message));
    }
}

/* =============================================================
   LEARNING CRUD
   ============================================================= */

async function handleLearningSubmit(event) {
    event.preventDefault();
    const form = document.getElementById("learning-form");
    const msg = document.getElementById("form-message");
    const spinner = document.getElementById("form-spinner");
    const submitBtn = document.getElementById("learning-submit-btn");

    const topic = document.getElementById("topic").value.trim();
    const category = document.getElementById("category").value.trim();
    const what_i_learned = document.getElementById("what_i_learned").value.trim();
    const problem = document.getElementById("problem").value.trim();
    const project = document.getElementById("project").value.trim();
    const lesson = document.getElementById("lesson").value.trim();

    // Validation checks for blanks
    let hasError = false;
    if (!topic) { setFieldError("topic", "Topic cannot be blank."); hasError = true; } else { clearFieldError("topic"); }
    if (!category) { setFieldError("category", "Category cannot be blank."); hasError = true; } else { clearFieldError("category"); }
    if (!what_i_learned) { setFieldError("what_i_learned", "What You Learned cannot be blank."); hasError = true; } else { clearFieldError("what_i_learned"); }

    if (hasError) {
        msg.style.color = "var(--danger)";
        msg.textContent = "Please fill in all required fields.";
        return;
    }

    msg.textContent = "";
    spinner.style.display = "inline-block";
    submitBtn.disabled = true;

    const payload = {
        topic,
        category,
        problem: problem || null,
        what_i_learned,
        project: project || null,
        lesson: lesson || null
    };

    try {
        // 1. Save Learning Note
        const createRes = await authFetch("/learning/", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        const createdLearning = await createRes.json();
        if (!createRes.ok) {
            throw new Error(getErrorMessage(createdLearning, "Failed to save learning note"));
        }

        // 2. Generate Post via AI
        const genRes = await authFetch(`/posts/generate/${createdLearning.id}`, { method: "POST" });
        const post = await genRes.json();
        if (!genRes.ok) {
            throw new Error(getErrorMessage(post, "AI post generation failed. Please click 'Generate Post' to retry."));
        }

        msg.style.color = "var(--success)";
        msg.textContent = "Learning saved and AI draft generated successfully!";
        form.reset();

        await loadLearnings();
        await loadPosts();
    } catch (err) {
        msg.style.color = "var(--danger)";
        msg.textContent = getErrorMessage(err.message);
    } finally {
        spinner.style.display = "none";
        submitBtn.disabled = false;
    }
}

async function loadLearnings() {
    const container = document.getElementById("learning-container");
    const countBadge = document.getElementById("learning-count");

    try {
        const res = await authFetch("/learning/");
        if (!res.ok) {
            const data = await res.json();
            throw new Error(getErrorMessage(data, "Failed to load learning entries"));
        }
        const items = await res.json();

        countBadge.textContent = items.length;
        container.innerHTML = "";

        if (items.length === 0) {
            container.innerHTML = `<p class="empty-text">No learning entries yet. Fill out the form above!</p>`;
            return;
        }

        items.forEach(item => {
            const card = document.createElement("div");
            card.className = "item-card";
            card.innerHTML = `
                <h3>${escapeHtml(item.topic)}</h3>
                <div class="item-meta">Category: <strong>${escapeHtml(item.category)}</strong> • ${new Date(item.created_at).toLocaleDateString()}</div>
                <div class="item-content">${escapeHtml(item.what_i_learned)}</div>
                ${item.lesson ? `<p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 8px;"><em>💡 Takeaway: ${escapeHtml(item.lesson)}</em></p>` : ""}
                <div class="item-actions">
                    <button class="btn btn-secondary btn-sm" onclick="generateAdditionalPost(${item.id})">Generate Post</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteLearning(${item.id})">Delete</button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        container.innerHTML = `<p class="empty-text">${escapeHtml(getErrorMessage(err.message))}</p>`;
    }
}

async function generateAdditionalPost(learningId) {
    try {
        const res = await authFetch(`/posts/generate/${learningId}`, { method: "POST" });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(getErrorMessage(data, "AI generation failed"));
        }
        await loadPosts();
    } catch (err) {
        alert("Failed to generate post: " + getErrorMessage(err.message));
    }
}

async function deleteLearning(learningId) {
    if (!confirm("Delete this learning entry? Associated draft posts will remain.")) return;
    try {
        const res = await authFetch(`/learning/${learningId}`, { method: "DELETE" });
        if (!res.ok) {
            const data = await res.json();
            throw new Error(getErrorMessage(data, "Delete failed"));
        }
        await loadLearnings();
    } catch (err) {
        alert(getErrorMessage(err.message));
    }
}

/* =============================================================
   POSTS & MULTI-IMAGE / MULTI-PLATFORM PUBLICATIONS
   ============================================================= */

async function loadPosts() {
    const container = document.getElementById("posts-container");
    const countBadge = document.getElementById("posts-count");

    try {
        const [postsRes, pubsRes] = await Promise.all([
            authFetch("/posts/"),
            authFetch("/publications/")
        ]);

        if (!postsRes.ok) {
            const data = await postsRes.json();
            throw new Error(getErrorMessage(data, "Failed to load posts"));
        }
        const posts = await postsRes.json();
        const publications = pubsRes.ok ? await pubsRes.json() : [];

        countBadge.textContent = posts.length;
        container.innerHTML = "";

        if (posts.length === 0) {
            container.innerHTML = `<p class="empty-text">No posts available yet. Create a learning note to generate one!</p>`;
            return;
        }

        posts.forEach(post => {
            const postPubs = publications.filter(p => p.post_id === post.id);
            const card = document.createElement("div");
            card.className = "item-card";

            let statusClass = "status-draft";
            if (post.status === "published") statusClass = "status-published";
            else if (post.status === "scheduled") statusClass = "status-scheduled";

            // Resolve list of images attached to this post
            const images = (Array.isArray(post.image_urls) && post.image_urls.length > 0)
                ? post.image_urls
                : (post.image_url ? [post.image_url] : []);

            const hasImages = images.length > 0;

            // Destination options for each platform
            const fbAccounts = connectedSocialAccounts.filter(a => a.platform === "facebook");
            const igAccounts = connectedSocialAccounts.filter(a => a.platform === "instagram");

            const hasLinkedIn = connectedLinkedInAccounts.length > 0;
            const hasFacebook = fbAccounts.length > 0;
            const hasInstagram = igAccounts.length > 0;
            const hasAnyPlatform = hasLinkedIn || hasFacebook || hasInstagram;

            const liOptions = connectedLinkedInAccounts.map(
                acc => `<option value="${acc.id}">${escapeHtml(acc.name)}</option>`
            ).join("");

            const fbOptions = fbAccounts.map(
                acc => `<option value="${acc.id}">${escapeHtml(acc.name)}</option>`
            ).join("");

            const igOptions = igAccounts.map(
                acc => `<option value="${acc.id}">${escapeHtml(acc.name)} (${escapeHtml(acc.account_identifier)})</option>`
            ).join("");

            let pubDetailsHtml = "";
            if (postPubs.length > 0) {
                pubDetailsHtml = `<div style="margin-top: 10px; font-size: 0.8rem; background: #fafafa; padding: 10px; border-radius: 6px; border: 1px solid #eee;">
                    <strong>Published Destinations:</strong>
                    ${postPubs.map(p => {
                    let platTag = `<span class="platform-tag tag-${p.platform || 'linkedin'}">${p.platform || 'linkedin'}</span>`;
                    let idStr = p.remote_post_id || p.linkedin_post_urn;
                    return `
                        <div style="margin-top: 6px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            ${platTag}
                            <span class="status-pill status-${p.status}">${p.status}</span>
                            ${idStr ? `<code>${escapeHtml(idStr)}</code>` : ""}
                            ${p.error_message ? `<span style="color: var(--danger);">${escapeHtml(p.error_message)}</span>` : ""}
                        </div>`;
                }).join("")}
                </div>`;
            }

            // Multi-Image Gallery HTML
            let imageGalleryHtml = "";
            if (images.length > 0) {
                let gridClass = "grid-1";
                if (images.length === 2) gridClass = "grid-2";
                else if (images.length > 2) gridClass = "grid-many";

                const thumbsHtml = images.map((imgUrl, idx) => `
                    <div class="post-image-thumb-wrapper" title="Image ${idx + 1} of ${images.length}">
                        <img src="${API_URL}${imgUrl}" class="post-image-thumb" alt="Post attachment ${idx + 1}" onclick="window.open('${API_URL}${imgUrl}', '_blank')" />
                        <button type="button" class="btn-delete-img" title="Delete image" onclick="deletePostImage(${post.id}, ${idx})">&times;</button>
                    </div>
                `).join("");

                imageGalleryHtml = `
                    <div class="post-images-grid ${gridClass}">
                        ${thumbsHtml}
                    </div>
                `;
            }

            // Destination Picker HTML
            let destinationPickerHtml = `
                <div class="destination-picker-box">
                    <div class="destination-picker-title">
                        <span>🎯 Pick Where to Post To:</span>
                    </div>
                    <div class="destinations-row">
                        <div class="destination-item">
                            <input type="checkbox" id="dest-li-${post.id}" ${hasLinkedIn ? "checked" : "disabled"}>
                            <span class="platform-tag tag-linkedin">LinkedIn</span>
                            ${hasLinkedIn
                                ? `<select id="acc-li-${post.id}" class="destination-select">${liOptions}</select>`
                                : `<span style="font-size: 0.78rem; color: var(--text-secondary);">(Connect LinkedIn above)</span>`
                            }
                        </div>

                        <div class="destination-item">
                            <input type="checkbox" id="dest-fb-${post.id}" ${hasFacebook ? "" : "disabled"}>
                            <span class="platform-tag tag-facebook">Facebook</span>
                            ${hasFacebook
                                ? `<select id="acc-fb-${post.id}" class="destination-select">${fbOptions}</select>`
                                : `<span style="font-size: 0.78rem; color: var(--text-secondary);">(Connect Facebook above)</span>`
                            }
                        </div>

                        <div class="destination-item">
                            <input type="checkbox" id="dest-ig-${post.id}" ${hasInstagram ? "" : "disabled"} onchange="validateInstagramPick(${post.id}, this)">
                            <span class="platform-tag tag-instagram">Instagram</span>
                            ${hasInstagram
                                ? `<select id="acc-ig-${post.id}" class="destination-select">${igOptions}</select>`
                                : `<span style="font-size: 0.78rem; color: var(--text-secondary);">(Connect Instagram above)</span>`
                            }
                            ${hasImages
                                ? `<span class="ig-ready-badge">📷 Ready (${images.length} image${images.length > 1 ? "s" : ""})</span>`
                                : `<span class="ig-warning-badge" id="ig-warn-${post.id}">⚠️ Image required</span>`
                            }
                        </div>
                    </div>
                </div>
            `;

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div>
                        <span class="status-pill ${statusClass}">${post.status}</span>
                        <small style="margin-left: 8px; color: var(--text-secondary);">${new Date(post.created_at).toLocaleString()}</small>
                    </div>
                    <div>
                        <button class="btn btn-secondary btn-sm" onclick="openEditPost(${post.id})">✏️ Edit</button>
                    </div>
                </div>

                <div class="item-content" id="post-content-${post.id}">${escapeHtml(post.content)}</div>

                <div id="post-edit-box-${post.id}" class="post-edit-box" style="display: none;">
                    <textarea id="post-edit-textarea-${post.id}" class="post-edit-textarea">${escapeHtml(post.content)}</textarea>
                    <div class="post-edit-actions">
                        <button class="btn btn-primary btn-sm" onclick="saveEditPost(${post.id})">💾 Save Changes</button>
                        <button class="btn btn-secondary btn-sm" onclick="cancelEditPost(${post.id})">Cancel</button>
                    </div>
                </div>

                ${imageGalleryHtml}

                <div style="margin: 8px 0 12px 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    <label class="btn btn-secondary btn-sm btn-upload-label" id="upload-label-${post.id}">
                        <span>📷 ${hasImages ? "+ Add More Images" : "Attach Image(s)"}</span>
                        <input type="file" multiple accept="image/png, image/jpeg, image/gif, image/webp" onchange="uploadPostImages(${post.id}, this.files)" />
                    </label>
                    <span class="spinner" id="upload-spinner-${post.id}" style="display: none;"></span>
                    ${hasImages ? `<span class="image-badge-count">(${images.length} image${images.length > 1 ? "s" : ""} attached)</span>` : ""}
                </div>

                ${pubDetailsHtml}

                ${destinationPickerHtml}

                <div class="item-actions">
                    ${hasAnyPlatform ? `
                        <button class="btn btn-primary btn-sm" onclick="publishSelectedDestinations(${post.id}, ${hasImages})">
                            🚀 Publish to Selected
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="toggleScheduleInput(${post.id})">
                            📅 Schedule
                        </button>
                    ` : `<span style="font-size: 0.8rem; color: var(--text-secondary);">Connect at least one account above to publish</span>`}
                    <button class="btn btn-danger btn-sm" style="margin-left: auto;" onclick="deletePost(${post.id})">Delete</button>
                </div>

                <div id="schedule-box-${post.id}" style="display: none; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #ddd;">
                    <label style="font-size: 0.8rem;">Select publication date & time (LinkedIn schedule):</label>
                    <input type="datetime-local" id="schedule-time-${post.id}" style="width: auto; margin-right: 8px;">
                    <button class="btn btn-primary btn-sm" onclick="schedulePostNow(${post.id})">Confirm Schedule</button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        container.innerHTML = `<p class="empty-text">${escapeHtml(getErrorMessage(err.message))}</p>`;
    }
}

function validateInstagramPick(postId, checkbox) {
    if (checkbox.checked) {
        const warnBadge = document.getElementById(`ig-warn-${postId}`);
        if (warnBadge) {
            alert("⚠️ Instagram Notice: Instagram requires an image attachment. Please attach one or more images before publishing to Instagram.");
        }
    }
}

async function uploadPostImages(postId, fileList) {
    if (!fileList || fileList.length === 0) return;

    const spinner = document.getElementById(`upload-spinner-${postId}`);
    const label = document.getElementById(`upload-label-${postId}`);

    if (spinner) spinner.style.display = "inline-block";
    if (label) label.style.opacity = "0.5";

    const formData = new FormData();
    for (let i = 0; i < fileList.length; i++) {
        formData.append("files", fileList[i]);
    }

    try {
        const res = await authFetch(`/posts/${postId}/images`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(getErrorMessage(data, "Image upload failed"));
        }
        await loadPosts();
    } catch (err) {
        alert("Upload error: " + getErrorMessage(err.message));
    } finally {
        if (spinner) spinner.style.display = "none";
        if (label) label.style.opacity = "1";
    }
}

async function deletePostImage(postId, imageIndex) {
    if (!confirm("Are you sure you want to remove this image from the post?")) return;

    try {
        const res = await authFetch(`/posts/${postId}/images/${imageIndex}`, {
            method: "DELETE"
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(getErrorMessage(data, "Failed to remove image"));
        }
        await loadPosts();
    } catch (err) {
        alert("Error removing image: " + getErrorMessage(err.message));
    }
}

async function publishSelectedDestinations(postId, hasImages) {
    const checkLi = document.getElementById(`dest-li-${postId}`);
    const checkFb = document.getElementById(`dest-fb-${postId}`);
    const checkIg = document.getElementById(`dest-ig-${postId}`);

    const destinations = [];

    if (checkLi && checkLi.checked) {
        const sel = document.getElementById(`acc-li-${postId}`);
        if (!sel || !sel.value) {
            alert("Please select a LinkedIn account for the LinkedIn destination.");
            return;
        }
        destinations.push({ platform: "linkedin", account_id: parseInt(sel.value) });
    }

    if (checkFb && checkFb.checked) {
        const sel = document.getElementById(`acc-fb-${postId}`);
        if (!sel || !sel.value) {
            alert("Please select a Facebook page for the Facebook destination.");
            return;
        }
        destinations.push({ platform: "facebook", account_id: parseInt(sel.value) });
    }

    if (checkIg && checkIg.checked) {
        if (!hasImages) {
            alert("Instagram requires an image attachment. Please attach at least one image to your post before publishing to Instagram.");
            return;
        }
        const sel = document.getElementById(`acc-ig-${postId}`);
        if (!sel || !sel.value) {
            alert("Please select an Instagram account for the Instagram destination.");
            return;
        }
        destinations.push({ platform: "instagram", account_id: parseInt(sel.value) });
    }

    if (destinations.length === 0) {
        alert("Please select at least one platform (LinkedIn, Facebook, or Instagram) to publish to.");
        return;
    }

    try {
        const res = await authFetch("/publications/publish-multi", {
            method: "POST",
            body: JSON.stringify({
                post_id: postId,
                destinations
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(getErrorMessage(data, "Publication failed"));

        const publishedCount = data.filter(d => d.status === "published").length;
        const failedCount = data.filter(d => d.status === "failed").length;

        let alertMsg = `Publication complete! Published: ${publishedCount}`;
        if (failedCount > 0) alertMsg += `, Failed: ${failedCount}`;
        alert(alertMsg);

        await loadPosts();
    } catch (err) {
        alert("Publish error: " + getErrorMessage(err.message));
    }
}

function openEditPost(postId) {
    const contentEl = document.getElementById(`post-content-${postId}`);
    const editArea = document.getElementById(`post-edit-box-${postId}`);
    if (contentEl && editArea) {
        contentEl.style.display = "none";
        editArea.style.display = "block";
    }
}

function cancelEditPost(postId) {
    const contentEl = document.getElementById(`post-content-${postId}`);
    const editArea = document.getElementById(`post-edit-box-${postId}`);
    if (contentEl && editArea) {
        contentEl.style.display = "block";
        editArea.style.display = "none";
    }
}

async function saveEditPost(postId) {
    const textarea = document.getElementById(`post-edit-textarea-${postId}`);
    if (!textarea) return;
    const newContent = textarea.value.trim();
    if (!newContent) {
        alert("Post content cannot be blank or contain only spaces.");
        return;
    }

    try {
        const res = await authFetch(`/posts/${postId}`, {
            method: "PUT",
            body: JSON.stringify({ content: newContent })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to update post"));
        await loadPosts();
    } catch (err) {
        alert("Edit error: " + getErrorMessage(err.message));
    }
}

function toggleScheduleInput(postId) {
    const box = document.getElementById(`schedule-box-${postId}`);
    if (box) {
        box.style.display = box.style.display === "none" ? "block" : "none";
    }
}

async function schedulePostNow(postId) {
    const checkLi = document.getElementById(`dest-li-${postId}`);
    const sel = document.getElementById(`acc-li-${postId}`);
    const timeInput = document.getElementById(`schedule-time-${postId}`);

    if (!checkLi || !checkLi.checked || !sel || !sel.value) {
        alert("Please ensure LinkedIn is selected with a connected account to schedule.");
        return;
    }
    if (!timeInput || !timeInput.value) {
        alert("Please select a future date and time.");
        return;
    }

    const accountId = parseInt(sel.value);
    const scheduledAt = new Date(timeInput.value).toISOString();

    try {
        const res = await authFetch("/publications/schedule", {
            method: "POST",
            body: JSON.stringify({
                post_id: postId,
                linkedin_account_id: accountId,
                scheduled_at: scheduledAt
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(getErrorMessage(data, "Scheduling failed"));

        alert("Post scheduled successfully for: " + new Date(scheduledAt).toLocaleString());
        await loadPosts();
    } catch (err) {
        alert("Scheduling error: " + getErrorMessage(err.message));
    }
}

async function deletePost(postId) {
    if (!confirm("Are you sure you want to delete this draft?")) return;
    try {
        const res = await authFetch(`/posts/${postId}`, { method: "DELETE" });
        if (!res.ok) {
            const data = await res.json();
            throw new Error(getErrorMessage(data, "Delete failed"));
        }
        await loadPosts();
    } catch (err) {
        alert(getErrorMessage(err.message));
    }
}

/* =============================================================
   INIT
   ============================================================= */

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

async function loadAllData() {
    await Promise.all([
        loadAllAccounts(),
        loadLearnings(),
        loadPosts()
    ]);
}

// Attach live validation listeners once DOM is ready
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupInputLiveValidation);
} else {
    setupInputLiveValidation();
}

// Initial session check on load
checkAuthSession();
