# MealSync - AI-Powered Household Meal Planning Platform

> **Academic Project**: MSc Advanced Software Engineering (CN7021)
> **Institution**: University of East London
> **Submission Date**: 22nd December 2025

> **Note**: This README documents the **backend API** implementation. A separate React frontend is being developed by team member 2 in a different repository.

## Project Overview

MealSync is a collaborative meal planning and household management platform that demonstrates advanced software engineering principles through the integration of AI-powered features. This backend API provides intelligent recipe generation, smart meal planning, ingredient matching, and grocery list management using Google Gemini AI.

### Problem Statement

Modern households face challenges in coordinating meal planning, managing ingredients, and reducing food waste. Existing solutions lack intelligent automation and collaborative features that adapt to household preferences and available ingredients. MealSync addresses these challenges by providing a RESTful API for:

- AI-driven meal plan generation based on available inventory
- Smart ingredient matching to reduce duplicate purchases
- Collaborative household management with authorization
- Automated grocery list generation from planned meals

### Project Scope

This backend implementation focuses on:

1. **AI Integration**: Gemini-powered recipe generation and meal planning
2. **Advanced Architecture**: Repository pattern, service layer, and dependency injection
3. **Comprehensive Testing**: 77 tests total (60 AI tests + auth/service tests) with 63% coverage
4. **CI/CD Pipeline**: Automated testing and code coverage reporting via GitHub Actions
5. **RESTful API**: Well-documented endpoints following OpenAPI standards

## Key Features Implemented

### 🤖 AI-Powered Planning (Backend API)
- **Smart Recipe Generation**: Generate complete recipes from meal names with AI-suggested ingredients, cook times, and instructions
- **Intelligent Meal Planning**: Create 7-day meal plans based on available ingredients and dietary preferences
- **Fuzzy Ingredient Matching**: Intelligent matching (90% confidence threshold using difflib.SequenceMatcher) to household inventory
- **Bulk Meal Saving**: Atomic transaction-based bulk meal creation with fuzzy recipe auto-matching (85% threshold)

### 🏠 Household Collaboration (Backend API)
- **Multi-User Households**: Household membership management with creator/member roles
- **Shared Ingredient Inventory**: Centralized pantry tracking across household members
- **Meal Assignment**: Assign cooking responsibilities to household members via `assigned_to_id`
- **Recipe Sharing**: Public/private recipe management within households (`is_public` flag)

### 📅 Meal Planning (Backend API)
- **Scheduled Meals**: Create meals with date, type (breakfast/lunch/dinner/snack), and servings
- **Recipe Linking**: Link meals to recipes via `recipe_id` (manual or AI auto-matched)
- **Dietary Restrictions**: AI generates recipes considering dietary preferences (passed as request parameters)
- **Meal Retrieval**: Query meals by household, date range, and type

### 📖 Recipe Management (Backend API)
- **Custom Recipes**: Create and store recipes with ingredients, instructions, and metadata
- **Difficulty Levels**: Categorize by difficulty (EASY, MEDIUM, HARD enums)
- **Cuisine Types**: 10+ cuisine categories (ITALIAN, MEXICAN, ASIAN, AMERICAN, etc.)
- **Nutritional Info**: Store calories_per_serving field
- **Public/Private Recipes**: `is_public` boolean flag for sharing

### 🥕 Ingredient & Inventory (Backend API)
- **Categorized Ingredients**: 15 categories (PRODUCE, MEAT, DAIRY, SPICES, etc.)
- **Unit Conversion Support**: 18 unit types (GRAM, KILOGRAM, CUP, TABLESPOON, PIECE, etc.)
- **Household-Scoped**: All ingredients tied to specific households
- **Smart Matching**: AI-powered fuzzy matching to avoid duplicates

### 🛒 Grocery Lists (Backend API)
- **List Management**: Create grocery lists linked to households
- **Category Grouping**: Items organized by ingredient category
- **Purchase Tracking**: Mark items as purchased with `is_purchased` flag
- **Meal Integration**: Add ingredients from meal plans to grocery lists

### 📊 Software Engineering Practices

