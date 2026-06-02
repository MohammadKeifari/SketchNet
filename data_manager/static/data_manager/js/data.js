// ===== UPLOAD MODAL =====
function openUploadModal() {
    const modal = document.getElementById("uploadModal");
    if (modal) {
        modal.style.display = "flex";
        document.getElementById("modalTitle").textContent = "Upload Dataset";
        document.getElementById("datasetForm").action = "/data/upload/";
        document.getElementById("datasetForm").reset();
        document.getElementById("fileName").textContent = "";
    }
}

function closeUploadModal() {
    const modal = document.getElementById("uploadModal");
    if (modal) {
        modal.style.display = "none";
    }
}

// Close modal on overlay click
document.addEventListener("click", function (e) {
    if (e.target.id === "uploadModal") {
        closeUploadModal();
    }
});

// Close modal on escape
document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
        closeUploadModal();
    }
});
// ===== EDIT MODAL =====
function openEditModal(datasetId) {
    document.getElementById("uploadModal").style.display = "flex";
    document.getElementById("modalTitle").textContent = "Edit Dataset";
    document.getElementById("datasetForm").action = `/data/${datasetId}/edit/`;

    // Fetch existing dataset data to populate form
    fetch(`/data/${datasetId}/`)
        .then((response) => response.text())
        .then((html) => {
            // Store dataset ID for search functionality
            document.getElementById("uploadModal").dataset.datasetId =
                datasetId;

            // Show private access section if checkbox is checked
            const isPrivateCheckbox = document.getElementById("id_is_private");
            const privateAccessSection = document.getElementById(
                "privateAccessSection",
            );
            if (
                isPrivateCheckbox &&
                privateAccessSection &&
                isPrivateCheckbox.checked
            ) {
                privateAccessSection.style.display = "block";
                loadExistingAllowedUsers(datasetId);
            }
        });
}

function loadExistingAllowedUsers(datasetId) {
    // This would need an API endpoint to list current allowed users
    // For now, just set up the search functionality
    allowedUserIds = [];
    document.getElementById("allowedUsersList").innerHTML = "";
}

// Close modal on overlay click
document.addEventListener("click", function (e) {
    if (e.target.id === "uploadModal") {
        closeUploadModal();
    }
});

// ===== DRAG & DROP =====
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileNameDisplay = document.getElementById("fileName");

if (dropZone && fileInput) {
    dropZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            fileNameDisplay.textContent = `Selected: ${fileInput.files[0].name}`;
        }
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            fileNameDisplay.textContent = `Selected: ${e.dataTransfer.files[0].name}`;
        }
    });
}

// ===== PRIVATE TOGGLE =====
const privateCheckbox = document.getElementById("id_is_private");
const privateAccessSection = document.getElementById("privateAccessSection");

if (privateCheckbox && privateAccessSection) {
    privateCheckbox.addEventListener("change", () => {
        privateAccessSection.style.display = privateCheckbox.checked
            ? "block"
            : "none";
    });
}

// ===== USER SEARCH =====
const userSearchInput = document.getElementById("userSearchInput");
const userSearchResults = document.getElementById("userSearchResults");
const allowedUsersList = document.getElementById("allowedUsersList");
let allowedUserIds = [];

if (userSearchInput) {
    let searchTimeout;
    userSearchInput.addEventListener("input", () => {
        clearTimeout(searchTimeout);
        const query = userSearchInput.value.trim();

        if (query.length < 2) {
            userSearchResults.style.display = "none";
            return;
        }

        searchTimeout = setTimeout(() => {
            // Get dataset ID from the modal (works for edit, not for upload)
            const modal = document.getElementById("uploadModal");
            const datasetId = modal ? modal.dataset.datasetId : null;

            if (!datasetId) {
                // During upload - search users globally, but can't add yet
                fetch(
                    `/data/search-users-global/?q=${encodeURIComponent(query)}`,
                )
                    .then((res) => res.json())
                    .then((data) => {
                        renderSearchResults(data, null);
                    });
                return;
            }

            fetch(
                `/data/${datasetId}/search-users/?q=${encodeURIComponent(query)}`,
            )
                .then((res) => res.json())
                .then((data) => {
                    renderSearchResults(data, datasetId);
                });
        }, 300);
    });

    document.addEventListener("click", (e) => {
        if (
            userSearchResults &&
            !userSearchResults.contains(e.target) &&
            e.target !== userSearchInput
        ) {
            userSearchResults.style.display = "none";
        }
    });
}

function renderSearchResults(data, datasetId) {
    if (!userSearchResults) return;

    if (data.users && data.users.length > 0) {
        userSearchResults.innerHTML = data.users
            .map(
                (u) => `
                <div class="search-result-item" onclick="addUser('${datasetId || ""}', ${u.id}, '${u.username}')">
                    <span>${u.username}</span>
                    <span style="color: var(--text-secondary); font-size: 0.75rem;">${u.email}</span>
                </div>
            `,
            )
            .join("");
        userSearchResults.style.display = "block";
    } else {
        userSearchResults.innerHTML =
            '<div class="search-result-item">No users found</div>';
        userSearchResults.style.display = "block";
    }
}

