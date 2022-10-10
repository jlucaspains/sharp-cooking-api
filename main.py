from typing import Union
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from logging.handlers import RotatingFileHandler
from pydantic import BaseModel
from recipe_scrapers import scrape_me
from fractions import Fraction
from pint import UnitRegistry
import re
import uuid
import time
import os
import logging
import requests
import base64

app = FastAPI()

environment = os.getenv("APP_ENVIRONMENT", "DEV")

origins = ["https://app.sharpcooking.net"]

if environment != "PROD":
    origins += [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RecipeIngredient(BaseModel):
    raw: str
    quantity: float
    unit: str

class RecipeInstruction(BaseModel):
    raw: str
    minutes: float

class Recipe(BaseModel):
    title: Union[str, None] = None
    totalTime: Union[int, None] = None
    yields: Union[str, None] = None
    ingredients: list[RecipeIngredient] = []
    instructions: list[RecipeInstruction] = []
    image: Union[str, None] = None
    host: Union[str, None] = None

class ParseRequest(BaseModel):
    url: str
    downloadImage: bool = False

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
        
        if parse_request.downloadImage:
            image_uri = parse_recipe_image(result["image"])
            result["image"] = image_uri

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
    qty_re = re.search(r"^(?P<Value>\d{1,5}\s\d{1,5}\/\d{1,5}|\d{1,5}\/\d{1,5}|\d{1,5}\.?\d{0,5})\d*\s?(?P<Unit>\w*\b)",
                    text)

    if not qty_re:
        return { "raw": text, "quantity": 0, "unit": "" }

    value = qty_re.group("Value")
    unit = qty_re.group("Unit")
    
    unit_value = ""
    if unit and unit in ureg:
        unit_value = ureg.get_name(unit)

    parts = value.split(" ")
    
    if parts.__len__() == 2:
        whole = int(parts[0])
        fraction = Fraction(parts[1])
        return { "raw": text, "quantity": whole + float(fraction).__round__(2), "unit": unit_value }
    
    if parts[0].count("/") == 1:
        fraction = Fraction(parts[0])
        return { "raw": text, "quantity": float(fraction).__round__(2), "unit": unit_value }
        
    regular = parts[0]
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

def parse_recipe_image(image_url: str):
    response = requests.get(image_url)
    return ("data:" +  response.headers['Content-Type'] + ";" + "base64," + base64.b64encode(response.content).decode("utf-8"))