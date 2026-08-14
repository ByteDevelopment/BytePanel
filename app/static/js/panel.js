

function refreshIcons() {
    if (window.lucide) lucide.createIcons();
}

document.addEventListener("DOMContentLoaded", function () {
    refreshIcons();

    
    var menu = document.getElementById("menu-toggle");
    var backdrop = document.getElementById("backdrop");
    if (menu) {
        menu.addEventListener("click", function () {
            document.body.classList.toggle("nav-open");
        });
    }
    if (backdrop) {
        backdrop.addEventListener("click", function () {
            document.body.classList.remove("nav-open");
        });
    }

    
    document.querySelectorAll(".flash").forEach(function (el) {
        setTimeout(function () {
            el.classList.add("hiding");
            setTimeout(function () { el.remove(); }, 350);
        }, 5000);
    });

    
    document.querySelectorAll("[data-close]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            closeModal(btn.closest(".modal"));
        });
    });

    
    document.querySelectorAll(".modal").forEach(function (m) {
        m.addEventListener("click", function (e) {
            if (e.target === m) closeModal(m);
        });
    });

    
    document.querySelectorAll("[data-confirm]").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            confirmDialog({
                title: btn.dataset.confirmTitle || "Are you sure?",
                message: btn.dataset.confirm || "",
                confirmText: btn.dataset.confirmOk || "Confirm",
                danger: true,
                onConfirm: function () {
                    submitButtonForm(btn);
                }
            });
        });
    });

    
    var okBtn = document.getElementById("confirm-ok");
    if (okBtn) {
        okBtn.addEventListener("click", function () {
            var cb = window.__confirmCb || null;
            closeModal("confirm-modal");
            if (cb) cb();
        });
    }
});

function openModal(id) {
    var m = typeof id === "string" ? document.getElementById(id) : id;
    if (!m) return;
    m.hidden = false;
    document.body.classList.add("modal-open");
    var first = m.querySelector("input, select, textarea, button:not([data-close])");
    if (first && first.focus) setTimeout(function () { first.focus(); }, 60);
}

function closeModal(id) {
    var m = typeof id === "string" ? document.getElementById(id) : id;
    if (!m) return;
    m.hidden = true;
    if (!document.querySelector(".modal:not([hidden])")) {
        document.body.classList.remove("modal-open");
    }
}

function confirmDialog(opts) {
    var m = document.getElementById("confirm-modal");
    if (!m) return;
    document.getElementById("confirm-title").textContent = opts.title || "Are you sure?";
    document.getElementById("confirm-message").textContent = opts.message || "";
    var ok = document.getElementById("confirm-ok");
    ok.textContent = opts.confirmText || "Confirm";
    ok.className = "btn " + (opts.danger ? "btn-danger" : "");
    window.__confirmCb = opts.onConfirm || null;
    openModal(m);
}

function submitButtonForm(btn) {
    var form = btn.closest("form");
    if (form) {
        form.submit();
        return;
    }
    if (btn.tagName === "A" && btn.href) {
        window.location.href = btn.href;
        return;
    }
    if (btn.dataset.url) {
        fetch(btn.dataset.url, { method: "POST" }).then(function () {
            if (btn.dataset.refresh) window.location.reload();
        });
    }
}

function setBtnLoading(btn, loading) {
    if (!btn) return;
    if (loading) btn.classList.add("loading");
    else btn.classList.remove("loading");
}


function Graph(canvasId, color) {
    this.canvas = document.getElementById(canvasId);
    this.color = color || "#6366f1";
    this.maxPoints = 60;
    this.values = [];
    if (this.canvas) this.canvas.dataset.kind = "graph";
}

Graph.prototype.push = function (v) {
    this.values.push(v === null || v === undefined ? 0 : v);
    if (this.values.length > this.maxPoints) this.values.shift();
};

Graph.prototype.draw = function () {
    if (!this.canvas) return;
    var cv = this.canvas;
    var dpr = window.devicePixelRatio || 1;
    var w = cv.clientWidth || 300;
    var h = cv.clientHeight || 84;
    cv.width = w * dpr;
    cv.height = h * dpr;
    var ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    var vals = this.values;
    var n = vals.length;
    if (n < 2) return;

    var max = Math.max.apply(null, vals.concat([1]));
    var range = max || 1;
    var step = w / (this.maxPoints - 1);
    var pad = 4;

    ctx.lineWidth = 2;
    ctx.strokeStyle = this.color;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.beginPath();
    for (var i = 0; i < n; i++) {
        var x = w - (n - 1 - i) * step;
        var y = h - pad - ((vals[i] / range) * (h - pad * 2));
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.stroke();

    var g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, this.color + "55");
    g.addColorStop(1, this.color + "00");
    ctx.lineTo(w - (n - 1) * step + step, h);
    ctx.lineTo(w - (n - 1) * step, h);
    ctx.closePath();
    ctx.fillStyle = g;
    ctx.fill();
};

window.refreshIcons = refreshIcons;
window.openModal = openModal;
window.closeModal = closeModal;
window.confirmDialog = confirmDialog;
window.Graph = Graph;
