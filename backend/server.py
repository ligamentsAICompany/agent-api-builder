"""
Auto API Builder - Backend Server
Python Flask server for handling API generation requests
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import json
import os
import re
from datetime import datetime
import zipfile
import io
import base64
import shutil
from git import Repo, Actor
from github import Github
from openai import OpenAI
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration
GENERATED_DIR = 'generated_apis'
if not os.path.exists(GENERATED_DIR):
    os.makedirs(GENERATED_DIR)

GIT_REPOS_DIR = 'git_repos'
if not os.path.exists(GIT_REPOS_DIR):
    os.makedirs(GIT_REPOS_DIR)

# Initialize API clients (support both OpenAI and Groq)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

openai_client = None
groq_client = None

# Initialize OpenAI client (optional)
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("[INFO] OpenAI client initialized")
    except Exception as e:
        print(f"WARNING: Failed to initialize OpenAI client: {e}")

# Initialize Groq client (preferred for Llama/Mixtral models)
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("[INFO] Groq client initialized")
    except Exception as e:
        print(f"WARNING: Failed to initialize Groq client: {e}")
else:
    print("INFO: GROQ_API_KEY not found. Using OpenAI models. For Llama/Mixtral models, set GROQ_API_KEY in .env")

# Default to Groq if available, otherwise use OpenAI
client = groq_client if groq_client else openai_client
client_type = "groq" if groq_client else "openai" if openai_client else None

if not client:
    print("WARNING: No API client available. Please set GROQ_API_KEY or OPENAI_API_KEY in .env file.")


def cleanup_old_repos(repo_base_name, keep_count=3):
    """
    Clean up old repository directories, keeping only the most recent ones
    to avoid disk space issues.
    """
    import glob
    import shutil

    # Find all directories matching the pattern
    pattern = os.path.join(GIT_REPOS_DIR, f"{repo_base_name}_*")
    repo_dirs = glob.glob(pattern)

    if len(repo_dirs) <= keep_count:
        return

    # Sort by modification time (newest first)
    repo_dirs.sort(key=os.path.getmtime, reverse=True)

    # Remove old ones, keeping only the most recent
    for old_repo in repo_dirs[keep_count:]:
        try:
            shutil.rmtree(old_repo)
        except (OSError, PermissionError):
            # If we can't delete it, just skip it
            pass


def normalize_schema(schema):
    """
    Universal Schema Parser
    Converts various JSON schema formats into a standardized format:
    {'ModelName': {'field_name': 'type', ...}, ...}
    """
    normalized = {}

    def extract_fields(field_data):
        """Helper to extract fields from list or dict"""
        fields = {}
        
        # Case 1: List of fields [{"name": "id", "type": "int"}, ...]
        if isinstance(field_data, list):
            for f in field_data:
                if isinstance(f, dict):
                    name = f.get('name') or f.get('field') or f.get('column')
                    dtype = f.get('type') or f.get('datatype') or 'string'
                    if name:
                        fields[name] = dtype
                        
        # Case 2: Dict of fields {"id": "int", "name": {"type": "str"}}
        elif isinstance(field_data, dict):
            for name, info in field_data.items():
                if isinstance(info, str):
                    fields[name] = info
                elif isinstance(info, dict):
                    fields[name] = info.get('type', 'string')
                    
        return fields

    def process_model(model_data, model_name=None):
        """Helper to process a potential model definition"""
        # Try to find fields using common keys
        field_keys = ['fields', 'properties', 'attributes', 'columns', 'Fields', 'Properties']
        found_fields = None
        
        if isinstance(model_data, dict):
            # Check if name is embedded
            if not model_name:
                model_name = model_data.get('name') or model_data.get('model') or model_data.get('title')
            
            # Look for fields container
            for key in field_keys:
                if key in model_data:
                    found_fields = extract_fields(model_data[key])
                    break
            
            # If no container found, maybe the dict itself is fields (Simple format)
            if not found_fields and model_name:
                # Verify it looks like fields (values are strings or type dicts)
                is_simple = all(isinstance(v, (str, dict)) for v in model_data.values())
                if is_simple:
                    found_fields = extract_fields(model_data)

        if model_name and found_fields:
            # Normalize types
            clean_fields = {}
            for k, v in found_fields.items():
                v = str(v).lower()
                if 'int' in v: v = 'integer'
                elif 'bool' in v: v = 'boolean'
                elif 'date' in v and 'time' in v: v = 'datetime'
                elif 'decimal' in v or 'double' in v or 'number' in v: v = 'float'
                elif 'text' in v: v = 'text'
                else: v = 'string'
                clean_fields[k] = v
            normalized[model_name] = clean_fields

    # Strategy 1: Input is a List (Array of Models)
    if isinstance(schema, list):
        for item in schema:
            process_model(item)

    # Strategy 2: Input is a Dict (Map of Models or OpenAPI)
    elif isinstance(schema, dict):
        # Check for OpenAPI/Swagger structure
        if 'components' in schema and 'schemas' in schema['components']:
            for name, data in schema['components']['schemas'].items():
                process_model(data, name)
        elif 'definitions' in schema:
            for name, data in schema['definitions'].items():
                process_model(data, name)
        else:
            # Check if it's already in normalized format {"ModelName": {"field": "type"}}
            # Check if all values are dicts with string values (already normalized)
            is_already_normalized = (
                len(schema) > 0 and 
                all(isinstance(v, dict) and 
                    all(isinstance(field_val, str) for field_val in v.values()) 
                    for v in schema.values())
            )
            
            if is_already_normalized:
                # Already in the correct format, just normalize types
                for model_name, fields in schema.items():
                    clean_fields = {}
                    for k, v in fields.items():
                        v = str(v).lower()
                        if 'int' in v: v = 'integer'
                        elif 'bool' in v: v = 'boolean'
                        elif 'date' in v and 'time' in v: v = 'datetime'
                        elif 'decimal' in v or 'double' in v or 'number' in v: v = 'float'
                        elif 'text' in v: v = 'text'
                        else: v = 'string'
                        clean_fields[k] = v
                    normalized[model_name] = clean_fields
            else:
                # Check if it's a map of models {"User": {...}, "Order": {...}}
                # or a single model definition {"name": "User", "fields": [...]}
                
                # Try treating as single model first
                process_model(schema)
                
                # If that didn't work, try treating as map of models
                if not normalized:
                    for name, data in schema.items():
                        process_model(data, name)

    # If normalization failed but we have a dict, try to use it as-is (might already be normalized)
    if not normalized and isinstance(schema, dict) and len(schema) > 0:
        # Last resort: assume it's already normalized format
        try:
            if all(isinstance(v, dict) for v in schema.values()):
                normalized = schema
        except:
            pass

    return normalized if normalized else schema  # Return normalized or original


def handle_git_operations(config, generated_files_path):
    """
    Handle Git operations: Clone, Copy, Commit, Push
    """
    git_config = config.get('git_config')
    if not git_config or not git_config.get('repo_url'):
        return None

    repo_url = git_config['repo_url']
    token = git_config.get('token')
    username = git_config.get('username', 'Auto API Builder')
    email = git_config.get('email', 'auto-api@example.com')
    
    # Insert token into URL for authentication
    if token and 'https://' in repo_url:
        auth_url = repo_url.replace('https://', f'https://{token}@')
    else:
        auth_url = repo_url

    repo_name = repo_url.split('/')[-1].replace('.git', '')
    repo_path = os.path.join(GIT_REPOS_DIR, repo_name)
    
    try:
        # Clone or Open Repo
        if os.path.exists(repo_path):
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull()
        else:
            repo = Repo.clone_from(auth_url, repo_path)
            
        # Copy generated files to repo
        for item in os.listdir(generated_files_path):
            s = os.path.join(generated_files_path, item)
            d = os.path.join(repo_path, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
                
        # Git Add, Commit, Push
        repo.git.add(A=True)
        
        if repo.is_dirty():
            author = Actor(username, email)
            repo.index.commit(f"Update API: {config['project_name']}", author=author, committer=author)
            origin = repo.remotes.origin
            origin.push()
            return {"status": "success", "message": "Code pushed to repository"}
        else:
            return {"status": "skipped", "message": "No changes to commit"}
            
    except Exception as e:
        print(f"Git Error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.route('/api/git/load', methods=['POST'])
def load_git_repo():
    """
    Clone/Pull a git repo and return its text files
    """
    try:
        data = request.get_json()
        git_config = data.get('git_config')
        
        if not git_config or not git_config.get('repo_url'):
            return jsonify({'error': 'Missing git configuration'}), 400

        repo_url = git_config['repo_url']
        token = git_config.get('token')

        # Insert token into URL for authentication
        if token and 'https://' in repo_url:
            auth_url = repo_url.replace('https://', f'https://{{token}}@')
        else:
            auth_url = repo_url

        repo_name = repo_url.split('/')[-1].replace('.git', '')

        # Clean up old repositories first
        cleanup_old_repos(repo_name)

        # Use timestamp to create unique directory for fresh clone (avoids Windows file locking)
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        repo_path = os.path.join(GIT_REPOS_DIR, f"{repo_name}_{timestamp}")

        # Clone fresh repository to unique directory
        Repo.clone_from(auth_url, repo_path)
            
        # Read files
        files = {}
        MAX_FILES = 100
        MAX_SIZE = 100 * 1024 # 100KB
        file_count = 0
        
        for root, dirs, filenames in os.walk(repo_path):
            if '.git' in dirs:
                dirs.remove('.git')
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
                
            for filename in filenames:
                if file_count >= MAX_FILES:
                    break
                    
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, repo_path)
                rel_path = rel_path.replace('\\', '/')
                
                # Skip binary or large files
                if os.path.getsize(file_path) > MAX_SIZE:
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        files[rel_path] = f.read()
                    file_count += 1
                except UnicodeDecodeError:
                    pass # Skip binary files
            
            if file_count >= MAX_FILES:
                break
        
        # Extract metadata
        metadata = extract_project_metadata(repo_path)
                
        return jsonify({
            'message': 'Repository loaded successfully',
            'repo_name': repo_name,
            'files': files,
            'metadata': metadata
        })

    except Exception as e:
        print(f"Load Git Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/git/push', methods=['POST'])
def push_to_git():
    """
    Push changes to Git repository
    """
    try:
        data = request.get_json()
        git_config = data.get('git_config')
        commit_message = data.get('commit_message')
        files = data.get('files')
        
        if not git_config or not git_config.get('repo_url'):
            return jsonify({'error': 'Missing git configuration'}), 400
            
        if not files:
            return jsonify({'error': 'No files to push'}), 400
            
        repo_url = git_config['repo_url']
        token = git_config.get('token')
        username = git_config.get('username')
        email = git_config.get('email')

        # Validate repository URL
        if not repo_url or not repo_url.startswith(('http://', 'https://')):
            return jsonify({'error': 'Invalid repository URL. Must be a valid HTTP/HTTPS URL.'}), 400

        # Validate token for GitHub repositories
        if 'github.com' in repo_url and not token:
            return jsonify({'error': 'GitHub repository requires a personal access token for authentication.'}), 400

        # Insert token into URL
        if token and 'https://' in repo_url:
            # Ensure token doesn't already contain credentials
            if '@' in repo_url:
                return jsonify({'error': 'Repository URL already contains authentication credentials.'}), 400

            # Validate token format (should be just the token, not username:token)
            if ':' in token:
                return jsonify({'error': 'Token should be just the access token, not username:token format.'}), 400

            auth_url = repo_url.replace('https://', f'https://{token}@')
            print(f"Token length: {len(token) if token else 0}")
            print(f"Using authenticated URL: {repo_url.replace('https://', 'https://[TOKEN]@')}")
        else:
            auth_url = repo_url
            if 'github.com' in repo_url:
                print(f"WARNING: No token provided for GitHub repository - this will fail!")
            print(f"Using URL without authentication: {auth_url}")
            
        repo_name = repo_url.split('/')[-1].replace('.git', '')

        # Use timestamp to create unique directory for fresh clone (avoids Windows file locking)
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        repo_path = os.path.join(GIT_REPOS_DIR, f"{repo_name}_{timestamp}")

        try:
            # Clone fresh repository to unique directory
            print(f"Cloning repository: {repo_url.replace('https://', 'https://[TOKEN]@') if token else auth_url}")
            try:
                Repo.clone_from(auth_url, repo_path)
                repo = Repo(repo_path)
                print(f"Repository cloned successfully to: {repo_path}")
            except Exception as clone_error:
                error_msg = str(clone_error)
                if '403' in error_msg or 'Forbidden' in error_msg:
                    return jsonify({
                        'error': 'Authentication failed (403 Forbidden). Please check your GitHub token.',
                        'details': 'Make sure your personal access token has the correct permissions (repo scope for private repos).'
                    }), 401
                elif '404' in error_msg or 'Not Found' in error_msg:
                    return jsonify({
                        'error': 'Repository not found (404). Please check the repository URL.',
                        'details': 'Verify that the repository exists and you have access to it.'
                    }), 404
                else:
                    raise clone_error

            # Configure user
            if username:
                repo.config_writer().set_value("user", "name", username).release()
                print(f"Set username: {username}")
            if email:
                repo.config_writer().set_value("user", "email", email).release()
                print(f"Set email: {email}")

            # Write files
            for filename, content in files.items():
                file_path = os.path.join(repo_path, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Written file: {filename}")

            # Add and Commit
            repo.git.add(A=True)
            print("Files added to git")

            if repo.is_dirty():
                # Try to get the current branch name
                current_branch = repo.active_branch.name
                print(f"Current branch: {current_branch}")

                repo.index.commit(commit_message)
                print(f"Committed with message: {commit_message}")

                origin = repo.remotes.origin
                print("Attempting to push...")

                # Try to push with better error handling
                try:
                    push_result = origin.push()
                    print(f"Push result: {push_result}")
                    return jsonify({
                        'message': 'Pushed successfully',
                        'commit_hash': repo.head.commit.hexsha,
                        'branch': current_branch
                    })
                except Exception as push_error:
                    error_msg = str(push_error)
                    print(f"Push failed: {error_msg}")

                    # Check for specific error types
                    if '403' in error_msg or 'Forbidden' in error_msg:
                        return jsonify({
                            'error': 'Push failed due to authentication (403 Forbidden)',
                            'details': 'Your GitHub token may be invalid, expired, or lack push permissions. Check token scopes.'
                        }), 403
                    elif 'Repository not found' in error_msg or 'does not exist' in error_msg:
                        return jsonify({
                            'error': 'Repository not found or access denied',
                            'details': 'Verify the repository URL and your access permissions.'
                        }), 404

                    # Try to force push if regular push fails
                    try:
                        print("Attempting force push...")
                        push_result = origin.push(force=True)
                        print(f"Force push result: {push_result}")
                        return jsonify({
                            'message': 'Pushed successfully (force push)',
                            'commit_hash': repo.head.commit.hexsha,
                            'branch': current_branch
                        })
                    except Exception as force_push_error:
                        force_error_msg = str(force_push_error)
                        print(f"Force push also failed: {force_error_msg}")

                        if '403' in force_error_msg:
                            return jsonify({
                                'error': 'Force push failed due to authentication',
                                'details': 'Even force push failed. Check your token permissions.'
                            }), 403
                        else:
                            return jsonify({
                                'error': 'Push failed',
                                'details': f'Both regular and force push failed. Error: {error_msg}'
                            }), 500
            else:
                print("No changes to commit")
                return jsonify({
                    'message': 'No changes to push',
                    'commit_hash': repo.head.commit.hexsha
                })

        except Exception as e:
            print(f"Push operation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Push operation failed: {str(e)}'}), 500

    except Exception as e:
        print(f"Push Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


def extract_project_metadata(repo_path):
    """Extract project name and package from repository files"""
    metadata = {
        'project_name': None,
        'package_name': None,
        'language': None
    }
    
    try:
        # 1. Detect Language and Metadata
        
        # Check for Python
        if os.path.exists(os.path.join(repo_path, 'pyproject.toml')):
            metadata['language'] = 'python'
            try:
                with open(os.path.join(repo_path, 'pyproject.toml'), 'r', encoding='utf-8') as f:
                    content = f.read()
                    import re
                    match = re.search(r'(?:^|\n)\s*name\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        metadata['project_name'] = match.group(1)
            except: pass
            
        if not metadata['language'] and (os.path.exists(os.path.join(repo_path, 'setup.py')) or os.path.exists(os.path.join(repo_path, 'requirements.txt'))):
            metadata['language'] = 'python'
            if os.path.exists(os.path.join(repo_path, 'setup.py')):
                try:
                    with open(os.path.join(repo_path, 'setup.py'), 'r', encoding='utf-8') as f:
                        content = f.read()
                        import re
                        match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            metadata['project_name'] = match.group(1)
                except: pass

        # Check for Java (Maven)
        if os.path.exists(os.path.join(repo_path, 'pom.xml')):
            metadata['language'] = 'java'
            try:
                with open(os.path.join(repo_path, 'pom.xml'), 'r', encoding='utf-8') as f:
                    content = f.read()
                    import re
                    # Try to find name tag first
                    match = re.search(r'<name>\s*([^<]+)\s*</name>', content)
                    if match:
                        metadata['project_name'] = match.group(1)
                    
                    # If no name, look for artifactId but skip parent
                    if not metadata['project_name']:
                        # Remove parent block to avoid confusion
                        content_no_parent = re.sub(r'<parent>.*?</parent>', '', content, flags=re.DOTALL)
                        match = re.search(r'<artifactId>\s*([^<]+)\s*</artifactId>', content_no_parent)
                        if match:
                            metadata['project_name'] = match.group(1)
                            
                    # For package name, try groupId from non-parent content
                    content_no_parent = re.sub(r'<parent>.*?</parent>', '', content, flags=re.DOTALL)
                    match = re.search(r'<groupId>\s*([^<]+)\s*</groupId>', content_no_parent)
                    if match:
                        metadata['package_name'] = match.group(1)
            except: pass

        # 2. Infer Package Name (if missing)
        if metadata['language'] == 'python' and not metadata['package_name']:
            # Look for directories with __init__.py
            potential_packages = []
            for root, dirs, files in os.walk(repo_path):
                if '.git' in dirs: dirs.remove('.git')
                if '__pycache__' in dirs: dirs.remove('__pycache__')
                
                if '__init__.py' in files:
                    rel_path = os.path.relpath(root, repo_path)
                    if rel_path == '.': continue
                    
                    # Convert path to package notation
                    package = rel_path.replace(os.sep, '.')
                    # Filter out common non-package dirs
                    if not any(x in package.lower() for x in ['test', 'tests', 'docs', 'examples', 'build', 'dist']):
                        potential_packages.append(package)
            
            # Pick the shortest top-level package
            if potential_packages:
                potential_packages.sort(key=len)
                metadata['package_name'] = potential_packages[0]
                
        # Java Package Inference from Directory Structure (More reliable than pom.xml)
        if metadata['language'] == 'java':
            src_main_java = os.path.join(repo_path, 'src', 'main', 'java')
            if os.path.exists(src_main_java):
                # Walk to find the first directory containing files
                for root, dirs, files in os.walk(src_main_java):
                    if files: # Found a directory with files
                        rel_path = os.path.relpath(root, src_main_java)
                        if rel_path != '.':
                            package = rel_path.replace(os.sep, '.')
                            metadata['package_name'] = package
                            break

        # 3. Fallbacks
        if not metadata['project_name']:
            metadata['project_name'] = os.path.basename(repo_path)
            
    except Exception as e:
        print(f"Metadata extraction error: {e}")
        
    return metadata


def generate_api_with_openai(config, schema):
    """
    Generate API code using OpenAI based on language/framework and schema.
    This function replaces the hardcoded templates and supports any language.
    
    Args:
        config: Configuration object with project details
        schema: Normalized JSON schema defining models
    
    Returns:
        Dictionary with file contents (filename -> content)
    """
    if not client:
        raise ValueError("API client not configured. Please set GROQ_API_KEY or OPENAI_API_KEY in .env file or environment variables.")
    
    # Build the prompt for OpenAI
    models_list = list(schema.keys())
    schema_description = json.dumps(schema, indent=2)
    
    # Map language to framework details
    language_frameworks = {
        'python-flask': {
            'framework': 'Python Flask',
            'orm': 'SQLAlchemy',
            'main_file': 'app.py',
            'structure': 'Single file Flask application with SQLAlchemy models'
        },
        'python-fastapi': {
            'framework': 'Python FastAPI',
            'orm': 'Pydantic models with in-memory database',
            'main_file': 'main.py',
            'structure': 'FastAPI application with Pydantic models'
        },
        'java-spring': {
            'framework': 'Java Spring Boot',
            'orm': 'JPA/Hibernate',
            'main_file': 'src/main/java/{package}/Application.java',
            'structure': 'Spring Boot with Entity, DTO, Repository, Service, Controller layers'
        },
        'nodejs-express': {
            'framework': 'Node.js Express',
            'orm': 'No ORM (plain JavaScript objects)',
            'main_file': 'server.js',
            'structure': 'Express.js REST API with in-memory storage'
        },
        'nodejs-nestjs': {
            'framework': 'Node.js NestJS',
            'orm': 'TypeORM or Prisma',
            'main_file': 'src/main.ts',
            'structure': 'NestJS with modules, controllers, services, entities'
        },
        'typescript-express': {
            'framework': 'TypeScript Express',
            'orm': 'TypeORM or Prisma',
            'main_file': 'src/server.ts',
            'structure': 'Express.js with TypeScript, proper types and interfaces'
        },
        'nextjs-approuter': {
            'framework': 'Next.js App Router',
            'orm': 'Prisma or node-postgres',
            'main_file': 'app/layout.tsx',
            'structure': 'Next.js 13+ App Router with API Routes (app/api/[resource]/route.ts)'
        }
    }
    
    # Handle custom languages
    language_key = config['language']
    if language_key == 'custom':
        # Try to infer from package name (e.g., com.example -> Java, org.example -> Java/Kotlin)
        package_name = config.get('package_name') or ''
        if package_name and (package_name.startswith('com.') or package_name.startswith('org.')):
            language_key = 'java-spring'
            print(f"Inferred Java from package name: {package_name}")
        elif package_name:
            # Use package name as language hint
            language_key = package_name.split('.')[0] if '.' in package_name else 'python-flask'
            print(f"Using custom language: {language_key}")
        else:
            language_key = 'python-flask'
            print(f"No package name provided, defaulting to: {language_key}")
    
    framework_info = language_frameworks.get(language_key, {
        'framework': config['language'] if config['language'] != 'custom' else language_key,
        'orm': 'Standard ORM for the language',
        'main_file': 'main.py',
        'structure': 'Standard REST API structure following best practices for the language'
    })
    
    # Add language-specific file requirements
    dep_file_instructions = ""
    if config['language'] in ['nodejs-express', 'nodejs-nestjs', 'typescript-express', 'nextjs-approuter']:
        dep_file_instructions = """
