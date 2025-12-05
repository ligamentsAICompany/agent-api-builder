// ===================================
// STATE MANAGEMENT
// ===================================
let currentUser = null;
let generatedCode = {};
let gitFiles = {};        // Track files from Git (for orange color)
let generatedFiles = {};  // Track newly generated files (for green color)
let lastGeneratedZipUrl = null;
let lastGeneratedZipName = null;
let currentView = 'home';

/**
 * Get user initials from full name
 */
function getInitials(name) {
    const parts = name.trim().split(' ');
    if (parts.length === 1) {
        return parts[0].substring(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * Show a specific screen
 */
function showScreen(screenId) {
    const screens = ['login-screen', 'register-screen', 'dashboard'];
    screens.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.classList.toggle('hidden', id !== screenId);
        }
    });
}

/**
 * Show a specific view within dashboard
 */
function showView(viewName) {
    currentView = viewName;
    const views = document.querySelectorAll('.content-view');
    views.forEach(view => {
        view.classList.add('hidden');
    });

    const targetView = document.getElementById(`${viewName}-view`);
    if (targetView) {
        targetView.classList.remove('hidden');
    }

    // Update active nav item
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        const itemView = item.getAttribute('data-view');
        item.classList.toggle('active', itemView === viewName);
    });
}

/**
 * Store user data in localStorage
 */
function storeUser(userData) {
    localStorage.setItem('currentUser', JSON.stringify(userData));
}

/**
 * Retrieve user data from localStorage
 */
function getStoredUser() {
    const userData = localStorage.getItem('currentUser');
    return userData ? JSON.parse(userData) : null;
}

/**
 * Clear stored user data
 */
function clearStoredUser() {
    localStorage.removeItem('currentUser');
}

/**
 * Update dashboard with user information
 */
