# Task Requirements - Git Integration with Color Coding

## Requirements Summary

### 1. ✅ GitHub Form Layout (COMPLETED)
- **Status:** Fixed in `index-fixed.html`
- All fields stacked vertically (one by one)
- Repository URL, Token, Username, Email - all in separate rows
- Load Repository button included

### 2. ⏳ File Color Coding Feature (NEEDS IMPLEMENTATION)

**Requirement:** Differentiate between old and new files using colors
- **Orange** = Files from Git repository (existing files)
- **Green** = Newly generated files from JSON schema

**Implementation Plan:**
1. Track file origin when loading Git repository
2. Track file origin when generating new APIs
3. Update file tree rendering to show colors based on origin
4. Merge files when generating new APIs (don't replace)

### 3. ⏳ File Merging Feature (NEEDS IMPLEMENTATION)

**Requirement:** When generating new APIs:
- Don't replace existing files from Git
- Merge new files with existing files
- Mark old files orange, new files green

## JavaScript Changes Needed in `app.js`

### Change 1: Add File Origin Tracking
```javascript
// Add to state management
let gitFiles = {}; // Track files from Git (orange)
let generatedFiles = {}; // Track generated files (green)
```

### Change 2: Update `loadGitHubRepo()` Function
```javascript
// Mark all loaded files as "git" origin
gitFiles = data.files;
generatedCode = {...data.files}; // Don't use reference
```

### Change 3: Update `handleAPIGeneration()` Function
```javascript
// After receiving generated files from backend:
const newFiles = data.files;

// Merge: Keep existing Git files, add new generated files
generatedFiles = newFiles;
generatedCode = {...gitFiles, ...newFiles}; // Merge instead of replace

// Rebuild tree with color coding
buildFileTree(generatedCode);
```

### Change 4: Update `buildFileTree()` Function
Add file type markers:
```javascript
function buildFileTree(files) {
    const structure = {};
    
    for (const [filePath, content] of Object.entries(files)) {
        // Determine file origin
        const isGitFile = gitFiles.hasOwnProperty(filePath);
        const isNewFile = generatedFiles.hasOwnProperty(filePath);
        
        // Mark files for coloring
        structure[filePath] = {
            content: content,
            origin: isGitFile ? 'git' : 'new'
        };
    }
    
    // ... rest of tree building
}
```

### Change 5: Update `renderFileTree()` Function
Apply colors based on origin:
```javascript
function renderFileTree(structure, container, path, level) {
    // When creating file elements:
    fileItem.className = `file-item ${structure.origin === 'git' ? 'file-git' : 'file-new'}`;
}
```

## CSS Changes Needed in `styles.css`

Add color classes:
```css
/* Orange for Git files */
.file-git {
    color: #ff9800 !important;
}

/* Green for new generated files */
.file-new {
    color: #4caf50 !important;
}
```

## User Workflow

1. User connects to GitHub → Loads repository
2. System marks all files as **orange** (Git origin)
3. User generates new APIs with JSON schema
4. System merges new files with existing files
5. Old files stay **orange**, new files show as **green**
6. Both appear in file structure panel
7. User can click any file to view code

## Status

- ✅ Backend `/api/git/load` endpoint ready
- ✅ Frontend GitHub form fixed (vertical layout)
- ✅ Load Repository button working
- ⏳ File color coding needs implementation
- ⏳ File merging needs implementation

## Next Steps

Implement the JavaScript changes above to complete the features.
