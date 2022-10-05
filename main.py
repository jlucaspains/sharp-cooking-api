from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from recipe_scrapers import scrape_me
import re
from fractions import Fraction
import time
from pint import UnitRegistry

app = FastAPI()

class RecipeIngredient(BaseModel):
    raw: str
    quantity: float
    unit: str

class RecipeInstruction(BaseModel):
    raw: str
    minutes: float

class Recipe(BaseModel):
    title: str = None
    totalTime: int = None
    yields: str = None
    ingredients: list[RecipeIngredient] = None
    instructions: list[RecipeInstruction] = None
    image: str = None
    host: str = None

class ParseRequest(BaseModel):
    url: str

ureg = UnitRegistry()

@app.post("/recipe/parse", response_model=Recipe)
def parse_recipe(parse_request: ParseRequest):
    try:
        start = time.perf_counter()
        scraper = scrape_me(parse_request.url, wild_mode=True)
        
        lang = scraper.language() or "en"
        
        ingredients = map(lambda x: parse_recipe_ingredient(x, lang), scraper.ingredients())
        instructions = map(lambda x: parse_recipe_instructions(x, lang), scraper.instructions_list())
        
        result = {
            "title": scraper.title(),
            "totalTime": scraper.total_time(),
            "yields": scraper.yields(),
            "ingredients": list(ingredients),
            "instructions": list(instructions),
            "image": scraper.image(),
            "host": scraper.host()
        }

        return result
    except:
        raise HTTPException(status_code=400, detail="Could not find a recipe in the web page")
    finally:
        end = time.perf_counter()
        print(f"total time: {end - start:0.4f}")
        
def parse_recipe_ingredient(text: str, lang: str):
    qty_re = re.search(r"^(?P<Value>\d{1,5}\s\d{1,5}\/\d{1,5}|\d{1,5}\/\d{1,5}|\d{1,5}\.?\d{0,5})\s?(?P<Unit>\w*\b)",
                    text)

    if not qty_re:
        return { "raw": text, "quantity": 0, "unit": "" }

    value = qty_re.group("Value")
    unit = qty_re.group("Unit")
    
    unit_value = ""
    if unit and unit in ureg:
        unit_value = ureg.get_name(unit)

    if value:
        parts = value.split(" ")
        
        if parts.__len__() == 2:
            whole = int(parts[0])
            fraction = Fraction(parts[1])
            return { "raw": text, "quantity": whole + float(fraction).__round__(2), "unit": unit_value }
        
        if parts[0].count("/") >= 0:
            fraction = Fraction(parts[0])
            return { "raw": text, "quantity": float(fraction).__round__(2), "unit": unit_value }
            
        regular = parts[0]
        return { "raw": text, "quantity": float(regular), "unit": unit_value }
    
    return { "raw": text, "quantity": float(regular), "unit": unit_value }

def parse_recipe_instructions(text: str, lang: str):
    qty_re = re.findall(r"(?P<Minutes>\d{1,5}\.?\d{0,5})\s*(minutes|minute|min)\b|(?P<Hours>\d{1,5}\.?\d{0,5})\s*(hours|hour)\b|(?P<Days>\d{1,5}\.?\d{0,5})\s*(days|day)\b",
                    text)
    minutes = 0
    
    for match in qty_re:
        minutes += int(match[0] or "0")
        minutes += int(match[2] or "0") * 60
        minutes += int(match[4] or "0") * 24 * 60
    
    return { "raw": text, "minutes": minutes }