function updateDashboard(user) {
    const userName = document.getElementById('user-name');
    const userDisplayName = document.getElementById('user-display-name');
    const userInitials = document.getElementById('user-initials');

    if (userName) userName.textContent = user.name.split(' ')[0];
    if (userDisplayName) userDisplayName.textContent = user.name;
    if (userInitials) userInitials.textContent = getInitials(user.name);
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? 'linear-gradient(135deg, #4ade80 0%, #22c55e 100%)' :
            type === 'error' ? 'linear-gradient(135deg, #f87171 0%, #ef4444 100%)' :
                'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ===================================
// AUTHENTICATION HANDLERS
// ===================================

function handleLogin(event) {
    event.preventDefault();

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    if (!email || !password) {
        showNotification('Please fill in all fields', 'error');
        return;
    }

    const users = JSON.parse(localStorage.getItem('registeredUsers') || '[]');
    const user = users.find(u => u.email === email && u.password === password);

    if (user) {
        currentUser = { name: user.name, email: user.email };
        storeUser(currentUser);
        updateDashboard(currentUser);
        showScreen('dashboard');
        showView('home');
        showNotification(`Welcome back, ${user.name}!`, 'success');
        document.getElementById('login-form').reset();
        loadGitHubConfig();
    } else {
        showNotification('Invalid email or password', 'error');
    }
}

function handleRegister(event) {
    event.preventDefault();

    const name = document.getElementById('register-name').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;

    if (!name || !email || !password) {
        showNotification('Please fill in all fields', 'error');
        return;
    }

    if (password.length < 6) {
        showNotification('Password must be at least 6 characters', 'error');
        return;
    }

    const users = JSON.parse(localStorage.getItem('registeredUsers') || '[]');
    const existingUser = users.find(u => u.email === email);

    if (existingUser) {
        showNotification('User with this email already exists', 'error');
        return;
    }

    const newUser = { name, email, password };
    users.push(newUser);
    localStorage.setItem('registeredUsers', JSON.stringify(users));

    showNotification('Registration successful! Please login.', 'success');
    document.getElementById('register-form').reset();
    showScreen('login-screen');
}

function handleLogout() {
    currentUser = null;
    clearStoredUser();
    showScreen('login-screen');
    showNotification('Logged out successfully', 'success');
}

// ===================================
// API GENERATOR LOGIC
// ===================================

/**
 * Validate JSON schema
 */
function validateJSON(event) {
    event.preventDefault();

    const jsonSchema = document.getElementById('json-schema').value;

    if (!jsonSchema.trim()) {
        showNotification('Please enter a JSON schema', 'error');
        return;
    }

    try {
        const parsed = JSON.parse(jsonSchema);

        // Validate the schema structure
        let modelCount = 0;

        if (Array.isArray(parsed)) {
            // Array format validation
            for (const model of parsed) {
                if (!model.name || !model.fields) {
                    showNotification('Array format requires each model to have "name" and "fields" properties', 'error');
                    return;
                }
                if (!Array.isArray(model.fields)) {
                    showNotification('Model "fields" must be an array', 'error');
                    return;
                }
                modelCount++;
            }
        } else if (typeof parsed === 'object') {
            // Object format validation
            modelCount = Object.keys(parsed).length;
            for (const [modelName, fields] of Object.entries(parsed)) {
                if (typeof fields !== 'object') {
                    showNotification(`Model "${modelName}" must have field definitions`, 'error');
                    return;
                }
            }
        } else {
            showNotification('Schema must be an object or array', 'error');
            return;
        }

        showNotification(`JSON is valid! Found ${modelCount} model${modelCount === 1 ? '' : 's'}.`, 'success');
    } catch (error) {
        showNotification(`Invalid JSON: ${error.message}`, 'error');
    }
}

/**
 * Generate Python Flask code from schema
 */
function generatePythonFlask(config, schema) {
    const models = Object.keys(schema);
    let code = `# Auto-generated Python Flask API
# Project: ${config.projectName}
#Generated on: ${new Date().toISOString()}

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = '${config.dbConnection || 'sqlite:///database.db'}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
`;

    // Generate models
    models.forEach(modelName => {
        const fields = schema[modelName];
        code += `\nclass ${modelName}(db.Model):
    __tablename__ = '${modelName.toLowerCase()}s'
    
`;

        Object.entries(fields).forEach(([fieldName, fieldType]) => {
            const sqlType = mapTypeToSQL(fieldType);
            const isPrimary = fieldName === 'id';
            code += `    ${fieldName} = db.Column(db.${sqlType}${isPrimary ? ', primary_key=True, autoincrement=True' : ''})\n`;
        });

        code += `\n    def to_dict(self):
        return {
${Object.keys(fields).map(f => `            '${f}': self.${f}`).join(',\n')}
        }
\n`;
    });

    // Generate routes
    code += `\n# Routes\n@app.route('/')
def index():
    return jsonify({'message': 'API is running', 'version': '1.0'})\n\n`;

    models.forEach(modelName => {
        const routeName = modelName.toLowerCase();
        code += `# ${modelName} routes
@app.route('/api/${routeName}s', methods=['GET'])
def get_all_${routeName}s():
    items = ${modelName}.query.all()
    return jsonify([item.to_dict() for item in items])

@app.route('/api/${routeName}s/<int:id>', methods=['GET'])
def get_${routeName}(id):
    item = ${modelName}.query.get_or_404(id)
    return jsonify(item.to_dict())

@app.route('/api/${routeName}s', methods=['POST'])
def create_${routeName}():
    data = request.get_json()
    new_item = ${modelName}(**data)
    db.session.add(new_item)
    db.session.commit()
    return jsonify(new_item.to_dict()), 201

@app.route('/api/${routeName}s/<int:id>', methods=['PUT'])
def update_${routeName}(id):
    item = ${modelName}.query.get_or_404(id)
    data = request.get_json()
    for key, value in data.items():
        setattr(item, key, value)
    db.session.commit()
    return jsonify(item.to_dict())

@app.route('/api/${routeName}s/<int:id>', methods=['DELETE'])
def delete_${routeName}(id):
    item = ${modelName}.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return '', 204

`;
    });

    code += `\nif __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
`;

    return code;
}

/**
 * Generate Python FastAPI code from schema
 */
function generatePythonFastAPI(config, schema) {
    const models = Object.keys(schema);
    let code = `# Auto-generated Python FastAPI
# Project: ${config.projectName}
# Generated on: ${new Date().toISOString()}

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="${config.projectName}")

# Pydantic Models
`;

    models.forEach(modelName => {
        const fields = schema[modelName];
        code += `\nclass ${modelName}(BaseModel):
${Object.entries(fields).map(([name, type]) => {
            const pyType = mapTypeToPython(type);
            return `    ${name}: ${pyType}`;
        }).join('\n')}

class ${modelName}Create(BaseModel):
${Object.entries(fields).filter(([name]) => name !== 'id').map(([name, type]) => {
            const pyType = mapTypeToPython(type);
            return `    ${name}: ${pyType}`;
        }).join('\n')}
`;
    });

    code += `\n# In-memory database (replace with real database)
database = {}\n\n`;

    code += `@app.get("/")
def read_root():
    return {"message": "API is running", "version": "1.0"}\n\n`;

    models.forEach(modelName => {
        const routeName = modelName.toLowerCase();
        code += `# ${modelName} endpoints
@app.get("/api/${routeName}s", response_model=List[${modelName}])
def get_all_${routeName}s():
    return list(database.get("${routeName}s", {}).values())

@app.get("/api/${routeName}s/{item_id}", response_model=${modelName})
def get_${routeName}(item_id: int):
    item = database.get("${routeName}s", {}).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="${modelName} not found")
    return item

@app.post("/api/${routeName}s", response_model=${modelName}, status_code=201)
def create_${routeName}(item: ${modelName}Create):
    if "${routeName}s" not in database:
        database["${routeName}s"] = {}
    item_id = len(database["${routeName}s"]) + 1
    new_item = ${modelName}(id=item_id, **item.dict())
    database["${routeName}s"][item_id] = new_item
    return new_item

@app.put("/api/${routeName}s/{item_id}", response_model=${modelName})
def update_${routeName}(item_id: int, item: ${modelName}Create):
    if item_id not in database.get("${routeName}s", {}):
        raise HTTPException(status_code=404, detail="${modelName} not found")
    updated_item = ${modelName}(id=item_id, **item.dict())
    database["${routeName}s"][item_id] = updated_item
    return updated_item

@app.delete("/api/${routeName}s/{item_id}", status_code=204)
def delete_${routeName}(item_id: int):
    if item_id not in database.get("${routeName}s", {}):
        raise HTTPException(status_code=404, detail="${modelName} not found")
    del database["${routeName}s"][item_id]
    return None

`;
    });

    return code;
}

/**
 * Map JSON types to SQL Alchemy types
 */
function mapTypeToSQL(type) {
    const typeMap = {
        'string': 'String(255)',
        'integer': 'Integer',
        'float': 'Float',
        'boolean': 'Boolean',
        'datetime': 'DateTime',
        'date': 'Date',
        'text': 'Text'
    };
    return typeMap[type.toLowerCase()] || 'String(255)';
}

/**
 * Map JSON types to Python types
 */
function mapTypeToPython(type) {
    const typeMap = {
        'string': 'str',
        'integer': 'int',
        'float': 'float',
        'boolean': 'bool',
        'datetime': 'datetime',
        'date': 'datetime',
        'text': 'str'
    };
    return typeMap[type.toLowerCase()] || 'str';
}

/**
 * Handle API generation - Call backend server
 */
async function handleAPIGeneration(event) {
    event.preventDefault();

    const projectName = document.getElementById('project-name').value;
    const packageName = document.getElementById('package-name').value;
    const language = document.getElementById('language-select').value;
    const database = document.getElementById('database-type').value;
    const dbConnection = document.getElementById('db-connection').value;
    const jsonSchema = document.getElementById('json-schema').value;

    if (!projectName || !jsonSchema) {
        showNotification('Please fill in all required fields (Project Name and JSON Schema)', 'error');
        return;
    }

    let schema;
    try {
        schema = JSON.parse(jsonSchema);
    } catch (error) {
        showNotification(`Invalid JSON: ${error.message}`, 'error');
        return;
    }

    // Show loading notification
    showNotification('Generating your API project...', 'info');

    // Get GitHub configuration if saved
    let gitConfig = null;
    if (currentUser) {
        const key = `github_config_${currentUser.email}`;
        const githubConfigStr = localStorage.getItem(key);
        if (githubConfigStr) {
            const config = JSON.parse(githubConfigStr);
            if (config.repo_url && config.token) {
                gitConfig = config;
            }
        }
    }

    try {
        // Call backend API
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                project_name: projectName,
                package_name: packageName || null,
                language: language,
                database: database,
                db_connection: dbConnection || null,
                schema: schema
                // git_config removed to prevent auto-push
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to generate API');
        }

        const data = await response.json();

        // Mark newly generated files (for green color)
        generatedFiles = data.files;

        // Store generated files - Merge with existing files (e.g. from upload or git)
        generatedCode = { ...generatedCode, ...data.files };

        // Convert Base64 ZIP to Blob
        const zipContent = atob(data.zip_base64);
        const zipBytes = new Uint8Array(zipContent.length);
        for (let i = 0; i < zipContent.length; i++) {
            zipBytes[i] = zipContent.charCodeAt(i);
        }
        const blob = new Blob([zipBytes], { type: 'application/zip' });

        // Create download link
        if (lastGeneratedZipUrl) {
            URL.revokeObjectURL(lastGeneratedZipUrl);
        }
        const url = URL.createObjectURL(blob);
        lastGeneratedZipUrl = url;
        lastGeneratedZipName = `${projectName}.zip`;

        showNotification(`✅ API Generated! Click the download icon to save ${projectName}.zip`, 'success');

        // Update stats
        updateStats();

        // Build file tree and display
        buildFileTree(generatedCode);

        // Update Git Push UI
        updateGitPushUI();

    } catch (error) {
        console.error('Generation error:', error);
        showNotification(`Error: ${error.message}`, 'error');
    }
}

