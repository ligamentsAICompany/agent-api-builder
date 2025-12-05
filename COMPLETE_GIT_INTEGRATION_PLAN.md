# Complete Implementation: Git Repository Integration

## User Requirements

### 1. Auto-Load Project Metadata from Git Repository
When loading a Git repository, automatically:
- Extract **project name** from configuration files
- Extract **package name** from code files
- Auto-fill these values in the API Generator form

### 2. Maintain File Structure
- Display loaded Git files in the same **three-column layout** as generated files
- Use the **same file tree structure**
- Allow clicking files to view code

### 3. Smart File Merging
When generating new APIs after loading Git repo:
- **Keep** all existing Git files
- **Add** newly generated files
- **Color code**:
  - 🟠 Orange = Files from Git (existing)
  - 🟢 Green = Newly generated files

## Implementation Steps

### Step 1: Backend - Extract Project Metadata

Modify `/api/git/load` endpoint to extract metadata:

```python
@app.route('/api/git/load', methods=['POST'])
def load_git_repo():
    # ... existing code ...
    
    # NEW: Extract project metadata
    metadata = extract_project_metadata(repo_path)
    
    return jsonify({
        'message': 'Repository loaded successfully',
        'repo_name': repo_name,
        'files': files,
        'metadata': metadata  # NEW
    })

def extract_project_metadata(repo_path):
    """Extract project name and package from repository files"""
    metadata = {
        'project_name': None,
        'package_name': None,
        'language': None
    }
    
    # Check for Python projects
    if os.path.exists(os.path.join(repo_path, 'requirements.txt')):
        metadata['language'] = 'python'
        # Try to get from setup.py or pyproject.toml
        setup_py = os.path.join(repo_path, 'setup.py')
        if os.path.exists(setup_py):
            with open(setup_py, 'r') as f:
                content = f.read()
                # Extract name from setup(name='...')
                import re
                match = re.search(r"name=['\"]([^'\"]+)['\"]", content)
                if match:
                    metadata['project_name'] = match.group(1)
    
    # Check for Java/Spring projects
    elif os.path.exists(os.path.join(repo_path, 'pom.xml')):
        metadata['language'] = 'java-spring'
        pom_path = os.path.join(repo_path, 'pom.xml')
        with open(pom_path, 'r') as f:
            content = f.read()
            # Extract artifactId
            import re
            match = re.search(r'<artifactId>([^<]+)</artifactId>', content)
            if match:
                metadata['project_name'] = match.group(1)
            # Extract groupId
            match = re.search(r'<groupId>([^<]+)</groupId>', content)
            if match:
                metadata['package_name'] = match.group(1)
    
    # Scan Python files for package structure
    if metadata['language'] == 'python' and not metadata['package_name']:
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        content = f.read()
                        # Look for package imports
                        match = re.search(r'from\s+(\w+)\.\w+\s+import', content)
                        if match:
                            metadata['package_name'] = match.group(1)
                            break
            if metadata['package_name']:
                break
    
    # Fallback to repo name
    if not metadata['project_name']:
        metadata['project_name'] = os.path.basename(repo_path)
    
    return metadata
```

### Step 2: Frontend - Auto-Fill Form Fields

Modify `loadGitH

ubRepo()` in `app.js`:

```javascript
async function loadGitHubRepo() {
    // ... existing code ...
    
    const data = await response.json();
    
    // Mark files as from Git (for color coding)
    gitFiles = data.files;
    generatedCode = {...data.files};
    
    // NEW: Auto-fill project metadata
    if (data.metadata) {
        const projectNameInput = document.getElementById('project-name');
        const packageNameInput = document.getElementById('package-name');
        const languageSelect = document.getElementById('language-select');
        
        if (data.metadata.project_name && projectNameInput) {
            projectNameInput.value = data.metadata.project_name;
        }
        
        if (data.metadata.package_name && packageNameInput) {
            packageNameInput.value = data.metadata.package_name;
        }
        
        if (data.metadata.language && languageSelect) {
            languageSelect.value = data.metadata.language;
        }
    }
    
    // Switch to API Generator view and show files
    showView('json-generator');
    buildFileTree(generatedCode);
    
    showNotification(`✅ Loaded ${Object.keys(data.files).length} files from ${data.repo_name}`, 'success');
}
```

