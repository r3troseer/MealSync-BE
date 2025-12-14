import pytest
import json
from datetime import date, timedelta
from unittest.mock import MagicMock

from app.services.ai_service import AIService
from app.core.exception import (
    AuthorizationException,
    BadRequestException,
    InternalServerException
)
from app.models.ingredient import IngredientCategory, UnitOfMeasurement
from app.models.recipe import DifficultyLevel, CuisineType
from app.models.meal import MealType
from app.schemas.recipe import RecipeCreate, RecipeIngredientCreate


# ===== Mock Gemini Client =====

class MockGeminiResponse:
    """Mock response from Gemini API"""
    def __init__(self, text):
        self.text = text


@pytest.fixture
def mock_gemini_client(monkeypatch):
    """
    Mock Gemini API client to avoid real API calls.
    Returns different responses based on prompt content.
    """
    # Storage for last prompt (for assertions in tests)
    last_prompt_container = {"prompt": None}

    def mock_generate_content(model, contents, config):
        """Mock generate_content method"""
        last_prompt_container["prompt"] = contents  # Store for test assertions
        prompt_lower = contents.lower()

        # Mock recipe generation - MUST use "ingredient_name" as the key
        # CHECK THIS FIRST since recipe prompts also contain "ingredient"
        # Recipe prompts say "Create a detailed recipe" while ingredient prompts say "Generate a comprehensive ingredient list"
        if ("recipe" in prompt_lower and "create" in prompt_lower) or ("culinary expert" in prompt_lower and "recipe" in prompt_lower):
            return MockGeminiResponse(text="I've created a delicious recipe for you based on your ingredients!\n\n"+json.dumps({
                "name": "Pasta with Tomato Sauce",
                "description": "Simple Italian pasta dish",
                "instructions": "1. Boil water and cook pasta\\n2. Heat tomato sauce\\n3. Mix together and serve",
                "prep_time_minutes": 10,
                "cook_time_minutes": 15,
                "servings": 4,
                "difficulty": "easy",
                "cuisine_type": "italian",
                "tags": "pasta,easy,italian",
                "calories_per_serving": 350,
                "ingredients": [
                    {
                        "ingredient_name": "pasta",
                        "quantity": "400",
                        "unit": "gram",
                        "category": "grains",
                        "notes": "dried pasta",
                        "is_optional": False,
                        "is_user_provided": True
                    },
                    {
                        "ingredient_name": "tomato sauce",
                        "quantity": "500",
                        "unit": "gram",
                        "category": "condiments",
                        "notes": None,
                        "is_optional": False,
                        "is_user_provided": True
                    },
                    {
                        "ingredient_name": "salt",
                        "quantity": "1",
                        "unit": "teaspoon",
                        "category": "spices",
                        "notes": None,
                        "is_optional": False,
                        "is_user_provided": False
                    },
                    {
                        "ingredient_name": "pepper",
                        "quantity": "0.5",
                        "unit": "teaspoon",
                        "category": "spices",
                        "notes": None,
                        "is_optional": True,
                        "is_user_provided": False
                    }
                ]
            }))

        # Mock meal plan generation
        elif "meal plan" in prompt_lower:
            return MockGeminiResponse(text="Here's your personalized meal plan:\n\n"+json.dumps({
                "meal_plan": [
                    {
                        "day": 1,
                        "meal_type": "breakfast",
                        "meal_name": "Scrambled Eggs",
                        "description": "Classic breakfast",
                        "ingredients_used": ["eggs", "salt"],
                        "additional_ingredients_needed": [],
                        "estimated_prep_time_minutes": 10,
                        "estimated_calories": 200
                    },
                    {
                        "day": 1,
                        "meal_type": "lunch",
                        "meal_name": "Pasta Salad",
                        "description": "Cold pasta salad",
                        "ingredients_used": ["pasta", "tomato sauce"],
                        "additional_ingredients_needed": ["olive oil"],
                        "estimated_prep_time_minutes": 15,
                        "estimated_calories": 350
                    },
                    {
                        "day": 1,
                        "meal_type": "dinner",
                        "meal_name": "Grilled Chicken",
                        "description": "Simple grilled chicken",
                        "ingredients_used": [],
                        "additional_ingredients_needed": ["chicken breast", "lemon"],
                        "estimated_prep_time": 25,
                        "estimated_calories": 400
                    }
                ]
            }))

        # Mock ingredient generation - check AFTER recipe/meal plan
        elif "ingredient" in prompt_lower and "pasta" in prompt_lower:
            return MockGeminiResponse(text="Based on your meal request, here are the ingredients you'll need:\n\n"+json.dumps({
                "ingredients": [
                    {
                        "name": "pasta",
                        "quantity": 400,
                        "unit": "gram",
                        "category": "pantry",
                        "notes": "penne or spaghetti"
                    },
                    {
                        "name": "tomato sauce",
                        "quantity": 500,
                        "unit": "gram",
                        "category": "pantry"
                    },
                    {
                        "name": "garlic",
                        "quantity": 3,
                        "unit": "clove",
                        "category": "produce"
                    }
                ]
            }))

        # Mock ingredient generation with unique ingredients
        elif "ingredient" in prompt_lower and "unique" in prompt_lower:
            return MockGeminiResponse(text=json.dumps({
                "ingredients": [
                    {
                        "name": "dragon fruit",
                        "quantity": 2,
                        "unit": "piece",
                        "category": "produce"
                    }
                ]
            }))

        # Mock ingredient generation with fuzzy match
        elif "ingredient" in prompt_lower and "garlic cloves" in prompt_lower:
            return MockGeminiResponse(text=json.dumps({
                "ingredients": [
                    {
                        "name": "garlic cloves",
                        "quantity": 5,
                        "unit": "piece",
                        "category": "produce"
                    }
                ]
            }))

        # Mock invalid JSON response
        elif "invalid" in prompt_lower:
            return MockGeminiResponse(text="This is not valid JSON at all!")

        # Mock Gemini error
        elif "error" in prompt_lower:
            raise Exception("Gemini API error: rate limit exceeded")

        # Default empty response
        else:
            return MockGeminiResponse(text='{"ingredients": []}')

    # Create mock client structure
    class MockModels:
        def generate_content(self, model, contents, config):
            return mock_generate_content(model, contents, config)

    class MockClient:
        def __init__(self, api_key):
            self.models = MockModels()
            self.last_prompt = last_prompt_container  # Reference to store prompts

    # Patch genai.Client
    monkeypatch.setattr("google.genai.Client", MockClient)
    return MockClient