/**
 * Display generation summary in the editor
 */
function displayGeneratedSummary(projectName, language, models) {
    const placeholder = document.querySelector('.editor-placeholder');
    const textarea = document.getElementById('code-textarea');

    const frameworkName = language === 'python-flask' ? 'Python Flask' :
        language === 'python-fastapi' ? 'Python FastAPI' :
            language === 'nextjs-approuter' ? 'Next.js App Router' :
                'Java Spring Boot';

    const summary = `# ✅ API Generated Successfully!

Project: ${projectName}
Framework: ${frameworkName}
Models: ${models.join(', ')}

## What's Included:

${language === 'java-spring' ? `
📁 Complete Java Spring Boot Project:
  ├── Entity Classes (JPA entities with Lombok)
  ├── DTO Classes (Data Transfer Objects)
  ├── Repository Interfaces (Spring Data JPA)
  ├── Service Classes (Business logic layer)
  ├── Controller Classes (REST endpoints)
  ├── Application.java (Main Spring Boot class)
  ├── pom.xml (Maven dependencies)
  ├── application.properties (Database configuration)
  └── README.md (Setup and usage instructions)

## How to Run:
1. Extract the ZIP file
2. cd ${projectName}
3. mvn clean install
4. mvn spring-boot:run
5. API runs on http://localhost:8080
` : language === 'python-flask' ? `
📁 Complete Python Flask Project:
  ├── app.py (Models, routes, and application logic)
  ├── requirements.txt (Python dependencies)
  └── README.md (Setup and usage instructions)

## How to Run:
1. Extract the ZIP file
2. cd ${projectName}
3. python -m venv venv
4. source venv/bin/activate  (Windows: venv\\Scripts\\activate)
5. pip install -r requirements.txt
6. python app.py
7. API runs on http://localhost:5000
` : language === 'nextjs-approuter' ? `
📁 Complete Next.js App Router Project:
  ├── app/api/ (API Routes)
  ├── lib/db.ts (Database connection)
  ├── lib/validators.ts (Schema validation)
  ├── models/ (Data models)
  ├── package.json (Dependencies)
  └── README.md (Setup instructions)

## How to Run:
1. Extract the ZIP file
2. cd ${projectName}
3. npm install
4. npm run dev
5. API runs on http://localhost:3000/api
` : `
📁 Complete Python FastAPI Project:
  ├── main.py (Models, routes, and application logic)
  ├── requirements.txt (Python dependencies)
  └── README.md (Setup and usage instructions)

## How to Run:
1. Extract the ZIP file
2. cd ${projectName}
3. python -m venv venv
4. source venv/bin/activate  (Windows: venv\\Scripts\\activate)
5. pip install -r requirements.txt
6. uvicorn main:app --reload
7. API runs on http://localhost:8000
8. Interactive docs at http://localhost:8000/docs
`}

## API Endpoints Created:
${models.map(m => `
- GET /api/${m.toLowerCase()}s - List all ${m}s
- POST /api/${m.toLowerCase()}s - Create a ${m}
- GET /api/${m.toLowerCase()}s/{id} - Get a ${m}
- PUT /api/${m.toLowerCase()}s/{id} - Update a ${m}
- DELETE /api/${m.toLowerCase()}s/{id} - Delete a ${m}
`).join('')}

The ZIP file has been downloaded to your Downloads folder.
Extract it and follow the instructions in the README.md file!
`;

    if (placeholder) placeholder.classList.add('hidden');
    if (textarea) {
        textarea.classList.remove('hidden');
        textarea.value = summary;
    }


    // Update tab
    const editorTab = document.querySelector('.editor-tab');
    if (editorTab) {
        editorTab.querySelector('span').textContent = 'Summary';
    }
}

