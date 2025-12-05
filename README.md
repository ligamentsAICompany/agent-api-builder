# 🚀 Auto API Builder

A powerful, modern web application for automatically generating REST APIs from JSON schemas. Built with Python Flask backend and vanilla JavaScript frontend.

## 📁 Project Structure

```
auto-api-generator/
│
├── 📁 frontend/                 # Frontend Application
│   ├── index.html               # Main application (Login, Register, Dashboard, API Generator)
│   ├── styles.css               # Complete styling (1000+ lines of modern CSS)
│   ├── app.js                   # Frontend logic & API generation (650+ lines)
│   └── setup-test-user.html     # Quick test user creation page
│
├── 📁 backend/                  # Python Flask Backend
│   ├── server.py                # Backend server (500+ lines)
│   ├── requirements.txt         # Python dependencies
│   └── generated_apis/          # Generated API projects (auto-created)
│
├── 📁 examples/                 # Example JSON schemas
│   ├── blog-schema.json         # Blog API example
│   └── ecommerce-schema.json    # E-commerce API example
│
├── start-backend.bat            # Windows batch script to start backend
├── README.md                    # This file - Comprehensive documentation
├── QUICKSTART.md                # Step-by-step quick start guide
├── PROJECT_SUMMARY.md           # Complete feature list and technical details
└── .gitignore                   # Git ignore rules
```

## ✨ Features

### 🔐 Authentication System
- **Secure Login & Registration**: User authentication with localStorage persistence
- **User Profile Management**: Display logged-in user information with avatar
- **Session Management**: Persistent sessions across browser refreshes

### 🎨 Modern UI/UX
- **Dark Theme**: Sleek, professional dark mode interface
- **Glassmorphism Effects**: Frosted glass effects on cards and panels
- **Smooth Animations**: Micro-animations for enhanced user experience
- **Gradient Backgrounds**: Dynamic floating gradient orbs
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile

### ⚙️ API Generator
- **AI-Powered Code Generation**: Uses OpenAI to generate code automatically
- **Multi-Framework Support**:
  - Python Flask (with SQLAlchemy)
  - Python FastAPI (with Pydantic)
  - Java Spring Boot
  - Node.js Express
  - Node.js NestJS
  - TypeScript Express
  - And many more! (Any language/framework supported by OpenAI)
  
- **Database Support**:
  - PostgreSQL
  - MySQL
  - SQLite
  - MongoDB

- **JSON Schema Input**: Define your API models using simple JSON
- **Auto-Generated Code**:
  - Models with proper typing
  - Full CRUD endpoints (Create, Read, Update, Delete)
  - Request validation
  - Error handling
  - Documentation

- **Code Editor**: Built-in code viewer with syntax highlighting
- **Download**: Download generated API as a complete ZIP file
- **File Upload**: Upload existing projects for editing

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Modern web browser (Chrome, Firefox, Safari, Edge)
- pip (Python package manager)

### Installation

1. **Clone or download the project**
   ```bash
   cd auto-api-generator
   ```

2. **Install Python backend dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure OpenAI API Key** (Required for code generation)
   
   The application uses OpenAI to generate code for any language/framework. You need to set up your OpenAI API key:
   
   **Option 1: Using .env file (Recommended)**
   ```bash
   cd backend
   # Create a .env file
   echo "OPENAI_API_KEY=your_api_key_here" > .env
   ```
   
   **Option 2: Using environment variable**
   ```bash
   # Windows PowerShell
   $env:OPENAI_API_KEY="your_api_key_here"
   
   # Windows CMD
   set OPENAI_API_KEY=your_api_key_here
   
   # Linux/Mac
   export OPENAI_API_KEY=your_api_key_here
   ```
   
   **Get your API key:**
   - Visit https://platform.openai.com/api-keys
   - Sign up or log in to your OpenAI account
   - Create a new API key
   - Copy the key and add it to your `.env` file or environment variables
   
   ⚠️ **Important**: Never commit your `.env` file or API key to version control!

4. **Start the backend server**
   ```bash
   python server.py
   ```
   The backend will start on `http://localhost:5001`

5. **Open the frontend**
   - Option 1: Simply open `frontend/index.html` in your browser
   - Option 2: Use a local server:
     ```bash
     # From project root
     python -m http.server 8000
     
     # Then open http://localhost:8000/frontend/
     ```

### Quick Start with Test User

1. Open `frontend/setup-test-user.html` in your browser
2. Click "Create Test User"
3. Login with:
   - **Email**: `admin@example.com`
   - **Password**: `admin123`

## 📖 Usage Guide

### 1. Login/Register
- Register a new account or use the test user credentials
- Your session will be saved automatically

### 2. Navigate to API Generator
- Click "API Generator" in the sidebar
- Fill in the configuration form:
  - **Project Name**: e.g., "my-blog-api"
  - **Package Name**: e.g., "com.example.blog"
  - **Language/Framework**: Choose from Python Flask, FastAPI, Java Spring, Node.js Express, NestJS, TypeScript Express, or enter any custom language/framework name
  - **Database**: Select your preferred database
  - **Connection String**: Enter your database URL