- **Layered Architecture**: Separation of concerns (API → Service → Repository → Model)
- **Design Patterns**: Repository, Service Layer, Dependency Injection, Factory Pattern, Result Wrapper
- **SOLID Principles**: Single Responsibility, Open/Closed, Dependency Inversion demonstrated
- **Test-Driven Development**: 77 total tests (60 AI tests fully mocked, 13 auth service tests, 4 conftest helpers)
- **Version Control**: Git with conventional commits
- **CI/CD**: GitHub Actions with automated testing and Codecov integration

## Technology Stack

### Backend Framework
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.11+ | Programming language |
| **FastAPI** | 0.120.4 | Modern async web framework |
| **SQLAlchemy** | 2.0.44 | ORM and database toolkit |
| **PostgreSQL** | Latest | Production database (SQLite for tests) |
| **Pydantic** | 2.12.3 | Data validation and settings |
| **Alembic** | 1.17.1 | Database migrations |

### AI & External Services
| Technology | Version | Purpose |
|------------|---------|---------|
| **Google Gemini AI** | 1.54.0+ | Recipe & meal plan generation |
| **httpx** | 0.28.1 | Async HTTP client for Gemini API |

### Security & Authentication
| Technology | Version | Purpose |
|------------|---------|---------|
| **JWT (PyJWT)** | 2.10.1 | Token-based authentication |
| **bcrypt** | 5.0.0 | Password hashing |
| **Passlib** | 1.7.4 | Password utilities |

### Testing & Quality Assurance
| Technology | Version | Purpose |
|------------|---------|---------|
| **pytest** | Latest | Testing framework |
| **pytest-cov** | Latest | Coverage reporting |
| **pytest-asyncio** | Latest | Async test support |
| **Factory Boy** | Latest | Test fixture generation |
| **Faker** | Latest | Mock data generation |

### DevOps & CI/CD
| Technology | Version | Purpose |
|------------|---------|---------|
| **GitHub Actions** | - | CI/CD pipeline |
| **Codecov** | - | Coverage & test results reporting |

> **Note**: Docker containerization is listed but not yet fully configured.

## System Architecture

### Architectural Pattern: Layered Architecture

```
┌─────────────────────────────────────────────┐
│           API Layer (FastAPI)                │
│   /api/v1/{ai, auth, households, recipes,   │
│            meals, ingredients, groceries}    │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│          Service Layer (Business Logic)      │
│   AIService, AuthService, MealService, etc.  │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│       Repository Layer (Data Access)         │
│   RecipeRepo, MealRepo, IngredientRepo, etc.│
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Model Layer (SQLAlchemy ORM)         │
│   User, Household, Recipe, Meal, Ingredient  │
└─────────────────────────────────────────────┘
```

### Key Design Patterns

1. **Repository Pattern**: Abstracts data access logic (base class in `app/repositories/repository.py`)
2. **Service Layer Pattern**: Encapsulates business logic (all services in `app/services/`)
3. **Dependency Injection**: Loose coupling via FastAPI `Depends()` (`app/dependencies.py`)
4. **Factory Pattern**: Test fixture generation via Factory Boy (`tests/conftest.py`)
5. **Result Wrapper Pattern**: Standardized API responses (`app/schemas/result.py`)

## Project Structure