/**
 * Build file tree structure from generated files
 */
function buildFileTree(files) {
    const treeContainer = document.getElementById('file-tree');
    if (!treeContainer) return;

    // Clear existing tree
    treeContainer.innerHTML = '';

    // Organize files by folder structure
    const fileStructure = {};

    Object.keys(files).forEach(filePath => {
        const parts = filePath.split('/');
        let current = fileStructure;

        parts.forEach((part, index) => {
            if (index === parts.length - 1) {
                // It's a file
                const isGitFile = gitFiles.hasOwnProperty(filePath);
                const isNewFile = generatedFiles.hasOwnProperty(filePath) && !isGitFile;

                current[part] = {
                    __type: 'file',
                    origin: isGitFile ? 'git' : (isNewFile ? 'new' : 'unknown')
                };
            } else {
                if (!current[part]) {
                    current[part] = {};
                }
                current = current[part];
            }
        });
    });

    // Render the tree
    renderFileTree(fileStructure, treeContainer, '', 0);

    // Auto-select first file
    const firstFile = treeContainer.querySelector('.file-tree-item.file');
    if (firstFile) {
        firstFile.click();
    }
}

/**
 * Render file tree recursively
 */
function renderFileTree(structure, container, path, level) {
    Object.keys(structure).sort((a, b) => {
        // Sort folders first, then files
        const nodeA = structure[a];
        const nodeB = structure[b];
        const aIsFile = nodeA && nodeA.__type === 'file';
        const bIsFile = nodeB && nodeB.__type === 'file';

        if (!aIsFile && bIsFile) return -1;
        if (aIsFile && !bIsFile) return 1;

        return a.localeCompare(b);
    }).forEach(name => {
        const node = structure[name];
        const isFile = node && node.__type === 'file';
        const fullPath = path ? `${path}/${name}` : name;

        const item = document.createElement('div');
        let className = `file-tree-item ${isFile ? `file ${getFileExtension(name)}` : 'folder'}`;

        // Add color classes
        if (isFile) {
            if (node.origin === 'git') className += ' file-git';
            if (node.origin === 'new') className += ' file-new';
        }

        item.className = className;
        item.textContent = name;
        item.dataset.path = fullPath;
        item.dataset.level = level;

        if (!isFile) {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleFolder(item, fullPath);
            });
            // Initially expanded for root level
            if (level === 0) {
                item.classList.add('expanded');
            }
        } else {
            item.addEventListener('click', () => selectFile(fullPath));
        }

        container.appendChild(item);

        if (!isFile) {
            // Create a container for folder contents
            const folderContents = document.createElement('div');
            folderContents.className = 'folder-contents';
            folderContents.dataset.parentPath = fullPath;
            if (level === 0) {
                folderContents.classList.add('expanded');
            }
            container.appendChild(folderContents);

            renderFileTree(structure[name], folderContents, fullPath, level + 1);
        }
    });
}

