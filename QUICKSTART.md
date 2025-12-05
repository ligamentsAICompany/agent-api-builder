# 🚀 Quick Start Guide

Get up and running in 5 minutes!

## Step 1: Install Python Dependencies

Open a terminal/command prompt in the project directory:

```bash
cd backend
pip install -r requirements.txt
```

## Step 2: Start the Backend Server

### Option A: Using the Batch Script (Windows)
```bash
# From the project root directory
start-backend.bat
```

### Option B: Manual Start
```bash
cd backend
python server.py
```

The server will start on `http://localhost:5001`

## Step 3: Open the Frontend

### Option A: Direct File Access
Navigate to the `frontend` folder and double-click `index.html`

### Option B: Local Server (Recommended)
```bash
# From project root
python -m http.server 8000

# Then open http://localhost:8000/frontend/ in your browser
```

## Step 4: Create a Test User

1. Open `frontend/setup-test-user.html` in your browser
2. Click "Create Test User"
3. You'll be redirected to the login page

## Step 5: Login

Use these credentials:
- **Email**: `admin@example.com`
- **Password**: `admin123`

## Step 6: Generate Your First API

1. Click **"API Generator"** in the sidebar
2. Fill in the form:
   - Project Name: `blog-api`
   - Package Name: `com.example.blog`
   - Language: `Python - Flask`
   - Database: `SQLite`
   
3. Add this JSON schema:
```json
{
  "Post": {
    "id": "integer",
    "title": "string",
    "content": "text",
    "published": "boolean",
    "created_at": "datetime"
  }
}
```

4. Click **"Generate API"**
5. View the generated code in the editor
6. Click the download icon to get your complete API project!

## Step 7: Run Your Generated API

```bash
cd path/to/downloaded/blog-api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Your API will be running at `http://localhost:5000`!

## 🎉 That's It!

You now have:
- ✅ A running API generator
- ✅ Your first generated API
- ✅ Full CRUD endpoints for your models

## 📁 Project Structure

```
auto-api-generator/
├── frontend/           # All frontend files (HTML, CSS, JS)
├── backend/            # Python Flask backend
├── examples/           # Example JSON schemas
└── ...                 # Documentation files
```

## 📚 What's Next?

- Try generating a FastAPI project
- Add more complex models with relationships
- Customize the generated code
- Deploy your API to a cloud platform

## 🆘 Troubleshooting

### Backend won't start
- Make sure Python 3.8+ is installed
- Check that all dependencies installed successfully
- Verify port 5001 is not being used by another application

### Frontend not loading
- Clear browser cache
- Make sure JavaScript is enabled
- Try a different browser
- Check that you're opening files from the `frontend/` folder

### "Cannot generate API" errors
- Verify backend is running on port 5001
- Check JSON schema is valid (use "Validate JSON" button)
- Ensure all required fields are filled

---

**Need help?** Check the full README.md for detailed documentation!
