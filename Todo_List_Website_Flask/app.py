from flask import Flask, render_template, request, url_for, flash, redirect, session
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import select, ForeignKey
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional
from datetime import datetime, date, timezone
from sqlalchemy import Date
from types import SimpleNamespace

# Initialize Flask app and plugins
app = Flask(__name__)
Bootstrap(app)

# Security and database configuration
app.config["SECRET_KEY"] = "any-secret-key-you-choose"  # Used for session signing, CSRF protection, etc.
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///todos.db"  # SQLite database file
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # Silent disable of object tracking


# ORM (Object-Relational Mapping) initialization
db = SQLAlchemy(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"      # Redirect unauthorized users to this route


# --- Database Models ---

class Todo(db.Model):
    """
    Represents a single to-do item.
    Associates with User via foreign key and relationship.
    """
    id: Mapped[int] = mapped_column(primary_key = True)
    date: Mapped[date] = mapped_column(Date, nullable = False)  # Creation timestamp
    text: Mapped[str] = mapped_column(nullable = False)         # To‑do description
    done: Mapped[bool] = mapped_column(nullable=False, default=False)   # Completed flag
    due_on_date: Mapped[Date] = mapped_column(Date, nullable = True)    # Optional due date

    # New ForeignKey"s column
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable = False)

    # Relationship to access owner (optional)
    user = relationship("User",  back_populates = "todos")

    def to_dict(self):
        """
        Return dictionary mapping column names to values (for JSON or API usage).
        """
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class User(UserMixin, db.Model):
    """
    User model for authentication.
    Inherits Flask-Login's UserMixin for session integration.
    """

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)     # Hashed password
    password: Mapped[str] = mapped_column(nullable=False)

    # Relationship with this user's TODOs
    todos = relationship("Todo", back_populates = "user", cascade = "all, delete")  # Owned tasks


# --- Forms ---

class TodoForm(FlaskForm):
    """
    Defines a form for creating or editing a to-do.
    Uses WTForms integration with Flask-WTF for CSRF, validation, etc.
    """

    date = DateField(label = "Date", validators = [Optional()])
    text = StringField(label = "Todo", validators = [DataRequired()])
    done = BooleanField(label= "Done")
    due_on_date = DateField(label = "Due on date", validators = [Optional()])
    submit = SubmitField(label = "Add")


# --- User loading callback ---

@login_manager.user_loader
def load_user(user_id):
    """
    Called by Flask-Login to reload the user object from session.
    """
    return db.session.get(User, user_id)


# --- Guest session tracking ---

@app.before_request
def ensure_guest_id():
    """
    Ensure anonymous users get a unique guest_id stored in session.
    Facilitates temporary to-do storage per user session.
    """
    if not current_user.is_authenticated and "guest_id" not in session:
        session["guest_id"] = str(uuid.uuid4())


# --- Authentication Routes ---
@app.route("/register", methods = ["GET", "POST"])
def register():
    """
    Registration endpoint:
    - GET: render registration page.
    - POST: create new user after validating unique email.
    Passwords are hashed before storing.
    """
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        existing_user = db.session.query(User).filter_by(email = request.form["email"]).first()

        if existing_user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for("register"))

        new_user = User(
            name = request.form["name"],
            email = request.form["email"],
            password = generate_password_hash(request.form["password"],method = "pbkdf2:sha256", salt_length = 8)
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("home", name = new_user.name))


    return render_template("register.html")


@app.route("/login", methods = ["GET", "POST"])
def login():
    """
    Login endpoint:
    - GET: render login form.
    - POST: authenticate user.
      Uses flash messages on failure.
    """
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = db.session.execute(select(User).filter_by(email = email)).scalars().first()

        if not user:
            flash("That email does not exist, please try again.")
            return render_template("login.html")

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("home"))

        else:
            flash("Password incorrect, please try again.")
            return render_template("login.html")

    return render_template("login.html", logged_in = current_user.is_authenticated)


@app.route("/logout")
@login_required
def logout():
    """
    Logs out current user and redirects to home.
    """
    logout_user()
    return redirect(url_for("home"))


# --- Main Application Logic ---