function addUser(datasetId, userId, username) {
    if (!datasetId) {
        // Can't add during upload - store temporarily
        if (allowedUserIds.includes(userId)) return;
        allowedUserIds.push(userId);
        addUserTag(userId, username, null);
        return;
    }

    if (allowedUserIds.includes(userId)) return;

    fetch(`/data/${datasetId}/add-user/${userId}/`)
        .then((res) => res.json())
        .then((data) => {
            if (data.success) {
                allowedUserIds.push(userId);
                addUserTag(userId, username, datasetId);
                userSearchResults.style.display = "none";
                userSearchInput.value = "";
            }
        });
}

function addUserTag(userId, username, datasetId) {
    if (!allowedUsersList) return;

    const tag = document.createElement("span");
    tag.className = "allowed-user-tag";
    tag.id = `user-tag-${userId}`;
    tag.innerHTML = `${username} <button onclick="removeUser('${datasetId || ""}', ${userId})">✕</button>`;
    allowedUsersList.appendChild(tag);
}

function removeUser(datasetId, userId) {
    if (!datasetId) {
        allowedUserIds = allowedUserIds.filter((id) => id !== userId);
        const tag = document.getElementById(`user-tag-${userId}`);
        if (tag) tag.remove();
        return;
    }

    fetch(`/data/${datasetId}/remove-user/${userId}/`)
        .then((res) => res.json())
        .then((data) => {
            if (data.success) {
                allowedUserIds = allowedUserIds.filter((id) => id !== userId);
                const tag = document.getElementById(`user-tag-${userId}`);
                if (tag) tag.remove();
            }
        });
}

