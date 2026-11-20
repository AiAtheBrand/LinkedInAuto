const API_URL =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:8000"
        : "https://linkedinauto-edi2.onrender.com";


let currentUser = null;
let connectedAccounts = [];
let authMode = "login"; // 'login' or 'register'

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

    // Don't force application/json if sending FormData (browser needs to set multipart boundary)
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
            // Token expired or invalid
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
    const email = document.getElementById("auth-email").value.trim();
    const password = document.getElementById("auth-password").value;
    const fullName = document.getElementById("auth-fullname").value.trim();
    const msg = document.getElementById("auth-message");
    const submitBtn = document.getElementById("auth-submit-btn");

    msg.textContent = "";
    submitBtn.disabled = true;

    try {
        if (authMode === "register") {
            // Register
            const res = await fetch(`${API_URL}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password, full_name: fullName || null })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Registration failed");

            // Auto-login after registration
            const loginRes = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });
            const loginData = await loginRes.json();
            if (!loginRes.ok) throw new Error(loginData.detail || "Login failed");

            setToken(loginData.access_token);
            currentUser = loginData.user;
        } else {
            // Login
            const res = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Invalid credentials");

            setToken(data.access_token);
            currentUser = data.user;
        }

        updateUI();
        loadAllData();
    } catch (err) {
        msg.style.color = "var(--danger)";
        msg.textContent = err.message;
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
    connectedAccounts = [];
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
   LINKEDIN ACCOUNTS & OAUTH
   ============================================================= */

async function loadLinkedInAccounts() {
    const listEl = document.getElementById("linkedin-accounts-list");
    try {
        const res = await authFetch("/linkedin/accounts");
        if (!res.ok) throw new Error("Failed to load accounts");
        connectedAccounts = await res.json();

        listEl.innerHTML = "";
        if (connectedAccounts.length === 0) {
            listEl.innerHTML = `<p class="empty-text">No LinkedIn accounts connected. Click "+ Connect LinkedIn Account" above.</p>`;
            return;
        }

        connectedAccounts.forEach(acc => {
            const pill = document.createElement("div");
            pill.className = "account-pill";
            pill.innerHTML = `
                <div class="account-avatar">in</div>
                <div class="account-info">
                    <h4>${acc.name}</h4>
                    <p>${acc.email || acc.linkedin_member_urn}</p>
                </div>
                <button class="btn btn-danger btn-sm" onclick="disconnectAccount(${acc.id})">Disconnect</button>
            `;
            listEl.appendChild(pill);
        });
    } catch (err) {
        listEl.innerHTML = `<p class="empty-text">${err.message}</p>`;
    }
}

async function startLinkedInOAuth() {
    try {
        const res = await authFetch("/linkedin/oauth/authorize");
        if (!res.ok) throw new Error("Failed to start OAuth");
        const data = await res.json();

        // Open LinkedIn in a new tab/window
        const authWindow = window.open(data.authorization_url, "_blank", "width=600,height=700");

        // Poll or listen for completion
        const timer = setInterval(async () => {
            if (authWindow && authWindow.closed) {
                clearInterval(timer);
                await loadLinkedInAccounts();
                await loadPosts();
            }
        }, 1500);
    } catch (err) {
        alert("OAuth initiation failed: " + err.message);
    }
}

async function disconnectAccount(accountId) {
    if (!confirm("Are you sure you want to disconnect this LinkedIn account?")) return;
    try {
        const res = await authFetch(`/linkedin/accounts/${accountId}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Failed to disconnect");
        await loadLinkedInAccounts();
        await loadPosts();
    } catch (err) {
        alert(err.message);
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

    msg.textContent = "";
    spinner.style.display = "inline-block";
    submitBtn.disabled = true;

    const payload = {
        topic: document.getElementById("topic").value.trim(),
        category: document.getElementById("category").value.trim(),
        problem: document.getElementById("problem").value.trim() || null,
        what_i_learned: document.getElementById("what_i_learned").value.trim(),
        project: document.getElementById("project").value.trim() || null,
        lesson: document.getElementById("lesson").value.trim() || null
    };

    try {
        // 1. Save Learning
        const createRes = await authFetch("/learning/", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        const createdLearning = await createRes.json();
        if (!createRes.ok) throw new Error(createdLearning.detail || "Failed to save learning note");

        // 2. Generate Post via AI
        const genRes = await authFetch(`/posts/generate/${createdLearning.id}`, { method: "POST" });
        const post = await genRes.json();
        if (!genRes.ok) throw new Error(post.detail || "Failed to generate AI post");

        msg.style.color = "var(--success)";
        msg.textContent = "Learning saved and AI LinkedIn draft generated successfully!";
        form.reset();

        await loadLearnings();
        await loadPosts();
    } catch (err) {
        msg.style.color = "var(--danger)";
        msg.textContent = err.message;
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
        if (!res.ok) throw new Error("Failed to load learning entries");
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
        container.innerHTML = `<p class="empty-text">${err.message}</p>`;
    }
}

async function generateAdditionalPost(learningId) {
    try {
        const res = await authFetch(`/posts/generate/${learningId}`, { method: "POST" });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Generation failed");
        }
        await loadPosts();
    } catch (err) {
        alert("Failed to generate post: " + err.message);
    }
}

async function deleteLearning(learningId) {
    if (!confirm("Delete this learning entry? Associated draft posts will remain.")) return;
    try {
        const res = await authFetch(`/learning/${learningId}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Delete failed");
        await loadLearnings();
    } catch (err) {
        alert(err.message);
    }
}

/* =============================================================
   POSTS & PUBLICATIONS
   ============================================================= */

async function loadPosts() {
    const container = document.getElementById("posts-container");
    const countBadge = document.getElementById("posts-count");

    try {
        const [postsRes, pubsRes] = await Promise.all([
            authFetch("/posts/"),
            authFetch("/publications/")
        ]);

        if (!postsRes.ok) throw new Error("Failed to load posts");
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

            let accountOptions = connectedAccounts.map(
                acc => `<option value="${acc.id}">${escapeHtml(acc.name)}</option>`
            ).join("");

            let pubDetailsHtml = "";
            if (postPubs.length > 0) {
                pubDetailsHtml = `<div style="margin-top: 10px; font-size: 0.8rem; background: #fafafa; padding: 8px; border-radius: 6px;">
                    <strong>Publications:</strong>
                    ${postPubs.map(p => `
                        <div style="margin-top: 4px;">
                            • Status: <span class="status-pill status-${p.status}">${p.status}</span>
                            ${p.linkedin_post_urn ? `URN: <code>${p.linkedin_post_urn}</code>` : ""}
                            ${p.error_message ? `<span style="color: var(--danger);">${escapeHtml(p.error_message)}</span>` : ""}
                        </div>
                    `).join("")}
                </div>`;
            }

            const imageHtml = post.image_url ? `
                <div class="post-media-container">
                    <img src="${API_URL}${post.image_url}" class="post-media-img" alt="Attached post image" />
                </div>
            ` : '';

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

                ${imageHtml}

                <div style="margin: 8px 0 12px 0;">
                    <label class="btn btn-secondary btn-sm btn-upload-label">
                        <span>📷 ${post.image_url ? "Change Image" : "Attach Image"}</span>
                        <input type="file" accept="image/png, image/jpeg, image/gif, image/webp" onchange="uploadPostImage(${post.id}, this.files[0])" />
                    </label>
                </div>

                ${pubDetailsHtml}

                <div class="item-actions">
                    ${connectedAccounts.length > 0 ? `
                        <select id="acc-select-${post.id}" style="width: auto; padding: 4px 8px; font-size: 0.8rem;">
                            ${accountOptions}
                        </select>
                        <button class="btn btn-primary btn-sm" onclick="publishPostNow(${post.id})">Publish to LinkedIn</button>
                        <button class="btn btn-secondary btn-sm" onclick="toggleScheduleInput(${post.id})">Schedule</button>
                    ` : `<span style="font-size: 0.8rem; color: var(--text-secondary);">Connect a LinkedIn account above to publish</span>`}
                    <button class="btn btn-danger btn-sm" style="margin-left: auto;" onclick="deletePost(${post.id})">Delete</button>
                </div>

                <div id="schedule-box-${post.id}" style="display: none; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #ddd;">
                    <label style="font-size: 0.8rem;">Select publication date & time:</label>
                    <input type="datetime-local" id="schedule-time-${post.id}" style="width: auto; margin-right: 8px;">
                    <button class="btn btn-primary btn-sm" onclick="schedulePostNow(${post.id})">Confirm Schedule</button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        container.innerHTML = `<p class="empty-text">${err.message}</p>`;
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
        alert("Post content cannot be empty.");
        return;
    }

    try {
        const res = await authFetch(`/posts/${postId}`, {
            method: "PUT",
            body: JSON.stringify({ content: newContent })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to update post");
        await loadPosts();
    } catch (err) {
        alert("Edit error: " + err.message);
    }
}

async function uploadPostImage(postId, file) {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await authFetch(`/posts/${postId}/image`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Image upload failed");
        await loadPosts();
    } catch (err) {
        alert("Upload error: " + err.message);
    }
}

async function publishPostNow(postId) {
    const select = document.getElementById(`acc-select-${postId}`);
    if (!select) return;
    const accountId = parseInt(select.value);

    try {
        const res = await authFetch("/publications/publish", {
            method: "POST",
            body: JSON.stringify({
                post_id: postId,
                linkedin_account_id: accountId
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Publication failed");

        alert("Post publication submitted! Status: " + data.status);
        await loadPosts();
    } catch (err) {
        alert("Publish error: " + err.message);
    }
}

function toggleScheduleInput(postId) {
    const box = document.getElementById(`schedule-box-${postId}`);
    if (box) {
        box.style.display = box.style.display === "none" ? "block" : "none";
    }
}

async function schedulePostNow(postId) {
    const select = document.getElementById(`acc-select-${postId}`);
    const timeInput = document.getElementById(`schedule-time-${postId}`);
    if (!select || !timeInput || !timeInput.value) {
        alert("Please select a future date and time.");
        return;
    }

    const accountId = parseInt(select.value);
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
        if (!res.ok) throw new Error(data.detail || "Scheduling failed");

        alert("Post scheduled successfully for: " + new Date(scheduledAt).toLocaleString());
        await loadPosts();
    } catch (err) {
        alert("Scheduling error: " + err.message);
    }
}

async function deletePost(postId) {
    if (!confirm("Are you sure you want to delete this draft?")) return;
    try {
        const res = await authFetch(`/posts/${postId}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Delete failed");
        await loadPosts();
    } catch (err) {
        alert(err.message);
    }
}

/* =============================================================
   INIT
   ============================================================= */

function escapeHtml(text) {
    if (!text) return "";
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

async function loadAllData() {
    await Promise.all([
        loadLinkedInAccounts(),
        loadLearnings(),
        loadPosts()
    ]);
}

// Initial session check on load
checkAuthSession();