```
MealSync/
├── app/
│   ├── api/v1/              # API endpoints (RESTful routes) - 65 endpoints
│   │   ├── ai.py            # AI-powered features (5 endpoints, 60 tests)
│   │   ├── auth.py          # Authentication (6 endpoints)
│   │   ├── households.py    # Household management (10 endpoints)
│   │   ├── recipes.py       # Recipe CRUD (7 endpoints)
│   │   ├── meals.py         # Meal scheduling (11 endpoints)
│   │   ├── ingredients.py   # Ingredient inventory (6 endpoints)
│   │   ├── grocery_lists.py # Grocery lists (13 endpoints)
│   │   └── user.py          # User management (7 endpoints)
│   ├── core/                # Core utilities & config
│   │   ├── exception.py     # Custom exception classes
│   │   └── middleware.py    # Request/response middleware
│   ├── models/              # SQLAlchemy ORM models (8 models)
│   │   ├── base.py          # BaseModel with UUID, timestamps
│   │   ├── user.py
│   │   ├── household.py
│   │   ├── recipe.py
│   │   ├── meal.py
│   │   ├── ingredient.py    # Ingredient + RecipeIngredient
│   │   └── grocery_list.py  # GroceryList + GroceryListItem
│   ├── repositories/        # Data access layer (7 repositories)
│   │   ├── repository.py    # Base repository with CRUD
│   │   ├── recipe_repository.py
│   │   ├── meal_repository.py
│   │   ├── ingredient_repository.py
│   │   ├── household_repository.py
│   │   ├── userRepository.py
│   │   └── grocery_list_repository.py
│   ├── schemas/             # Pydantic validation schemas (8 schema files)
│   │   ├── ai.py            # AI request/response schemas
│   │   ├── recipe.py
│   │   ├── meal.py
│   │   ├── ingredient.py
│   │   ├── household.py
│   │   ├── user.py
│   │   ├── grocery_list.py
│   │   └── result.py        # Result wrapper pattern
│   ├── services/            # Business logic layer (7 services)
│   │   ├── ai_service.py    # AI integration (93% coverage, 743 LOC)
│   │   ├── recipe_service.py
│   │   ├── meal_service.py
│   │   ├── authService.py
│   │   ├── userService.py
│   │   ├── household_service.py
│   │   └── grocery_list_service.py
│   ├── utils/               # Utility functions
│   │   └── security.py      # Password hashing, JWT creation
│   ├── config.py            # Settings via Pydantic BaseSettings
│   ├── database.py          # Database session management
│   ├── dependencies.py      # FastAPI dependency injection
│   └── main.py              # Application entry point
├── tests/
│   ├── unit/                # Unit tests (40 AI + 13 auth = 53 tests)
│   │   └── test_services/
│   │       ├── test_ai_service.py (40 tests, 8 classes)
│   │       └── test_auth_service.py (13 tests)
│   ├── integration/         # Integration tests (20 AI tests)
│   │   └── test_api/
│   │       └── test_ai_endpoints.py (20 tests, 4 classes)
│   └── conftest.py          # Shared test fixtures (4 helper tests)
├── alembic/                 # Database migrations
│   ├── versions/            # Migration scripts
│   └── env.py
├── .github/workflows/       # CI/CD pipelines
│   └── test.yml             # Automated testing + Codecov
├── pyproject.toml           # Project dependencies (62 packages)
├── pytest.ini               # Pytest configuration (4 markers)
├── .env.example             # Environment variable template
└── README.md                # This file
```

## Installation & Setup

### Prerequisites