### 3. Define JSON Schema
- Enter your model definitions in JSON format
- Example:
  ```json
  {
    "User": {
      "id": "integer",
      "name": "string",
      "email": "string",
      "created_at": "datetime"
    },
    "Post": {
      "id": "integer",
      "title": "string",
      "content": "text",
      "author_id": "integer",
      "published": "boolean"
    }
  }
  ```

### 4. Generate API
- Click "Validate JSON" to check your schema
- Click "Generate API" to create the code
- View the generated code in the editor panel
- Download the complete project as a ZIP file

### 5. Run Your Generated API

#### For Python Flask:
```bash
cd your-project-name
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

#### For Python FastAPI:
```bash
cd your-project-name
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## 🎯 Supported Field Types

| JSON Type  | Python Flask   | Python FastAPI | Database   |
|------------|---------------|----------------|------------|
| string     | String(255)   | str            | VARCHAR    |
| integer    | Integer       | int            | INTEGER    |
| float      | Float         | float          | FLOAT      |
| boolean    | Boolean       | bool           | BOOLEAN    |
| datetime   | DateTime      | datetime       | DATETIME   |
| date       | Date          | datetime       | DATE       |
| text       | Text          | str            | TEXT       |

## 🔧 Configuration Options

### Project Name
- Alphanumeric with hyphens
- Used for project folder name

### Package Name
- Reverse domain notation (e.g., com.example.api)
- Used for Java package structure

### Language/Framework
- **Python Flask**: Traditional, battle-tested web framework
- **Python FastAPI**: Modern, fast, with automatic API docs
- **Java Spring Boot**: Enterprise-grade Java framework
- **Node.js Express**: Popular JavaScript web framework
- **Node.js NestJS**: Progressive Node.js framework with TypeScript
- **TypeScript Express**: Express.js with TypeScript support
- **Custom**: Enter any language/framework name - OpenAI will generate appropriate code structure!

### Database
- **PostgreSQL**: Production-ready, feature-rich
- **MySQL**: Popular, widely supported
- **SQLite**: Simple, file-based, great for development
- **MongoDB**: NoSQL, document-based (Coming Soon)

## 📊 Generated API Features

### Endpoints
For each model, the generator creates:
- `GET /api/models` - List all items
- `GET /api/models/<id>` - Get specific item
- `POST /api/models` - Create new item
- `PUT /api/models/<id>` - Update existing item
- `DELETE /api/models/<id>` - Delete item

### Additional Endpoints
- `GET /` - API information and available endpoints
- `GET /health` - Health check endpoint

### Features
- ✅ Input validation
- ✅ Error handling
- ✅ CORS enabled
- ✅ JSON responses
- ✅ Auto-generated documentation
- ✅ Database migrations (Flask)
- ✅ Interactive docs (FastAPI)

## 🎨 Customization

### Colors & Theme
Edit CSS variables in `frontend/styles.css`:
```css
:root {
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --bg-dark: #0f0f1e;
    --text-primary: #ffffff;
    /* ... more variables */
}
```

### Backend Configuration
Modify `backend/server.py`:
- Change default port (default: 5001)
- Customize generation templates
- Add new frameworks

## 🔒 Security Notes

⚠️ **Important**: This is a demonstration/development tool.

For production use:
1. Implement proper backend authentication
2. Use HTTPS
3. Hash and salt passwords (use bcrypt, argon2)
4. Add rate limiting
5. Implement CSRF protection
6. Validate and sanitize all inputs server-side
7. Use environment variables for sensitive data
8. Add proper authorization/permissions
9. Regular security audits

## 🚧 Roadmap

- [x] Python Flask generation
- [x] Python FastAPI generation
- [x] File upload functionality
- [x] Organized project structure with frontend/backend folders
- [ ] Java Spring Boot generation
- [ ] MongoDB schema generation
- [ ] GraphQL API generation
- [ ] Real-time code preview
- [ ] Docker configuration generation
- [ ] API testing suite generation
- [ ] OpenAPI/Swagger documentation
- [ ] GitHub integration
- [ ] Custom templates
- [ ] Multi-file editing
- [ ] Code formatting/linting
- [ ] Project versioning

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Add more frameworks (Django, Express.js, NestJS)
- Improve code generation templates
- Add database migration scripts
- Enhanced error handling
- Unit tests
- Integration tests
- Deployment guides

## 📄 License

This project is open source and available for educational and commercial use.

## 🙏 Credits

- **Design**: Modern web design principles
- **Icons**: Inline SVG icons
- **Fonts**: Google Fonts (Inter, Fira Code)
- **Animations**: CSS3 keyframes

## 📞 Support

For issues, questions, or feature requests:
1. Check the documentation
2. Review existing issues
3. Create a new issue with details

---

**Built with ❤️ using Python Flask and Vanilla JavaScript**

🌟 **Star this project if you find it useful!**