### Step 3: File Merging & Color Coding

Add state tracking at the top of `app.js`:

```javascript
// State Management
let currentUser = null;
let generatedCode = {};
let gitFiles = {};        // NEW: Track Git files
let generatedFiles = {};  // NEW: Track generated files
let lastGeneratedZipUrl = null;
let lastGeneratedZipName = null;
let currentView = 'home';
```

Modify `handleAPIGeneration()` to merge files:

```javascript
async function handleAPIGeneration(event) {
    // ... existing code for generation ...
    
    const data = await response.json();
    
    // NEW: Mark newly generated files
    generatedFiles = data.files;
    
    // NEW: Merge with existing Git files instead of replacing
    generatedCode = {...gitFiles, ...data.files};
    
    // ... rest of code ...
    
    // Rebuild file tree with color coding
    buildFileTree(generatedCode);
}
```

Modify `buildFileTree()` to add file origin markers:

```javascript
function buildFileTree(files) {
    const structure = {};
    
    for (const [filePath, content] of Object.entries(files)) {
        const parts = filePath.split('/');
        let current = structure;
        
        for (let i = 0; i < parts.length; i++) {
            const part = parts[i];
            
            if (i === parts.length - 1) {
                // It's a file
                // NEW: Determine file origin
                const isGitFile = gitFiles.hasOwnProperty(filePath);
                const isNewFile = generatedFiles.hasOwnProperty(filePath) && !isGitFile;
                
                current[part] = {
                    type: 'file',
                    path: filePath,
                    content: content,
                    origin: isGitFile ? 'git' : (isNewFile ? 'new' : 'unknown')  // NEW
                };
            } else {
                // It's a folder
                if (!current[part]) {
                    current[part] = { type: 'folder', children: {} };
                }
                current = current[part].children;
            }
        }
    }
    
    // Render tree
    const treeContainer = document.getElementById('file-tree');
    treeContainer.innerHTML = '';
    renderFileTree(structure, treeContainer, '', 0);
}
```

Modify `renderFileTree()` to apply colors:

```javascript
function renderFileTree(structure, container, path, level) {
    for (const [name, node] of Object.entries(structure)) {
        if (node.type === 'file') {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            // NEW: Add color class based on origin
            if (node.origin === 'git') {
                fileItem.classList.add('file-git');  // Orange
            } else if (node.origin === 'new') {
                fileItem.classList.add('file-new');  // Green
            }
            
            const fileIcon = getFileIcon(name);
            fileItem.innerHTML = `${fileIcon} ${name}`;
            fileItem.style.paddingLeft = `${(level + 1) * 20}px`;
            fileItem.onclick = () => selectFile(node.path);
            container.appendChild(fileItem);
        }
        // ... folder handling ...
    }
}
```

### Step 4: CSS for Color Coding

Add to `styles.css`:

```css
/* Git files - Orange */
.file-git {
    color: #ff9800 !important;
}

.file-git:hover {
    color: #ffb74d !important;
}

/* Newly generated files - Green */
.file-new {
    color: #4caf50 !important;
}

.file-new:hover {
    color: #66bb6a !important;
}
```

## User Workflow

### Scenario 1: Load Existing Project
1. User clicks "GitHub" tab
2. Enters repo URL and token
3. Clicks "📂 Load Repository Code"
4. System:
   - Loads all files (orange color)
   - Auto-fills project name, package name
   - Switches to API Generator view
   - Shows file structure in middle panel

### Scenario 2: Generate New APIs
1. User modifies JSON schema
2. Clicks "Generate API"
3. System:
   - Generates new files (green color)
   - **Merges** with existing Git files
   - Shows **both** in file tree:
     - 🟠 Orange = Original files from Git
     - 🟢 Green = Newly added files
   - Pushes all files to GitHub

## Benefits

✅ **No data lost** - All Git files preserved  
✅ **Visual clarity** - Colors show file origin  
✅ **Auto-configuration** - No manual entry needed  
✅ **Seamless workflow** - Load → Modify → Generate → Push  

## Next Steps

Would you like me to implement this complete solution?
