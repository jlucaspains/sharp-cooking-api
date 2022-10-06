from fastapi.testclient import TestClient
from main import app, parse_recipe_ingredient, parse_recipe_instruction

client = TestClient(app)

def test_docs():
    response = client.get("/docs")
    assert response.status_code == 200

# parse recipe post method
def test_recipe_parse():
    response = client.post("/recipe/parse", json={
            "url": "https://www.foodnetwork.com/recipes/rachael-ray/pork-chops-with-golden-apple-sauce-recipe-1915826",
        })
    assert response.status_code == 200
    parsed_response = response.json()
    assert parsed_response["title"] == "Pork Chops with Golden Apple Sauce"
    assert len(parsed_response["ingredients"]) == 12
    assert parsed_response["ingredients"][1]["raw"] == "2 teaspoons lemon juice"
    assert parsed_response["ingredients"][1]["quantity"] == 2
    assert parsed_response["ingredients"][1]["unit"] == "teaspoon"
    
    assert len(parsed_response["instructions"]) == 2
    assert parsed_response["instructions"][0]["minutes"] == 12

# ingredient parser
def test_ingredient_parse_simple():
    parsed = parse_recipe_ingredient("10 grams flour", "en")
    assert parsed["raw"] == "10 grams flour"
    assert parsed["quantity"] == 10
    assert parsed["unit"] == "gram"

def test_ingredient_parse_fraction():
    parsed = parse_recipe_ingredient("1/2 grams flour", "en")
    assert parsed["raw"] == "1/2 grams flour"
    assert parsed["quantity"] == 0.5
    assert parsed["unit"] == "gram"

def test_ingredient_parse_composite_fraction():
    parsed = parse_recipe_ingredient("2 1/2 grams flour", "en")
    assert parsed["raw"] == "2 1/2 grams flour"
    assert parsed["quantity"] == 2.5
    assert parsed["unit"] == "gram"

def test_ingredient_bad_qty():
    parsed = parse_recipe_ingredient("flour", "en")
    assert parsed["raw"] == "flour"
    assert parsed["quantity"] == 0
    assert parsed["unit"] == ""

def test_ingredient_bad_unit():
    parsed = parse_recipe_ingredient("10 ggg flour", "en")
    assert parsed["raw"] == "10 ggg flour"
    assert parsed["quantity"] == 10
    assert parsed["unit"] == ""

def test_ingredient_no_unit():
    parsed = parse_recipe_ingredient("10 flour", "en")
    assert parsed["raw"] == "10 flour"
    assert parsed["quantity"] == 10
    assert parsed["unit"] == ""

def test_ingredient_nothing():
    parsed = parse_recipe_ingredient("", "en")
    assert parsed["raw"] == ""
    assert parsed["quantity"] == 0
    assert parsed["unit"] == ""

# instruction parser
def test_instruction_parse_minutes():
    parsed = parse_recipe_instruction("Do something and wait 15 minutes", "en")
    assert parsed["raw"] == "Do something and wait 15 minutes"
    assert parsed["minutes"] == 15

def test_instruction_parse_hours():
    parsed = parse_recipe_instruction("Do something and wait 1 hour", "en")
    assert parsed["raw"] == "Do something and wait 1 hour"
    assert parsed["minutes"] == 60

def test_instruction_parse_days():
    parsed = parse_recipe_instruction("Do something and wait 2 days", "en")
    assert parsed["raw"] == "Do something and wait 2 days"
    assert parsed["minutes"] == 2880

def test_instruction_parse_composite():
    parsed = parse_recipe_instruction("Do something and wait 1 minute and 1 hour and 1 day", "en")
    assert parsed["raw"] == "Do something and wait 1 minute and 1 hour and 1 day"
    assert parsed["minutes"] == 1501

def test_instruction_parse_no_time():
    parsed = parse_recipe_instruction("Do something", "en")
    assert parsed["raw"] == "Do something"
    assert parsed["minutes"] == 0

def test_instruction_parse_nothing():
    parsed = parse_recipe_instruction("", "en")
    assert parsed["raw"] == ""
    assert parsed["minutes"] == 0