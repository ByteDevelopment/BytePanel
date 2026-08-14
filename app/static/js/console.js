

(function () {
    var SERVER_ID = window.SERVER_ID;
    var after = 0;
    var stick = true;
    var fetching = false;
    var MAX_LINES = 1200;

    var box = document.getElementById("console");
    var input = document.getElementById("cmd-input");
    var badge = document.getElementById("status-badge");
    var statusText = document.getElementById("status-text");

    

    var ANSI_BASIC = {
        30: "#9aa4b5", 31: "#f87171", 32: "#4ade80", 33: "#facc15",
        34: "#60a5fa", 35: "#c084fc", 36: "#22d3ee", 37: "#e5e7eb"
    };
    var ANSI_BRIGHT = {
        90: "#7d8590", 91: "#fca5a5", 92: "#86efac", 93: "#fde047",
        94: "#93c5fd", 95: "#d8b4fe", 96: "#67e8f9", 97: "#ffffff"
    };
    var ANSI_16 = ["#000000", "#800000", "#008000", "#808000", "#000080", "#800080", "#008080",
        "#c0c0c0", "#808080", "#ff0000", "#00ff00", "#ffff00", "#0000ff", "#ff00ff", "#00ffff", "#ffffff"];
    var CUBE = [0, 95, 135, 175, 215, 255];

    function rgb(r, g, b) { return "rgb(" + r + "," + g + "," + b + ")"; }

    function color256(n) {
        if (n < 16) return ANSI_16[n];
        if (n < 232) {
            n -= 16;
            return rgb(CUBE[Math.floor(n / 36)], CUBE[Math.floor((n % 36) / 6)], CUBE[n % 6]);
        }
        var v = 8 + (n - 232) * 10;
        return rgb(v, v, v);
    }

    function newState() {
        return {
            fg: null, bg: null, bold: false, dim: false, italic: false,
            underline: false, strike: false, reverse: false
        };
    }

    function parseSgr(params, s) {
        for (var i = 0; i < params.length; i++) {
            var code = parseInt(params[i], 10);
            if (isNaN(code)) continue;
            if (code === 0) {
                var n = newState(); s.fg = n.fg; s.bg = n.bg; s.bold = n.bold;
                s.dim = n.dim; s.italic = n.italic; s.underline = n.underline;
                s.strike = n.strike; s.reverse = n.reverse;
            } else if (code === 1) s.bold = true;
            else if (code === 2) s.dim = true;
            else if (code === 3) s.italic = true;
            else if (code === 4) s.underline = true;
            else if (code === 7) s.reverse = true;
            else if (code === 9) s.strike = true;
            else if (code === 39) s.fg = null;
            else if (code === 49) s.bg = null;
            else if (code >= 30 && code <= 37) s.fg = ANSI_BASIC[code];
            else if (code >= 90 && code <= 97) s.fg = ANSI_BRIGHT[code];
            else if (code >= 100 && code <= 107) s.bg = ANSI_BRIGHT[code - 60];
            else if (code >= 40 && code <= 47) s.bg = ANSI_16[code - 40];
            else if (code === 38 || code === 48) {
                var target = code === 38 ? "fg" : "bg";
                var mode = parseInt(params[i + 1], 10);
                if (mode === 5) {
                    s[target] = color256(parseInt(params[i + 2], 10));
                    i += 2;
                } else if (mode === 2) {
                    s[target] = rgb(
                        parseInt(params[i + 2], 10),
                        parseInt(params[i + 3], 10),
                        parseInt(params[i + 4], 10)
                    );
                    i += 4;
                }
            }
        }
    }

    function cssFor(s) {
        var out = [];
        if (s.bold) out.push("font-weight:700");
        if (s.dim) out.push("opacity:.78");
        if (s.italic) out.push("font-style:italic");
        if (s.underline) out.push("text-decoration:underline");
        if (s.strike) out.push("text-decoration:line-through");
        if (s.fg) out.push("color:" + s.fg);
        if (s.bg) out.push("background:" + s.bg);
        return out.join(";");
    }

    function escapeHtml(s) {
        return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function renderAnsi(raw) {
        // strip OSC (title etc.) and non-SGR CSI sequences
        var text = raw
            .replace(/\x1b\][^\x1b]*(\x07|\x1b\\)/g, "")
            .replace(/\x1b\[[0-9;?]*([a-zA-Z])/g, function (m, ch) {
                return ch === "m" ? m : "";
            });

        var re = /\x1b\[[0-9;]*m/g;
        var parts = text.split(re);
        var codes = text.match(re) || [];
        var html = "";
        var state = newState();
        for (var i = 0; i < parts.length; i++) {
            var part = parts[i];
            if (part) {
                var css = cssFor(state);
                html += (css ? '<span style="' + css + '">' : "") +
                    escapeHtml(part) +
                    (css ? "</span>" : "");
            }
            if (codes[i]) {
                parseSgr(codes[i].slice(2, -1).split(";"), state);
            }
        }
        return html;
    }

    /* ---------------- console logic ---------------- */

    function setStatus(status) {
        if (badge) {
            badge.className = "status-pill " + status;
            badge.classList.add(status);
        }
        if (statusText) statusText.textContent = status;
        document.querySelectorAll(".js-ctl").forEach(function (b) {
            var act = b.dataset.action;
            if (act === "start") b.disabled = status === "running";
            if (act === "stop" || act === "kill") b.disabled = status !== "running";
        });
    }

    function pruneLines() {
        var excess = box.children.length - MAX_LINES;
        if (excess > 0) box.replaceChildren.apply(box, Array.from(box.children).slice(excess));
    }

    function onScroll() {
        var dist = box.scrollHeight - box.scrollTop - box.clientHeight;
        stick = dist < 48;
    }

    function applyBatch(lines) {
        if (!lines.length) return;
        var frag = document.createDocumentFragment();
        var text;
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];
            if (line.id <= after) continue;
            var div = document.createElement("div");
            div.className = "line";
            text = line.text;
            if (text.indexOf("> ") === 0) div.classList.add("cmd");
            div.innerHTML = renderAnsi(text.replace(/\n$/, ""));
            frag.appendChild(div);
            after = line.id;
        }
        box.appendChild(frag);
        pruneLines();
        if (stick) box.scrollTop = box.scrollHeight;
    }

    async function poll() {
        if (fetching) return;
        fetching = true;
        try {
            var res = await fetch("/servers/" + SERVER_ID + "/api/logs?after=" + after);
            var data = await res.json();
            setStatus(data.status);
            applyBatch(data.logs);
        } catch (e) { /* panel unreachable */ }
        fetching = false;
    }

    function clearConsole() {
        after = 0;
        while (box.firstChild) box.removeChild(box.firstChild);
        stick = true;
    }

    async function send() {
        var cmd = input.value.trim();
        if (!cmd) return;
        await fetch("/servers/" + SERVER_ID + "/api/command", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command: cmd })
        });
        input.value = "";
        stick = true;
        box.scrollTop = box.scrollHeight;
        poll();
    }

    function doAction(btn, action) {
        setBtnLoading(btn, true);
        fetch("/servers/" + SERVER_ID + "/" + action, { method: "POST" })
            .then(function () {
                if (action === "start") clearConsole();
                setTimeout(function () {
                    setBtnLoading(btn, false);
                    poll();
                }, 1100);
            })
            .catch(function () { setBtnLoading(btn, false); });
    }

    document.getElementById("btn-clear").addEventListener("click", clearConsole);
    document.getElementById("btn-send").addEventListener("click", send);
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") send(); });
    box.addEventListener("scroll", onScroll);

    document.querySelectorAll(".js-ctl").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            var action = btn.dataset.action;
            if (action === "kill") {
                confirmDialog({
                    title: "Kill server?",
                    message: "Force-kill the server? Running processes will be terminated immediately.",
                    confirmText: "Kill",
                    danger: true,
                    onConfirm: function () { doAction(btn, "kill"); }
                });
            } else {
                doAction(btn, action);
            }
        });
    });

    clearConsole();
    poll();
    setInterval(poll, 1500);
})();