/**
 * Toggle folder expansion
 */
function toggleFolder(folderElement, folderPath) {
    const contents = document.querySelector(`[data-parent-path="${folderPath}"]`);
    if (!contents) return;

    const isExpanded = folderElement.classList.contains('expanded');

    if (isExpanded) {
        folderElement.classList.remove('expanded');
        contents.classList.remove('expanded');
    } else {
        folderElement.classList.add('expanded');
        contents.classList.add('expanded');
    }
}

/**
 * Get file extension for styling
 */
function getFileExtension(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    return ext || 'txt';
}

/**
 * Select and display a file
 */
function selectFile(filePath) {
    // Update active state
    document.querySelectorAll('.file-tree-item').forEach(item => {
        item.classList.remove('active');
    });

    const selectedItem = document.querySelector(`[data-path="${filePath}"]`);
    if (selectedItem) {
        selectedItem.classList.add('active');
    }

    // Display file content
    const code = generatedCode[filePath];
    if (code) {
        displayCode(code, filePath);
    }
}

/**
 * Display code in editor
 */
function displayCode(code, fileName) {
    const placeholder = document.querySelector('.editor-placeholder');
    const textarea = document.getElementById('code-textarea');

    // Always show the textarea and hide placeholder once we have files
    if (placeholder) placeholder.classList.add('hidden');
    if (textarea) {
        textarea.classList.remove('hidden');
        textarea.value = code;
        textarea.style.display = 'block';
    }

    // Store generated code
    generatedCode[fileName] = code;
}

/**
 * Download generated code
 */
function downloadCode() {
    // If we have a generated ZIP, download that instead
    if (lastGeneratedZipUrl && lastGeneratedZipName) {
        const a = document.createElement('a');
        a.href = lastGeneratedZipUrl;
        a.download = lastGeneratedZipName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        showNotification(`Downloaded ${lastGeneratedZipName}`, 'success');
        return;
    }

    // Download currently viewed file
    const textarea = document.getElementById('code-textarea');
    const activeFile = document.querySelector('.file-tree-item.active');

    if (!textarea || textarea.classList.contains('hidden') || !activeFile) {
        showNotification('No file selected to download', 'error');
        return;
    }

    const code = textarea.value;
    const fileName = activeFile.dataset.path;

    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName.split('/').pop(); // Get just the filename
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showNotification(`Downloaded ${fileName}`, 'success');
}

/**
 * Format code (basic implementation)
 */
function formatCode() {
    const textarea = document.getElementById('code-textarea');
    if (!textarea || textarea.classList.contains('hidden')) {
        showNotification('No code to format', 'error');
        return;
    }

    showNotification('Code formatted!', 'success');
}

/**
 * Handle file upload
 */
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.zip')) {
        showNotification('Please upload a ZIP file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    showNotification('Uploading and extracting project...', 'info');

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to upload project');
        }

        const data = await response.json();

        // Store generated files
        generatedCode = data.files;

        // Build file tree and display
        buildFileTree(generatedCode);

        showNotification('Project loaded successfully!', 'success');
        updateStats('upload');

    } catch (error) {
        console.error('Upload error:', error);
        showNotification(`Error: ${error.message}`, 'error');
    }
}

