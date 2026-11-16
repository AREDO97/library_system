from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User
from app.decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/users")
@login_required
@role_required("super_admin")
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
@role_required("super_admin")
def update_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")

    if user.id == current_user.id:
        flash("You cannot change your own role.", "warning")
        return redirect(url_for("admin.users"))

    if new_role not in ("student", "librarian", "super_admin"):
        flash("Invalid role selected.", "danger")
        return redirect(url_for("admin.users"))

    user.role = new_role
    db.session.commit()
    flash(f"Updated {user.name}'s role to {new_role}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-status", methods=["POST"])
@login_required
@role_required("super_admin")
def toggle_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate yourself.", "warning")
        return redirect(url_for("admin.users"))

    user.is_active = not user.is_active
    db.session.commit()
    state = "activated" if user.is_active else "deactivated"
    flash(f"Account for {user.name} has been {state}.", "info")
    return redirect(url_for("admin.users"))