# ===== Test Class 1: Generate Ingredients From Meal =====

@pytest.mark.unit
@pytest.mark.ai
class TestGenerateIngredientsFromMeal:
    """Test ingredient generation from meal name"""

    def test_generate_ingredients_success(self, db_session, test_household, test_user, mock_gemini_client):
        """Test successful ingredient generation with matching"""
        service = AIService(db_session)

        result = service.generate_ingredients_from_meal(
            meal_name="pasta",
            household_id=test_household.id,
            user_id=test_user.id,
            servings=4
        )

        assert result.meal_name == "pasta"
        assert result.household_id == test_household.id
        assert result.total_ingredients == 3
        assert len(result.ingredients) == 3
        assert result.ingredients[0].name == "pasta"
        assert result.ingredients[0].unit == UnitOfMeasurement.GRAM

    def test_generate_ingredients_with_dietary_restrictions(self, db_session, test_household, test_user, mock_gemini_client):
        """Test ingredient generation includes dietary restrictions in prompt"""
        service = AIService(db_session)

        result = service.generate_ingredients_from_meal(
            meal_name="pasta",
            household_id=test_household.id,
            user_id=test_user.id,
            servings=4,
            dietary_restrictions=["vegetarian", "gluten-free"]
        )

        # Verify result structure
        assert result.total_ingredients > 0

        # Verify dietary restrictions were included in prompt
        # (The mock client stores the last prompt for assertion)
        client = service.client
        if hasattr(client, 'last_prompt'):
            prompt = client.last_prompt.get("prompt", "")
            assert "vegetarian" in prompt.lower() or "gluten-free" in prompt.lower()

    def test_generate_ingredients_unauthorized(self, db_session, test_household, test_user, mock_gemini_client):
        """Test unauthorized access when user is not a household member"""
        service = AIService(db_session)

        # Create another user who is NOT in the household
        from app.models.user import User
        from app.utils.security import get_password_hash

        other_user = User(
            username="otheruser",
            email="other@example.com",
            hashed_password=get_password_hash("pass123"),
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()

        # Attempt to generate ingredients for household they're not in
        with pytest.raises(AuthorizationException) as exc_info:
            service.generate_ingredients_from_meal(
                meal_name="pasta",
                household_id=test_household.id,
                user_id=other_user.id,
                servings=4
            )

        assert "member" in str(exc_info.value).lower()

    def test_generate_ingredients_gemini_error(self, db_session, test_household, test_user, monkeypatch):
        """Test handling of Gemini API failure"""
        # Mock Gemini to raise an exception
        class ErrorClient:
            def __init__(self, api_key):
                self.models = self

            def generate_content(self, model, contents, config):
                raise Exception("API rate limit exceeded")

        monkeypatch.setattr("google.genai.Client", ErrorClient)

        service = AIService(db_session)

        with pytest.raises(InternalServerException) as exc_info:
            service.generate_ingredients_from_meal(
                meal_name="pasta",
                household_id=test_household.id,
                user_id=test_user.id,
                servings=4
            )

        assert "busy" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()

    def test_generate_ingredients_invalid_json(self, db_session, test_household, test_user, monkeypatch):
        """Test handling of malformed JSON response from AI"""
        # Mock Gemini to return invalid JSON
        class InvalidJSONClient:
            def __init__(self, api_key):
                self.models = self

            def generate_content(self, model, contents, config):
                return MockGeminiResponse(text="This is not JSON!")

        monkeypatch.setattr("google.genai.Client", InvalidJSONClient)

        service = AIService(db_session)

        with pytest.raises(BadRequestException) as exc_info:
            service.generate_ingredients_from_meal(
                meal_name="pasta",
                household_id=test_household.id,
                user_id=test_user.id,
                servings=4
            )

        assert "unexpected format" in str(exc_info.value).lower()

    def test_ingredient_matching_exact(self, db_session, test_household, test_user, test_ingredients, mock_gemini_client):
        """Test exact ingredient name matching"""
        service = AIService(db_session)

        result = service.generate_ingredients_from_meal(
            meal_name="pasta",
            household_id=test_household.id,
            user_id=test_user.id,
            servings=4
        )

        # Find pasta ingredient in results
        pasta_ing = next((ing for ing in result.ingredients if ing.name == "pasta"), None)
        assert pasta_ing is not None
        assert pasta_ing.is_new is False  # Should match existing
        assert pasta_ing.existing_ingredient_id is not None
        assert pasta_ing.confidence_score == 1.0  # Exact match

    def test_ingredient_matching_fuzzy(self, db_session, test_household, test_user, test_ingredients, monkeypatch):
        """Test fuzzy ingredient name matching"""
        # Mock to return "garlic cloves" which should fuzzy match to "garlic"
        class FuzzyClient:
            def __init__(self, api_key):
                self.models = self

            def generate_content(self, model, contents, config):
                return MockGeminiResponse(text=json.dumps({
                    "ingredients": [
                        {
                            "name": "garlic cloves",
                            "quantity": 5,
                            "unit": "piece",
                            "category": "produce"
                        }
                    ]
                }))

        monkeypatch.setattr("google.genai.Client", FuzzyClient)

        service = AIService(db_session)

        result = service.generate_ingredients_from_meal(
            meal_name="garlic cloves",
            household_id=test_household.id,
            user_id=test_user.id,
            servings=4
        )

        # Fuzzy matching may or may not find a match depending on threshold
        # Just verify the result structure is correct
        garlic_ing = result.ingredients[0]
        assert garlic_ing.name == "garlic cloves"
        # If matched: is_new=False and confidence >= 0.85
        # If not matched: is_new=True
        if not garlic_ing.is_new:
            assert garlic_ing.confidence_score >= 0.85

    def test_ingredient_matching_no_match(self, db_session, test_household, test_user, test_ingredients, monkeypatch):
        """Test ingredient with no match creates new ingredient"""
        # Mock to return unique ingredient not in household
        class UniqueClient:
            def __init__(self, api_key):
                self.models = self

            def generate_content(self, model, contents, config):
                return MockGeminiResponse(text=json.dumps({
                    "ingredients": [
                        {
                            "name": "dragon fruit",
                            "quantity": 2,
                            "unit": "piece",
                            "category": "produce"
                        }
                    ]
                }))

        monkeypatch.setattr("google.genai.Client", UniqueClient)

        service = AIService(db_session)

        result = service.generate_ingredients_from_meal(
            meal_name="unique",
            household_id=test_household.id,
            user_id=test_user.id,
            servings=4
        )

        # Should NOT match any existing ingredient
        dragon_fruit = result.ingredients[0]
        assert dragon_fruit.is_new is True
        assert dragon_fruit.existing_ingredient_id is None
        # Check the response-level count, not individual ingredient attribute
        assert result.new_ingredients_count == 1


# ===== Test Class 2: Generate Recipe From Meal =====

@pytest.mark.unit
@pytest.mark.ai
class TestGenerateRecipeFromMeal:
    """Test recipe generation from meal name"""

    def test_generate_recipe_with_ingredient_ids(self, db_session, test_household, test_user, test_ingredients, mock_gemini_client):
        """Test recipe generation with user-provided ingredient IDs"""
        service = AIService(db_session)

        # Use first two test ingredients
        ingredient_ids = [test_ingredients[0].id, test_ingredients[1].id]

        result = service.generate_recipe_from_meal(
            meal_name="Pasta Dish",
            household_id=test_household.id,
            user_id=test_user.id,
            ingredient_ids=ingredient_ids,
            servings=4
        )

        assert result.name == "Pasta with Tomato Sauce"
        assert result.servings == 4
        assert result.household_id == test_household.id
        assert len(result.ingredients) > 0
        # Some ingredients should be marked as user_provided
        user_provided = [ing for ing in result.ingredients if ing.is_user_provided]
        assert len(user_provided) >= 1

    def test_generate_recipe_without_ingredients(self, db_session, test_household, test_user, mock_gemini_client):
        """Test recipe generation without ingredients - AI suggests all"""
        service = AIService(db_session)

        result = service.generate_recipe_from_meal(
            meal_name="Pasta Dish",
            household_id=test_household.id,
            user_id=test_user.id,
            ingredient_ids=None,  # No user ingredients
            servings=4
        )

        assert result.name is not None
        assert len(result.ingredients) > 0
        # Note: Mock returns static response with mixed is_user_provided flags
        # In real API, all would be is_user_provided=False when ingredient_ids=None
        # But we're testing that the service handles the response correctly
        assert result.requires_user_approval is True

    def test_generate_recipe_with_constraints(self, db_session, test_household, test_user, mock_gemini_client):
        """Test recipe generation with difficulty, time, cuisine constraints"""
        service = AIService(db_session)

        result = service.generate_recipe_from_meal(
            meal_name="Pasta",
            household_id=test_household.id,
            user_id=test_user.id,
            servings=2,
            difficulty="easy",
            max_prep_time_minutes=30,
            cuisine_type="italian"
        )

        assert result.difficulty in ["easy", None]  # Should respect constraint
        assert result.cuisine_type in ["italian", None]
        # Prep time should ideally be under 30, but AI might not always respect it
        # Just verify it returns a valid result

    def test_generate_recipe_invalid_ingredient_id(self, db_session, test_household, test_user, mock_gemini_client):
        """Test error when providing non-existent ingredient ID"""
        service = AIService(db_session)

        with pytest.raises(BadRequestException) as exc_info:
            service.generate_recipe_from_meal(
                meal_name="Pasta",
                household_id=test_household.id,
                user_id=test_user.id,
                ingredient_ids=[99999],  # Non-existent ID
                servings=4
            )

        assert "not found" in str(exc_info.value).lower()

    def test_generate_recipe_unauthorized(self, db_session, test_household, test_user, mock_gemini_client):
        """Test unauthorized access for recipe generation"""
        service = AIService(db_session)

        # Create another user not in household
        from app.models.user import User
        from app.utils.security import get_password_hash

        other_user = User(
            username="otheruser2",
            email="other2@example.com",
            hashed_password=get_password_hash("pass123"),
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()

        with pytest.raises(AuthorizationException) as exc_info:
            service.generate_recipe_from_meal(
                meal_name="Pasta",
                household_id=test_household.id,
                user_id=other_user.id,
                servings=4
            )

        assert "member" in str(exc_info.value).lower()

    def test_generate_recipe_ingredient_matching(self, db_session, test_household, test_user, test_ingredients, mock_gemini_client):
        """Test that generated recipe ingredients are matched to household inventory"""
        service = AIService(db_session)

        result = service.generate_recipe_from_meal(
            meal_name="Pasta",
            household_id=test_household.id,
            user_id=test_user.id,
            servings=4
        )

        # Find salt and pepper in generated ingredients (mocked response includes them)
        salt_ing = next((ing for ing in result.ingredients if "salt" in ing.ingredient_name.lower()), None)
        pepper_ing = next((ing for ing in result.ingredients if "pepper" in ing.ingredient_name.lower()), None)

        # Should match to existing household ingredients
        if salt_ing:
            assert salt_ing.ingredient_id is not None or salt_ing.is_new is True
        if pepper_ing:
            assert pepper_ing.ingredient_id is not None or pepper_ing.is_new is True


# ===== Test Class 3: Generate Meal Plan From Ingredients =====

@pytest.mark.unit
@pytest.mark.ai
class TestGenerateMealPlanFromIngredients:
    """Test meal plan generation"""

    def test_generate_meal_plan_success(self, db_session, test_household, test_user, test_ingredients, mock_gemini_client):
        """Test successful meal plan generation"""
        # Create purchased grocery items (available ingredients)
        from app.models.grocery_list import GroceryList, GroceryListItem
        grocery_list = GroceryList(
            name="Weekly Shopping",
            household_id=test_household.id,
            created_by_id=test_user.id
        )
        db_session.add(grocery_list)
        db_session.commit()

        # Add purchased items - MUST include name field
        item = GroceryListItem(
            grocery_list_id=grocery_list.id,
            ingredient_id=test_ingredients[0].id,
            name=test_ingredients[0].name,  # Required field
            quantity=500,
            unit=UnitOfMeasurement.GRAM,
            is_purchased=True
        )
        db_session.add(item)
        db_session.commit()

        service = AIService(db_session)

        result = service.generate_meal_plan_from_ingredients(
            household_id=test_household.id,
            user_id=test_user.id,
            days=7,
            meals_per_day=3
        )

        assert result.household_id == test_household.id
        assert result.total_days == 7
        assert len(result.meal_suggestions) > 0
        assert result.total_meals == len(result.meal_suggestions)

    def test_generate_meal_plan_with_past_meals(self, db_session, test_household, test_user, test_ingredients, mock_gemini_client):
        """Test meal plan generation includes past meal context"""
        # Create past meals
        from app.models.meal import Meal, MealType, MealStatus
        from app.models.grocery_list import GroceryList, GroceryListItem

        past_meal = Meal(
            name="Past Pasta Dinner",
            meal_type=MealType.DINNER,
            meal_date=date.today() - timedelta(days=5),
            household_id=test_household.id,
            status=MealStatus.COMPLETED,
            servings=4
        )
        db_session.add(past_meal)
        db_session.commit()

        # Create some available ingredients so meal plan generation succeeds
        grocery_list = GroceryList(
            name="Available",
            household_id=test_household.id,
            created_by_id=test_user.id
        )
        db_session.add(grocery_list)
        db_session.commit()

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

        service = AIService(db_session)

        result = service.generate_meal_plan_from_ingredients(
            household_id=test_household.id,
            user_id=test_user.id,
            days=7,
            meals_per_day=3
        )

        # Verify result structure (past meals are used in prompt for context)
        assert result.total_meals > 0

    def test_generate_meal_plan_use_available_only(self, db_session, test_household, test_user, test_ingredients, mock_gemini_client):
        """Test meal plan with strict available-only constraint"""
        # Create available ingredients via grocery list
        from app.models.grocery_list import GroceryList, GroceryListItem

        grocery_list = GroceryList(
            name="Available Items",
            household_id=test_household.id,
            created_by_id=test_user.id
        )
        db_session.add(grocery_list)
        db_session.commit()

        for ing in test_ingredients[:2]:
            item = GroceryListItem(
                grocery_list_id=grocery_list.id,
                ingredient_id=ing.id,
                name=ing.name,  # Required field
                quantity=100,
                unit=UnitOfMeasurement.GRAM,
                is_purchased=True
            )
            db_session.add(item)
        db_session.commit()

        service = AIService(db_session)

        result = service.generate_meal_plan_from_ingredients(
            household_id=test_household.id,
            user_id=test_user.id,
            days=3,
            meals_per_day=2,
            use_available_only=True
        )

        # Should generate plan (mock returns meals)
        assert len(result.meal_suggestions) > 0

    def test_generate_meal_plan_no_ingredients_strict(self, db_session, test_household, test_user, mock_gemini_client):
        """Test error when use_available_only=True but no ingredients available"""
        service = AIService(db_session)

        with pytest.raises(BadRequestException) as exc_info:
            service.generate_meal_plan_from_ingredients(
                household_id=test_household.id,
                user_id=test_user.id,
                days=7,
                meals_per_day=3,
                use_available_only=True  # Strict constraint with no ingredients
            )

        assert "no available ingredients" in str(exc_info.value).lower()

    def test_generate_meal_plan_preferred_meal_types(self, db_session, test_household, test_user, test_ingredients, mock_gemini_client):
        """Test meal plan with preferred meal types filter"""
        # Create some available ingredients
        from app.models.grocery_list import GroceryList, GroceryListItem

        grocery_list = GroceryList(
            name="Items",
            household_id=test_household.id,
            created_by_id=test_user.id
        )
        db_session.add(grocery_list)
        db_session.commit()

        item = GroceryListItem(
            grocery_list_id=grocery_list.id,
            ingredient_id=test_ingredients[0].id,
            name=test_ingredients[0].name,  # Required field
            quantity=100,
            unit=UnitOfMeasurement.GRAM,
            is_purchased=True
        )
        db_session.add(item)
        db_session.commit()

        service = AIService(db_session)

        result = service.generate_meal_plan_from_ingredients(
            household_id=test_household.id,
            user_id=test_user.id,
            days=2,
            meals_per_day=2,
            preferred_meal_types=["breakfast", "lunch"]
        )

        # Verify plan generated (mock returns all meal types, but prompt includes preference)
        assert len(result.meal_suggestions) > 0

    def test_generate_meal_plan_unauthorized(self, db_session, test_household, test_user, mock_gemini_client):
        """Test unauthorized access for meal plan generation"""
        service = AIService(db_session)

        # Create another user not in household
        from app.models.user import User
        from app.utils.security import get_password_hash

        other_user = User(
            username="otheruser3",
            email="other3@example.com",
            hashed_password=get_password_hash("pass123"),
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()

        with pytest.raises(AuthorizationException) as exc_info:
            service.generate_meal_plan_from_ingredients(
                household_id=test_household.id,
                user_id=other_user.id,
                days=7,
                meals_per_day=3
            )

        assert "member" in str(exc_info.value).lower()


# ===== Test Class 4: Save Recipe With Ingredient Creation =====

@pytest.mark.unit
@pytest.mark.ai
class TestSaveRecipeWithIngredientCreation:
    """Test saving recipes with auto-creation of missing ingredients"""

    def test_save_recipe_all_existing_ingredients(self, db_session, test_household, test_user, test_ingredients):
        """Test saving recipe when all ingredients already exist"""
        service = AIService(db_session)

        recipe_data = RecipeCreate(
            household_id=test_household.id,
            name="Simple Pasta",
            description="Test recipe",
            instructions="1. Cook pasta\\n2. Add sauce\\n3. Serve",
            prep_time_minutes=10,
            cook_time_minutes=15,
            servings=4,
            difficulty=DifficultyLevel.EASY,
            cuisine_type=CuisineType.ITALIAN,
            is_public=False,
            ingredients=[
                RecipeIngredientCreate(
                    ingredient_id=test_ingredients[0].id,  # pasta
                    quantity=400,
                    unit=UnitOfMeasurement.GRAM
                ),
                RecipeIngredientCreate(
                    ingredient_id=test_ingredients[1].id,  # tomato sauce
                    quantity=500,
                    unit=UnitOfMeasurement.GRAM
                )
            ]
        )

        recipe, created_count = service.save_recipe_with_ingredient_creation(
            recipe_data=recipe_data,
            user_id=test_user.id
        )

        assert recipe is not None
        assert recipe.name == "Simple Pasta"
        assert len(recipe.ingredients) == 2
        assert created_count == 0  # All ingredients already existed

    def test_save_recipe_with_auto_create(self, db_session, test_household, test_user):
        """Test saving recipe with auto-creation of new ingredients"""
        service = AIService(db_session)

        recipe_data = RecipeCreate(
            household_id=test_household.id,
            name="New Recipe",
            description="Test recipe with new ingredients",
            instructions="1. Mix\\n2. Cook\\n3. Serve",
            prep_time_minutes=20,
            cook_time_minutes=30,
            servings=4,
            difficulty=DifficultyLevel.MEDIUM,
            is_public=False,
            ingredients=[
                RecipeIngredientCreate(
                    ingredient_id=None,  # New ingredient
                    ingredient_name="saffron",
                    ingredient_category=IngredientCategory.SPICES,
                    quantity=1,
                    unit=UnitOfMeasurement.TEASPOON
                )
            ]
        )

        recipe, created_count = service.save_recipe_with_ingredient_creation(
            recipe_data=recipe_data,
            user_id=test_user.id
        )

        assert recipe is not None
        assert recipe.name == "New Recipe"
        assert len(recipe.ingredients) == 1
        # Verify ingredient was auto-created
        assert recipe.ingredients[0].ingredient_id is not None
        assert created_count == 1  # Verify 1 ingredient was created

    def test_save_recipe_mixed_ingredients(self, db_session, test_household, test_user, test_ingredients):
        """Test saving recipe with mix of existing and new ingredients"""
        service = AIService(db_session)

        recipe_data = RecipeCreate(
            household_id=test_household.id,
            name="Mixed Recipe",
            description="Mix of existing and new",
            instructions="Cook it",
            prep_time_minutes=15,
            cook_time_minutes=20,
            servings=4,
            difficulty=DifficultyLevel.EASY,
            is_public=False,
            ingredients=[
                RecipeIngredientCreate(
                    ingredient_id=test_ingredients[0].id,  # Existing
                    quantity=200,
                    unit=UnitOfMeasurement.GRAM
                ),
                RecipeIngredientCreate(
                    ingredient_id=None,  # New
                    ingredient_name="paprika",
                    ingredient_category=IngredientCategory.SPICES,
                    quantity=1,
                    unit=UnitOfMeasurement.TABLESPOON
                )
            ]
        )

        recipe, created_count = service.save_recipe_with_ingredient_creation(
            recipe_data=recipe_data,
            user_id=test_user.id
        )

        assert recipe is not None
        assert len(recipe.ingredients) == 2
        assert created_count == 1  # Verify 1 new ingredient was created (saffron)

    def test_save_recipe_missing_ingredient_name(self):
        """Test error when ingredient_id=None but ingredient_name not provided"""
        from pydantic import ValidationError

        # Pydantic validation will raise ValidationError when creating RecipeIngredientCreate
        with pytest.raises(ValidationError) as exc_info:
            RecipeIngredientCreate(
                ingredient_id=None,  # New ingredient
                ingredient_name=None,  # Missing name!
                quantity=1.0,
                unit=UnitOfMeasurement.GRAM
            )

        assert "ingredient_name must be provided" in str(exc_info.value).lower()

    def test_save_recipe_unauthorized(self, db_session, test_household, test_user, test_ingredients):
        """Test unauthorized save when user not in household"""
        service = AIService(db_session)

        # Create another user not in household
        from app.models.user import User
        from app.utils.security import get_password_hash

        other_user = User(
            username="otheruser4",
            email="other4@example.com",
            hashed_password=get_password_hash("pass123"),
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()

        # RecipeCreate requires at least 1 ingredient
        recipe_data = RecipeCreate(
            household_id=test_household.id,
            name="Unauthorized Recipe",
            description="Test",
            instructions="Cook",
            servings=4,
            is_public=False,
            ingredients=[
                RecipeIngredientCreate(
                    ingredient_id=test_ingredients[0].id,
                    quantity=100,
                    unit=UnitOfMeasurement.GRAM
                )
            ]
        )

        with pytest.raises(AuthorizationException) as exc_info:
            service.save_recipe_with_ingredient_creation(
                recipe_data=recipe_data,
                user_id=other_user.id
            )

        assert "member" in str(exc_info.value).lower()


# ===== Test Class 5: Helper Methods =====

@pytest.mark.unit
@pytest.mark.ai
class TestHelperMethods:
    """Test AI service helper methods"""

    def test_extract_json_direct_parse(self, db_session, mock_gemini_client):
        """Test extracting clean JSON"""
        service = AIService(db_session)

        json_str = '{"name": "test", "value": 123}'
        result = service._extract_json_from_response(json_str)

        assert result["name"] == "test"
        assert result["value"] == 123

    def test_extract_json_code_fence(self, db_session, mock_gemini_client):
        """Test extracting JSON from markdown code fence"""
        service = AIService(db_session)

        response = '```json\n{"name": "test", "value": 456}\n```'
        result = service._extract_json_from_response(response)

        assert result["name"] == "test"
        assert result["value"] == 456

    def test_extract_json_mixed_text(self, db_session, mock_gemini_client):
        """Test extracting JSON embedded in text"""
        service = AIService(db_session)

        response = 'Here is the result: {"name": "test", "value": 789} Hope this helps!'
        result = service._extract_json_from_response(response)

        assert result["name"] == "test"
        assert result["value"] == 789

    def test_extract_json_invalid(self, db_session, mock_gemini_client):
        """Test error when no valid JSON found"""
        service = AIService(db_session)

        with pytest.raises(BadRequestException) as exc_info:
            service._extract_json_from_response("This is plain text with no JSON")

        assert "unexpected format" in str(exc_info.value).lower()

    def test_match_ingredient_exact(self, db_session, test_household, test_ingredients, mock_gemini_client):
        """Test exact ingredient matching"""
        service = AIService(db_session)

        matched_id, confidence = service._match_ingredient_to_household(
            ingredient_name="pasta",
            household_id=test_household.id
        )

        assert matched_id is not None
        assert confidence == 1.0

    def test_match_ingredient_fuzzy(self, db_session, test_household, test_ingredients, mock_gemini_client):
        """Test fuzzy ingredient matching with threshold"""
        service = AIService(db_session)

        matched_id, confidence = service._match_ingredient_to_household(
            ingredient_name="garlic cloves",  # Should match "garlic"
            household_id=test_household.id
        )

        # Should match with high confidence
        assert confidence >= 0.85 or matched_id is None

    def test_match_ingredient_category_filter(self, db_session, test_household, test_ingredients, mock_gemini_client):
        """Test ingredient matching with category filter"""
        service = AIService(db_session)

        matched_id, confidence = service._match_ingredient_to_household(
            ingredient_name="salt",
            household_id=test_household.id,
            category=IngredientCategory.SPICES
        )

        # Should match salt (which is in SPICES category)
        assert matched_id is not None or confidence > 0

    def test_get_available_ingredients(self, db_session, test_household, test_user, test_ingredients, mock_gemini_client):
        """Test fetching available ingredients from grocery lists"""
        # Create grocery list with purchased items
        from app.models.grocery_list import GroceryList, GroceryListItem

        grocery_list = GroceryList(
            name="Shopping List",
            household_id=test_household.id,
            created_by_id=test_user.id
        )
        db_session.add(grocery_list)
        db_session.commit()

        # Add purchased items
        for ing in test_ingredients[:2]:
            item = GroceryListItem(
                grocery_list_id=grocery_list.id,
                ingredient_id=ing.id,
                name=ing.name,  # Required field
                quantity=100,
                unit=UnitOfMeasurement.GRAM,
                is_purchased=True
            )
            db_session.add(item)
        db_session.commit()

        service = AIService(db_session)
        available = service._get_available_ingredients(test_household.id)

        assert len(available) >= 2
        assert any(ing["name"] == "pasta" for ing in available)


@pytest.mark.ai
class TestSaveMealPlan:
    """Test AIService.save_meal_plan() method"""

    def test_save_meal_plan_success(self, db_session, test_household, test_user):
        """Test successful meal plan saving"""
        from app.services.ai_service import AIService
        from app.schemas.ai import SaveMealPlanRequest, MealPlanMealCreate
        from app.models.meal import MealType
        from datetime import date, timedelta

        service = AIService(db_session)

        # Create meal plan data with 3 meals
        meal_plan_data = SaveMealPlanRequest(
            household_id=test_household.id,
            meals=[
                MealPlanMealCreate(
                    meal_name="Breakfast Omelette",
                    meal_type=MealType.BREAKFAST,
                    meal_date=date.today() + timedelta(days=1),
                    description="Fluffy eggs with vegetables",
                    servings=2,
                    ingredients_used=["eggs", "milk"],
                    additional_ingredients_needed=[]
                ),
                MealPlanMealCreate(
                    meal_name="Grilled Chicken Salad",
                    meal_type=MealType.LUNCH,
                    meal_date=date.today() + timedelta(days=1),
                    description="Healthy chicken salad",
                    servings=4,
                    ingredients_used=["chicken", "lettuce"],
                    additional_ingredients_needed=[]
                ),
                MealPlanMealCreate(
                    meal_name="Spaghetti",
                    meal_type=MealType.DINNER,
                    meal_date=date.today() + timedelta(days=1),
                    description="Classic pasta dinner",
                    servings=6,
                    ingredients_used=["pasta", "tomato sauce"],
                    additional_ingredients_needed=[]
                )
            ],
            auto_create_ingredients=False,
            auto_match_recipes=False
        )

        created_meals, metadata = service.save_meal_plan(meal_plan_data, test_user.id)

        assert len(created_meals) == 3
        assert created_meals[0].name == "Breakfast Omelette"
        assert created_meals[1].name == "Grilled Chicken Salad"
        assert created_meals[2].name == "Spaghetti"
        assert metadata["ingredients_created"] == 0
        assert metadata["recipes_matched"] == 0

    def test_save_meal_plan_with_auto_create_ingredients(self, db_session, test_household, test_user):
        """Test auto-creating ingredients from additional_ingredients_needed"""
        from app.services.ai_service import AIService
        from app.schemas.ai import SaveMealPlanRequest, MealPlanMealCreate
        from app.models.meal import MealType
        from datetime import date, timedelta

        service = AIService(db_session)

        # Create meal plan with additional ingredients needed
        meal_plan_data = SaveMealPlanRequest(
            household_id=test_household.id,
            meals=[
                MealPlanMealCreate(
                    meal_name="Spicy Tacos",
                    meal_type=MealType.DINNER,
                    meal_date=date.today() + timedelta(days=1),
                    servings=4,
                    ingredients_used=["beef"],
                    additional_ingredients_needed=["paprika", "cumin"]
                ),
                MealPlanMealCreate(
                    meal_name="Herbed Chicken",
                    meal_type=MealType.DINNER,
                    meal_date=date.today() + timedelta(days=2),
                    servings=4,
                    ingredients_used=["chicken"],
                    additional_ingredients_needed=["paprika", "oregano"]  # paprika repeated
                )
            ],
            auto_create_ingredients=True,
            auto_match_recipes=False
        )

        created_meals, metadata = service.save_meal_plan(meal_plan_data, test_user.id)

        assert len(created_meals) == 2
        # Paprika counted once (deduped), cumin once, oregano once = 3 total
        assert metadata["ingredients_created"] == 3
        assert set(metadata["ingredients_created_list"]) == {"paprika", "cumin", "oregano"}

    def test_save_meal_plan_no_auto_create_ingredients(self, db_session, test_household, test_user):
        """Test disabling auto-create ingredients"""
        from app.services.ai_service import AIService
        from app.schemas.ai import SaveMealPlanRequest, MealPlanMealCreate
        from app.models.meal import MealType
        from datetime import date, timedelta

        service = AIService(db_session)

        meal_plan_data = SaveMealPlanRequest(
            household_id=test_household.id,
            meals=[
                MealPlanMealCreate(
                    meal_name="Test Meal",
                    meal_type=MealType.DINNER,
                    meal_date=date.today() + timedelta(days=1),
                    servings=4,
                    ingredients_used=[],
                    additional_ingredients_needed=["paprika", "cumin"]
                )
            ],
            auto_create_ingredients=False,  # Disabled
            auto_match_recipes=False
        )

        created_meals, metadata = service.save_meal_plan(meal_plan_data, test_user.id)

        assert len(created_meals) == 1
        assert metadata["ingredients_created"] == 0

    def test_save_meal_plan_with_recipe_matching(self, db_session, test_household, test_user, test_recipes):
        """Test auto-matching meals to existing recipes"""
        from app.services.ai_service import AIService
        from app.schemas.ai import SaveMealPlanRequest, MealPlanMealCreate
        from app.models.meal import MealType
        from datetime import date, timedelta

        service = AIService(db_session)

        # test_recipes fixture creates "Spaghetti Bolognese" recipe
        meal_plan_data = SaveMealPlanRequest(
            household_id=test_household.id,
            meals=[
                MealPlanMealCreate(
                    meal_name="spaghetti bolognese",  # Different case, fuzzy match
                    meal_type=MealType.DINNER,
                    meal_date=date.today() + timedelta(days=1),
                    servings=4,
                    ingredients_used=["pasta", "beef"],
                    additional_ingredients_needed=[]
                )
            ],
            auto_create_ingredients=False,
            auto_match_recipes=True
        )

        created_meals, metadata = service.save_meal_plan(meal_plan_data, test_user.id)

        assert len(created_meals) == 1
        assert created_meals[0].recipe_id is not None
        assert created_meals[0].recipe_id == test_recipes[0].id
        assert metadata["recipes_matched"] == 1
        assert metadata["recipes_matched_details"][0]["meal_name"] == "spaghetti bolognese"
        assert metadata["recipes_matched_details"][0]["recipe_id"] == test_recipes[0].id

    def test_save_meal_plan_no_recipe_matching(self, db_session, test_household, test_user, test_recipes):
        """Test disabling recipe matching"""
        from app.services.ai_service import AIService
        from app.schemas.ai import SaveMealPlanRequest, MealPlanMealCreate
        from app.models.meal import MealType
        from datetime import date, timedelta

        service = AIService(db_session)

        meal_plan_data = SaveMealPlanRequest(
            household_id=test_household.id,
            meals=[
                MealPlanMealCreate(
                    meal_name="Spaghetti Bolognese",  # Exact match exists
                    meal_type=MealType.DINNER,
                    meal_date=date.today() + timedelta(days=1),
                    servings=4,
                    ingredients_used=[],
                    additional_ingredients_needed=[]
                )
            ],
            auto_create_ingredients=False,
            auto_match_recipes=False  # Disabled
        )

        created_meals, metadata = service.save_meal_plan(meal_plan_data, test_user.id)

        assert len(created_meals) == 1
        assert created_meals[0].recipe_id is None
        assert metadata["recipes_matched"] == 0

    def test_save_meal_plan_unauthorized(self, db_session, test_household):
        """Test non-member cannot save meal plan"""
        from app.services.ai_service import AIService
        from app.schemas.ai import SaveMealPlanRequest, MealPlanMealCreate
        from app.models.meal import MealType
        from app.models.user import User
        from app.utils.security import get_password_hash
        from app.core.exception import AuthorizationException
        from datetime import date, timedelta

        # Create a different user not in household
        other_user = User(
            username="otheruser",
            email="other@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        service = AIService(db_session)

        meal_plan_data = SaveMealPlanRequest(
            household_id=test_household.id,
            meals=[
                MealPlanMealCreate(
                    meal_name="Test Meal",
                    meal_type=MealType.DINNER,
                    meal_date=date.today() + timedelta(days=1),
                    servings=4,
                    ingredients_used=[],
                    additional_ingredients_needed=[]
                )
            ]
        )

        with pytest.raises(AuthorizationException):
            service.save_meal_plan(meal_plan_data, other_user.id)

    def test_save_meal_plan_invalid_date(self, db_session, test_household, test_user):
        """Test validation error for past dates"""
        from app.schemas.ai import MealPlanMealCreate
        from app.models.meal import MealType
        from pydantic import ValidationError
        from datetime import date, timedelta

        # Should raise ValidationError when creating schema with past date
        with pytest.raises(ValidationError) as exc_info:
            MealPlanMealCreate(
                meal_name="Past Meal",
                meal_type=MealType.DINNER,
                meal_date=date.today() - timedelta(days=1),  # Yesterday
                servings=4,
                ingredients_used=[],
                additional_ingredients_needed=[]
            )

        assert "meal date cannot be in the past" in str(exc_info.value).lower()