// ===== LIKE TOGGLE =====
function handleLikeClick(button) {
    const datasetId = button.dataset.id;
    fetch(`/data/${datasetId}/like/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
        },
    })
        .then((res) => res.json())
        .then((data) => {
            // Update all like buttons for this dataset
            document
                .querySelectorAll(
                    `.like-btn[data-id="${datasetId}"], .like-btn-large[data-id="${datasetId}"]`,
                )
                .forEach((btn) => {
                    if (data.liked) {
                        btn.innerHTML = `
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2">
                            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                        </svg>${btn.classList.contains("like-btn-large") ? " Liked" : ""}`;
                    } else {
                        btn.innerHTML = `
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                        </svg>${btn.classList.contains("like-btn-large") ? " Like" : ""}`;
                    }
                });
        });
}

document.querySelectorAll(".like-btn, .like-btn-large").forEach((btn) => {
    btn.addEventListener("click", function () {
        handleLikeClick(this);
    });
});

// ===== COPY TO CLIPBOARD =====
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showTooltip("Copied!");
    });
}

function showTooltip(message) {
    let tooltip = document.getElementById("copyTooltip");
    if (!tooltip) {
        tooltip = document.createElement("div");
        tooltip.id = "copyTooltip";
        tooltip.style.cssText = `
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--accent);
            color: #fff;
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            z-index: 9999;
            opacity: 0;
            transition: opacity 0.2s;
            pointer-events: none;
        `;
        document.body.appendChild(tooltip);
    }
    tooltip.textContent = message;
    tooltip.style.opacity = "1";
    setTimeout(() => {
        tooltip.style.opacity = "0";
    }, 1500);
}

// ===== CSRF COOKIE HELPER =====
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1),
                );
                break;
            }
        }
    }
    return cookieValue;
}

// ===== TOGGLE TEXT =====
const isPrivateCheckbox = document.getElementById("id_is_private");
const toggleText = document.getElementById("toggleText");

if (isPrivateCheckbox && toggleText) {
    isPrivateCheckbox.addEventListener("change", () => {
        toggleText.textContent = isPrivateCheckbox.checked
            ? "Private Dataset"
            : "Public Dataset";
    });
}

// ===== COVER IMAGE FILE NAME =====
const coverInput = document.getElementById("id_cover_image");
const coverFileName = document.getElementById("coverFileName");

if (coverInput && coverFileName) {
    coverInput.addEventListener("change", () => {
        if (coverInput.files.length > 0) {
            coverFileName.textContent = coverInput.files[0].name;
        } else {
            coverFileName.textContent = "No file chosen";
        }
    });
}

// ===== FORMAT HINT =====
function showFormatHint(select) {
    const hint = document.getElementById("formatHint");
    if (!hint) return;
    const format = select.value;
    if (format === "rar" || format === "zip") {
        hint.style.display = "flex";
    } else {
        hint.style.display = "none";
    }
}

// ===== CREATE DATASET MODAL =====
function openCreateModal() {
    const modal = document.getElementById("createModal");
    if (modal) {
        modal.style.display = "flex";
        document.getElementById("dsName").value = "";
        updateCreateParams(); // populate default params
    }
}

function closeCreateModal() {
    const modal = document.getElementById("createModal");
    if (modal) modal.style.display = "none";
}

// Close modal on overlay click
document.addEventListener("click", function (e) {
    if (e.target.id === "createModal") {
        closeCreateModal();
    }
});

// Handle form submit via AJAX
document
    .getElementById("createDatasetForm")
    ?.addEventListener("submit", function (e) {
        e.preventDefault();
        const form = this;
        const btn = document.getElementById("generateBtn");
        btn.disabled = true;
        btn.innerHTML = `<span>Generating...</span>`;

        const formData = new FormData(form);
        const csrfToken = formData.get("csrfmiddlewaretoken");

        fetch("/data/generate/", {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": csrfToken,
            },
        })
            .then(async (res) => {
                // Try to parse JSON, if fails, read text and throw
                const text = await res.text();
                let data;
                try {
                    data = JSON.parse(text);
                } catch (err) {
                    console.error("Server response (not JSON):", text);
                    throw new Error(
                        "Server returned an invalid response. Check console for details.",
                    );
                }

                if (!res.ok || !data.success) {
                    throw new Error(data.error || "Unknown error");
                }

                return data;
            })
            .then((data) => {
                showTooltip(
                    `Dataset "${data.name}" created! Shape: ${data.shape}`,
                );
                closeCreateModal();
                location.reload();
            })
            .catch((err) => {
                console.error("Create dataset error:", err);
                alert("Failed to create dataset: " + err.message);
            })
            .finally(() => {
                btn.disabled = false;
                btn.innerHTML = `<span>Generate</span>`;
            });
    });

// Dynamic parameters based on dataset type
function updateCreateParams() {
    const type = document.getElementById("dsType").value;
    const container = document.getElementById("paramsContainer");
    if (!container) return;

    let html = "";

    if (type === "classification") {
        html = `
            <div class="form-group"><label>Samples</label><input type="number" name="n_samples" class="form-input" value="100" min="10"></div>
            <div class="form-group"><label>Features</label><input type="number" name="n_features" class="form-input" value="2" min="1"></div>
            <div class="form-group"><label>Classes</label><input type="number" name="n_classes" class="form-input" value="2" min="2"></div>
            <div class="form-group"><label>Informative Features</label><input type="number" name="n_informative" class="form-input" value="2" min="1"></div>
            <div class="form-group"><label>Redundant Features</label><input type="number" name="n_redundant" class="form-input" value="0" min="0"></div>
            <div class="form-group"><label>Clusters per Class</label><input type="number" name="n_clusters_per_class" class="form-input" value="1" min="1"></div>
            <div class="form-group"><label>Label Noise (0-0.5)</label><input type="number" name="flip_y" class="form-input" value="0.0" step="0.01" min="0" max="0.5"></div>
            <div class="form-group"><label>Random Seed (optional)</label><input type="number" name="random_state" class="form-input" placeholder="42"></div>
        `;
    } else if (type === "regression") {
        html = `
            <div class="form-group"><label>Samples</label><input type="number" name="n_samples" class="form-input" value="100" min="10"></div>
            <div class="form-group"><label>Features</label><input type="number" name="n_features" class="form-input" value="1" min="1"></div>
            <div class="form-group"><label>Informative Features</label><input type="number" name="n_informative" class="form-input" value="1" min="1"></div>
            <div class="form-group"><label>Noise</label><input type="number" name="noise" class="form-input" value="0.1" step="0.01" min="0"></div>
            <div class="form-group"><label>Bias</label><input type="number" name="bias" class="form-input" value="0.0" step="0.1"></div>
            <div class="form-group"><label>Random Seed (optional)</label><input type="number" name="random_state" class="form-input" placeholder="42"></div>
        `;
    } else if (type === "clustering") {
        html = `
            <div class="form-group"><label>Samples</label><input type="number" name="n_samples" class="form-input" value="100" min="10"></div>
            <div class="form-group"><label>Features</label><input type="number" name="n_features" class="form-input" value="2" min="1"></div>
            <div class="form-group"><label>Centers (clusters)</label><input type="number" name="centers" class="form-input" value="3" min="1"></div>
            <div class="form-group"><label>Cluster Std Dev</label><input type="number" name="cluster_std" class="form-input" value="1.0" step="0.1" min="0.1"></div>
            <div class="form-group"><label>Random Seed (optional)</label><input type="number" name="random_state" class="form-input" placeholder="42"></div>
        `;
    }

    container.innerHTML = html;
}

// Initialize modal close on escape
document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
        closeCreateModal();
        closeUploadModal(); // also close upload if open
    }
});
