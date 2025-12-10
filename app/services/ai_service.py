from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, timedelta
from difflib import SequenceMatcher
import json
import re

from google import genai
from google.genai import types

from app.config import settings
from app.repositories.ingredient_repository import IngredientRepository
from app.repositories.household_repository import HouseholdRepository
from app.repositories.grocery_list_repository import GroceryListRepository
from app.services.recipe_service import RecipeService
from app.models.ingredient import IngredientCategory, UnitOfMeasurement
from app.schemas.ai import (
    GenerateIngredientsResponse,
    GeneratedIngredient,
    GenerateRecipeResponse,
    GeneratedRecipeIngredient,
    GenerateMealPlanResponse,
    GeneratedMealSuggestion,
)
from app.schemas.recipe import RecipeCreate, RecipeIngredientCreate
from app.core.exception import (
    BadRequestException,
    InternalServerException,
    AuthorizationException,
)


class AIService:
    """Service layer for AI operations using Google Gemini API."""

    def __init__(self, db: Session):
        self.db = db
        self.ingredient_repo = IngredientRepository(db)
        self.household_repo = HouseholdRepository(db)
        self.grocery_list_repo = GroceryListRepository(db)
        self.recipe_service = RecipeService(db)

        # Initialize Google GenAI client
        if (
            not settings.GEMINI_API_KEY
            or settings.GEMINI_API_KEY == "your_api_key_here"
        ):
            raise InternalServerException(
                "AI service is not configured. Please contact administrator."
            )

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def generate_ingredients_from_meal(
        self,
        meal_name: str,
        household_id: int,
        user_id: int,
        servings: int = 4,
        dietary_restrictions: Optional[List[str]] = None,
    ) -> GenerateIngredientsResponse:
        """
        Generate ingredient list from meal name using AI.

        Args:
            meal_name: Name of the meal
            household_id: Household ID for ingredient matching
            user_id: User ID for authorization
            servings: Number of servings
            dietary_restrictions: Optional dietary constraints

        Returns:
            GenerateIngredientsResponse with matched ingredients

        Raises:
            AuthorizationException: If user not member
            InternalServerException: If AI call fails
        """
        # Verify household membership
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        # Build prompt
        restrictions_str = (
            ", ".join(dietary_restrictions) if dietary_restrictions else "None"
        )

        prompt = f"""You are a culinary expert. Generate a comprehensive ingredient list for "{meal_name}".

Requirements:
- Servings: {servings}
- Dietary restrictions: {restrictions_str}
- Format: Return ONLY valid JSON with no additional text or markdown

JSON Schema:
{{
  "ingredients": [
    {{
      "name": "ingredient name (lowercase)",
      "quantity": number,
      "unit": "gram|kilogram|ounce|pound|milliliter|liter|teaspoon|tablespoon|cup|pint|quart|gallon|piece|slice|clove|package|can|bunch|to_taste|as_needed",
      "category": "produce|meat|seafood|dairy|bakery|pantry|spices|beverages|frozen|snacks|other",
      "notes": "preparation notes (optional)"
    }}
  ]
}}

Example:
{{"ingredients": [{{"name": "chicken breast", "quantity": 500, "unit": "gram", "category": "meat", "notes": "boneless, skinless"}}]}}

Generate ingredients for {meal_name}:

note: Return ONLY valid JSON with no additional text or markdown
"""

        # Call Gemini API
        response_text = self._call_gemini_with_retry(prompt, temperature=0.7)

        # Parse JSON response
        response_data = self._extract_json_from_response(response_text)

        if "ingredients" not in response_data:
            raise BadRequestException(
                "AI returned invalid response format. Please try again."
            )

        # Match ingredients to household inventory
        generated_ingredients: List[GeneratedIngredient] = []
        new_count = 0
        matched_count = 0

        for ing_data in response_data["ingredients"]:
            # Match ingredient
            matched_id, confidence = self._match_ingredient_to_household(
                ing_data["name"],
                household_id,
                category=IngredientCategory(ing_data.get("category", "other")),
            )

            is_new = matched_id is None
            if is_new:
                new_count += 1
            else:
                matched_count += 1

            generated_ingredients.append(
                GeneratedIngredient(
                    name=ing_data["name"],
                    quantity=float(ing_data["quantity"]),
                    unit=UnitOfMeasurement(ing_data["unit"]),
                    category=IngredientCategory(ing_data.get("category", "other")),
                    notes=ing_data.get("notes"),
                    existing_ingredient_id=matched_id,
                    is_new=is_new,
                    confidence_score=confidence,
                )
            )

        return GenerateIngredientsResponse(
            meal_name=meal_name,
            ingredients=generated_ingredients,
            total_ingredients=len(generated_ingredients),
            new_ingredients_count=new_count,
            matched_ingredients_count=matched_count,
        )

    def generate_recipe_from_meal(
        self,
        meal_name: str,
        ingredient_ids: List[int],
        household_id: int,
        user_id: int,
        servings: int = 4,
        difficulty: Optional[str] = None,
        max_prep_time_minutes: Optional[int] = None,
        cuisine_type: Optional[str] = None,
        dietary_restrictions: Optional[List[str]] = None,
    ) -> GenerateRecipeResponse:
        """
        Generate complete recipe from meal name and ingredients.

        Args:
            meal_name: Name of the meal
            ingredient_ids: List of household ingredient IDs
            household_id: Household ID
            user_id: User ID for authorization
            servings: Number of servings
            difficulty: Optional difficulty filter
            max_prep_time_minutes: Maximum prep time
            cuisine_type: Optional cuisine type
            dietary_restrictions: Optional dietary constraints

        Returns:
            GenerateRecipeResponse for user approval

        Raises:
            AuthorizationException: If user not member
            BadRequestException: If ingredients invalid
            InternalServerException: If AI call fails
        """
        # Verify household membership
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        # Fetch ingredients
        ingredients = []
        for ing_id in ingredient_ids:
            ingredient = self.ingredient_repo.get(ing_id)
            if not ingredient:
                raise BadRequestException(f"Ingredient with ID {ing_id} not found")
            if ingredient.household_id != household_id:
                raise BadRequestException(
                    f"Ingredient {ing_id} doesn't belong to this household"
                )
            ingredients.append(ingredient)

        ingredient_list = ", ".join([ing.name for ing in ingredients])
        restrictions_str = (
            ", ".join(dietary_restrictions) if dietary_restrictions else "None"
        )

        # Build prompt
        prompt = f"""You are a culinary expert. Create a detailed recipe for "{meal_name}" using these ingredients:
{ingredient_list}

Requirements:
- Servings: {servings}
- Difficulty: {difficulty or "any"}
- Max prep time: {max_prep_time_minutes or "no limit"} minutes
- Cuisine type: {cuisine_type or "any"}
- Dietary restrictions: {restrictions_str}
- Format: Return ONLY valid JSON with no additional text

JSON Schema:
{{
  "name": "recipe name",
  "description": "brief description",
  "instructions": "detailed step-by-step instructions (use \\n for line breaks)",
  "prep_time_minutes": number,
  "cook_time_minutes": number,
  "difficulty": "easy|medium|hard",
  "cuisine_type": "italian|chinese|mexican|indian|japanese|american|french|thai|mediterranean|middle_eastern|korean|vietnamese|other",
  "tags": "comma,separated,tags",
  "calories_per_serving": number (estimate),
  "ingredients": [
    {{
      "ingredient_name": "name from provided list",
      "quantity": number,
      "unit": "gram|kilogram|cup|tablespoon|teaspoon|piece|...",
      "notes": "preparation notes",
      "is_optional": false
    }}
  ]
}}

Generate recipe:

note: Return ONLY valid JSON with no additional text or markdown
"""

        # Call Gemini API
        response_text = self._call_gemini_with_retry(prompt, temperature=0.8)

        # Parse JSON response
        response_data = self._extract_json_from_response(response_text)

        # Map ingredient names back to IDs
        recipe_ingredients = []
        for ing_data in response_data.get("ingredients", []):
            # Find matching ingredient from provided list
            ingredient_name = ing_data["ingredient_name"].lower()
            matched_ingredient = next(
                (ing for ing in ingredients if ing.name.lower() == ingredient_name),
                None,
            )

            if not matched_ingredient:
                # Try fuzzy match
                for ing in ingredients:
                    similarity = SequenceMatcher(
                        None, ingredient_name, ing.name.lower()
                    ).ratio()
                    if similarity >= 0.8:
                        matched_ingredient = ing
                        break

            if matched_ingredient:
                recipe_ingredients.append(
                    GeneratedRecipeIngredient(
                        ingredient_id=matched_ingredient.id,
                        ingredient_name=matched_ingredient.name,
                        quantity=float(ing_data["quantity"]),
                        unit=UnitOfMeasurement(ing_data["unit"]),
                        notes=ing_data.get("notes"),
                        is_optional=ing_data.get("is_optional", False),
                    )
                )

        return GenerateRecipeResponse(
            name=response_data.get("name", meal_name),
            description=response_data.get("description"),
            instructions=response_data["instructions"],
            prep_time_minutes=response_data.get("prep_time_minutes"),
            cook_time_minutes=response_data.get("cook_time_minutes"),
            servings=servings,
            difficulty=response_data.get("difficulty"),
            cuisine_type=response_data.get("cuisine_type"),
            tags=response_data.get("tags"),
            calories_per_serving=response_data.get("calories_per_serving"),
            ingredients=recipe_ingredients,
            household_id=household_id,
        )

    def generate_meal_plan_from_ingredients(
        self,
        household_id: int,
        user_id: int,
        days: int = 7,
        meals_per_day: int = 3,
        start_date: Optional[date] = None,
        dietary_preferences: Optional[List[str]] = None,
        use_available_only: bool = False,
        preferred_meal_types: Optional[List[str]] = None,
    ) -> GenerateMealPlanResponse:
        """
        Generate meal plan suggestions from available household ingredients.

        Args:
            household_id: Household ID
            user_id: User ID for authorization
            days: Number of days to plan
            meals_per_day: Meals per day
            start_date: Start date for meal plan
            dietary_preferences: Optional dietary constraints
            use_available_only: Restrict to available ingredients only
            preferred_meal_types: Preferred meal types

        Returns:
            GenerateMealPlanResponse with meal suggestions

        Raises:
            AuthorizationException: If user not member
            InternalServerException: If AI call fails
        """
        # Verify household membership
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        # Get available ingredients
        available_ingredients = self._get_available_ingredients(household_id)

        if not available_ingredients and use_available_only:
            raise BadRequestException(
                "No available ingredients found. Cannot generate meal plan with available-only constraint."
            )

        # Set start date
        if not start_date:
            start_date = date.today()

        end_date = start_date + timedelta(days=days - 1)

        # Build prompt
        ingredient_list = (
            ", ".join([ing["name"] for ing in available_ingredients])
            if available_ingredients
            else "None"
        )
        preferences_str = (
            ", ".join(dietary_preferences) if dietary_preferences else "None"
        )
        meal_types_str = (
            ", ".join(preferred_meal_types)
            if preferred_meal_types
            else "breakfast, lunch, dinner"
        )

        prompt = f"""You are a meal planning expert. Create a {days}-day meal plan with {meals_per_day} meals per day.

Available Ingredients:
{ingredient_list}

Requirements:
- Use available ingredients prioritized
- Dietary preferences: {preferences_str}
- Strict constraint: {"Only use available ingredients" if use_available_only else "Can suggest additional ingredients"}
- Preferred meal types: {meal_types_str}
- Format: Return ONLY valid JSON

JSON Schema:
{{
  "meal_plan": [
    {{
      "day": 1,
      "meal_type": "breakfast|lunch|dinner|snack",
      "meal_name": "name",
      "description": "brief description",
      "ingredients_used": ["ingredient names from available list"],
      "additional_ingredients_needed": ["ingredient names not in available list"],
      "estimated_prep_time": minutes,
      "estimated_calories": number
    }}
  ]
}}

Generate meal plan:

note: Return ONLY valid JSON with no additional text or markdown
"""

        # Call Gemini API
        response_text = self._call_gemini_with_retry(prompt, temperature=0.6)

        # Parse JSON response
        response_data = self._extract_json_from_response(response_text)

        if "meal_plan" not in response_data:
            raise BadRequestException(
                "AI returned invalid response format. Please try again."
            )

        # Process meal suggestions
        meal_suggestions: List[GeneratedMealSuggestion] = []
        meals_with_all_ingredients = 0
        meals_requiring_shopping = 0

        for meal_data in response_data["meal_plan"]:
            day = meal_data["day"]
            meal_date = start_date + timedelta(days=day - 1)

            # Match ingredients
            ingredients_used = meal_data.get("ingredients_used", [])
            additional_needed = meal_data.get("additional_ingredients_needed", [])

            matched_ids = []
            for ing_name in ingredients_used:
                matched_id, _ = self._match_ingredient_to_household(
                    ing_name, household_id
                )
                if matched_id:
                    matched_ids.append(matched_id)

            requires_shopping = len(additional_needed) > 0

            if requires_shopping:
                meals_requiring_shopping += 1
            else:
                meals_with_all_ingredients += 1

            meal_suggestions.append(
                GeneratedMealSuggestion(
                    day=day,
                    meal_date=meal_date,
                    meal_type=meal_data["meal_type"],
                    meal_name=meal_data["meal_name"],
                    description=meal_data.get("description"),
                    ingredients_used=ingredients_used,
                    additional_ingredients_needed=additional_needed,
                    estimated_prep_time_minutes=meal_data.get("estimated_prep_time"),
                    estimated_calories=meal_data.get("estimated_calories"),
                    matched_ingredient_ids=matched_ids,
                    requires_shopping=requires_shopping,
                )
            )

        return GenerateMealPlanResponse(
            household_id=household_id,
            start_date=start_date,
            end_date=end_date,
            total_days=days,
            meal_suggestions=meal_suggestions,
            total_meals=len(meal_suggestions),
            available_ingredients_count=len(available_ingredients),
            meals_with_all_ingredients=meals_with_all_ingredients,
            meals_requiring_shopping=meals_requiring_shopping,
        )

    def save_generated_recipe_to_db(
        self, generated_recipe: GenerateRecipeResponse, user_id: int
    ) -> Any:
        """
        Save an AI-generated recipe to the database after user approval.

        Args:
            generated_recipe: Generated recipe response
            user_id: User ID creating the recipe

        Returns:
            Created Recipe object

        Raises:
            AuthorizationException: If user not member
        """
        # Convert to RecipeCreate schema
        recipe_create = RecipeCreate(
            household_id=generated_recipe.household_id,
            name=generated_recipe.name,
            description=generated_recipe.description,
            instructions=generated_recipe.instructions,
            prep_time_minutes=generated_recipe.prep_time_minutes,
            cook_time_minutes=generated_recipe.cook_time_minutes,
            servings=generated_recipe.servings,
            difficulty=generated_recipe.difficulty,
            cuisine_type=generated_recipe.cuisine_type,
            tags=generated_recipe.tags,
            calories_per_serving=generated_recipe.calories_per_serving,
            source_url="AI Generated",
            ingredients=[
                RecipeIngredientCreate(
                    ingredient_id=ing.ingredient_id,
                    quantity=ing.quantity,
                    unit=ing.unit,
                    notes=ing.notes,
                    is_optional=ing.is_optional,
                )
                for ing in generated_recipe.ingredients
            ],
        )

        return self.recipe_service.create_recipe(user_id, recipe_create)

    # ===== Helper Methods =====

    def _call_gemini_with_retry(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Call Gemini API with retry logic.

        Args:
            prompt: Prompt to send
            temperature: Temperature parameter

        Returns:
            Response text

        Raises:
            InternalServerException: On failure
        """
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=settings.GEMINI_MAX_TOKENS,
                ),
            )

            if not response or not response.text:
                raise InternalServerException("AI service returned empty response")

            return response.text

        except Exception as e:
            error_str = str(e).lower()
            print(f"Gemini API error: {error_str}")
            if "api" in error_str and "key" in error_str:
                raise InternalServerException(
                    "AI service configuration error. Please contact administrator."
                )
            elif "rate" in error_str or "limit" in error_str:
                raise InternalServerException(
                    "AI service is busy. Please try again in a few moments."
                )
            elif "timeout" in error_str:
                raise BadRequestException(
                    "AI request timed out. Please try with a simpler request."
                )
            else:
                raise InternalServerException(f"AI service error: {str(e)}")

    def _extract_json_from_response(self, response_text: str) -> dict:
        """
        Extract JSON from Gemini response that may contain additional text.

        Tries:
        1. Direct JSON parse
        2. Extract JSON block from markdown code fence
        3. Find JSON object with regex

        Args:
            response_text: Response text from AI

        Returns:
            Parsed JSON dict

        Raises:
            BadRequestException: If no valid JSON found
        """
        # Try direct parse
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try extracting from code fence
        code_fence_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(code_fence_pattern, response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding JSON object
        json_pattern = r"\{.*\}"
        match = re.search(json_pattern, response_text, re.DOTALL)
        print(f"Extracted JSON candidate: {match.group(0) if match else 'None'}")
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise BadRequestException(
            "AI returned invalid response format. Please try again."
        )

    def _match_ingredient_to_household(
        self,
        ingredient_name: str,
        household_id: int,
        category: Optional[IngredientCategory] = None,
    ) -> Tuple[Optional[int], float]:
        """
        Match AI-generated ingredient name to existing household ingredient.

        Args:
            ingredient_name: Ingredient name from AI
            household_id: Household ID
            category: Optional category filter

        Returns:
            Tuple of (ingredient_id, confidence_score) or (None, 0.0) if no match
        """
        # Exact match (case-insensitive)
        household_ingredients = self.ingredient_repo.get_by_household(household_id)

        for ing in household_ingredients:
            if ing.name.lower() == ingredient_name.lower():
                return (ing.id, 1.0)

        # Fuzzy match
        best_match = None
        best_score = 0.0
        threshold = 0.85  # 85% similarity required

        for ing in household_ingredients:
            # Filter by category if provided
            if category and ing.category != category:
                continue

            score = SequenceMatcher(
                None, ingredient_name.lower(), ing.name.lower()
            ).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = ing.id

        return (best_match, best_score)

    def _get_available_ingredients(self, household_id: int) -> List[Dict[str, Any]]:
        """
        Get ingredients available in household (purchased from grocery lists).

        Args:
            household_id: Household ID

        Returns:
            List of ingredient dicts with name, quantity, unit
        """
        # Get recent grocery lists
        grocery_lists = self.grocery_list_repo.get_by_household(
            household_id, skip=0, limit=10
        )

        available = []
        seen_ingredient_ids = set()

        for grocery_list in grocery_lists:
            grocery_list_with_items = self.grocery_list_repo.get_with_items(
                grocery_list.id
            )
            for item in grocery_list_with_items.items:
                if (
                    item.is_purchased
                    and item.ingredient_id
                    and item.ingredient_id not in seen_ingredient_ids
                ):
                    ingredient = self.ingredient_repo.get(item.ingredient_id)
                    if ingredient:
                        available.append(
                            {
                                "name": ingredient.name,
                                "ingredient_id": ingredient.id,
                                "quantity": item.quantity,
                                "unit": item.unit.value,
                                "category": ingredient.category.value
                                if ingredient.category
                                else "other",
                            }
                        )
                        seen_ingredient_ids.add(item.ingredient_id)

        return available
