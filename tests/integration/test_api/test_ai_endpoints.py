import pytest
import json
from datetime import date

from app.models.ingredient import IngredientCategory, UnitOfMeasurement
from app.models.recipe import DifficultyLevel, CuisineType
from app.models.meal import MealType


# ===== Mock Gemini Client for Integration Tests =====

class MockGeminiResponse:
    """Mock response from Gemini API"""
    def __init__(self, text):
        self.text = text


@pytest.fixture
def mock_gemini_for_integration(monkeypatch):
    """Mock Gemini API for integration tests"""
    def mock_generate_content(model, contents, config):
        prompt_lower = contents.lower()
        # Mock meal plan generation (check FIRST - most specific)
        if "meal plan" in prompt_lower:
            return MockGeminiResponse(text="Here's your personalized meal plan:\n\n"+json.dumps({
                "meal_plan": [
                    {
                        "day": 1,
                        "meal_type": MealType.BREAKFAST.value,
                        "meal_name": "Eggs",
                        "description": "Scrambled eggs",
                        "ingredients_used": ["eggs"],
                        "additional_ingredients_needed": [],
                        "estimated_prep_time_minutes": 10,
                        "estimated_calories": 200
                    },
                    {
                        "day": 1,
                        "meal_type": MealType.LUNCH.value,
                        "meal_name": "Pasta Salad",
                        "description": "Cold pasta",
                        "ingredients_used": ["pasta"],
                        "additional_ingredients_needed": ["dressing"],
                        "estimated_prep_time_minutes": 15,
                        "estimated_calories": 350
                    }
                ]
            }))

        # Mock recipe generation (check for "create" + "recipe")
        elif "create" in prompt_lower and "recipe" in prompt_lower:
            return MockGeminiResponse(text="Here's a delicious recipe for you!\n\n"+json.dumps({
                "name": "Pasta with Tomato Sauce",
                "description": "Simple pasta",
                "instructions": "1. Cook pasta\\n2. Add sauce\\n3. Serve",
                "prep_time_minutes": 10,
                "cook_time_minutes": 15,
                "servings": 4,
                "difficulty": "easy",
                "cuisine_type": "italian",
                "tags": "pasta,easy",
                "calories_per_serving": 350,
                "ingredients": [
                    {
                        "ingredient_name": "pasta",
                        "quantity": "400",
                        "unit": "gram",
                        "category": "grains",
                        "is_optional": False,
                        "is_user_provided": True
                    },
                    {
                        "ingredient_name": "olive oil",
                        "quantity": "2",
                        "unit": "tablespoon",
                        "category": "oils",
                        "is_optional": False,
                        "is_user_provided": False
                    }
                ]
            }))

        # Mock ingredient generation (check for "generate" + "ingredient")
        elif "generate" in prompt_lower and "ingredient" in prompt_lower:
            return MockGeminiResponse(text=json.dumps({
                "ingredients": [
                    {"name": "pasta", "quantity": 400, "unit": "gram", "category": "pantry"},
                    {"name": "tomato sauce", "quantity": 500, "unit": "gram", "category": "pantry"}
                ]
            }))

        return MockGeminiResponse(text='{}')

    class MockModels:
        def generate_content(self, model, contents, config):
            return mock_generate_content(model, contents, config)

    class MockClient:
        def __init__(self, api_key):
            self.models = MockModels()

    monkeypatch.setattr("google.genai.Client", MockClient)


# ===== Test Class 1: Generate Ingredients Endpoint =====

