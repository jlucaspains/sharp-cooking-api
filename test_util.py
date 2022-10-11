import base64
import io
from zipfile import ZipFile
from fastapi.testclient import TestClient
from main import app
from util import parse_recipe_ingredient, parse_recipe_ingredients, parse_recipe_instruction
from util import parse_recipe_instructions, replace_unicode_fractions, parse_image_from_backup
from pint import UnitRegistry

client = TestClient(app)

test_url = "/recipe/parse"

def test_docs():
    response = client.get("/docs")
    assert response.status_code == 200

# ingredient parser
def test_ingredient_parse_simple():
    parsed = parse_recipe_ingredient("10 grams flour", "en", UnitRegistry())
    assert parsed["raw"] == "10 grams flour"
    assert parsed["quantity"] == 10
    assert parsed["unit"] == "gram"

def test_ingredient_parse_fraction():
    parsed = parse_recipe_ingredient("1/2 grams flour", "en", UnitRegistry())
    assert parsed["raw"] == "1/2 grams flour"
    assert parsed["quantity"] == 0.5
    assert parsed["unit"] == "gram"

def test_ingredient_parse_composite_fraction():
    parsed = parse_recipe_ingredient("2 1/2 grams flour", "en", UnitRegistry())
    assert parsed["raw"] == "2 1/2 grams flour"
    assert parsed["quantity"] == 2.5
    assert parsed["unit"] == "gram"

def test_ingredient_bad_qty():
    parsed = parse_recipe_ingredient("flour", "en", UnitRegistry())
    assert parsed["raw"] == "flour"
    assert parsed["quantity"] == 0
    assert parsed["unit"] == ""

def test_ingredient_bad_unit():
    parsed = parse_recipe_ingredient("10 ggg flour", "en", UnitRegistry())
    assert parsed["raw"] == "10 ggg flour"
    assert parsed["quantity"] == 10
    assert parsed["unit"] == ""

def test_ingredient_no_unit():
    parsed = parse_recipe_ingredient("10 flour", "en", UnitRegistry())
    assert parsed["raw"] == "10 flour"
    assert parsed["quantity"] == 10
    assert parsed["unit"] == ""

def test_ingredient_nothing():
    parsed = parse_recipe_ingredient("", "en", UnitRegistry())
    assert parsed["raw"] == ""
    assert parsed["quantity"] == 0
    assert parsed["unit"] == ""

def test_ingredients_parse():
    parsed = parse_recipe_ingredients("100 grams flour\n1 cup water", UnitRegistry())
    assert parsed.__len__() == 2
    assert parsed[0]["raw"] == "100 grams flour"
    assert parsed[0]["quantity"] == 100
    assert parsed[0]["unit"] == "gram"
    assert parsed[1]["raw"] == "1 cup water"
    assert parsed[1]["quantity"] == 1
    assert parsed[1]["unit"] == "cup"

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

def test_instructions_parse():
    parsed = parse_recipe_instructions("Do something and wait 15 minutes\nAnd something else and wait 1 hour")
    assert parsed.__len__() == 2
    assert parsed[0]["raw"] == "Do something and wait 15 minutes"
    assert parsed[0]["minutes"] == 15
    assert parsed[1]["raw"] == "And something else and wait 1 hour"
    assert parsed[1]["minutes"] == 60

def test_replace_unicode_fractions_no_unicode():
    result = replace_unicode_fractions("1/2 cups of water")
    assert result == "1/2 cups of water"

def test_replace_unicode_fractions_number():
    result = replace_unicode_fractions("1 cup of water")
    assert result == "1 cup of water"

def test_replace_unicode_fractions_unicode():
    result = replace_unicode_fractions("½ cups of water")
    assert result == "1/2 cups of water"

# def test_parse_image_from_backup():
#     image_bytes = base64.b64encode("R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==".encode("utf-8"))
#     with ZipFile("tmp/test.zip", 'r') as zip:
#         zip.write()
#         result = parse_image_from_backup("image.png", zip)
#         assert result == "data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="