@app.route("/")
@app.route("/home")
def home():
    """
    Displays the to-do list, merging items from database and session:
    Supports filtering by completion status or due date,
    and sorting by date added or due date.
    """

    filter_done = request.args.get("filter", "all")
    sort_by = request.args.get("sort", "added-date-asc")

    todos = []

    if current_user.is_authenticated:
        # Load user-specific todos from DB
        db_todos = Todo.query.filter_by(user_id=current_user.id).all()
        for t in db_todos:
            t.source = "db"
        todos.extend(db_todos)

    # Load anonymous session-stored todos
    session_todos = session.get("todos", [])
    for index, item in enumerate(session_todos):
        # Normalize date strings into date objects
        due_date = item.get("due_on_date")
        if due_date:
            try:
                item["due_on_date"] = datetime.strptime(due_date, "%Y-%m-%d").date()
            except Exception as e:
                print(e)
                item["due_on_date"] = None

        created_date = item.get("date")
        if created_date:
            try:
                item["date"] = datetime.strptime(created_date, "%Y-%m-%d").date()
            except Exception as e:
                print(e)
                item["date"] = date.today()

        item["source"] = "session"
        item["session_id"] = index
        todos.append(SimpleNamespace(**item))

    # Apply filter
    if filter_done == "completed":
        todos = [todo for todo in todos if todo.done]
    elif filter_done == "active":
        todos = [todo for todo in todos if not todo.done]
    elif filter_done == "has-due-date":
        todos = [todo for todo in todos if todo.due_on_date]

    # Apply sorting
    if sort_by == "added-date-asc":
        todos.sort(key=lambda todo: todo.date or date.today())
    elif sort_by == "added-date-desc":
        todos.sort(key=lambda todo: todo.date or date.today(), reverse=True)
    elif sort_by == "due-date-asc":
        todos.sort(key=lambda todo: todo.due_on_date or date.max)
    elif sort_by == "due-date-desc":
        todos.sort(key=lambda todo: todo.due_on_date or date.min, reverse=True)

    return render_template("index.html", todos=todos, has_session_todos=bool(session_todos))


@app.route("/add", methods = ["POST"])
def add():
    """
    Handles creation of a new to‑do:
    - For authenticated users: saves directly to DB.
    - For guests: stores in session until login/save
    """
    text = request.form.get("text")
    due_date_str = request.form.get("date")

    if not text:
        return redirect(url_for("home"))

    creation_date = datetime.now(timezone.utc).date()
    due_on = None

    if due_date_str:
        try:
            due_on = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    if current_user.is_authenticated:
        # Logged-in user: saves in the database with user_id
        new_todo = Todo(
            text = text,
            date = creation_date,
            due_on_date = due_on,
            done = False,
            user_id = current_user.id
        )

        db.session.add(new_todo)
        db.session.commit()

    else:
        # Anonymous user: temporarily saves in session
        todo = {
            "id": str(uuid.uuid4()),    # Unique ID in string
            "text": text,
            "date": creation_date.isoformat(),
            "due_on_date": due_on.isoformat() if due_on else None,
            "done": False,

        }

        todos = session.get("todos", [])
        todos.append(todo)
        session["todos"] = todos
        session.modified = True

    return redirect(url_for("home"))


@app.route("/edit", methods=["GET", "POST"])
def edit():
    """
    Edit route for DB-stored to‑dos.
    GET: show pre-filled form; POST: validate and update entry.
    """
    todo_id = request.args.get("todo_id") or request.form.get("todo_id")

    if not todo_id:
        flash("Missing todo ID.")
        return redirect(url_for("home"))

    todo = db.session.get(Todo, int(todo_id))

    if not todo or todo.user_id != current_user.id:
        flash("Todo not found or unauthorized.")
        return redirect(url_for("home"))

    form = TodoForm(obj=todo)

    if request.method == "POST":
        if form.validate_on_submit():
            todo.text = form.text.data
            todo.date = form.date.data
            todo.done = form.done.data
            todo.due_on_date = form.due_on_date.data

            db.session.commit()
            flash("Todo updated successfully.")

            return redirect(url_for("home"))

        else:
            flash("Form validation failed. Check your inputs.")

    return render_template("edit.html", form=form, todo=todo)