@pytest.mark.integration
@pytest.mark.ai
class TestGenerateIngredientsEndpoint:
    """Integration tests for /api/v1/ai/generate-ingredients endpoint"""

    def test_generate_ingredients_success(self, client, auth_headers, test_household, mock_gemini_for_integration):
        """Test successful ingredient generation via API"""
        response = client.post(
            "/api/v1/ai/generate-ingredients",
            json={
                "meal_name": "pasta dish",
                "household_id": test_household.id,
                "servings": 4
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["meal_name"] == "pasta dish"
        assert data["data"]["household_id"] == test_household.id
        assert data["data"]["total_ingredients"] > 0
        assert len(data["data"]["ingredients"]) > 0

    def test_generate_ingredients_unauthorized(self, client, test_household, mock_gemini_for_integration):
        """Test endpoint requires authentication"""
        response = client.post(
            "/api/v1/ai/generate-ingredients",
            json={
                "meal_name": "pasta",
                "household_id": test_household.id,
                "servings": 4
            }
            # No auth headers
        )

        assert response.status_code == 401

    def test_generate_ingredients_validation_error(self, client, auth_headers, test_household, mock_gemini_for_integration):
        """Test validation error when meal_name is missing"""
        response = client.post(
            "/api/v1/ai/generate-ingredients",
            json={
                # Missing meal_name
                "household_id": test_household.id,
                "servings": 4
            },
            headers=auth_headers
        )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["category"] == "Validation"


# ===== Test Class 2: Generate Recipe Endpoint =====

@pytest.mark.integration
@pytest.mark.ai
class TestGenerateRecipeEndpoint:
    """Integration tests for /api/v1/ai/generate-recipe endpoint"""

    def test_generate_recipe_success(self, client, auth_headers, test_household, mock_gemini_for_integration):
        """Test successful recipe generation"""
        response = client.post(
            "/api/v1/ai/generate-recipe",
            json={
                "meal_name": "pasta dish",
                "household_id": test_household.id,
                "servings": 4
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] is not None
        assert data["data"]["household_id"] == test_household.id
        assert len(data["data"]["ingredients"]) > 0

    def test_generate_recipe_with_ingredients(self, client, auth_headers, test_household, test_ingredients, mock_gemini_for_integration):
        """Test recipe generation with specific ingredient IDs"""
        response = client.post(
            "/api/v1/ai/generate-recipe",
            json={
                "meal_name": "pasta dish",
                "household_id": test_household.id,
                "ingredient_ids": [test_ingredients[0].id, test_ingredients[1].id],
                "servings": 4
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["ingredients"]) > 0

    def test_generate_recipe_unauthorized(self, client, test_household, mock_gemini_for_integration):
        """Test endpoint requires authentication"""
        response = client.post(
            "/api/v1/ai/generate-recipe",
            json={
                "meal_name": "pasta",
                "household_id": test_household.id,
                "servings": 4
            }
        )

        assert response.status_code == 401

    def test_generate_recipe_validation_error(self, client, auth_headers, test_household, mock_gemini_for_integration):
        """Test validation error when required fields missing"""
        response = client.post(
            "/api/v1/ai/generate-recipe",
            json={
                # Missing meal_name
                "household_id": test_household.id
            },
            headers=auth_headers
        )

        assert response.status_code == 422


# ===== Test Class 3: Generate Meal Plan Endpoint =====

@pytest.mark.integration
@pytest.mark.ai
class TestGenerateMealPlanEndpoint:
    """Integration tests for /api/v1/ai/generate-meal-plan endpoint"""

    def test_generate_meal_plan_success(self, client, auth_headers, db_session, test_household, test_ingredients, mock_gemini_for_integration):
        """Test successful meal plan generation"""
        # Create available ingredients via grocery list
        from app.models.grocery_list import GroceryList, GroceryListItem

        grocery_list = GroceryList(
            name="Shopping",
            household_id=test_household.id,
            created_by_id=test_household.created_by_id
        )
        db_session.add(grocery_list)
        db_session.commit()
        db_session.refresh(grocery_list)

        item = GroceryListItem(
            grocery_list_id=grocery_list.id,
            ingredient_id=test_ingredients[0].id,
            name=test_ingredients[0].name,
            quantity=100,
            unit=UnitOfMeasurement.GRAM,
            is_purchased=True
        )
        db_session.add(item)
        db_session.commit()

        response = client.post(
            "/api/v1/ai/generate-meal-plan",
            json={
                "household_id": test_household.id,
                "days": 3,
                "meals_per_day": 2
            },
            headers=auth_headers
        )

        if response.status_code != 200:
            print(f"Response: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["household_id"] == test_household.id
        assert data["data"]["total_days"] == 3
        assert len(data["data"]["meal_suggestions"]) > 0

    def test_generate_meal_plan_custom_params(self, client, auth_headers, db_session, test_household, test_ingredients, mock_gemini_for_integration):
        """Test meal plan with custom parameters"""
        # Create available ingredient
        from app.models.grocery_list import GroceryList, GroceryListItem

        grocery_list = GroceryList(
            name="Items",
            household_id=test_household.id,
            created_by_id=test_household.created_by_id
        )
        db_session.add(grocery_list)
        db_session.commit()
        db_session.refresh(grocery_list)

        item = GroceryListItem(
            grocery_list_id=grocery_list.id,
            ingredient_id=test_ingredients[0].id,
            name=test_ingredients[0].name,
            quantity=100,
            unit=UnitOfMeasurement.GRAM,
            is_purchased=True
        )
        db_session.add(item)
        db_session.commit()

        response = client.post(
            "/api/v1/ai/generate-meal-plan",
            json={
                "household_id": test_household.id,
                "days": 5,
                "meals_per_day": 3,
                "dietary_preferences": ["vegetarian"],
                "preferred_meal_types": ["breakfast", "lunch"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_days"] == 5

    def test_generate_meal_plan_unauthorized(self, client, test_household, mock_gemini_for_integration):
        """Test endpoint requires authentication"""
        response = client.post(
            "/api/v1/ai/generate-meal-plan",
            json={
                "household_id": test_household.id,
                "days": 7,
                "meals_per_day": 3
            }
        )

        assert response.status_code == 401


# ===== Test Class 4: Save Recipe Endpoint =====

@pytest.mark.integration
@pytest.mark.ai
class TestSaveRecipeEndpoint:
    """Integration tests for /api/v1/ai/save-recipe endpoint"""

    def test_save_recipe_with_auto_create(self, client, auth_headers, test_household, mock_gemini_for_integration):
        """Test saving recipe with auto-creation of ingredients"""
        response = client.post(
            "/api/v1/ai/save-recipe",
            json={
                "household_id": test_household.id,
                "name": "New Pasta Recipe",
                "description": "Delicious pasta",
                "instructions": "1. Cook\\n2. Serve",
                "prep_time_minutes": 15,
                "cook_time_minutes": 20,
                "servings": 4,
                "difficulty": "easy",
                "is_public": False,
                "ingredients": [
                    {
                        "ingredient_id": None,  # New ingredient
                        "ingredient_name": "saffron",
                        "ingredient_category": "spices",
                        "quantity": 1,
                        "unit": "teaspoon",
                        "is_optional": False
                    },
                    {
                        "ingredient_id": None,  # Another new ingredient
                        "ingredient_name": "cardamom",
                        "ingredient_category": "spices",
                        "quantity": 0.5,
                        "unit": "teaspoon",
                        "is_optional": True
                    }
                ]
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["recipe_id"] is not None
        assert data["data"]["recipe_uuid"] is not None
        assert data["data"]["created_ingredients_count"] == 2

    def test_save_recipe_all_existing(self, client, auth_headers, test_household, test_ingredients, mock_gemini_for_integration):
        """Test saving recipe with all existing ingredients"""
        response = client.post(
            "/api/v1/ai/save-recipe",
            json={
                "household_id": test_household.id,
                "name": "Simple Pasta",
                "description": "Basic pasta",
                "instructions": "Cook and serve",
                "servings": 4,
                "is_public": False,
                "ingredients": [
                    {
                        "ingredient_id": test_ingredients[0].id,
                        "quantity": 400,
                        "unit": "gram"
                    },
                    {
                        "ingredient_id": test_ingredients[1].id,
                        "quantity": 500,
                        "unit": "gram"
                    }
                ]
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["created_ingredients_count"] == 0  # No new ingredients

    def test_save_recipe_unauthorized(self, client, test_household, mock_gemini_for_integration):
        """Test endpoint requires authentication"""
        response = client.post(
            "/api/v1/ai/save-recipe",
            json={
                "household_id": test_household.id,
                "name": "Test Recipe",
                "instructions": "Cook",
                "servings": 4,
                "is_public": False,
                "ingredients": []
            }
        )

        assert response.status_code == 401

    def test_save_recipe_validation_error(self, client, auth_headers, test_household, mock_gemini_for_integration):
        """Test validation error when ingredient_name missing for new ingredient"""
        response = client.post(
            "/api/v1/ai/save-recipe",
            json={
                "household_id": test_household.id,
                "name": "Invalid Recipe",
                "instructions": "Cook",
                "servings": 4,
                "is_public": False,
                "ingredients": [
                    {
                        "ingredient_id": None,  # New ingredient
                        "ingredient_name": None,  # Missing name!
                        "quantity": 1,
                        "unit": "gram"
                    }
                ]
            },
            headers=auth_headers
        )

        # Should get validation error from Pydantic or service
        assert response.status_code in [400, 422]


@pytest.mark.ai
class TestSaveMealPlanEndpoint:
    """Test POST /api/v1/ai/save-meal-plan endpoint"""

    def test_save_meal_plan_success(self, client, auth_headers, test_household):
        """Test successful meal plan save via API"""
        from datetime import date, timedelta

        response = client.post(
            "/api/v1/ai/save-meal-plan",
            json={
                "household_id": test_household.id,
                "meals": [
                    {
                        "meal_name": "Breakfast Omelette",
                        "meal_type": "breakfast",
                        "meal_date": str(date.today() + timedelta(days=1)),
                        "description": "Fluffy eggs",
                        "servings": 2,
                        "ingredients_used": ["eggs"],
                        "additional_ingredients_needed": []
                    },
                    {
                        "meal_name": "Grilled Chicken",
                        "meal_type": "lunch",
                        "meal_date": str(date.today() + timedelta(days=1)),
                        "servings": 4,
                        "ingredients_used": ["chicken"],
                        "additional_ingredients_needed": []
                    },
                    {
                        "meal_name": "Pasta Dinner",
                        "meal_type": "dinner",
                        "meal_date": str(date.today() + timedelta(days=1)),
                        "servings": 6,
                        "ingredients_used": ["pasta"],
                        "additional_ingredients_needed": []
                    }
                ],
                "auto_create_ingredients": False,
                "auto_match_recipes": False
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_meals_created"] == 3
        assert len(data["data"]["meal_ids"]) == 3
        assert len(data["data"]["meal_uuids"]) == 3

    def test_save_meal_plan_single_meal(self, client, auth_headers, test_household):
        """Test saving just one meal from plan"""
        from datetime import date, timedelta

        response = client.post(
            "/api/v1/ai/save-meal-plan",
            json={
                "household_id": test_household.id,
                "meals": [
                    {
                        "meal_name": "Solo Dinner",
                        "meal_type": "dinner",
                        "meal_date": str(date.today() + timedelta(days=1)),
                        "servings": 2,
                        "ingredients_used": [],
                        "additional_ingredients_needed": []
                    }
                ]
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["total_meals_created"] == 1

    def test_save_meal_plan_with_auto_features(self, client, auth_headers, test_household, test_recipes):
        """Test auto-create and auto-match features"""
        from datetime import date, timedelta

        response = client.post(
            "/api/v1/ai/save-meal-plan",
            json={
                "household_id": test_household.id,
                "meals": [
                    {
                        "meal_name": "Spaghetti Bolognese",  # Should match recipe
                        "meal_type": "dinner",
                        "meal_date": str(date.today() + timedelta(days=1)),
                        "servings": 4,
                        "ingredients_used": ["pasta"],
                        "additional_ingredients_needed": ["basil", "oregano"]
                    }
                ],
                "auto_create_ingredients": True,
                "auto_match_recipes": True
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["total_meals_created"] == 1
        assert data["data"]["ingredients_created"] == 2
        assert set(data["data"]["ingredients_created_list"]) == {"basil", "oregano"}
        assert data["data"]["recipes_matched"] == 1

    def test_save_meal_plan_unauthorized(self, client, test_household):
        """Test unauthorized access"""
        from datetime import date, timedelta

        response = client.post(
            "/api/v1/ai/save-meal-plan",
            json={
                "household_id": test_household.id,
                "meals": [
                    {
                        "meal_name": "Test",
                        "meal_type": "dinner",
                        "meal_date": str(date.today() + timedelta(days=1)),
                        "servings": 2,
                        "ingredients_used": [],
                        "additional_ingredients_needed": []
                    }
                ]
            }
            # No auth headers
        )

        assert response.status_code == 401

    def test_save_meal_plan_validation_error(self, client, auth_headers, test_household):
        """Test validation errors"""
        response = client.post(
            "/api/v1/ai/save-meal-plan",
            json={
                "household_id": test_household.id,
                "meals": []  # Empty list not allowed (min_items=1)
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_save_meal_plan_non_member(self, client, db_session, test_household, test_user):
        """Test non-member trying to save"""
        from app.models.user import User
        from app.models.household import Household
        from app.models.associations import user_household
        from app.utils.security import get_password_hash
        from sqlalchemy import insert
        from datetime import date, timedelta

        # Create different user and household
        other_user = User(
            username="otheruser",
            email="other@example.com",
            hashed_password=get_password_hash("password"),
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_household = Household(
            name="Other Household",
            created_by_id=other_user.id,
            invite_code="OTHER123"
        )
        db_session.add(other_household)
        db_session.commit()
        db_session.refresh(other_household)

        # Add other_user to other_household
        stmt = insert(user_household).values(
            user_id=other_user.id,
            household_id=other_household.id,
            role="admin"
        )
        db_session.execute(stmt)
        db_session.commit()

        # Get auth token for other_user
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "otheruser", "password": "password"}
        )
        other_token = login_response.json()["data"]["access_token"]

        # Try to save to test_household (should fail)
        response = client.post(
            "/api/v1/ai/save-meal-plan",
            json={
                "household_id": test_household.id,  # Not member of this
                "meals": [
                    {
                        "meal_name": "Test",
                        "meal_type": "dinner",
                        "meal_date": str(date.today() + timedelta(days=1)),
                        "servings": 2,
                        "ingredients_used": [],
                        "additional_ingredients_needed": []
                    }
                ]
            },
            headers={"Authorization": f"Bearer {other_token}"}
        )

        assert response.status_code == 403
