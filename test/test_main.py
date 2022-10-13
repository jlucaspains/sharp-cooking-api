from fastapi.testclient import TestClient
from src.main import app
from src.util import parse_recipe_ingredient, parse_recipe_instruction
from pint import UnitRegistry

client = TestClient(app)

parse_test_url = "/recipe/parse"
backup_test_url = "/recipe/backup/parse"
image_test_url = "/image/process"

def test_docs():
    response = client.get("/docs")
    assert response.status_code == 200

# parse recipe post method
def test_recipe_parse():
    response = client.post(parse_test_url, json={
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
    response = client.post(parse_test_url, json={
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
    response = client.post(parse_test_url, json={
            "url": "https://www.foodnk.com/recipes/rachael-ray/pork-chops-with-golden-apple-sauce-recipe-1915826",
        })
    assert response.status_code == 400
    parsed_response = response.text
    assert parsed_response == r'{"detail":"Could not find a recipe in the web page"}'

def test_parse_backup():
    response = client.post(backup_test_url, files={"file": ("test_backup.zip", open("test/test_backup.zip", "rb"), "application/x-zip-compressed")})
    assert response.status_code == 200
    parsed_response = response.json()
    
    assert len(parsed_response) == 1
    assert parsed_response[0]["title"] == "Carrot cake"
    assert parsed_response[0]["image"].startswith("data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD")
    
    assert len(parsed_response[0]["ingredients"]) == 6
    assert parsed_response[0]["ingredients"][0]["raw"] == "3 eggs"
    assert parsed_response[0]["ingredients"][0]["quantity"] == 3
    assert parsed_response[0]["ingredients"][0]["unit"] == ""
    assert parsed_response[0]["ingredients"][1]["raw"] == "1 cup sugar"
    assert parsed_response[0]["ingredients"][1]["quantity"] == 1
    assert parsed_response[0]["ingredients"][1]["unit"] == "cup"
    
    assert len(parsed_response[0]["instructions"]) == 6
    assert parsed_response[0]["instructions"][0]["raw"] == "Blend carrots, vegetable oil, sugar, and eggs together for about 5 minutes till smooth"
    assert parsed_response[0]["instructions"][0]["minutes"] == 5
    assert parsed_response[0]["instructions"][1]["raw"] == "Sift flour on a separate container"
    assert parsed_response[0]["instructions"][1]["minutes"] == 0

def test_parse_backup_bad_mime():
    response = client.post(backup_test_url, files={"file": ("test_backup.zip", open("test/test_backup.zip", "rb"), "application/zip")})
    assert response.status_code == 400
    parsed_response = response.json()
    
    assert parsed_response["detail"] == "The backup file does not seem to be well formatted or generated by Sharp Cooking app"

def test_process_image():
    response = client.post(image_test_url, files={"file": ("test_image.jpeg", open("test/test_image.jpeg", "rb"), "image/jpeg")})
    assert response.status_code == 200
    parsed_response = response.json()
    
    assert parsed_response["name"] == "test_image.jpeg"
    assert parsed_response["image"].startswith("data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD")

def test_process_image_bad_mime():
    response = client.post(image_test_url, files={"file": ("test_image.jpeg", open("test/test_image.jpeg", "rb"), "application/jpeg")})
    assert response.status_code == 400
    parsed_response = response.json()
    
    assert parsed_response["detail"] == "The image file is invalid"