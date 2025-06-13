# ✅ Flask To‑Do List App

A full-stack Flask web application for managing personal tasks (To‑Dos). Users can add, edit, complete, and delete tasks. The app supports anonymous session-based users and registered users with persistent storage. Authenticated users can save session tasks to their account after login.

---

## 📌 Table of Contents

- [✅ Flask To‑Do List App](#-flask-todo-list-app)
  - [📌 Table of Contents](#-table-of-contents)
  - [🚀 Features](#-features)
  - [⚙️ How It Works](#️-how-it-works)
  - [🧰 Technologies](#-technologies)
  - [🛠️ Getting Started](#️-getting-started)
    - [1. Clone the Repository](#1-clone-the-repository)
    - [2. Run the App](#2-run-the-app)
  - [📄 License](#-license)
  - [👤 Author](#-author)
  - [💬 Feedback](#-feedback)

---

## 🚀 Features

- Anonymous users can add and manage todos temporarily via session
- Registered users can save todos permanently to their account
- User registration and login with hashed passwords
- Edit and delete todos
- Filter by active, completed, or due tasks
- Sort todos by creation or due date
- Flash messages for feedback and validation
- Responsive UI with Bootstrap

---

## ⚙️ How It Works

- `app.py` defines Flask routes, models, and logic
- Todos are stored in a session for anonymous users and in a SQLite database for registered users
- Flask-Login handles authentication and user sessions
- Flask-WTF manages form handling and validation
- SQLAlchemy is used for database models and queries

---

## 🧰 Technologies

- **Python 3**
- **Flask**
  - Flask-Bootstrap
  - Flask-WTF
  - Flask-Login
- **SQLAlchemy + SQLite**
- **HTML + Jinja2**
- **Bootstrap 5**

---

## 🛠️ Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/CelmarPA/Python_Todo_List_Website
cd Cafe_Website_Flask
```

### 2. Run the App

```bash
pip install -r requirements.txt
python app.py
```

> The app will run on `http://127.0.0.1:5000/`

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 👤 Author

**Celmar Pereira**

- [GitHub](https://github.com/CelmarPA)
- [LinkedIn](https://linkedin.com/in/celmar-pereira-de-andrade-039830181)
- [Portfolio](https://yourportfolio.com)

---

## 💬 Feedback

Feel free to open issues or submit pull requests. Contributions are welcome!
