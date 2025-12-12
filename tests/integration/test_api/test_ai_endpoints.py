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
