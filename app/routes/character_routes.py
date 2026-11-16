import os
import json
from flask import Blueprint, request, abort, make_response
from ..db import db
from ..models.character import Character
from ..models.greeting import Greeting
from sqlalchemy import func, union, except_

from google import genai
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# from openai import OpenAI
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bp = Blueprint("characters", __name__, url_prefix="/characters")

@bp.post("")
def create_character():

    request_body = request.get_json()
    try:
        new_character = Character.from_dict(request_body)
        db.session.add(new_character)
        db.session.commit()

        return new_character.to_dict(), 201

    except KeyError as e:
        abort(make_response({"message": f"missing required value: {e}"}, 400))


@bp.get("")
def get_characters():
    character_query = db.select(Character)

    characters = db.session.scalars(character_query)
    response = [character.to_dict() for character in characters]

    return response


@bp.get("/<char_id>")
def get_character(char_id):
    character = validate_model(Character, char_id)
    return character.to_dict()

@bp.delete("/<char_id>/greetings")
def delete_greetings(char_id):
    character = validate_model(Character, char_id)
    if not character.greetings:
        return {"message" : "greetings not found"},404
    for greeting in character.greetings:
        db.session.delete(greeting)
    db.session.commit()
    return {"message": "Successfully deleted greetings"}, 200


@bp.get("/<char_id>/greetings")
def get_greetings(char_id):
    character = validate_model(Character, char_id)
    response = [greeting.to_dict()for greeting in character.greetings]

    return response



@bp.post("/<char_id>/generate")
def add_greetings(char_id):
    character_obj = validate_model(Character, char_id)
    if character_obj.greetings:
        return {"message" :" greetings already generated"}
    greetings = generate_greetings(character_obj)
    new_greetings = []
    for greeting in greetings:
        new_greeting = Greeting(
            greeting_text = greeting,
            character = character_obj
        )
        new_greetings.append(new_greeting)
    db.session.add_all(new_greetings)
    db.session.commit()
    return {"message" : "successfully created"}

###### OPENAIAPI ######
# def generate_greetings(character):
#     input_message = f"""
#     Generate exactly 10 greetings for an NPC named {character.name}.
#     They are {character.age} years old.
#     Their occupation is {character.occupation}.
#     Their personality is {character.personality}.

#     Return ONLY valid JSON in this format:
#     {{
#         "greetings": [
#             "Hey there, traveler!",
#             "Welcome to my shop!"
#         ]
#     }}
#     """
#     response = client.responses.create(
#         model="gpt-4o-mini",
#         input=input_message,
#         text={"format": {"type": "json_object"}}
#     )

#     print("OpenAI response:", response.output_text)

#     result = json.loads(response.output_text)

#     return result["greetings"]

###### GEMINIAPI ######
def generate_greetings(character):
    input_message = f"""
    Generate exactly 10 greetings for an NPC named {character.name}.
    They are {character.age} years old.
    Their occupation is {character.occupation}.
    Their personality is {character.personality}. 
    Please generate a Python style list of 10 stock phrases they might use when the main character talks to them.
    Please return just the list without a variable name and square brackets
    """
    response = client.models.generate_content(
        model="gemini-3.8-flash", contents=input_message
    )
    print(response)
    lines = response.text.splitlines()
    return [line.strip("\"'")for line in lines]

    


def validate_model(cls, id):
    try:
        id = int(id)
    except:
        response = {"message": f"{cls.__name__} {id} invalid"}
        abort(make_response(response, 400))

    query = db.select(cls).where(cls.id == id)
    model = db.session.scalar(query)
    if model:
        return model

    response = {"message": f"{cls.__name__} {id} not found"}
    abort(make_response(response, 404))