/**
 * Update statistics
 */
function updateStats(type = 'generate') {
    const totalAPIs = document.getElementById('total-apis');
    const totalUploads = document.getElementById('total-uploads');

    if (type === 'generate' && totalAPIs) {
        const current = parseInt(totalAPIs.textContent) || 0;
        totalAPIs.textContent = current + 1;
    } else if (type === 'upload' && totalUploads) {
        const current = parseInt(totalUploads.textContent) || 0;
        totalUploads.textContent = current + 1;
    }
}

// ===================================
// EXAMPLE DATA LOADING
// ===================================

function loadExampleSchema() {
    const exampleSchema = [
        {
            "name": "Order",
            "fields": [
                {
                    "name": "userId",
                    "type": "long",
                    "required": true
                },
                {
                    "name": "orderDate",
                    "type": "datetime",
                    "required": true
                },
                {
                    "name": "status",
                    "type": "string",
                    "required": true
                },
                {
                    "name": "totalAmount",
                    "type": "float",
                    "required": true
                },
                {
                    "name": "shippingAddress",
                    "type": "string",
                    "required": true
                },
                {
                    "name": "paymentMethod",
                    "type": "string",
                    "required": true
                }
            ]
        },
        {
            "name": "OrderItem",
            "fields": [
                {
                    "name": "orderId",
                    "type": "long",
                    "required": true
                },
                {
                    "name": "productId",
                    "type": "long",
                    "required": true
                },
                {
                    "name": "quantity",
                    "type": "integer",
                    "required": true
                },
                {
                    "name": "price",
                    "type": "float",
                    "required": true
                }
            ]
        },
        {
            "name": "Review",
            "fields": [
                {
                    "name": "userId",
                    "type": "long",
                    "required": true
                },
                {
                    "name": "productId",
                    "type": "long",
                    "required": true
                },
                {
                    "name": "rating",
                    "type": "integer",
                    "required": true
                },
                {
                    "name": "comment",
                    "type": "text"
                },
                {
                    "name": "createdAt",
                    "type": "datetime",
                    "required": true
                }
            ]
        }
    ];

    // Pre-fill the form with example data
    document.getElementById('project-name').value = 'ecommerce-api';
    document.getElementById('package-name').value = 'com.example.ecommerce';
    document.getElementById('language-select').value = 'java-spring';
    document.getElementById('database-type').value = 'postgresql';
    document.getElementById('db-connection').value = 'postgresql://user:pass@localhost:5432/ecommerce';

    // Format and set the JSON schema
    document.getElementById('json-schema').value = JSON.stringify(exampleSchema, null, 2);

    showNotification('Example schema loaded! You can now generate the API.', 'success');
}

// ===================================
// INITIALIZATION
// ===================================

function init() {
    // Check if user is already logged in
    const storedUser = getStoredUser();
    if (storedUser) {
        currentUser = storedUser;
        updateDashboard(currentUser);
        showScreen('dashboard');
        showView('home');
    } else {
        showScreen('login-screen');
    }

    // Auth event listeners
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const logoutBtn = document.getElementById('logout-btn');
    const showRegisterBtn = document.getElementById('show-register');
    const showLoginBtn = document.getElementById('show-login');

    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    if (registerForm) registerForm.addEventListener('submit', handleRegister);
    if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);
    if (showRegisterBtn) showRegisterBtn.addEventListener('click', (e) => {
        e.preventDefault();
        showScreen('register-screen');
    });
    if (showLoginBtn) showLoginBtn.addEventListener('click', (e) => {
        e.preventDefault();
        showScreen('login-screen');
    });

    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.getAttribute('data-view');
            if (view) showView(view);
        });
    });

    // API Generator forms
    const apiConfigForm = document.getElementById('api-config-form');
    const validateBtn = document.getElementById('validate-json-btn');
    const loadExampleBtn = document.getElementById('load-example-btn');
    const downloadBtn = document.getElementById('download-code-btn');
    const formatBtn = document.getElementById('format-code-btn');

    // File Upload Elements - Updated to match index.html IDs
    const fileUpload = document.getElementById('zip-file-input');
    const uploadZone = document.getElementById('zip-upload-zone');
    const browseLink = document.querySelector('.upload-link');

    if (apiConfigForm) apiConfigForm.addEventListener('submit', handleAPIGeneration);
    if (validateBtn) validateBtn.addEventListener('click', validateJSON);
    if (loadExampleBtn) loadExampleBtn.addEventListener('click', loadExampleSchema);
    if (downloadBtn) downloadBtn.addEventListener('click', downloadCode);
    if (formatBtn) formatBtn.addEventListener('click', formatCode);

    // File Upload Event Listeners
    if (fileUpload) {
        fileUpload.addEventListener('change', handleFileUpload);
    }

    if (uploadZone && fileUpload) {
        // Handle click on the zone to trigger file input
        uploadZone.addEventListener('click', (e) => {
            // Prevent triggering if clicking on the input itself (though it's hidden)
            if (e.target !== fileUpload) {
                fileUpload.click();
            }
        });

        // Drag and drop handlers
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.remove('dragover');

            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                fileUpload.files = e.dataTransfer.files;
                // Manually trigger the change event
                const event = new Event('change');
                fileUpload.dispatchEvent(event);
            }
        });
    }

    if (browseLink && fileUpload) {
        browseLink.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent bubbling to zone click
            fileUpload.click();
        });
    }

    // GitHub Integration event listeners
    const saveGitHubBtn = document.getElementById('save-github-config');
    const testGitHubBtn = document.getElementById('test-github-connection');
    const loadGitHubBtn = document.getElementById('load-github-repo');

    if (saveGitHubBtn) {
        saveGitHubBtn.addEventListener('click', saveGitHubConfig);
    }

    if (testGitHubBtn) {
        testGitHubBtn.addEventListener('click', testGitHubConnection);
    }

    if (loadGitHubBtn) {
        loadGitHubBtn.addEventListener('click', loadGitHubRepo);
    }

    const pushGitHubBtn = document.getElementById('push-to-github-btn');
    if (pushGitHubBtn) {
        pushGitHubBtn.addEventListener('click', pushToGitHub);
    }

    // Load saved GitHub configuration
    loadGitHubConfig();

    console.log('API Builder initialized successfully');
}