DEPENDENCY FILE REQUIREMENTS FOR NODE.JS/TYPESCRIPT:
- Include ONLY package.json (NOT requirements.txt - that's Python!)
- Do NOT include requirements.txt, setup.py, or any Python files
- package.json must have valid JSON structure with all npm dependencies listed
- Include all necessary npm packages in dependencies section
"""
    elif config['language'] in ['python-flask', 'python-fastapi']:
        dep_file_instructions = """
DEPENDENCY FILE REQUIREMENTS FOR PYTHON:
- Include ONLY requirements.txt (NOT package.json - that's Node.js!)
- Do NOT include package.json or any Node.js files
- List each Python package on a separate line
"""
    elif config['language'] == 'java-spring':
        dep_file_instructions = """
DEPENDENCY FILE REQUIREMENTS FOR JAVA:
- Include either pom.xml (Maven) or build.gradle (Gradle)
- Do NOT include requirements.txt or package.json
- Use proper Maven/Gradle dependency format
- CRITICAL: XML files (pom.xml) MUST have all newlines escaped as \\n and tabs as \\t
- Example for XML: "pom.xml": "<?xml version=\\"1.0\\"?>\\n<project>\\n  <modelVersion>4.0.0</modelVersion>\\n</project>"
"""

    # Check if we have existing files (from loaded repo)
    existing_files_context = ""
    package_to_use = config.get('detected_package') or config.get('package_name') or 'com.example.api'
    
    if config.get('existing_files'):
        existing_file_list = list(config['existing_files'].keys())[:10]  # Show first 10 files
        existing_entities_list = config.get('existing_entities', [])
        
        existing_files_context = f"""
EXISTING PROJECT DETECTED:
- This project was loaded from a repository
- Detected Package Structure: {config.get('detected_package', 'Not detected')}
- Existing files include: {', '.join(existing_file_list)}
- Existing entities (DO NOT regenerate): {', '.join(existing_entities_list) if existing_entities_list else 'None detected'}
- IMPORTANT: ONLY generate files for the NEW entities listed in the schema below
- IMPORTANT: Do NOT create files for entities that already exist ({', '.join(existing_entities_list)})
- IMPORTANT: Add new entities to the EXISTING package structure
- IMPORTANT: Follow the same folder organization as existing files
- IMPORTANT: Do NOT create duplicate folder structures
- IMPORTANT: Use package "{package_to_use}" for all new files
- IMPORTANT: Files to generate: Entity, DTO, Repository, Service, Controller, and Tests for NEW entities ONLY
- If existing files use "src/main/java/com/example/ecommerce", use that same path for new entities
"""

    prompt = f"""You are an expert API code generator. Generate a complete, production-ready REST API project based on the following specifications:

PROJECT CONFIGURATION:
- Project Name: {config['project_name']}
- Package Name: {package_to_use}
- Tech Stack: {config['language']} ({framework_info['framework']})
- Database: {config['database']}
- Database Connection: {config.get('db_connection', 'Not specified')}{existing_files_context}

JSON SCHEMA (Models and Fields):
{schema_description}

REQUIREMENTS:
1. Generate a complete, runnable REST API project for {framework_info['framework']}
2. Use {framework_info['orm']} for database operations
3. Follow {framework_info['structure']} architecture
4. CRITICAL: For EACH entity in the schema, you MUST generate ALL of the following:
   - Entity/Model class (e.g., Order.java)
   - DTO class (e.g., OrderDTO.java) - for data transfer
   - Repository interface (e.g., OrderRepository.java)
   - Service class (e.g., OrderService.java) - business logic
   - Controller class (e.g., OrderController.java) - REST endpoints
   - Unit Tests (e.g., OrderServiceTest.java)
5. Create full CRUD endpoints (GET, POST, PUT, DELETE) for each model
6. Include proper error handling, validation, and HTTP status codes
7. Add CORS support for cross-origin requests
8. Include a README.md with setup and usage instructions{ dep_file_instructions}
9. Use proper code structure and best practices for {config['language']}
10. Include proper type definitions/types/interfaces as appropriate for the language
11. All file content MUST be plain text strings, NOT objects or arrays

OUTPUT FORMAT:
Return ONLY a valid JSON object with this exact structure:
{{
    "files": {{
        "filename1": "file content as string",
        "filename2": "file content as string"
    }}
}}

CRITICAL OUTPUT REQUIREMENTS:
- Return ONLY valid JSON, no markdown code blocks, no explanations, no text before or after
- Start with {{ and end with }}
- Use double quotes for all JSON keys and string values
- Each file content MUST be a STRING, not an object or array
- Escape newlines as \\n in JSON strings
- Escape double quotes inside strings as \\"
- Escape backslashes as \\\\
- Do NOT wrap the JSON in ```json or ``` code blocks
- Do NOT add any explanatory text before or after the JSON
- The response must be parseable by json.loads() directly
- README.md content must be a SINGLE string with \\n for newlines. Do NOT use an object or array or list of strings.

WRONG FORMAT EXAMPLES (DO NOT USE):
- {{"files": {{"README.md": {{ "Line 1", "Line 2" }}}}}} ← WRONG! This is a set/object, not a string.
- {{"files": {{"README.md": ["Line 1", "Line 2"]}}}} ← WRONG! This is an array, not a string.
- {{"files": {{"README.md": {{ "content": "Line 1" }}}}}} ← WRONG! This is an object, not a string.
- {{# Comment\\n"files": {{...}}}}  ← WRONG! No markdown syntax in JSON

EXAMPLE OUTPUT FORMAT (return exactly this structure):
{{"files": {{"app.py": "from flask import Flask\\napp = Flask(__name__)\\n", "README.md": "# My API\\n\\nSetup instructions here\\n"}}}}

Include all necessary files for a complete, runnable project:
- For Java projects, use proper package structure: {package_to_use.replace('.', '/')}
  * Main source files: src/main/java/{package_to_use.replace('.', '/')}/
  * Test files: src/test/java/{package_to_use.replace('.', '/')}/
  * Resources: src/main/resources/
  * Test resources: src/test/resources/
  * IMPORTANT: Use the PROJECT NAME "{config['project_name']}" for the main Application class (e.g., {config['project_name'].replace('-', '').replace('_', '').title()}Application.java)
  * IMPORTANT: Test files should follow the pattern: EntityNameRepositoryTest.java, EntityNameServiceTest.java, etc.
  * DO NOT use generic names like "test" for folders - always use the full package path
  * Example structure for package "{package_to_use}" and entity "Order":
    - src/main/java/{package_to_use.replace('.', '/')}/{config['project_name'].replace('-', '').replace('_', '').title()}Application.java
    - src/main/java/{package_to_use.replace('.', '/')}/entity/Order.java
    - src/main/java/{package_to_use.replace('.', '/')}/repository/OrderRepository.java
    - src/main/java/{package_to_use.replace('.', '/')}/service/OrderService.java
    - src/main/java/{package_to_use.replace('.', '/')}/controller/OrderController.java
    - src/test/java/{package_to_use.replace('.', '/')}/OrderRepositoryTest.java
    - src/main/resources/application.properties
    - pom.xml
- For Next.js App Router projects:
  * STRICTLY follow this structure (based on reference):
    - app/api/[resource_name]/route.ts (GET, POST)
    - app/api/[resource_name]/[id]/route.ts (GET, PUT, DELETE)
    - lib/db.ts (Database connection)
    - lib/validators.ts (Zod/Joi schemas)
    - models/[Model].ts (Data models/Interfaces)
    - package.json
    - next.config.js
  * Do NOT use Java-style folders like src/main/java or controller/service layers
  * Example for entity "User":
    - app/api/users/route.ts
    - app/api/users/[id]/route.ts
    - models/User.ts
    - lib/db.ts
- For Node.js/TypeScript projects, include package.json with all dependencies (NO requirements.txt!)
- For Python projects, include requirements.txt (NO package.json!)
- Make sure the code is production-ready and follows best practices


Generate the complete project now. Return ONLY the JSON object:"""

    try:
        # Model selection based on client type
        if client_type == "groq":
            # Use Groq models (Llama/Mixtral) - optimized for code generation
            # Order: General reasoning -> Fast -> Multilingual
            models_to_try = [
                ("llama-3.1-70b-versatile", "Llama 3.1 70B - Strong reasoning"),
                ("llama-3.1-8b-instant", "Llama 3.1 8B - Fast & efficient"),
                ("mixtral-8x22b-32768", "Mixtral 8x22B - Balanced")
            ]
        else:
            # Fallback to OpenAI models
            models_to_try = [
                ("gpt-4o", "OpenAI GPT-4o"),
                ("gpt-4-turbo", "OpenAI GPT-4 Turbo"),
                ("gpt-4", "OpenAI GPT-4"),
                ("gpt-3.5-turbo", "OpenAI GPT-3.5 Turbo")
            ]
        
        response = None
        last_error = None
        
        for model_info in models_to_try:
            if isinstance(model_info, tuple):
                model_name, model_description = model_info
            else:
                model_name = model_info
                model_description = model_name
            
            try:
                # Call API (works for both Groq and OpenAI)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert code generator. You generate complete, production-ready API projects. CRITICAL: You MUST return ONLY valid JSON. Do NOT use markdown code blocks (```json or ```). Do NOT add any text before or after the JSON. Start with { and end with }. The JSON must be parseable by json.loads() directly. Escape all newlines as \\n and all quotes as \\\" in string values."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for more consistent code generation
                    max_tokens=16000  # Adjust based on project size
                )
                print(f"[INFO] Successfully used model: {model_name} ({model_description})")
                break  # Success, exit the loop
            except Exception as e:
                last_error = e
                print(f"[WARN] Model {model_name} failed: {str(e)}")
                continue  # Try next model
        
        if response is None:
            # Provide more helpful error messages based on error type
            error_str = str(last_error)
            api_provider = "Groq" if client_type == "groq" else "OpenAI"
            
            # Print full error for debugging
            print(f"[ERROR] Full error from {api_provider}: {error_str}")
            print(f"[ERROR] Error type: {type(last_error).__name__}")
            
            if 'insufficient_quota' in error_str or '429' in error_str or 'rate_limit' in error_str.lower():
                if client_type == "groq":
                    raise Exception(f"Groq API quota/rate limit exceeded. Error: {error_str}. Visit https://console.groq.com/ to check your usage limits and upgrade if needed.")
                else:
                    raise Exception(f"OpenAI API quota exceeded. Error: {error_str}. Visit https://platform.openai.com/account/billing to add credits.")
            elif 'model_not_found' in error_str or '404' in error_str or 'model_decommissioned' in error_str or 'decommissioned' in error_str or 'does not exist' in error_str.lower():
                if client_type == "groq":
                    raise Exception(f"Groq model issue. Error: {error_str}. Available models: llama-3.1-70b-versatile, llama-3.1-8b-instant, mixtral-8x22b-32768. Check https://console.groq.com/docs/models")
                else:
                    raise Exception(f"OpenAI model not available. Error: {error_str}. Check https://platform.openai.com/api-keys for model access.")
            elif '401' in error_str or 'invalid_api_key' in error_str or 'authentication' in error_str.lower() or 'unauthorized' in error_str.lower():
                if client_type == "groq":
                    raise Exception(f"Invalid Groq API key. Error: {error_str}. Check GROQ_API_KEY in .env file. Get a valid key at https://console.groq.com/keys")
                else:
                    raise Exception(f"Invalid OpenAI API key. Error: {error_str}. Check OPENAI_API_KEY in .env file. Get a key at https://platform.openai.com/api-keys")
            else:
                raise Exception(f"All {api_provider} models failed. Last error: {error_str}")
        
        # Extract the response content
        response_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present (handle various formats)
        # Remove ```json at start
        if response_text.startswith("```json"):
            response_text = response_text[7:].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:].strip()
        
        # Remove ``` at end
        if response_text.endswith("```"):
            response_text = response_text[:-3].strip()
        
        # Try to extract JSON if there's extra text
        # Look for JSON object boundaries (find the outermost { and })
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            response_text = response_text[json_start:json_end]
        
        response_text = response_text.strip()
        
        # Fix common JSON issues before parsing
        # Remove trailing commas
        response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
        
        # CRITICAL FIX: Escape unescaped control characters in JSON string values
        # This is especially important for XML files (pom.xml) which have lots of newlines/tabs
        def fix_unescaped_control_chars(json_text):
            """
            Fix unescaped control characters (newlines, tabs, etc.) in JSON string values.
            This is critical for XML content like pom.xml in Java projects.
            """
            # Strategy: Find all string values and properly escape control characters
            # We need to be careful not to double-escape already escaped characters
            
            result = []
            i = 0
            in_string = False
            escape_next = False
            
            while i < len(json_text):
                char = json_text[i]
                
                # Handle escape sequences
                if escape_next:
                    result.append(char)
                    escape_next = False
                    i += 1
                    continue
                
                if char == '\\':
                    result.append(char)
                    escape_next = True
                    i += 1
                    continue
                
                # Track if we're inside a string
                if char == '"':
                    result.append(char)
                    in_string = not in_string
                    i += 1
                    continue
                
                # If we're in a string, escape control characters
                if in_string:
                    if char == '\n':
                        result.append('\\n')
                        i += 1
                        continue
                    elif char == '\r':
                        result.append('\\r')
                        i += 1
                        continue
                    elif char == '\t':
                        result.append('\\t')
                        i += 1
                        continue
                    elif ord(char) < 32:  # Other control characters
                        # Replace with space or escape as unicode
                        result.append(' ')
                        i += 1
                        continue
                
                result.append(char)
                i += 1
            
            return ''.join(result)
        
        # Apply control character fix
        print(f"[INFO] Cleaning control characters from response...")
        response_text = fix_unescaped_control_chars(response_text)
        print(f"[INFO] Control characters cleaned")

        
        # Parse JSON response with better error handling
        result = None
        files = {}
        json_parsed = False
        
        try:
            result = json.loads(response_text)
            files = result.get('files', {})
            
            # Fix file content structure if files contain objects/arrays instead of strings
            if files:
                fixed_files = {}
                for filename, content in files.items():
                    if isinstance(content, dict):
                        # Convert dict to string by joining values
                        lines = []
                        for key, value in content.items():
                            if isinstance(value, str):
                                lines.append(value)
                            elif isinstance(value, (dict, list)):
                                lines.append(str(value))
                        fixed_files[filename] = '\n'.join(lines)
                        print(f"[INFO] Fixed file '{filename}': converted dict to string")
                    elif isinstance(content, list):
                        # Convert list to string by joining
                        fixed_files[filename] = '\n'.join(str(item) for item in content)
                        print(f"[INFO] Fixed file '{filename}': converted list to string")
                    else:
                        fixed_files[filename] = content
                files = fixed_files
            
            json_parsed = True
            
            # Validate that we got files
            if not files:
                raise ValueError("API returned empty files dictionary")
            
        except json.JSONDecodeError as e:
            api_provider = "Groq" if client_type == "groq" else "OpenAI"
            print(f"Failed to parse {api_provider} response as JSON: {e}")
            print(f"JSON Error at line {e.lineno}, column {e.colno}: {e.msg}")
            print(f"Response length: {len(response_text)}")
            print(f"Response preview (first 1000 chars): {response_text[:1000]}")
            print(f"Response preview (last 500 chars): {response_text[-500:]}")
            
            # Try multiple strategies to extract and fix JSON
            def fix_json_common_issues(text):
                """Fix common JSON issues"""
                # Remove trailing commas before } or ]
                text = re.sub(r',(\s*[}\]])', r'\1', text)
                # Remove comments (single line // and multi-line /* */)
                text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
                text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
                
                # Fix missing commas between file entries
                # Pattern: "filename": "content" "nextfile": "content"  -> add comma
                # Look for }" followed by " (missing comma between files)
                text = re.sub(r'"\s*}\s*"', '"},\n"', text)
                text = re.sub(r'"\s*\]\s*"', '"],\n"', text)
                
                return text.strip()
            
            def smart_truncate_json(text):
                """
                If JSON is incomplete/malformed, try to truncate at last valid file entry
                and properly close the JSON structure.
                Robust version: walks forward to track structure.
                """
                # Find start of files object
                files_start = text.find('"files"')
                if files_start == -1:
                    return None
                
                # Find opening brace of files object
                brace_after_files = text.find('{', files_start)
                if brace_after_files == -1:
                    return None
                    
                # Walk forward from the brace to find the last valid comma
                last_valid_comma = -1
                in_string = False
                escape_next = False
                brace_depth = 1  # We are inside the files object
                
                # Start scanning after the {
                i = brace_after_files + 1
                while i < len(text):
                    char = text[i]
                    
                    if escape_next:
                        escape_next = False
                        i += 1
                        continue
                        
                    if char == '\\':
                        escape_next = True
                        i += 1
                        continue
                        
                    if char == '"':
                        in_string = not in_string
                        i += 1
                        continue
                        
                    if not in_string:
                        if char == '{':
                            brace_depth += 1
                        elif char == '}':
                            brace_depth -= 1
                            if brace_depth == 0:
                                # We reached the end of files object normally
                                return text[:i+1] + '}' # Should be closed already
                        elif char == ',':
                            # This is a comma separating file entries (if brace_depth is 1)
                            if brace_depth == 1:
                                last_valid_comma = i
                    
                    i += 1
                    
                # If we ran out of text (unterminated), truncate at last valid comma
                if last_valid_comma != -1:
                    print(f"[INFO] Smart truncation: Truncating at position {last_valid_comma}")
                    return text[:last_valid_comma] + '\n  }\n}'
                    
                return None

            
            def fix_malformed_strings(text):
                """Try to fix malformed string values in JSON"""
                # Pattern: "key": "value with unescaped " quote" -> "key": "value with escaped \" quote"
                # But this is very complex, so we'll use a simpler approach
                # Look for patterns like: "key": "value"missing_quote
                # This is a heuristic fix
                return text
            
            def fix_file_content_structure(text):
                """Fix cases where file content is incorrectly structured as objects/arrays instead of strings"""
                # Pattern: "filename": { "line1", "line2" } should be "filename": "line1\nline2"
                # Pattern: "filename": [ "line1", "line2" ] should be "filename": "line1\nline2"
                
                # Find all file entries in the files object
                # Look for patterns like "filename": { or "filename": [
                files_pattern = r'"files"\s*:\s*\{'
                files_match = re.search(files_pattern, text)
                
                if files_match:
                    # Try to fix object/array file contents
                    # Pattern: "key": { "value1", "value2" } -> "key": "value1\nvalue2"
                    # This is a complex fix, so we'll try a simpler approach
                    # Replace { "line1", "line2" } with "line1\nline2"
                    def fix_object_content(match):
                        content = match.group(0)
                        # Extract string values from object/array
                        strings = re.findall(r'"([^"]*)"', content)
                        if strings:
                            # Join with newlines and escape properly
                            fixed = '\\n'.join(s.replace('\\', '\\\\').replace('"', '\\"') for s in strings)
                            return f'"{fixed}"'
                        return content
                    
                    # Try to fix common patterns
                    # This is a heuristic approach - if we find patterns like { "line", "line" } we convert to string
                    pass  # Will handle in a different way
                
                return text
            
            # Strategy 1: Find JSON object using balanced braces
            def find_json_object(text):
                """Find the largest valid JSON object in text"""
                start = text.find('{')
                if start == -1:
                    return None
                
                brace_count = 0
                end = start
                in_string = False
                escape_next = False
                
                for i in range(start, len(text)):
                    char = text[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                
                if brace_count == 0 and end > start:
                    return text[start:end]
                return None
            
            # Try Strategy 1: Extract JSON object and fix common issues
            extracted_json = find_json_object(response_text)
            if extracted_json:
                # Fix common JSON issues
                cleaned_json = fix_json_common_issues(extracted_json)
                
                # Try to fix file content structure issues (objects/arrays instead of strings)
                try:
                    # First attempt: parse as-is
                    result = json.loads(cleaned_json)
                    files = result.get('files', {})
                    
                    # Check if files have invalid structure (objects/arrays instead of strings)
                    needs_fixing = False
                    for filename, content in files.items():
                        if isinstance(content, (dict, list)):
                            needs_fixing = True
                            break
                    
                    if needs_fixing:
                        print(f"[WARN] Detected invalid file content structure (objects/arrays instead of strings), attempting to fix...")
                        fixed_files = {}
                        for filename, content in files.items():
                            if isinstance(content, dict):
                                # Convert dict to string by joining values
                                lines = []
                                for key, value in content.items():
                                    if isinstance(value, str):
                                        lines.append(value)
                                    elif isinstance(value, (dict, list)):
                                        lines.append(str(value))
                                fixed_files[filename] = '\n'.join(lines)
                            elif isinstance(content, list):
                                # Convert list to string by joining
                                fixed_files[filename] = '\n'.join(str(item) for item in content)
                            else:
                                fixed_files[filename] = content
                        files = fixed_files
                        print(f"[INFO] Fixed {len([f for f in files.values() if isinstance(f, str)])} file contents")
                    
                    if files:
                        print(f"[INFO] Successfully extracted and fixed JSON using balanced braces method")
                        json_parsed = True
                    else:
                        raise ValueError("Extracted JSON has no 'files' key")
                except (json.JSONDecodeError, ValueError) as parse_err:
                    print(f"[WARN] Balanced braces extraction failed: {parse_err}")
                    
                    # Try smart truncation as fallback
                    truncated_json = smart_truncate_json(extracted_json)
                    if truncated_json:
                        try:
                            print(f"[INFO] Attempting smart truncation recovery...")
                            result = json.loads(truncated_json)
                            files = result.get('files', {})
                            if files:
                                print(f"[INFO] Successfully recovered {len(files)} files using smart truncation")
                                json_parsed = True
                        except json.JSONDecodeError as truncate_err:
                            print(f"[WARN] Smart truncation also failed: {truncate_err}")
                            extracted_json = None
                    else:
                        extracted_json = None
            
            # Strategy 2: Try to fix the original response and parse again
            if not json_parsed:
                try:
                    cleaned_response = fix_json_common_issues(response_text)
                    result = json.loads(cleaned_response)
                    files = result.get('files', {})
                    
                    # Fix file content structure if needed
                    if files:
                        fixed_files = {}
                        for filename, content in files.items():
                            if isinstance(content, dict):
                                lines = []
                                for key, value in content.items():
                                    if isinstance(value, str):
                                        lines.append(value)
                                    elif isinstance(value, (dict, list)):
                                        lines.append(str(value))
                                fixed_files[filename] = '\n'.join(lines)
                            elif isinstance(content, list):
                                fixed_files[filename] = '\n'.join(str(item) for item in content)
                            else:
                                fixed_files[filename] = content
                        files = fixed_files
                        
                        if files:
                            print(f"[INFO] Successfully parsed JSON after fixing common issues")
                            json_parsed = True
                except json.JSONDecodeError as fix_err:
                    print(f"[WARN] Strategy 2 (fix common issues) failed: {fix_err}")
                    
                    # Try smart truncation on the cleaned response
                    truncated = smart_truncate_json(cleaned_response)
                    if truncated:
                        try:
                            print(f"[INFO] Attempting smart truncation on cleaned response...")
                            result = json.loads(truncated)
                            files = result.get('files', {})
                            if files:
                                print(f"[INFO] Successfully recovered {len(files)} files using smart truncation")
                                json_parsed = True
                        except json.JSONDecodeError:
                            pass
            
            # Strategy 3: Try regex pattern matching (last resort)
            if not json_parsed:
                json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                regex_matches = re.findall(json_pattern, response_text, re.DOTALL)
                
                for match in sorted(regex_matches, key=len, reverse=True):
                    try:
                        cleaned_match = fix_json_common_issues(match)
                        result = json.loads(cleaned_match)
                        files = result.get('files', {})
                        if files:
                            print(f"[INFO] Successfully extracted JSON using regex method")
                            json_parsed = True
                            break
                    except json.JSONDecodeError:
                        continue
            
            # If all strategies failed, provide detailed error
            if not json_parsed or not files:
                error_context = ""
                if hasattr(e, 'pos') and e.pos < len(response_text):
                    start = max(0, e.pos - 100)
                    end = min(len(response_text), e.pos + 100)
                    error_context = f"\n\nError context (around position {e.pos}):\n{response_text[start:end]}"
                
                raise ValueError(
                    f"{api_provider} returned invalid JSON.\n"
                    f"Error: Line {e.lineno}, Column {e.colno}: {e.msg}\n"
                    f"Response length: {len(response_text)} characters\n"
                    f"First 500 chars: {response_text[:500]}\n"
                    f"Last 500 chars: {response_text[-500:]}{error_context}"
                )
        
        # If we successfully parsed JSON (either directly or via extraction), continue
        if json_parsed and files:
            # Clean up incorrect files based on language
            language = config['language']
            files_to_remove = []
            
            # Remove Python files from Node.js/TypeScript projects
            if language in ['nodejs-express', 'nodejs-nestjs', 'typescript-express']:
                if 'requirements.txt' in files:
                    files_to_remove.append('requirements.txt')
                    print(f"[WARN] Removed requirements.txt from Node.js project (incorrect dependency file)")
                if 'setup.py' in files:
                    files_to_remove.append('setup.py')
                    print(f"[WARN] Removed setup.py from Node.js project (incorrect file)")
            
            # Remove Node.js files from Python projects
            elif language in ['python-flask', 'python-fastapi']:
                if 'package.json' in files:
                    files_to_remove.append('package.json')
                    print(f"[WARN] Removed package.json from Python project (incorrect dependency file)")
            
            # Remove Python/Node files from Java projects
            elif language == 'java-spring':
                if 'requirements.txt' in files:
                    files_to_remove.append('requirements.txt')
                    print(f"[WARN] Removed requirements.txt from Java project (incorrect file)")
                if 'package.json' in files:
                    files_to_remove.append('package.json')
                    print(f"[WARN] Removed package.json from Java project (incorrect file)")
            
            # Remove identified files
            for file_to_remove in files_to_remove:
                del files[file_to_remove]
            
            # Add README if not present (fallback)
            if 'README.md' not in files:
                readme_content = f"""# {config['project_name']}

Auto-generated REST API using {framework_info['framework']}

## Generated on
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Models
{', '.join(models_list)}

## Installation and Usage
Please refer to the framework-specific documentation for setup instructions.
"""
                files['README.md'] = readme_content
            
            return files
        else:
            raise ValueError("Failed to parse or extract valid JSON from API response")
            
    except Exception as e:
        api_provider = "Groq" if client_type == "groq" else "OpenAI"
        print(f"{api_provider} API error: {str(e)}")
        raise Exception(f"Failed to generate code with {api_provider}: {str(e)}")


@app.route('/')
def index():
    """Serve the main frontend application"""
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from frontend directory"""
    return send_from_directory('../frontend', filename)

@app.route('/api/')
def api_info():
    """API information"""
    return jsonify({
        'message': 'Auto API Builder Backend',
        'version': '1.0',
        'endpoints': {
            '/api/generate': 'POST - Generate API from JSON schema',
            '/api/health': 'GET - Health check'
        }
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@app.route('/api/generate', methods=['POST'])
def generate_api():
    """
    Generate API code from JSON schema
    
    Expected JSON body:
    {
        "project_name": "my-api",
        "package_name": "com.example.api",
        "language": "python-flask" | "python-fastapi" | "java-spring",
        "database": "postgresql" | "mysql" | "sqlite" | "mongodb",
        "db_connection": "connection_string",
        "schema": {
            "ModelName": {
                "field_name": "field_type"
            }
        }
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['project_name', 'language', 'schema']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        config = {
            'project_name': data['project_name'],
            'package_name': data.get('package_name') or 'com.example.api',
            'language': data['language'],
            'database': data.get('database', 'sqlite'),
            'db_connection': data.get('db_connection', 'sqlite:///database.db'),
            'git_config': data.get('git_config'),
            'existing_files': data.get('existing_files', {})  # Support for loaded repo files
        }
        
        schema = data['schema']
        
        # Debug: log the input schema
        print(f"[DEBUG] Input schema type: {type(schema)}")
        print(f"[DEBUG] Input schema: {json.dumps(schema, indent=2)[:500]}")
        
        # If existing files provided, detect project structure AND existing entities
        if config['existing_files']:
            print(f"[INFO] Existing project detected with {len(config['existing_files'])} files")
            
            # Detect package structure from existing files
            for filepath in config['existing_files'].keys():
                if filepath.startswith('src/main/java/'):
                    # Extract package from path
                    parts = filepath.replace('src/main/java/', '').split('/')
                    if len(parts) > 1:
                        # Check if this is an entity package path
                        if 'entity' in parts:
                            # Extract package before /entity/
                            entity_index = parts.index('entity')
                            detected_package = '.'.join(parts[:entity_index])
                        else:
                            # Extract from full path excluding filename
                            detected_package = '.'.join(parts[:-1])
                        
                        if detected_package and not config.get('detected_package'):
                            config['detected_package'] = detected_package
                            print(f"[INFO] Detected existing package structure: {detected_package}")
                            break
            
            # Detect existing entities to avoid regenerating them
            existing_entities = set()
            for filepath in config['existing_files'].keys():
                # Look for entity files: entity/EntityName.java or just EntityName.java
                if filepath.endswith('.java'):
                    filename = filepath.split('/')[-1]
                    # Remove .java extension
                    classname = filename.replace('.java', '')
                    
                    # Check if it's an entity (in entity folder or has Entity/DTO/Repository/Service/Controller suffix)
                    if '/entity/' in filepath or filepath.endswith('DTO.java'):
                        # Extract base entity name (remove DTO suffix if present)
                        entity_name = classname.replace('DTO', '')
                        existing_entities.add(entity_name)
                    elif any(suffix in classname for suffix in ['Repository', 'Service', 'Controller']):
                        # Extract entity name from Repository/Service/Controller
                        for suffix in ['Repository', 'Service', 'Controller']:
                            if classname.endswith(suffix):
                                entity_name = classname.replace(suffix, '')
                                existing_entities.add(entity_name)
                                break
            
            if existing_entities:
                config['existing_entities'] = list(existing_entities)
                print(f"[INFO] Detected existing entities: {', '.join(existing_entities)}")

        
        schema = normalize_schema(schema)
        
        # Debug: log the normalized schema
        print(f"[DEBUG] Normalized schema type: {type(schema)}")
        print(f"[DEBUG] Normalized schema: {json.dumps(schema, indent=2)[:500]}")
        
        # Filter out existing entities if we have a loaded project
        if config.get('existing_entities'):
            original_schema = schema.copy()
            filtered_schema = {}
            
            for entity_name, entity_def in schema.items():
                if entity_name not in config['existing_entities']:
                    filtered_schema[entity_name] = entity_def
                else:
                    print(f"[INFO] Skipping existing entity: {entity_name} (already in repository)")
            
            if not filtered_schema:
                return jsonify({
                    'error': 'All entities in the schema already exist in the loaded repository.',
                    'existing_entities': config['existing_entities'],
                    'hint': 'Add new entities that don\'t already exist, or clear the loaded repository to regenerate everything.'
                }), 400
            
            if len(filtered_schema) < len(original_schema):
                removed_count = len(original_schema) - len(filtered_schema)
                print(f"[INFO] Filtered schema: Removed {removed_count} existing entities, generating {len(filtered_schema)} new entities")
                print(f"[INFO] New entities to generate: {', '.join(filtered_schema.keys())}")
            
            schema = filtered_schema
        
        # Validate normalized schema
        if not isinstance(schema, dict) or not schema:
            return jsonify({'error': 'Invalid schema format. Schema must contain at least one model definition.'}), 400
        
        # Ensure schema has the expected format - check if normalization worked
        # If normalization failed, schema might still be in original format
        if not all(isinstance(v, dict) for v in schema.values()):
            # Try to provide more helpful error message
            return jsonify({
                'error': 'Invalid schema format. Each model must have field definitions.',
                'hint': 'Expected format: {"ModelName": {"field": "type"}} or {"name": "ModelName", "fields": [{"name": "field", "type": "type"}]}',
                'received': str(schema)[:200]
            }), 400
        
        # Generate code using OpenAI (supports any language/framework)
        try:
            files = generate_api_with_openai(config, schema)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'Code generation failed: {str(e)}'}), 500
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in files.items():
                zip_file.writestr(filename, content)
        
        zip_buffer.seek(0)
        zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
        
        # Save locally (optional)
        project_dir = os.path.join(GENERATED_DIR, config['project_name'])
        os.makedirs(project_dir, exist_ok=True)
        
        for filename, content in files.items():
            file_path = os.path.join(project_dir, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Handle Git Operations
        git_status = handle_git_operations(config, project_dir)
        
        return jsonify({
            'message': 'API generated successfully',
            'project_name': config['project_name'],
            'files': files,
            'zip_base64': zip_base64,
            'git_status': git_status
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_project():
    """
    Upload and extract a ZIP project
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if not file.filename.endswith('.zip'):
            return jsonify({'error': 'File must be a ZIP archive'}), 400
            
        files = {}
        
        # Read zip file from memory
        with zipfile.ZipFile(file) as z:
            for filename in z.namelist():
                if not filename.endswith('/'):  # Skip directories
                    try:
                        # Try to read as text
                        content = z.read(filename).decode('utf-8')
                        files[filename] = content
                    except UnicodeDecodeError:
                        # Skip binary files or handle differently if needed
                        pass
                        
        return jsonify({
            'message': 'Project uploaded successfully',
            'files': files
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("Auto API Builder - Backend Server")
    print("Server starting on http://localhost:5001")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5001)
