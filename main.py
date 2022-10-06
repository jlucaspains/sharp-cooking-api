import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from recipe_scrapers import scrape_me
import re
from fractions import Fraction
from pint import UnitRegistry
import logging
import time
from logging.handlers import RotatingFileHandler

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
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('local.log', maxBytes=5000000,
                                  backupCount=5)
logger.addHandler(handler)


@app.post("/recipe/parse", response_model=Recipe)
def parse_recipe(parse_request: ParseRequest):
    """Parses a recipe from a website

    Raises:
        HTTPException: when the recipe cannot be parsed

    Returns:
        dictionary: title, totalTime, yields, ingredients list, instructions list, image, host
    """
    correlation_id = uuid.uuid4()
    try:
        start = time.perf_counter()
        logger.info(f"processing request id {correlation_id} for url: {parse_request.url}")
        scraper = scrape_me(parse_request.url, wild_mode=True)
        
        lang = scraper.language() or "en"
        
        ingredients = map(lambda x: parse_recipe_ingredient(x, lang), scraper.ingredients())
        instructions = map(lambda x: parse_recipe_instruction(x, lang), scraper.instructions_list())
        
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
    except Exception as e:
        logger.error(f"Failed to process request id {correlation_id}. Error: {e}")
        raise HTTPException(status_code=400, detail="Could not find a recipe in the web page")
    finally:
        end = time.perf_counter()
        logger.info(f"Finished processing request id {correlation_id}. Time taken: {end - start:0.4f}s")


def parse_recipe_ingredient(text: str, lang: str):
    """Parses a single recipe ingredient

    Args:
        text (str): the ingredient e.g. 10 grams flour
        lang (str): language the ingredient is in

    Returns:
        dictionary: raw text, quantity parsed, unit identified
    """    
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

def parse_recipe_instruction(text: str, lang: str):
    """Parses a single recipe instruction

    Args:
        text (str): knead dough for 10 minutes
        lang (str): language the instruction is in

    Returns:
        dictionary: raw instruction, minutes identified for the instruction
    """    
    qty_re = re.findall(r"(?P<Minutes>\d{1,5}\.?\d{0,5})\s*(minutes|minute|min)\b|(?P<Hours>\d{1,5}\.?\d{0,5})\s*(hours|hour)\b|(?P<Days>\d{1,5}\.?\d{0,5})\s*(days|day)\b",
                    text)
    minutes = 0
    
    for match in qty_re:
        minutes += int(match[0] or "0")
        minutes += int(match[2] or "0") * 60
        minutes += int(match[4] or "0") * 24 * 60
    
    return { "raw": text, "minutes": minutes }
