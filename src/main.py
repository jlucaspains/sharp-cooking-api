import io
import json
import os
import logging
from zipfile import ZipFile
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from logging.handlers import RotatingFileHandler
from recipe_scrapers import scrape_me
from pint import UnitRegistry
from uuid import uuid4
from time import perf_counter
from src.util import parse_recipe_ingredient, parse_recipe_ingredients, parse_recipe_instruction
from src.util import parse_recipe_instructions, parse_recipe_image, parse_image
from src.models import ImageResult, ParseRequest, Recipe

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

ureg = UnitRegistry()
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('local.log', maxBytes=5000000, backupCount=5)
logger.addHandler(handler)

@app.post("/recipe/parse", response_model=Recipe)
def parse_recipe(parse_request: ParseRequest):
    """Parses a recipe from a website

    Raises:
        HTTPException: when the recipe cannot be parsed

    Returns:
        dictionary: title, totalTime, yields, ingredients list, instructions list, image, host
    """
    correlation_id = uuid4()
    try:
        start = perf_counter()
        logger.info(f"processing parse request id {correlation_id} for url: {parse_request.url}")
        scraper = scrape_me(parse_request.url, wild_mode=True)
        
        lang = scraper.language() or "en"
        
        ingredients = map(lambda x: parse_recipe_ingredient(x, lang, ureg), scraper.ingredients())
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
        logger.error(f"Failed to process parse request id {correlation_id}. Error: {e}")
        raise HTTPException(status_code=400, detail="Could not find a recipe in the web page")
    finally:
        end = perf_counter()
        logger.info(f"Finished processing parse request id {correlation_id}. Time taken: {end - start:0.4f}s")

@app.post("/recipe/backup/parse", response_model=list[Recipe])
def parse_backup(file: UploadFile):
    """Parses a Sharp Cooking backup file and return the recipes contained within in new json format

    Args:
        file (UploadFile): Backup file in zip

    Raises:
        HTTPException: if file uploaded is not a zip

    Returns:
        _type_: _description_
    """    

    correlation_id = uuid4()
    try:
        start = perf_counter()
        logger.info(f"processing backup request id {correlation_id}")
        
        if file.content_type != "application/x-zip-compressed" and file.content_type != "application/zip":
            raise HTTPException(status_code=400, detail="Only zip files are acceptted")
    
        with ZipFile(io.BytesIO(file.file.read()), 'r') as zip:
            json_file = zip.read("SharpBackup_Recipe.json")
            json_content = json.load(io.BytesIO(json_file))
            
            result = []
            for recipe in json_content:
                image_file = zip.read(recipe["MainImagePath"])
                result.append({
                    "title": recipe["Title"],
                    "totalTime": 0,
                    "yields": "",
                    "ingredients": parse_recipe_ingredients(recipe["Ingredients"], ureg),
                    "instructions": parse_recipe_instructions(recipe["Instructions"]),
                    "image": parse_image(recipe["MainImagePath"], image_file, zip),
                    "host": "",
                    "notes": recipe["Notes"]
                })

        return result
    except Exception as e:
        logger.error(f"Failed to process backup request id {correlation_id}. Error: {e}")
        raise HTTPException(status_code=400, detail="The backup file does not seem to be well formatted or generated by Sharp Cooking app")
    finally:
        end = perf_counter()
        logger.info(f"Finished processing backup request id {correlation_id}. Time taken: {end - start:0.4f}s")

@app.post("/image/process", response_model=ImageResult)
def parse_backup(file: UploadFile):
    """Processes an image and return a URI base64

    Args:
        file (UploadFile): image file

    Raises:
        HTTPException: if file uploaded is not an image

    Returns:
        str: image resized and formatted in URI base44
    """    

    correlation_id = uuid4()
    try:
        start = perf_counter()
        logger.info(f"processing image request id {correlation_id}")
        
        if not file.content_type.startswith("image"):
            raise HTTPException(status_code=400, detail="Only image files are acceptted")

        return {
            "name": file.filename,
            "image": parse_image(file.filename, file.file.read())
        }
    except Exception as e:
        logger.error(f"Failed to process image request id {correlation_id}. Error: {e}")
        raise HTTPException(status_code=400, detail="The image file is invalid")
    finally:
        end = perf_counter()
        logger.info(f"Finished processing image request id {correlation_id}. Time taken: {end - start:0.4f}s")
