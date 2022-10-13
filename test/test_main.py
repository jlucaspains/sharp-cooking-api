from fastapi.testclient import TestClient
from main import app
from util import parse_recipe_ingredient, parse_recipe_instruction
from pint import UnitRegistry

client = TestClient(app)

test_url = "/recipe/parse"

def test_docs():
    response = client.get("/docs")
    assert response.status_code == 200

# parse recipe post method
def test_recipe_parse():
    response = client.post(test_url, json={
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
    
    assert parsed_response["image"].startswith("http")

def test_recipe_parse_download_image():
    response = client.post(test_url, json={
            "url": "https://www.foodnetwork.com/recipes/rachael-ray/pork-chops-with-golden-apple-sauce-recipe-1915826",
            "downloadImage": True
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
    
    assert parsed_response["image"].startswith("data:")

def test_recipe_parse_exception():
    response = client.post(test_url, json={
            "url": "https://www.foodnk.com/recipes/rachael-ray/pork-chops-with-golden-apple-sauce-recipe-1915826",
        })
    assert response.status_code == 400
    parsed_response = response.text
    assert parsed_response == r'{"detail":"Could not find a recipe in the web page"}'