- **Python**: 3.11 or higher
- **PostgreSQL**: 12 or higher (for production; tests use SQLite)
- **Google Gemini API Key**: For AI features ([Get one here](https://ai.google.dev/))
- **Git**: For version control

### Installation Steps

1. **Clone the repository**:
```bash
git clone <repository-url>
cd mealsync
```

2. **Create and activate virtual environment**:
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -e .
```

4. **Configure environment variables**:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mealsync

# Security
SECRET_KEY=your-secret-key-here-min-32-characters
API_V1_STR=/api/v1

# AI Features
GEMINI_API_KEY=your-gemini-api-key-from-google

# Optional
ENVIRONMENT=development
DEBUG=true
```

5. **Initialize database**:
```bash
# Create database tables
alembic upgrade head
```

6. **Run the application**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Once running, access interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

### Test Structure

- **77 Total Tests**:
  - 60 AI tests (fully mocked, no API key required)
  - 13 Auth service tests
  - 4 Conftest helper tests
- **Test Coverage**: 63% overall, 93% for AI service
- **Test Categories**: Unit (53 tests) and Integration (20 tests)

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run only AI tests (no API key needed)
pytest -m ai -v

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only

# Run specific test file
pytest tests/unit/test_services/test_ai_service.py -v

# View coverage report
# Open htmlcov/index.html in browser
```

### Test Markers

Tests are organized using pytest markers defined in `pytest.ini`:
- `@pytest.mark.unit` - Unit tests (53 tests)
- `@pytest.mark.integration` - Integration tests (20 tests)
- `@pytest.mark.ai` - AI tests, fully mocked (60 tests)
- `@pytest.mark.slow` - Slow-running tests (not yet used)

### Current Coverage

- **Overall Coverage**: 63.24%
- **AI Service Coverage**: 93%
- **Total Tests**: 77 (60 AI + 13 auth + 4 helpers)
- **Lines of Code**: ~7,000 (app) + ~2,400 (tests) = ~9,400 total

## API Endpoints

> **Total**: 65 endpoints across 8 API modules

### Authentication (6 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login and receive JWT token |
| POST | `/api/v1/auth/logout` | Logout (invalidate token) |
| GET | `/api/v1/auth/me` | Get current user profile |
| PUT | `/api/v1/auth/change-password` | Change password |
| POST | `/api/v1/auth/refresh-token` | Refresh JWT token |

### AI Features (5 endpoints - Key Enhancements)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ai/generate-ingredients` | Generate ingredients from meal name |
| POST | `/api/v1/ai/generate-recipe` | Generate complete recipe with AI |
| POST | `/api/v1/ai/generate-meal-plan` | Generate 7-day meal plan |
| POST | `/api/v1/ai/save-recipe` | Save AI-generated recipe to database |
| POST | `/api/v1/ai/save-meal-plan` | Bulk save meal plan (atomic transaction) |

### Recipes (7 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/recipes` | List all recipes (with filters) |
| POST | `/api/v1/recipes` | Create new recipe |
| GET | `/api/v1/recipes/{id}` | Get recipe details |
| PUT | `/api/v1/recipes/{id}` | Update recipe |
| DELETE | `/api/v1/recipes/{id}` | Delete recipe |
| POST | `/api/v1/recipes/{id}/ingredients` | Add ingredient to recipe |
| DELETE | `/api/v1/recipes/{id}/ingredients/{ingredient_id}` | Remove ingredient |

### Meals (11 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/meals` | List scheduled meals |
| POST | `/api/v1/meals` | Schedule a meal |
| GET | `/api/v1/meals/{id}` | Get meal details |
| PUT | `/api/v1/meals/{id}` | Update meal |
| DELETE | `/api/v1/meals/{id}` | Delete meal |
| GET | `/api/v1/meals/calendar` | Get calendar view |
| GET | `/api/v1/meals/upcoming` | Get upcoming meals |
| PATCH | `/api/v1/meals/{id}/complete` | Mark meal as completed |
| GET | `/api/v1/meals/by-date` | Query meals by date range |
| GET | `/api/v1/meals/by-recipe/{recipe_id}` | Get meals using recipe |
| POST | `/api/v1/meals/bulk` | Bulk create meals |

### Households (10 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/households` | Create household |
| GET | `/api/v1/households` | List user's households |
| GET | `/api/v1/households/{id}` | Get household details |
| PUT | `/api/v1/households/{id}` | Update household |
| DELETE | `/api/v1/households/{id}` | Delete household |
| POST | `/api/v1/households/{id}/members` | Add member |
| DELETE | `/api/v1/households/{id}/members/{user_id}` | Remove member |
| GET | `/api/v1/households/{id}/members` | List members |
| PATCH | `/api/v1/households/{id}/transfer-ownership` | Transfer ownership |
| POST | `/api/v1/households/{id}/leave` | Leave household |

### Ingredients (6 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ingredients` | List ingredients |
| POST | `/api/v1/ingredients` | Add ingredient |
| GET | `/api/v1/ingredients/{id}` | Get ingredient details |
| PUT | `/api/v1/ingredients/{id}` | Update ingredient |
| DELETE | `/api/v1/ingredients/{id}` | Delete ingredient |
| GET | `/api/v1/ingredients/search` | Search ingredients |

### Grocery Lists (13 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/grocery-lists` | List grocery lists |
| POST | `/api/v1/grocery-lists` | Create grocery list |
| GET | `/api/v1/grocery-lists/{id}` | Get list details |
| PUT | `/api/v1/grocery-lists/{id}` | Update list |
| DELETE | `/api/v1/grocery-lists/{id}` | Delete list |
| POST | `/api/v1/grocery-lists/{id}/items` | Add items |
| PUT | `/api/v1/grocery-lists/{id}/items/{item_id}` | Update item |
| DELETE | `/api/v1/grocery-lists/{id}/items/{item_id}` | Remove item |
| PATCH | `/api/v1/grocery-lists/{id}/items/{item_id}/purchase` | Mark as purchased |
| POST | `/api/v1/grocery-lists/{id}/from-meal-plan` | Generate from meal plan |
| GET | `/api/v1/grocery-lists/{id}/by-category` | Group items by category |
| PATCH | `/api/v1/grocery-lists/{id}/clear-purchased` | Clear purchased items |
| POST | `/api/v1/grocery-lists/{id}/share` | Share list with household |

### User Management (7 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/me` | Get current user |
| PUT | `/api/v1/users/me` | Update current user |
| DELETE | `/api/v1/users/me` | Delete account |
| GET | `/api/v1/users/{id}` | Get user by ID |
| GET | `/api/v1/users/{id}/recipes` | Get user's recipes |
| GET | `/api/v1/users/{id}/households` | Get user's households |
| POST | `/api/v1/users/search` | Search users |

## Software Metrics & Cost Estimation

### COCOMO Model Estimation

**Project Metrics** (Verified):
- **Lines of Code**: ~7,000 (app code, excluding tests/comments)
- **Test Lines**: ~2,400
- **Total Lines**: ~9,400
- **Mode**: Organic (well-understood domain, small team)
- **Team Size**: 3-4 developers

**Effort Estimation** (COCOMO Basic Model):
- **Estimated Effort**: 6-8 person-months
- **Development Time**: 3-4 months
- **Team Size**: 2-3 developers

> **Note**: Actual project timeline was ~2 months (academic semester constraint).

### Code Metrics (Verified)

| Metric | Value |
|--------|-------|
| Total Python Files | 50 |
| Lines of Code (app) | ~7,000 |
| Lines of Code (tests) | ~2,400 |
| Test Coverage | 63.24% |
| Number of Modules | 50+ |
| API Endpoints | 65 |
| Database Models | 8 |
| Repository Classes | 7 |
| Service Classes | 7 |
| Test Cases | 77 |

## Advanced Features Implemented

### 1. AI-Powered Meal Plan Saving (Latest Enhancement)

**Feature**: Bulk meal plan creation with intelligent recipe matching

**Implementation**:
- Atomic transactions (all-or-nothing via SQLAlchemy session)
- Fuzzy recipe name matching (85% confidence threshold using `difflib.SequenceMatcher`)
- Auto-creation of missing ingredients with deduplication (set-based)
- Frontend can edit before saving (cherry-pick meals, modify dates/servings)
- Auto-matching uses existing household recipes

**File**: [app/services/ai_service.py:621-743](app/services/ai_service.py#L621-L743)

**Tests**: 13 tests (7 unit + 6 integration)

**Example Usage**:
```python
POST /api/v1/ai/save-meal-plan
{
  "household_id": 1,
  "meals": [
    {
      "meal_name": "Spaghetti Bolognese",
      "meal_type": "dinner",
      "meal_date": "2025-12-20",
      "servings": 4,
      "additional_ingredients_needed": ["basil", "oregano"]
    }
  ],
  "auto_create_ingredients": true,
  "auto_match_recipes": true
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "message": "Successfully created 1 meals",
    "total_meals_created": 1,
    "meal_ids": [42],
    "meal_uuids": ["550e8400-e29b-41d4-a716-446655440000"],
    "ingredients_created": 2,
    "ingredients_created_list": ["basil", "oregano"],
    "recipes_matched": 1,
    "recipes_matched_details": [
      {
        "meal_name": "Spaghetti Bolognese",
        "recipe_id": 15,
        "recipe_name": "Spaghetti Bolognese"
      }
    ]
  }
}
```

### 2. Ingredient Fuzzy Matching

**Algorithm**: `difflib.SequenceMatcher` with 90% confidence threshold

**Implementation**: [app/services/ai_service.py:846-932](app/services/ai_service.py#L846-L932)

**Benefits**:
- Reduces duplicate ingredients
- Handles typos and case variations ("Tomato" vs "tomato")
- Category-based filtering for improved accuracy

**Example**:
- User input: "tomatoe" → Matches existing "Tomato" (ratio: 0.93)
- User input: "chicken breast" → Matches "Chicken Breast" (ratio: 1.0)

### 3. Repository Pattern Implementation

**Base Repository**: [app/repositories/repository.py](app/repositories/repository.py)

**Benefits**:
- Abstraction of data access (service layer doesn't know about SQLAlchemy)
- Testability (easy to mock repositories in service tests)
- Consistent CRUD operations across all models
- Reusable query logic (filters, pagination)

**Pattern**:
```python
class BaseRepository:
    def get(self, id: int) -> Optional[Model]
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Model]
    def create(self, obj: Model) -> Model
    def update(self, id: int, obj_in: dict) -> Optional[Model]
    def delete(self, id: int) -> bool
```

## CI/CD Pipeline

### GitHub Actions Workflow

**Automated on every push/PR** (`.github/workflows/test.yml`):
1. Setup Python 3.11 environment with uv package installer
2. Install project dependencies
3. Start PostgreSQL 13 test database service
4. Set environment variables (DATABASE_URL, GEMINI_API_KEY=dummy)
5. Run all tests with coverage: `pytest tests/ --cov=app --junitxml=junit.xml -v`
6. Upload coverage report to Codecov
7. Upload test results (JUnit XML) to Codecov

**Status**: ✅ CI passing, all tests green

**Coverage Reports**: Automatically uploaded to Codecov with historical tracking

## Development Practices

### Version Control

- **Strategy**: Feature branching (not enforced for academic project)
- **Commit Format**: Conventional commits (`feat:`, `fix:`, `test:`, `docs:`)
- **Branch**: `main` (single branch for academic submission)
- **History**: Clean commit history with descriptive messages

### Code Quality

- **Linting**: Ruff configured in `pyproject.toml` (not strictly enforced)
- **Type Hints**: Extensive use of Python type hints and Pydantic models
- **Docstrings**: Google-style docstrings for all public methods
- **Error Handling**: Custom exception hierarchy in `app/core/exception.py`

### Testing Strategy

1. **Unit Tests**: Test individual service methods and business logic
2. **Integration Tests**: Test full request/response cycles with TestClient
3. **Mocking**: All AI calls mocked using `unittest.mock` for reproducibility
4. **Fixtures**: Reusable test data via pytest fixtures in `conftest.py`

## Academic Context

### Module: CN7021 - Advanced Software Engineering
### Institution: University of East London
### Assessment: Group Coursework (50%)

### Learning Outcomes Demonstrated

1. **LO1**: Software architecture design → Layered architecture, Repository pattern, Service layer
2. **LO2**: Testing strategies → 77 tests (unit/integration), 63% coverage, mocking, TDD principles
3. **LO3**: Refactoring and code quality → SOLID principles, DRY, clean code practices
4. **LO4**: Version control → Git with conventional commits
5. **LO5**: Continuous integration → GitHub Actions with automated testing + Codecov
6. **LO6**: AI integration → Gemini API integration, prompt engineering, error handling
7. **LO7**: Database design → PostgreSQL schema, SQLAlchemy ORM, Alembic migrations
8. **LO8**: API design → RESTful principles, OpenAPI docs, authentication, Result wrapper

### Enhancements Over Base Project

> **Note**: This is a **new project** built from scratch (not an enhancement of existing open-source project). The "enhancements" listed below represent advanced features beyond a basic CRUD API.

| Enhancement | Implementation | Evidence |
|-------------|----------------|----------|
| AI Integration | Gemini-powered recipe & meal plan generation | [app/services/ai_service.py](app/services/ai_service.py) (743 LOC) |
| Advanced Testing | 77 tests with full AI mocking | [tests/](tests/) directory |
| Repository Pattern | Data access abstraction | [app/repositories/](app/repositories/) (7 repositories) |
| Service Layer | Business logic separation | [app/services/](app/services/) (7 services) |
| CI/CD Pipeline | Automated testing + Codecov | [.github/workflows/test.yml](.github/workflows/test.yml) |
| Bulk Operations | Atomic meal plan saving | [app/api/v1/ai.py:204-251](app/api/v1/ai.py#L204-L251) |
| Fuzzy Matching | Intelligent ingredient/recipe matching | [app/services/ai_service.py:846-932](app/services/ai_service.py#L846-L932) |
| Result Wrapper | Standardized API responses | [app/schemas/result.py](app/schemas/result.py) |

## Frontend Integration

> **Important**: The React frontend is being developed separately by team member 2 in a different Git repository.

### Frontend-Backend Architecture

```
┌─────────────────────────────────────┐
│      React Frontend (Member 2)      │
│   - UI/UX components                │
│   - State management                │
│   - API client service              │
└──────────────┬──────────────────────┘
               │ HTTP/JSON
               │ JWT Authentication
┌──────────────▼──────────────────────┐
│      FastAPI Backend (This Repo)    │
│   - RESTful API (65 endpoints)      │
│   - Business logic                  │
│   - Database persistence            │
└─────────────────────────────────────┘
```

### API Consumption Example (Frontend)

```typescript
// Example: Frontend consuming the save-meal-plan endpoint
const saveMealPlan = async (mealPlan: GeneratedMealPlan) => {
  const response = await fetch('/api/v1/ai/save-meal-plan', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getJWT()}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      household_id: mealPlan.household_id,
      meals: mealPlan.meal_suggestions.map(m => ({
        meal_name: m.meal_name,
        meal_type: m.meal_type,
        meal_date: m.meal_date,
        servings: 4,
        additional_ingredients_needed: m.additional_ingredients_needed
      })),
      auto_create_ingredients: true,
      auto_match_recipes: true
    })
  });

  const result = await response.json();
  if (result.success) {
    console.log(`Created ${result.data.total_meals_created} meals`);
  }
};
```

## Future Enhancements

- [ ] **Expiration Date Tracking**: Add `expiration_date` field to Ingredient model
- [ ] **Nutritional Analysis**: Integrate with nutrition API for detailed macros
- [ ] **Recipe Recommendation Engine**: ML-based recommendations based on user preferences
- [ ] **Real-time Collaboration**: WebSocket support for live meal plan updates
- [ ] **Recipe Rating & Reviews**: User rating system for recipes
- [ ] **Meal Prep Scheduling**: Advanced scheduling with prep-ahead logic
- [ ] **Shopping List Optimization**: Route optimization by store layout
- [ ] **Dietary Goal Tracking**: Calorie/macro tracking against user goals
- [ ] **Recipe Import**: Parse recipes from URLs or images (OCR)
- [ ] **Smart Notifications**: Expiration alerts, meal prep reminders

## References

### Academic References

1. Bass, L., Clements, P. and Kazman, R. (2022) *Software Architecture in Practice*. 4th edn. Boston: Addison-Wesley.

2. Fowler, M. (2018) *Refactoring: Improving the Design of Existing Code*. 2nd edn. Boston: Addison-Wesley.

3. Martin, R.C. (2017) *Clean Architecture: A Craftsman's Guide to Software Structure and Design*. Upper Saddle River: Prentice Hall.

4. Percival, H. and Gregory, B. (2020) *Architecture Patterns with Python*. Sebastopol: O'Reilly Media.

### Technical Documentation

- FastAPI Documentation: https://fastapi.tiangolo.com/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- Google Gemini API: https://ai.google.dev/
- Pytest Documentation: https://docs.pytest.org/
- Pydantic Documentation: https://docs.pydantic.dev/

## License

This project is submitted as academic coursework for CN7021 at the University of East London.

## Authors & Contributors

**Group Leader & Backend Developer**: Pius - u2845374
- API implementation
- AI integration with Google Gemini
- Comprehensive testing (77 tests, 63% coverage)
- CI/CD pipeline setup
- Database schema design

**Frontend Developer**: Bilal - [Student ID TBA]
- React UI development (separate repository)
- Frontend-backend integration
- User interface design

**Tutor**: [Tutor Name]
**Tutorial Group**: [Group Number]

---

**Developed for CN7021 Advanced Software Engineering**
**University of East London | 2025-26**
