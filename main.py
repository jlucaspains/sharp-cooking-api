from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from recipe_scrapers import scrape_me
import re
from fractions import Fraction

app = FastAPI()

class Recipe(BaseModel):
    title: str = None
    totalTime: int = None
    yields: str = None
    ingredients: list[str] = None
    instructions: list[str] = None
    image: str = None
    host: str = None

class ParseRequest(BaseModel):
    url: str

@app.post("/recipe/parse")#, response_model=Recipe)
def parse_recipe(parse_request: ParseRequest):
    # try:
        scraper = scrape_me(parse_request.url, wild_mode=True)
        
        lang = scraper.language() or "en"
        ingredients = map(lambda x: parse_recipe_ingredient(x, lang), scraper.ingredients())
        instructions = map(lambda x: parse_recipe_instructions(x, lang), scraper.instructions_list())

        return {
            "title": scraper.title(),
            "totalTime": scraper.total_time(),
            "yields": scraper.yields(),
            "ingredients": list(ingredients),
            "instructions": list(instructions),
            "image": scraper.image(),
            "host": scraper.host()
        }
    # except:
        # raise HTTPException(status_code=400, detail="Could not find a recipe in the web page")

def parse_recipe_ingredient(text: str, lang: str):
    qty_re = re.search(r"^(?P<CompositeFraction>\d{1,5} \d{1,5}\/\d{1,5})|(?P<Fraction>\d{1,5}\/\d{1,5})|^(?P<Regular>\d{1,5}\.?\d{0,5})",
                       text)
    
    if not qty_re:
        return { "raw": text, "quantity": 0 }
        
    compositeFraction = qty_re.group("CompositeFraction")
    
    if compositeFraction:
        parts = compositeFraction.split(" ")
        whole = int(parts[0])
        fraction = Fraction(parts[1])
        return { "raw": text, "quantity": whole + float(fraction) }
    
    fraction = qty_re.group("Fraction")

    if fraction:
        fraction = Fraction(fraction)
        return { "raw": text, "quantity": float(fraction) }

    regular = qty_re.group("Regular")
    return { "raw": text, "quantity": float(regular) }


def parse_recipe_instructions(text: str, lang: str):
    qty_re = re.findall(r"(?P<Minutes>\d{1,5}\.?\d{0,5})\s*(minutes|minute|min)\b|(?P<Hours>\d{1,5}\.?\d{0,5})\s*(hours|hour)\b|(?P<Days>\d{1,5}\.?\d{0,5})\s*(days|day)\b",
                       text)
    minutes = 0
    
    for match in qty_re:
        minutes += int(match[0] or "0")
        minutes += int(match[2] or "0") * 60
        minutes += int(match[4] or "0") * 24 * 60
    
    return { "raw": text, "minutes": minutes }