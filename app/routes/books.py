from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db
from app.models import Book, User, BorrowRecord
from app.decorators import role_required

books_bp = Blueprint("books", __name__)

@books_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    query = Book.query

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Book.title.ilike(term),
                Book.author.ilike(term),
                Book.isbn.ilike(term),
                Book.shelf_location.ilike(term),
                Book.category.ilike(term),
            )
        )

    books = query.order_by(Book.created_at.desc()).all()
    return render_template("books/index.html", books=books, search=search)


@books_bp.route("/books/<int:book_id>")
@login_required
def detail(book_id):
    book = Book.query.get_or_404(book_id)
    students = User.query.filter_by(role="student", is_active=True).order_by(User.name).all() if current_user.is_staff else []
    active_loans = BorrowRecord.query.filter_by(book_id=book.id, returned_at=None).all()
    return render_template("books/detail.html", book=book, students=students, active_loans=active_loans)


@books_bp.route("/books/new", methods=["GET", "POST"])
@login_required
@role_required("librarian", "super_admin")
def create():
    if request.method == "POST":
        isbn = request.form.get("isbn", "").strip()
        if Book.query.filter_by(isbn=isbn).first():
            flash("A book with this ISBN already exists in the catalogue.", "danger")
            return render_template("books/form.html", book=None)

        qty = int(request.form.get("quantity", 1))
        book = Book(
            title=request.form.get("title", "").strip(),
            author=request.form.get("author", "").strip(),
            isbn=isbn,
            publisher=request.form.get("publisher", "").strip(),
            publication_year=int(request.form.get("publication_year")),
            category=request.form.get("category", "General").strip(),
            total_quantity=qty,
            available_quantity=qty,
            shelf_location=request.form.get("shelf_location", "").strip(),
        )
        db.session.add(book)
        db.session.commit()
        flash(f"'{book.title}' added to the library catalogue.", "success")
        return redirect(url_for("books.index"))

    return render_template("books/form.html", book=None)


@books_bp.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("librarian", "super_admin")
def edit(book_id):
    book = Book.query.get_or_404(book_id)

    if request.method == "POST":
        new_isbn = request.form.get("isbn", "").strip()
        if new_isbn != book.isbn and Book.query.filter_by(isbn=new_isbn).first():
            flash("Another book already uses this ISBN.", "danger")
            return render_template("books/form.html", book=book)

        new_total = int(request.form.get("quantity", book.total_quantity))
        diff = new_total - book.total_quantity

        book.title = request.form.get("title", "").strip()
        book.author = request.form.get("author", "").strip()
        book.isbn = new_isbn
        book.publisher = request.form.get("publisher", "").strip()
        book.publication_year = int(request.form.get("publication_year"))
        book.category = request.form.get("category", "General").strip()
        book.total_quantity = new_total
        book.available_quantity = max(0, book.available_quantity + diff)
        book.shelf_location = request.form.get("shelf_location", "").strip()

        db.session.commit()
        flash("Book details updated.", "success")
        return redirect(url_for("books.detail", book_id=book.id))

    return render_template("books/form.html", book=book)


@books_bp.route("/books/<int:book_id>/delete", methods=["POST"])
@login_required
@role_required("super_admin")
def delete(book_id):
    book = Book.query.get_or_404(book_id)
    title = book.title
    db.session.delete(book)
    db.session.commit()
    flash(f"'{title}' has been permanently deleted.", "warning")
    return redirect(url_for("books.index"))


@books_bp.route("/books/<int:book_id>/issue", methods=["POST"])
@login_required
@role_required("librarian", "super_admin")
def issue_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.available_quantity < 1:
        flash("No copies currently available to issue.", "danger")
        return redirect(url_for("books.detail", book_id=book.id))

    student_id = int(request.form.get("student_id"))
    days = int(request.form.get("days", 14))

    record = BorrowRecord(
        user_id=student_id,
        book_id=book.id,
        due_date=datetime.now(timezone.utc) + timedelta(days=days)
    )
    book.available_quantity -= 1
    db.session.add(record)
    db.session.commit()

    flash("Book issued successfully.", "success")
    return redirect(url_for("books.detail", book_id=book.id))


@books_bp.route("/loans/<int:record_id>/return", methods=["POST"])
@login_required
@role_required("librarian", "super_admin")
def return_book(record_id):
    record = BorrowRecord.query.get_or_404(record_id)
    if not record.returned_at:
        record.returned_at = datetime.now(timezone.utc)
        record.book.available_quantity = min(record.book.total_quantity, record.book.available_quantity + 1)
        db.session.commit()
        flash(f"'{record.book.title}' marked as returned.", "success")
    return redirect(request.referrer or url_for("books.loans"))


@books_bp.route("/loans")
@login_required
def loans():
    if current_user.is_staff:
        records = BorrowRecord.query.order_by(BorrowRecord.borrowed_at.desc()).all()
    else:
        records = BorrowRecord.query.filter_by(user_id=current_user.id).order_by(BorrowRecord.borrowed_at.desc()).all()
    return render_template("books/loans.html", records=records)