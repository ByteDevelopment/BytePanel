

document.addEventListener("DOMContentLoaded", function () {
    var rows = Array.prototype.slice.call(document.querySelectorAll("#file-tbody .file-row"));
    var search = document.getElementById("file-search");

    if (search) {
        search.addEventListener("input", function () {
            var q = search.value.trim().toLowerCase();
            rows.forEach(function (row) {
                var name = (row.dataset.name || "").toLowerCase();
                row.style.display = !q || name.indexOf(q) !== -1 ? "" : "none";
            });
        });
    }

    function submitForm(action, data) {
        var form = document.createElement("form");
        form.method = "post";
        form.action = action;
        Object.keys(data).forEach(function (k) {
            var inp = document.createElement("input");
            inp.type = "hidden";
            inp.name = k;
            inp.value = data[k];
            form.appendChild(inp);
        });
        document.body.appendChild(form);
        form.submit();
    }

    document.getElementById("btn-upload").addEventListener("click", function () {
        openModal("modal-upload");
    });

    function openNew(kind, title) {
        document.getElementById("new-kind").value = kind;
        document.getElementById("new-title").textContent = title;
        document.getElementById("new-name").value = "";
        openModal("modal-new");
    }
    document.getElementById("btn-new-file").addEventListener("click", function () {
        openNew("file", "Create file");
    });
    document.getElementById("btn-new-dir").addEventListener("click", function () {
        openNew("dir", "Create folder");
    });

    document.querySelectorAll("[data-action='rename']").forEach(function (btn) {
        btn.addEventListener("click", function () {
            document.getElementById("rename-path").value = btn.dataset.path;
            document.getElementById("rename-name").value = btn.dataset.name;
            openModal("modal-rename");
        });
    });

    document.querySelectorAll("[data-action='delete']").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            confirmDialog({
                title: "Delete " + btn.dataset.name + "?",
                message: "This will permanently delete \"" + btn.dataset.path + "\". This cannot be undone.",
                confirmText: "Delete",
                danger: true,
                onConfirm: function () {
                    submitForm(btn.dataset.form || "", { path: btn.dataset.path });
                }
            });
        });
    });
});
