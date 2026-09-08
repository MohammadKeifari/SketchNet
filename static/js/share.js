(function () {
    const overlay = document.getElementById("shareOverlay");
    if (!overlay) return;

    const urlInput = document.getElementById("shareUrlInput");
    const caption = document.getElementById("shareCaption");
    const mailto = document.getElementById("shareMailto");
    const twitter = document.getElementById("shareTwitter");
    const linkedin = document.getElementById("shareLinkedin");
    const nativeBtn = document.getElementById("shareNative");
    const ownerBox = document.getElementById("shareOwner");
    const privateToggle = document.getElementById("sharePrivateToggle");
    const privateText = document.getElementById("sharePrivateText");
    const viewLabel = document.getElementById("shareViewLabel");
    const viewInvite = document.getElementById("shareViewInvite");
    const forkRow = document.getElementById("shareForkRow");
    const forkToggle = document.getElementById("shareForkToggle");
    const forkText = document.getElementById("shareForkText");
    const forkInvite = document.getElementById("shareForkInvite");
    const viewSearch = document.getElementById("shareViewSearch");
    const forkSearch = document.getElementById("shareForkSearch");
    const viewResults = document.getElementById("shareViewResults");
    const forkResults = document.getElementById("shareForkResults");
    const viewChips = document.getElementById("shareViewChips");
    const forkChips = document.getElementById("shareForkChips");

    let state = {
        kind: "",
        id: "",
        owner: false,
        viewIds: {},
        forkIds: {},
        datasetIds: {},
    };

    function csrf() {
        const cookie = document.cookie
            .split("; ")
            .find((row) => row.startsWith("csrftoken="));
        return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
    }

    function postForm(url, body) {
        return fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrf(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: body,
        }).then((res) => res.json().then((data) => ({ ok: res.ok, data })));
    }

    function toast(message) {
        let tip = document.getElementById("copyTooltip");
        if (!tip) {
            tip = document.createElement("div");
            tip.id = "copyTooltip";
            tip.style.cssText =
                "position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:var(--accent);color:#fff;padding:8px 20px;border-radius:20px;font-size:0.85rem;font-weight:600;z-index:9999;opacity:0;transition:opacity 0.2s;pointer-events:none;";
            document.body.appendChild(tip);
        }
        tip.textContent = message;
        tip.style.opacity = "1";
        setTimeout(() => {
            tip.style.opacity = "0";
        }, 1500);
    }

    function encodeShare(title, url) {
        const text = title + "\n" + url;
        mailto.href =
            "mailto:?subject=" +
            encodeURIComponent(title) +
            "&body=" +
            encodeURIComponent(text);
        twitter.href =
            "https://x.com/intent/tweet?text=" +
            encodeURIComponent(title) +
            "&url=" +
            encodeURIComponent(url);
        linkedin.href =
            "https://www.linkedin.com/sharing/share-offsite/?url=" +
            encodeURIComponent(url);
    }

    function isPrivate() {
        if (state.kind === "dataset") return privateToggle.checked;
        return privateToggle.checked;
    }

    function setCaption() {
        caption.textContent = isPrivate()
            ? "Only you and people you invite can open this link."
            : "Anyone with the link can view this.";
    }

    function setToggleLabels() {
        if (state.kind === "dataset") {
            viewLabel.textContent = "Private dataset";
            privateText.textContent = privateToggle.checked ? "Private" : "Public";
            forkRow.hidden = true;
            viewInvite.classList.toggle("is-visible", privateToggle.checked);
            forkInvite.classList.remove("is-visible");
        } else {
            viewLabel.textContent = "Who can view";
            privateText.textContent = privateToggle.checked ? "Private" : "Public";
            forkText.textContent = forkToggle.checked ? "Private" : "Public";
            forkRow.hidden = false;
            viewInvite.classList.toggle("is-visible", privateToggle.checked);
            forkInvite.classList.toggle("is-visible", forkToggle.checked);
        }
        setCaption();
    }

    function renderChips(container, map, kind) {
        container.replaceChildren();
        Object.keys(map).forEach((id) => {
            const chip = document.createElement("span");
            chip.className = "share-chip";
            const name = document.createElement("span");
            name.textContent = map[id];
            const btn = document.createElement("button");
            btn.type = "button";
            btn.setAttribute("aria-label", "Remove");
            btn.textContent = "✕";
            btn.addEventListener("click", () => removeUser(kind, Number(id)));
            chip.append(name, btn);
            container.append(chip);
        });
    }

    function renderAllChips() {
        if (state.kind === "dataset") {
            renderChips(viewChips, state.datasetIds, "dataset");
            forkChips.replaceChildren();
        } else {
            renderChips(viewChips, state.viewIds, "view");
            renderChips(forkChips, state.forkIds, "fork");
        }
    }

    function loadPeople() {
        if (!state.owner) return Promise.resolve();
        if (state.kind === "model") {
            return fetch("/models/" + encodeURIComponent(state.id) + "/access/")
                .then((res) => res.json())
                .then((data) => {
                    state.viewIds = {};
                    state.forkIds = {};
                    (data.users || []).forEach((u) => {
                        if (u.can_view) state.viewIds[u.user_id] = u.username;
                        if (u.can_fork) state.forkIds[u.user_id] = u.username;
                    });
                    renderAllChips();
                });
        }
        return fetch("/data/" + encodeURIComponent(state.id) + "/access/")
            .then((res) => res.json())
            .then((data) => {
                state.datasetIds = {};
                (data.users || []).forEach((u) => {
                    state.datasetIds[u.id] = u.username;
                });
                renderAllChips();
            });
    }

    function saveVisibility() {
        if (!state.owner) return;
        if (state.kind === "dataset") {
            return postForm(
                "/data/" + encodeURIComponent(state.id) + "/share/",
                "is_private=" + (privateToggle.checked ? "true" : "false"),
            );
        }
        return postForm(
            "/models/" + encodeURIComponent(state.id) + "/share/",
            "view_access=" +
                (privateToggle.checked ? "private" : "public") +
                "&fork_access=" +
                (forkToggle.checked ? "private" : "public"),
        );
    }

    function postModelAccess(userId, canView, canFork) {
        return postForm(
            "/models/" + encodeURIComponent(state.id) + "/access/",
            "user_id=" +
                userId +
                "&can_view=" +
                canView +
                "&can_fork=" +
                canFork,
        );
    }

    function addUser(kind, user) {
        if (state.kind === "dataset") {
            return postForm(
                "/data/" +
                    encodeURIComponent(state.id) +
                    "/add-user/" +
                    user.id +
                    "/",
                "",
            ).then((result) => {
                if (result.ok && result.data.success) {
                    state.datasetIds[user.id] = user.username;
                    renderAllChips();
                }
            });
        }
        const inView = Boolean(state.viewIds[user.id]) || kind === "view";
        const inFork = Boolean(state.forkIds[user.id]) || kind === "fork";
        return postModelAccess(user.id, inView, inFork).then((result) => {
            if (result.ok && result.data.success) {
                if (inView) state.viewIds[user.id] = user.username;
                if (inFork) state.forkIds[user.id] = user.username;
                renderAllChips();
            }
        });
    }

    function removeUser(kind, userId) {
        if (state.kind === "dataset") {
            return postForm(
                "/data/" +
                    encodeURIComponent(state.id) +
                    "/remove-user/" +
                    userId +
                    "/",
                "",
            ).then((result) => {
                if (result.ok && result.data.success) {
                    delete state.datasetIds[userId];
                    renderAllChips();
                }
            });
        }
        const keepView = kind !== "view" && Boolean(state.viewIds[userId]);
        const keepFork = kind !== "fork" && Boolean(state.forkIds[userId]);
        const finish = () => {
            if (kind === "view") delete state.viewIds[userId];
            if (kind === "fork") delete state.forkIds[userId];
            renderAllChips();
        };
        if (!keepView && !keepFork) {
            return postForm(
                "/models/" +
                    encodeURIComponent(state.id) +
                    "/access/" +
                    userId +
                    "/remove/",
                "",
            ).then((result) => {
                if (result.ok && result.data.success) finish();
            });
        }
        return postModelAccess(userId, keepView, keepFork).then((result) => {
            if (result.ok && result.data.success) finish();
        });
    }

    function bindSearch(input, resultsEl, kind) {
        let timer = null;
        input.addEventListener("input", () => {
            clearTimeout(timer);
            const q = input.value.trim();
            if (q.length < 2) {
                resultsEl.style.display = "none";
                resultsEl.replaceChildren();
                return;
            }
            timer = setTimeout(() => {
                const path =
                    state.kind === "dataset"
                        ? "/data/" + encodeURIComponent(state.id) + "/search-users/"
                        : "/models/" + encodeURIComponent(state.id) + "/search-users/";
                fetch(path + "?q=" + encodeURIComponent(q))
                    .then((res) => res.json())
                    .then((data) => {
                        resultsEl.replaceChildren();
                        (data.users || []).forEach((u) => {
                            const btn = document.createElement("button");
                            btn.type = "button";
                            btn.className = "share-search-item";
                            btn.textContent = u.username + (u.email ? " · " + u.email : "");
                            btn.addEventListener("click", () => {
                                const role =
                                    state.kind === "dataset" ? "dataset" : kind;
                                addUser(role, u);
                                input.value = "";
                                resultsEl.style.display = "none";
                                resultsEl.replaceChildren();
                            });
                            resultsEl.append(btn);
                        });
                        resultsEl.style.display = data.users && data.users.length
                            ? "block"
                            : "none";
                    });
            }, 200);
        });
    }

    function openFrom(trigger) {
        state.kind = trigger.dataset.shareKind || "";
        state.id = trigger.dataset.shareId || "";
        state.owner = trigger.dataset.shareOwner === "1";
        const title = trigger.dataset.shareTitle || "SketchNet";
        let url = trigger.dataset.shareUrl || window.location.href;
        if (url.startsWith("/")) url = window.location.origin + url;
        urlInput.value = url;
        encodeShare(title, url);
        nativeBtn.style.display =
            typeof navigator.share === "function" ? "inline-flex" : "none";
        nativeBtn.dataset.shareTitle = title;

        if (state.kind === "dataset") {
            privateToggle.checked = trigger.dataset.sharePrivate === "1";
        } else {
            privateToggle.checked = trigger.dataset.shareView === "private";
            forkToggle.checked = trigger.dataset.shareFork === "private";
        }
        ownerBox.classList.toggle("is-visible", state.owner);
        setToggleLabels();
        overlay.classList.add("is-open");
        if (state.owner) loadPeople();
        else {
            state.viewIds = {};
            state.forkIds = {};
            state.datasetIds = {};
            renderAllChips();
        }
    }

    function close() {
        overlay.classList.remove("is-open");
        viewResults.style.display = "none";
        forkResults.style.display = "none";
    }

    document.addEventListener(
        "click",
        (event) => {
            const trigger = event.target.closest(".share-trigger");
            if (trigger) {
                event.preventDefault();
                event.stopPropagation();
                openFrom(trigger);
            }
        },
        true,
    );

    document.getElementById("shareClose").addEventListener("click", close);
    overlay.addEventListener("click", (event) => {
        if (event.target === overlay) close();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && overlay.classList.contains("is-open")) close();
    });

    document.getElementById("shareCopy").addEventListener("click", () => {
        const value = urlInput.value;
        const copied = () => toast("Copied!");
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(value).then(copied).catch(() => {
                urlInput.select();
                document.execCommand("copy");
                copied();
            });
        } else {
            urlInput.select();
            document.execCommand("copy");
            copied();
        }
    });

    nativeBtn.addEventListener("click", () => {
        if (typeof navigator.share !== "function") return;
        navigator.share({
            title: nativeBtn.dataset.shareTitle || "SketchNet",
            text: urlInput.value,
            url: urlInput.value,
        });
    });

    privateToggle.addEventListener("change", () => {
        setToggleLabels();
        saveVisibility();
    });
    forkToggle.addEventListener("change", () => {
        setToggleLabels();
        saveVisibility();
    });

    bindSearch(viewSearch, viewResults, "view");
    bindSearch(forkSearch, forkResults, "fork");
})();
