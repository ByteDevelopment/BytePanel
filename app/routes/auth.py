from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..audit import audit
from ..storage import db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = db.get_user_by_username(username)
        if user and user.check_password(password):
            login_user(user)
            audit("auth.login", f"{username} logged in", username=username)
            next_url = request.args.get("next")
            return redirect(next_url or url_for("main.dashboard"))

        audit("auth.login", f"failed login attempt for {username}", level="warn")
        flash("Invalid username or password.", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    audit("auth.logout", f"{current_user.username} logged out")
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if db.count_users() > 0:
        abort(404)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not password:
            flash("Username and password are required.", "error")
        elif db.get_user_by_username(username):
            flash("That username is already taken.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            user = db.add_user(username=username, password_hash="", is_admin=True)
            user.set_password(password)
            db.save_user(user)
            login_user(user)
            audit("user.create", f"admin account {username} registered", username=username)
            flash("Admin account created. Welcome!", "success")
            return redirect(url_for("main.dashboard"))

    return render_template("register.html")