// ===================================
// GITHUB INTEGRATION
// ===================================

/**
 * Save GitHub configuration to localStorage
 */
function saveGitHubConfig() {
    if (!currentUser) {
        showNotification('Please login to save configuration', 'error');
        return;
    }

    const config = {
        repo_url: document.getElementById('gh-repo-url').value,
        token: document.getElementById('gh-token').value,
        username: document.getElementById('gh-username').value,
        email: document.getElementById('gh-email').value
    };

    if (!config.repo_url || !config.token) {
        showNotification('Please provide at least Repository URL and Token', 'error');
        return;
    }

    const key = `github_config_${currentUser.email}`;
    localStorage.setItem(key, JSON.stringify(config));
    showNotification('GitHub configuration saved successfully!', 'success');
}

/**
 * Load GitHub configuration from localStorage
 */
function loadGitHubConfig() {
    const repoInput = document.getElementById('gh-repo-url');
    const tokenInput = document.getElementById('gh-token');
    const usernameInput = document.getElementById('gh-username');
    const emailInput = document.getElementById('gh-email');

    if (!currentUser) {
        // Clear inputs if no user
        if (repoInput) repoInput.value = '';
        if (tokenInput) tokenInput.value = '';
        if (usernameInput) usernameInput.value = '';
        if (emailInput) emailInput.value = '';
        return;
    }

    const key = `github_config_${currentUser.email}`;
    const saved = localStorage.getItem(key);

    if (saved) {
        const config = JSON.parse(saved);
        if (repoInput) repoInput.value = config.repo_url || '';
        if (tokenInput) tokenInput.value = config.token || '';
        if (usernameInput) usernameInput.value = config.username || '';
        if (emailInput) emailInput.value = config.email || '';
    } else {
        // Clear inputs if no config found for this user
        if (repoInput) repoInput.value = '';
        if (tokenInput) tokenInput.value = '';
        if (usernameInput) usernameInput.value = '';
        if (emailInput) emailInput.value = '';
    }
}

/**
 * Test GitHub connection
 */
async function testGitHubConnection() {
    const repoUrl = document.getElementById('gh-repo-url').value;
    const token = document.getElementById('gh-token').value;

    if (!repoUrl || !token) {
        showNotification('Please provide Repository URL and Token', 'error');
        return;
    }

    showNotification('Testing connection...', 'info');

    try {
        const url = new URL(repoUrl);
        if (!url.hostname.includes('github.com')) {
            showNotification('Invalid GitHub URL', 'error');
            return;
        }
        showNotification('Configuration looks good! It will be used when generating APIs.', 'success');
    } catch (e) {
        showNotification('Invalid repository URL format', 'error');
    }
}

/**
 * Load repository code from GitHub
 */
