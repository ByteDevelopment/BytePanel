

(function () {
    var SERVER_ID = window.SERVER_ID;

    var graphs = {
        cpu: new Graph("chart-cpu", "#6366f1"),
        mem: new Graph("chart-mem", "#22d3ee"),
        disk: new Graph("chart-disk", "#eab308"),
        net: new Graph("chart-net", "#22c55e")
    };
    var sparks = {
        cpu: new Graph("spark-cpu", "#a855f7"),
        mem: new Graph("spark-mem", "#22d3ee"),
        disk: new Graph("spark-disk", "#eab308"),
        net: new Graph("spark-net", "#22c55e")
    };
    
    Object.keys(graphs).forEach(function (k) {
        graphs[k].push(0);
        sparks[k].push(0);
    });

    function fmtNum(v) { return v === null || v === undefined ? "—" : v; }
    function setText(id, t) {
        var el = document.getElementById(id);
        if (el) el.textContent = t;
    }
    function setStatus(status) {
        var badge = document.getElementById("status-badge");
        var text = document.getElementById("status-text");
        if (badge) {
            badge.className = "status-pill " + status;
            badge.classList.remove("running", "offline", "restarting");
            badge.classList.add(status);
        }
        if (text) text.textContent = status;
        setText("stat-status", status === "running" ? "Online" : "Offline");
        document.querySelectorAll(".js-ctl").forEach(function (b) {
            var act = b.dataset.action;
            b.disabled = (act === "start" || act === "stop" || act === "kill") && (status === "running") === (act === "start");
        });
    }

    var LIMITS = {
        mem: { used: 0, limit: window.SERVER_MEM_LIMIT || 0 },
        cpu: { used: 0, limit: window.SERVER_CPU_LIMIT || 0 },
        disk: { used: 0, limit: window.SERVER_DISK_LIMIT || 0 }
    };

    function updateLimit(id, valEl, barEl, used, limit) {
        if (!limit) return;
        var pct = Math.min(used / limit * 100, 100);
        setText(valEl, Math.round(used) + " / " + limit + " " + (id === "cpu" ? "%" : "MB"));
        barEl.style.setProperty("--pct", pct + "%");
        var fill = barEl.querySelector("span");
        fill.style.width = pct + "%";
        barEl.classList.remove("warn", "over");
        if (pct >= 100) barEl.classList.add("over");
        else if (pct >= 80) barEl.classList.add("warn");
    }

    function applyLimits(s) {
        if (!s.folder && !s.memory) return;
        updateLimit("mem", "lim-mem-val", document.getElementById("lim-mem-bar"),
            s.memory ? s.memory.used_mb : 0, LIMITS.mem.limit);
        updateLimit("cpu", "lim-cpu-val", document.getElementById("lim-cpu-bar"),
            s.cpu == null ? 0 : s.cpu, LIMITS.cpu.limit);
        updateLimit("disk", "lim-disk-val", document.getElementById("lim-disk-bar"),
            s.folder ? s.folder.used_mb : 0, LIMITS.disk.limit);
        var meta = document.getElementById("limit-meta");
        if (meta && s.limit) {
            meta.innerHTML = "<span style=\"color:var(--orange)\">Over limit (" +
                escapeHtml(s.limit.reason) + ") \u2014 warning " + s.limit.strikes +
                "/" + s.limit.max + ", server will be stopped if it continues.</span>";
        } else if (meta) {
            meta.textContent = "Servers that stay above their limits for a sustained period are stopped automatically (5 warnings first).";
        }
    }

    function escapeHtml(s) {
        return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function drawAll() {
        Object.keys(graphs).forEach(function (k) { graphs[k].draw(); sparks[k].draw(); });
    }

    async function poll() {
        try {
            var res = await fetch("/servers/" + SERVER_ID + "/api/stats");
            var s = await res.json();
            setStatus(s.status);
            applyLimits(s);

            // uptime
            setText("uptime-val", s.uptime ? Math.floor(s.uptime / 60) + " min" : "");

            // players
            setText("stat-players", s.players == null ? "—" : s.players);

            // cpu
            var cpu = s.cpu == null ? null : s.cpu;
            setText("stat-cpu", cpu == null ? "—" : cpu.toFixed(1) + "%");
            setText("g-cpu", cpu == null ? "—" : cpu.toFixed(1) + "%");
            graphs.cpu.push(cpu == null ? 0 : cpu);
            sparks.cpu.push(cpu == null ? 0 : cpu);

            // memory
            if (s.memory) {
                var memPct = (s.memory.used_mb / s.memory.total_mb) * 100;
                setText("stat-mem", Math.round(s.memory.used_mb) + " MB");
                setText("stat-mem-sub", "of " + Math.round(s.memory.total_mb) + " MB");
                setText("g-mem", memPct.toFixed(1) + "%");
                graphs.mem.push(memPct);
                sparks.mem.push(memPct);
            } else {
                setText("stat-mem", "—");
                setText("stat-mem-sub", "");
                setText("g-mem", "—");
                graphs.mem.push(0);
                sparks.mem.push(0);
            }

            // disk
            if (s.disk) {
                setText("stat-disk", s.disk.used_pct.toFixed(1) + "%");
                setText("stat-disk-sub", s.disk.free_mb.toFixed(0) + " MB free");
                setText("g-disk", s.disk.used_pct.toFixed(1) + "%");
                graphs.disk.push(s.disk.used_pct);
                sparks.disk.push(s.disk.used_pct);
            } else {
                setText("stat-disk", "—");
                setText("stat-disk-sub", "");
                setText("g-disk", "—");
                graphs.disk.push(0);
                sparks.disk.push(0);
            }

            // network
            if (s.network) {
                setText("stat-net", "↓ " + s.network.rx_kbs.toFixed(1) + " KB/s");
                setText("stat-net-sub", "↑ " + s.network.tx_kbs.toFixed(1) + " KB/s");
                setText("g-net", (s.network.rx_kbs + s.network.tx_kbs).toFixed(1) + " KB/s");
                graphs.net.push(s.network.rx_kbs + s.network.tx_kbs);
                sparks.net.push(s.network.rx_kbs + s.network.tx_kbs);
            } else {
                setText("stat-net", "—");
                setText("stat-net-sub", "");
                setText("g-net", "—");
                graphs.net.push(0);
                sparks.net.push(0);
            }

            drawAll();
        } catch (e) { /* panel unreachable */ }
    }

    // control buttons
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

    function doAction(btn, action) {
        setBtnLoading(btn, true);
        fetch("/servers/" + SERVER_ID + "/" + action, { method: "POST" })
            .then(function () {
                setTimeout(function () {
                    setBtnLoading(btn, false);
                    poll();
                }, 1200);
            })
            .catch(function () { setBtnLoading(btn, false); });
    }

    poll();
    setInterval(poll, 3000);
    window.addEventListener("resize", drawAll);
})();
