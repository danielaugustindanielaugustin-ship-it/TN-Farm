# 🌾 TNFarm — Farmer Discovery & Social Commerce Platform

A dynamic web app for Tamil Nadu: farmers create digital profiles, list produce,
post updates, and chat directly with customers. Built with **Python Flask +
SQLAlchemy + SQLite**, server-rendered templates, and a green/earth themed UI.

This is the **Milestone 1 & 2** build from the TNFarm roadmap:
Setup → Auth → Roles → Farmer Profiles → Farms → Products → Home →
Search → Social Feed → Follow → Likes/Comments → Reviews → Chat →
Notifications → Dashboards (Farmer / Customer / Admin).

No online ordering, cart, or payments in this version — by design (see roadmap).

---

## 🧱 Tech Stack

| Layer      | Technology                          |
|------------|--------------------------------------|
| Backend    | Python 3, Flask                      |
| Database   | SQLite (via SQLAlchemy ORM)          |
| Auth       | Flask-Login (session-based)          |
| Frontend   | Jinja2 templates, HTML5, CSS3, vanilla JS |
| Styling    | Custom CSS (Poppins + Inter, green/earth theme) |

---

## 📁 Project Structure

```
tnfarm/
├── app.py               # Flask app + all routes
├── models.py             # SQLAlchemy models (User, Farm, Product, Post, etc.)
├── config.py              # App configuration
├── seed.py                 # Sample data loader
├── requirements.txt
├── static/
│   ├── css/style.css
│   ├── img/leaf-pattern.svg
│   └── uploads/          # user-uploaded images (farms, products, posts)
└── templates/            # all HTML pages (Jinja2)
```

---

## 🚀 Run it locally (VS Code)

1. **Open the folder in VS Code**
   - `File → Open Folder…` → select the unzipped `tnfarm` folder.
   - Install the official **Python extension** if prompted.

2. **Create a virtual environment** (Terminal → New Terminal in VS Code):
   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Seed the database with sample farms, products & posts**
   ```bash
   python seed.py
   ```
   This creates `tnfarm.db` with demo accounts:
   - Farmer: `murugan@example.com` / `password123`
   - Customer: `priya@example.com` / `password123`
   - Admin: `admin@tnfarm.local` / `admin123`

5. **Run the app**
   ```bash
   python app.py
   ```
   Open **http://127.0.0.1:5000** in your browser.

   In VS Code you can also just press **F5** (with the Python extension) or use
   the Run ▶ button on `app.py`.

---

## 🔧 Resetting the database

If you want a clean slate at any point:
```bash
python seed.py
```
(This drops and recreates all tables, then reloads sample data.)

---

## ☁️ Publish to GitHub

From inside the `tnfarm` folder:

```bash
git init
git add .
git commit -m "Initial commit: TNFarm dynamic web app"
git branch -M main
git remote add origin https://github.com/<your-username>/tnfarm.git
git push -u origin main
```

> `tnfarm.db` and `static/uploads/*` are excluded via `.gitignore` so you don't
> commit local data/user images. Anyone cloning the repo just runs `python seed.py`
> to get a working database again.

### Deploying it live (optional next step)
Once on GitHub, you can deploy for free on **Render**, **Railway**, or
**PythonAnywhere** — all support Flask out of the box. Ask me when you're ready
and I'll walk you through whichever platform you pick.

---

## ✅ What's implemented (Milestone 1 & 2 of the roadmap)

- Farmer & Customer registration/login (secure password hashing, sessions)
- Role-based access (Farmer / Customer / Admin)
- Farmer profile & farm management (cover photo, logo, location, organic status)
- Product module (add / edit / delete / browse / search / filter by category & organic)
- Home page (hero search, categories, featured farms, trending products, recent posts)
- Social feed (posts, likes, comments)
- Follow system
- Reviews & star ratings
- Basic direct messaging (farmer ↔ customer chat)
- Notifications (follow, comment, review, message events)
- Dashboards: Farmer, Customer, Admin (with district-wise stats)

## 🔜 Not yet built (later roadmap phases)
- Google Maps live embed (fields exist in the DB — `latitude`/`longitude`/`map_url` — ready to wire up)
- Real-time chat (current chat is page-refresh based, not WebSocket push)
- AI chatbot, disease detection, semantic search
- Analytics charts (data model supports it; charts not rendered yet)
- Production deployment / SSL / Nginx config

Tell me which phase to build next and I'll extend this same codebase.