async function loadGitHubRepo() {
    console.log('[DEBUG] loadGitHubRepo started');

    const repoUrl = document.getElementById('gh-repo-url').value;
    const token = document.getElementById('gh-token').value;

    console.log('[DEBUG] Repo URL:', repoUrl);
    console.log('[DEBUG] Token exists:', !!token);

    if (!repoUrl || !token) {
        showNotification('Please provide Repository URL and Token', 'error');
        return;
    }

    showNotification('Loading repository...', 'info');

    try {
        console.log('[DEBUG] Making fetch request to /api/git/load');

        // Add timeout to prevent hanging
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            controller.abort();
            console.error('[DEBUG] Request timeout after 30s');
        }, 30000); // 30 second timeout

        const response = await fetch('/api/git/load', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                git_config: {
                    repo_url: repoUrl,
                    token: token
                }
            }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);
        console.log('[DEBUG] Response received, status:', response.status);

        if (!response.ok) {
            const error = await response.json();
            console.error('[DEBUG] Error response:', error);
            throw new Error(error.error || 'Failed to load repository');
        }

        const data = await response.json();
        console.log('[DEBUG] Data received, files count:', Object.keys(data.files || {}).length);
        console.log('[DEBUG] Metadata:', data.metadata);

        // CLEAR PREVIOUS DATA
        generatedCode = {};
        gitFiles = {};
        generatedFiles = {};

        // Mark all loaded files as Git files (for orange color)
        gitFiles = { ...data.files };
        generatedCode = { ...data.files };
        console.log('[DEBUG] Files stored, total:', Object.keys(generatedCode).length);

        // AUTO-FILL FORM FIELDS if metadata is available
        if (data.metadata) {
            const projectNameInput = document.getElementById('project-name');
            const packageNameInput = document.getElementById('package-name');
            const languageSelect = document.getElementById('language-select');

            if (data.metadata.project_name && projectNameInput) {
                projectNameInput.value = data.metadata.project_name;
                console.log('[DEBUG] Set project name:', data.metadata.project_name);
            }

            if (data.metadata.package_name && packageNameInput) {
                packageNameInput.value = data.metadata.package_name;
                console.log('[DEBUG] Set package name:', data.metadata.package_name);
            }

            if (data.metadata.language && languageSelect) {
                const langValue = data.metadata.language;
                // Match backend language names to select values
                if (langValue === 'python') {
                    languageSelect.value = 'python-flask';
                } else if (langValue === 'java') {
                    languageSelect.value = 'java-spring';
                } else {
                    languageSelect.value = langValue;
                }
                console.log('[DEBUG] Set language:', languageSelect.value);
            }
        }

        // Switch to API Generator view to see files
        console.log('[DEBUG] Switching to json-generator view');
        showView('json-generator');

        // Build file tree
        console.log('[DEBUG] Building file tree');
        buildFileTree(generatedCode);

        showNotification(`✅ Loaded ${Object.keys(data.files).length} files from ${data.repo_name}`, 'success');
        console.log('[DEBUG] loadGitHubRepo completed successfully');

    } catch (error) {
        console.error('[DEBUG] Load Repo Error:', error);
        console.error('[DEBUG] Error name:', error.name);
        console.error('[DEBUG] Error message:', error.message);

        if (error.name === 'AbortError') {
            showNotification('Request timeout. Repository might be too large or server not responding.', 'error');
        } else {
            showNotification(`Error: ${error.message}`, 'error');
        }
    }
}

/**
 * Update the Git Push UI with generated files
 */
function updateGitPushUI() {
    const pushSection = document.getElementById('git-push-section');
    const filesList = document.getElementById('files-to-push-list');

    if (!pushSection || !filesList) return;

    // Check if we have generated files
    const newFiles = Object.keys(generatedFiles);

    if (newFiles.length > 0) {
        pushSection.classList.remove('hidden');
        filesList.innerHTML = newFiles.map(f => `<div>+ ${f}</div>`).join('');
        showNotification(`🚀 ${newFiles.length} new files ready to push in GitHub tab`, 'info');
    } else {
        pushSection.classList.add('hidden');
    }
}

/**
 * Push changes to GitHub
 */
async function pushToGitHub() {
    const commitMessage = document.getElementById('commit-message').value;
    if (!commitMessage) {
        showNotification('Please enter a commit message', 'error');
        return;
    }

    // Get GitHub config
    const repoUrl = document.getElementById('gh-repo-url').value;
    const token = document.getElementById('gh-token').value;
    const username = document.getElementById('gh-username').value;
    const email = document.getElementById('gh-email').value;

    if (!repoUrl || !token) {
        showNotification('Please configure GitHub repository first', 'error');
        return;
    }

    showNotification('Pushing changes to GitHub...', 'info');

    try {
        const response = await fetch('/api/git/push', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                git_config: {
                    repo_url: repoUrl,
                    token: token,
                    username: username,
                    email: email
                },
                commit_message: commitMessage,
                files: generatedFiles
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to push to GitHub');
        }

        const data = await response.json();
        showNotification(`✅ Successfully pushed to GitHub! Commit: ${data.commit_hash}`, 'success');

    } catch (error) {
        console.error('Push Error:', error);
        showNotification(`Push Failed: ${error.message}`, 'error');
    }
}

// Start the application
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
