# 🧪 Test Inputs for Each Language

## 🔧 **Recent Fixes Applied** ✅
- **Java Spring Boot**: Fixed "Invalid control character" errors in XML files (pom.xml)
- **Node.js/NestJS**: Fixed incorrect `requirements.txt` generation and JSON structure issues
- **All Languages**: Enhanced AI prompts and control character escaping

**Last Updated:** 2025-12-05

This document provides simple test inputs to verify that each supported language/framework generates code correctly.

---

## 📋 Test Case Format

For each test, use these fields in the API Generator:
- **Project Name**: The suggested project name
- **Package Name**: Language-specific package identifier (required for Java, optional for others)
- **Language/Framework**: Select from dropdown
- **Database**: Select database type (we'll use SQLite for simplicity)
- **JSON Schema**: Copy the provided JSON schema

---

## 🐍 Test 1: Python - Flask

### Configuration
- **Project Name**: `user-api-flask`
- **Package Name**: *(leave empty or enter `com.example.userapi`)*
- **Language**: `Python - Flask`
- **Database**: `SQLite`

### JSON Schema
```json
{
  "User": {
    "id": "integer",
    "username": "string",
    "email": "string",
    "active": "boolean",
    "created_at": "datetime"
  }
}
```

### Expected Output Files
- `app.py` - Main Flask application
- `models.py` - SQLAlchemy models
- `requirements.txt` - Dependencies
- `README.md` - Documentation

---

## ⚡ Test 2: Python - FastAPI

### Configuration
- **Project Name**: `product-api-fastapi`
- **Package Name**: *(leave empty or enter `com.example.productapi`)*
- **Language**: `Python - FastAPI`
- **Database**: `SQLite`

### JSON Schema
```json
{
  "Product": {
    "id": "integer",
    "name": "string",
    "price": "float",
    "in_stock": "boolean",
    "description": "text"
  }
}
```

### Expected Output Files
- `main.py` - Main FastAPI application
- `models.py` - Pydantic models
- `database.py` - Database configuration
- `requirements.txt` - Dependencies
- `README.md` - Documentation

---

## ☕ Test 3: Java - Spring Boot

### Configuration
- **Project Name**: `order-api-spring`
- **Package Name**: `com.example.orderapi` *(required for Java)*
- **Language**: `Java - Spring Boot`
- **Database**: `SQLite`

### JSON Schema
```json
{
  "Order": {
    "id": "integer",
    "customer_name": "string",
    "total_amount": "float",
    "status": "string",
    "order_date": "datetime"
  }
}
```

### Expected Output Files
- `OrderController.java` - REST controller
- `Order.java` - Entity model
- `OrderService.java` - Business logic
- `OrderRepository.java` - Data access
- `pom.xml` or `build.gradle` - Build configuration
- `application.properties` - Configuration
- `README.md` - Documentation

---

## 🟢 Test 4: Node.js - Express

### Configuration
- **Project Name**: `task-api-express`
- **Package Name**: *(leave empty)*
- **Language**: `Node.js - Express`
- **Database**: `SQLite`

### JSON Schema
```json
{
  "Task": {
    "id": "integer",
    "title": "string",
    "description": "text",
    "completed": "boolean",
    "priority": "integer",
    "due_date": "datetime"
  }
}
```

### Expected Output Files
- `server.js` or `app.js` - Main Express application
- `routes/tasks.js` - API routes
- `models/Task.js` - Database model
- `package.json` - Dependencies
- `.env.example` - Environment variables
- `README.md` - Documentation

---

## 🟢 Test 5: Node.js - NestJS

### Configuration
- **Project Name**: `blog-api-nestjs`
- **Package Name**: *(leave empty)*
- **Language**: `Node.js - NestJS`
- **Database**: `SQLite`

### JSON Schema
```json
{
  "Post": {
    "id": "integer",
    "title": "string",
    "content": "text",
    "published": "boolean",
    "author": "string",
    "created_at": "datetime"
  }
}
```

### Expected Output Files
- `src/main.ts` - Application entry point
- `src/app.module.ts` - Root module
- `src/posts/posts.controller.ts` - Controller
- `src/posts/posts.service.ts` - Service
- `src/posts/entities/post.entity.ts` - Entity
- `package.json` - Dependencies
- `README.md` - Documentation

---

## 🔷 Test 6: TypeScript - Express

### Configuration
- **Project Name**: `customer-api-ts`
- **Package Name**: *(leave empty)*
- **Language**: `TypeScript - Express`
- **Database**: `SQLite`

### JSON Schema
```json
{
  "Customer": {
    "id": "integer",
    "first_name": "string",
    "last_name": "string",
    "email": "string",
    "phone": "string",
    "registered_at": "datetime"
  }
}
```

### Expected Output Files
- `src/server.ts` - Main application
- `src/routes/customers.ts` - API routes
- `src/models/Customer.ts` - TypeScript interfaces/models
- `src/controllers/CustomerController.ts` - Controller logic
- `package.json` - Dependencies
- `tsconfig.json` - TypeScript configuration
- `README.md` - Documentation

---

## 🧪 Multiple Entity Test (Advanced)

Use this test to verify the generator handles multiple entities with relationships:

### Configuration
- **Project Name**: `shop-api-complete`
- **Package Name**: `com.example.shopapi` (for Java) or leave empty
- **Language**: *(Choose any)*
- **Database**: `PostgreSQL` *(for advanced testing)*

### JSON Schema
```json
{
  "Category": {
    "id": "integer",
    "name": "string",
    "description": "text"
  },
  "Product": {
    "id": "integer",
    "name": "string",
    "price": "float",
    "category_id": "integer",
    "in_stock": "boolean"
  },
  "Review": {
    "id": "integer",
    "product_id": "integer",
    "rating": "integer",
    "comment": "text",
    "reviewer_name": "string",
    "created_at": "datetime"
  }
}
```

---

## ✅ Verification Checklist

After generating each API, verify:

### 1. **Code Generation**
- [ ] All expected files are created
- [ ] No syntax errors in generated code
- [ ] Proper file structure follows framework conventions

### 2. **CRUD Operations**
- [ ] CREATE endpoint (POST)
- [ ] READ endpoints (GET single & GET all)
- [ ] UPDATE endpoint (PUT/PATCH)
- [ ] DELETE endpoint (DELETE)

### 3. **Database Integration**
- [ ] Database configuration is included
- [ ] Models/Entities are properly defined
- [ ] ORM/Database library is configured

### 4. **Dependencies**
- [ ] `requirements.txt` for Python
- [ ] `package.json` for Node.js/TypeScript
- [ ] `pom.xml`/`build.gradle` for Java

### 5. **Documentation**
- [ ] README.md with setup instructions
- [ ] API endpoint documentation
- [ ] Environment variable examples

### 6. **Best Practices**
- [ ] Proper error handling
- [ ] Input validation
- [ ] Security considerations (e.g., parameterized queries)
- [ ] Environment-based configuration

---

## 🚀 Quick Test Commands

### Testing Python Flask
```bash
cd user-api-flask
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python app.py
```

### Testing Python FastAPI
```bash
cd product-api-fastapi
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Testing Node.js/TypeScript
```bash
cd task-api-express
npm install
npm start
```

### Testing Java Spring Boot
```bash
cd order-api-spring
mvn clean install
mvn spring-boot:run
```

---

## 📊 Test Results Template

Use this table to track your test results:

| Language/Framework | Generated Successfully | Files Created | CRUD Works | Notes |
|-------------------|----------------------|---------------|-----------|-------|
| Python - Flask | ⬜ Yes / ⬜ No | ⬜ | ⬜ | |
| Python - FastAPI | ⬜ Yes / ⬜ No | ⬜ | ⬜ | |
| Java - Spring Boot | ⬜ Yes / ⬜ No | ⬜ | ⬜ | |
| Node.js - Express | ⬜ Yes / ⬜ No | ⬜ | ⬜ | |
| Node.js - NestJS | ⬜ Yes / ⬜ No | ⬜ | ⬜ | |
| TypeScript - Express | ⬜ Yes / ⬜ No | ⬜ | ⬜ | |

---

## 🐛 Common Issues & Solutions

### Issue: "Package name is required"
- **Solution**: For Java Spring Boot, always provide package name like `com.example.myapi`

### Issue: "Invalid JSON schema"
- **Solution**: Ensure your JSON is valid. Use the "Validate JSON" button if available

### Issue: Generated code has syntax errors
- **Solution**: Check the AI service (Anthropic/OpenAI) is properly configured in backend `.env`

### Issue: Missing files in output
- **Solution**: Check browser console for errors. Ensure backend is running on port 5001

---

## 📝 Notes

- All test schemas are intentionally simple (single entity) to quickly verify basic functionality
- For production use, consider adding:
  - Foreign key relationships
  - Input validation rules
  - Custom business logic
  - Authentication/Authorization
  - API versioning

- The "Multiple Entity Test" provides a more realistic scenario with related entities

---

**Happy Testing! 🎉**

If you encounter any issues, check the backend logs in the terminal where `server.py` is running.