@app.route("/edit_session", methods=["GET", "POST"])
def edit_session():
    """
    Edit route for session-stored todos (signed-out users).
    POST applies changes in session rather than DB.
    """
    todo_id = request.args.get("todo_id") or request.form.get("todo_id")

    todos = session.get("todos", [])
    todo = next((todo for todo in todos if todo["id"] == todo_id), None)

    if not todo:
        flash("Todo not found.")
        return redirect(url_for("home"))

    if request.method == "POST":
        new_text = request.form.get("text")
        new_due = request.form.get("due_on_date")

        if new_text:
            todo["text"] = new_text

        if new_due:
            try:
                # Normalize input due date string to ISO format
                due_date_obj = datetime.strptime(new_due, "%Y-%m-%d").date()
                todo["due_on_date"] = due_date_obj.strftime("%Y-%m-%d")
            except ValueError:
                todo["due_on_date"] = None
        else:
            todo["due_on_date"] = None

        # Normalize 'date' field to ISO string (to avoid format issues later)
        todo["date"] = normalize_date(todo.get("date"))

        session["todos"] = todos
        session.modified = True
        flash("Todo updated successfully.")

        return redirect(url_for("home"))

    return render_template("edit_session.html", todo=todo, todo_id=todo_id)


@app.route("/toggle_done", methods = ["POST"])
def toggle_done():
    """
    Toggles 'done' status for a given todo ID.
    Works for both DB and session todos.
    """
    todo_id = request.form.get("todo_id")

    if current_user.is_authenticated:
        todo = db.session.get(Todo, int(todo_id))

        if todo and todo.user_id == current_user.id:
            todo.done = not todo.done
            db.session.commit()

    else:
        todos = session.get("todos", [])

        for todo in todos:
            if todo["id"] == todo_id:
                todo["done"] = not todo.get("done", False)
                session["todos"] = todos
                session.modified = True
                break

    return redirect(url_for("home"))


@app.route("/save")
@login_required
def save():
    """
    Moves session-stored todos into the authenticated user's account in the DB.
    Clears the session list upon success.
    """
    todos = session.get("todos", [])

    if not todos:
        flash("No todos to save.")
        return redirect(url_for("home"))

    for item in todos:
        text = item.get("text")
        if not text:
            continue

        # Normalize date and due_on_date
        date_value = normalize_date(item.get("date"))
        due_on_date_value = normalize_date(item.get("due_on_date")) if item.get("due_on_date") else None

        new_todo = Todo(
            text=text,
            date=date_value,
            due_on_date=due_on_date_value,
            done=item.get("done", False),
            user_id=current_user.id
        )

        db.session.add(new_todo)

    try:
        db.session.commit()
        session.pop("todos", None)
        flash("Todos saved to your account.")
    except Exception as e:
        db.session.rollback()
        flash(f"Error saving todos: {e}")

    return redirect(url_for("home"))


@app.route("/delete", methods = ["POST"])
def delete():
    """
    Deletes to‑do either from the DB (authenticated) or session storage (guest).
    """
    todo_id = request.form.get("todo_id")

    if not todo_id:
        return redirect(url_for("home"))

    # If user is logged in, delete from database
    if current_user.is_authenticated:
        todo = db.session.get(Todo, todo_id)
        if todo and todo.user_id == current_user.id:
            db.session.delete(todo)
            db.session.commit()

    # If not logged in, delete from the list in memory
    else:
        todo_list = session.get("todos", [])

        # Filter all but the one with the matching ID
        updated_list = [todo for todo in todo_list if todo.get("id") != todo_id]
        session["todos"] = updated_list
        session.modified = True

    return redirect(url_for("home"))


# --- Helper functions ---

def normalize_date(date_value):
    """
    Converts an ISO-formatted string or datetime to a date object.
    Falls back to today() on parsing errors.
    """
    if isinstance(date_value, date):
        return date_value

    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value, "%Y-%m-%d").date()

        except ValueError:
            try:
                return datetime.strptime(date_value, "%a, %d %b %Y %H:%M:%S %Z").date()

            except ValueError:
                return datetime.today().date()

    return datetime.today().date()


@app.template_filter("human_date")
def human_date(value):
    """
    Jinja2 filter to render dates in human-friendly format,
    with ordinal suffixes (1st, 2nd, 3rd...).
    Accepts strings, datetime, or date instances.
    """
    if not value:
        return "No date"

    if isinstance(value, str):
        try:
            # Try the first format
            value = datetime.strptime(value[:10], "%Y-%m-%d").date()

        except ValueError:
            try:
                # Try format type "Mon, 02 Jun 2025 00:00:00 GMT"
                value = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %Z").date()

            except ValueError:
                return value

    elif isinstance(value, datetime):
        value = value.date()

    # Add ordinal suffix (1st, 2nd, 3rd etc.)
    suffix = lambda d: "th" if 11 <= d <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")

    return f"{value.day}{suffix(value.day)} {value.strftime('%b %Y')}"


# --- Entry point ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()     # Ensure tables exist
    app.run(debug=True)
