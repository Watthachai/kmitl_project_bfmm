import re
from flask import Flask, request, jsonify
import speech_recognition as sr
import os
import subprocess
from pydub import AudioSegment
from flask_cors import cross_origin
import sklearn_crfsuite
from pythainlp.tokenize import word_tokenize
from pythainlp.tag import pos_tag
from rapidfuzz import process
from app.models.order import Order  # Assuming these models exist
from app import db                  # Assuming this is your database instance
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from app.models.menu import Menu    # Assuming this model exists
from app.models.ingredients import Ingredients # Assuming this is your models
from app.models.menuingredients import MenuIngredients # Assuming this is your models
from app.models.ingredientpack import IngredientPack
from app.models.menuingredientpack import MenuIngredientPack

# --- Configuration ---
# Use os.path.expanduser() to handle tilde expansion reliably
BASE_DIR = os.path.expanduser("~/kmitl_project_bfmm/backend/app")
NLP_DIR = os.path.join(BASE_DIR, "nlp")
OUTPUT_DIR = os.path.join(NLP_DIR, "output")
MODEL_PATH = os.path.join(NLP_DIR, "crf_model_ner_v1")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Check if the model file actually exists
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"CRF model file not found at: {MODEL_PATH}")
print(f"Loading CRF model from: {MODEL_PATH}")


# --- Helper Functions ---

def recognize_audio(audio_path):
    """Recognizes speech from an audio file using Google Speech Recognition."""
    recog = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = recog.record(source)

    try:
        text = recog.recognize_google(audio, language="th-TH")
        return text
    except sr.UnknownValueError:
        return "ไม่สามารถแปลงเสียงได้"
    except sr.RequestError:
        return "เกิดข้อผิดพลาดในการเชื่อมต่อกับ API"

def convert_text(text):
    """Converts Thai number words to Arabic numerals and removes extra spaces."""
    number_map = {
        "ศูนย์": "0", "หนึ่ง": "1", "สอง": "2", "สาม": "3", "สี่": "4",
        "ห้า": "5", "หก": "6", "เจ็ด": "7", "แปด": "8", "เก้า": "9", "สิบ": "10",
        "pizza": "พิซซ่า"  # Keep this as it might be relevant for fuzzy matching
    }

    for thai_num, arabic_num in number_map.items():
        text = text.replace(thai_num, arabic_num)
    text = re.sub(r"\s+", "", text)  # Remove multiple spaces
    return text

# --- NER and Intent Recognition ---

# Load CRF model
crf_model = sklearn_crfsuite.CRF(
    algorithm='lbfgs',
    c1=0.1,
    c2=0.1,
    max_iterations=500,
    all_possible_transitions=True,
    model_filename=MODEL_PATH  # Use the absolute path
)

def doc2features(doc, i):
    """Extract features for CRF model."""
    word = doc[i][0]
    postag = doc[i][1]
    features = {
        'word.word': word,
        'word.isspace': word.isspace(),
        'postag': postag,
        'word.isdigit()': word.isdigit()
    }
    if i > 0:
        prevword = doc[i-1][0]
        postag1 = doc[i-1][1]
        features['word.prevword'] = prevword
        features['word.previsspace'] = prevword.isspace()
        features['word.prepostag'] = postag1
        features['word.prevwordisdigit'] = prevword.isdigit()
    else:
        features['BOS'] = True
    if i < len(doc)-1:
        nextword = doc[i+1][0]
        postag1 = doc[i+1][1]
        features['word.nextword'] = nextword
        features['word.nextisspace'] = nextword.isspace()
        features['word.nextpostag'] = postag1
        features['word.nextwordisdigit'] = nextword.isdigit()
    else:
        features['EOS'] = True
    return features

def extract_features(doc):
    """Extract features for the entire document."""
    return [doc2features(doc, i) for i in range(len(doc))]

def postag(text):  # This function seems unused, but I'll keep it.
    """Perform POS tagging."""
    listtxt = [i for i in text.split('\n') if i!='']
    list_word = []
    for data in listtxt:
        list_word.append(data.split('\t')[0])
    list_word=pos_tag(list_word,engine="perceptron")
    text=""
    i=0
    for data in listtxt:
        text+=data.split('\t')[0]+'\t'+list_word[i][1]+'\t'+data.split('\t')[1]+'\n'
        i+=1
    return text

def get_ner(text):
    """Perform Named Entity Recognition."""
    word_cut = word_tokenize(text, keep_whitespace=False)
    list_word = pos_tag(word_cut, engine='perceptron')
    X_test = extract_features([(data, list_word[i][1]) for i, data in enumerate(word_cut)])
    y_ = crf_model.predict_single(X_test)
    return [(word_cut[i], list_word[i][1], data) for i, data in enumerate(y_)]


def process_data(data):
    """Process NER results to extract structured information."""
    result = {"TABLE": [], "COMMAND": "", "FOOD": [], "QUESTION": False}
    current_table = None
    current_food = []

    # Fetch menu list from the database
    menu_list = Menu.query.all()
    menu_list = [menu.name for menu in menu_list]

    for word, tag, label in data:
        if label.startswith("B-TABLE"):
            current_table = word if word.isdigit() else None
        elif label.startswith("I-TABLE"):
            if current_table is None:
                current_table = word if word.isdigit() else None
            elif current_table is not None and word.isdigit():
                current_table += word
        elif label.startswith("B-FOOD"):
            current_food = [word]
        elif label.startswith("I-FOOD"):
            current_food.append(word)
        elif label.startswith("B-COMMAND_"):
            result["COMMAND"] = "COMMAND_" + label.split("_")[1]
        elif label.startswith("B-QUESTION"):
            result["QUESTION"] = True
        elif label == "O":
            if current_table is not None and current_table.isdigit():
                result["TABLE"].append(int(current_table))
                current_table = None
            if current_food:
                matched_food = "".join(current_food)
                best_match = process.extractOne(matched_food, menu_list)
                if best_match and best_match[1] > 60:  # Fuzzy matching threshold
                    result["FOOD"].append(best_match[0])
                else:
                    result["FOOD"].append(matched_food)
                current_food = []

    if current_table is not None and current_table.isdigit():
        result["TABLE"].append(int(current_table))
    if current_food:
        matched_food = "".join(current_food)
        best_match = process.extractOne(matched_food, menu_list)
        if best_match and best_match[1] > 60:
            result["FOOD"].append(best_match[0])
        else:
            result["FOOD"].append(matched_food)

    return result


def predict_resp(txt):
    """Predict response based on the input text."""
    p_data = get_ner(txt)
    return process_data(p_data)


# --- Stock Management and Order Updates ---

def validate_input(data, required_keys):
    """Validates input data."""
    for key in required_keys:
        if key not in data or not data[key]:
            return False, f"{key} is required!"
    return True, ""


def stock_manager(menu_id, qty):
    try:
        print("📦 เริ่มระบบ stock_manager...")

        # --- 1. จัดการ stock วัตถุดิบจาก table 'menuingredients' ---
        print(f"🔍 ดึงวัตถุดิบเดี่ยวของ menu_id: {menu_id}")
        menu_ingredients = db.session.execute(
            text("SELECT ingredient_id, volume FROM menuingredients WHERE menu_id = :menu_id"),
            {"menu_id": menu_id}
        ).mappings().fetchall()

        if not menu_ingredients:
            print("⚠️ ไม่พบข้อมูลใน menuingredients")

        ingredient_ids = [ingredient["ingredient_id"] for ingredient in menu_ingredients]

        ingredient_stocks = []
        if ingredient_ids:
            ingredient_stocks = db.session.execute(
                text(f"SELECT Ingredients_id, main_stock FROM ingredients WHERE Ingredients_id IN ({', '.join(map(str, ingredient_ids))})")
            ).mappings().fetchall()

        stock_dict = {item["Ingredients_id"]: item["main_stock"] for item in ingredient_stocks}

        for ingredient in menu_ingredients:
            ingredient_id = ingredient["ingredient_id"]
            volume = ingredient["volume"]
            if ingredient_id in stock_dict:
                used_amount = volume * qty
                new_stock = stock_dict[ingredient_id] - used_amount
                print(f"→ ลด stock วัตถุดิบ id {ingredient_id}: -{used_amount}, คงเหลือใหม่: {new_stock}")

                db.session.execute(
                    text("UPDATE ingredients SET main_stock = :new_stock WHERE Ingredients_id = :ingredient_id"),
                    {"new_stock": new_stock, "ingredient_id": ingredient_id}
                )
            else:
                print(f"❗ ไม่พบ ingredient_id {ingredient_id} ใน stock")
                return jsonify({"message": f"Ingredient with id {ingredient_id} not found!"}), 404

        # --- 2. จัดการ stock จากระบบ Pack (menuingredientpack) ---
        print(f"🔍 ดึงวัตถุดิบแบบ Pack ของ menu_id: {menu_id}")
        menu_ingredient_packs = db.session.execute(
            text("SELECT ingredient_pack_id, qty FROM menuingredientpack WHERE menu_id = :menu_id"),
            {"menu_id": menu_id}
        ).mappings().fetchall()

        if not menu_ingredient_packs:
            print("⚠️ ไม่พบข้อมูลใน menuingredientpack")

        pack_ids = [pack["ingredient_pack_id"] for pack in menu_ingredient_packs]

        ingredient_pack_stocks = []
        if pack_ids:
            ingredient_pack_stocks = db.session.execute(
                text(f"SELECT id, stock FROM ingredientpack WHERE id IN ({', '.join(map(str, pack_ids))})")
            ).mappings().fetchall()

        pack_stock_dict = {item["id"]: item["stock"] for item in ingredient_pack_stocks}

        for pack in menu_ingredient_packs:
            pack_id = pack["ingredient_pack_id"]
            pack_qty = pack["qty"]
            if pack_id in pack_stock_dict:
                used_amount = pack_qty * qty
                new_stock = pack_stock_dict[pack_id] - used_amount
                print(f"→ ลด stock Pack id {pack_id}: -{used_amount}, คงเหลือใหม่: {new_stock}")

                db.session.execute(
                    text("UPDATE ingredientpack SET stock = :new_stock WHERE id = :pack_id"),
                    {"new_stock": new_stock, "pack_id": pack_id}
                )
            else:
                print(f"❗ ไม่พบ ingredient_pack_id {pack_id} ใน stock")
                return jsonify({"message": f"Ingredient Pack with id {pack_id} not found!"}), 404

        db.session.commit()
        print("✅ stock_manager ทำงานสำเร็จทั้งหมด")
        return {"status": 200, "message": "Stock has been successfully updated!"}

    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"❌ Database Error: {str(e)}")
        return {"status": 500, "message": f"Database Error: {str(e)}"}
    except Exception as e:
        db.session.rollback()
        print(f"❌ Unexpected Error: {str(e)}")
        return {"status": 500, "message": f"Unexpected Error: {str(e)}"}

def change_status_order(ai_data):
    try:
        print("❤❤❤ เริ่มต้นเปลี่ยนสถานะคำสั่งซื้อ ❤❤❤")
        print(f"Data received from AI: {ai_data}")

        required_keys = ['TABLE', 'COMMAND', 'FOOD']
        valid, message = validate_input(ai_data, required_keys)
        if not valid:
            print(f"Invalid input: {message}")
            return jsonify({"message": message}), 400

        table_ids = ai_data['TABLE']
        command_type = ai_data['COMMAND']
        food_names = ai_data['FOOD']
        question = ai_data.get('QUESTION', False)

        print(f"Table IDs: {table_ids}, Command Type: {command_type}, Food Names: {food_names}, Question: {question}")

        # สถานะเริ่มต้น
        status_change = 0

        if question:
            print("Question received, returning status_change 2")
            return jsonify({"status_change": 2}), 200

        if command_type and food_names and table_ids:
            print("Valid input, checking different cases")

            # ตรวจสอบกรณีต่างๆ
            if len(food_names) > 1 and len(table_ids) == 1:
                print(f"Multiple food items ({len(food_names)}) but only one table ID ({len(table_ids)})")
                for food in food_names:
                    table_id = table_ids[0]
                    menu = get_menu_id(food)
                    if menu:
                        print(f"Menu found for food: {food}, table_id: {table_id}")
                        order_id = get_order_id(table_id)
                        if order_id:
                            print(f"Order ID found for table_id {table_id}: {order_id}")
                            status_change = process_status_change(command_type, food, table_id, order_id)
                        else:
                            print(f"No order ID found for table_id {table_id}")
                    else:
                        print(f"No menu found for food: {food}")
            elif len(food_names) == 1 and len(table_ids) > 1:
                print(f"Single food item but multiple table IDs ({len(table_ids)})")
                for table_id in table_ids:
                    food = food_names[0]
                    menu = get_menu_id(food)
                    if menu:
                        print(f"Menu found for food: {food}, table_id: {table_id}")
                        order_id = get_order_id(table_id)
                        if order_id:
                            print(f"Order ID found for table_id {table_id}: {order_id}")
                            status_change = process_status_change(command_type, food, table_id, order_id)
                        else:
                            print(f"No order ID found for table_id {table_id}")
                    else:
                        print(f"No menu found for food: {food}")
            elif len(food_names) == 1 and len(table_ids) == 1:
                print(f"One food item and one table ID, food: {food_names[0]}, table_id: {table_ids[0]}")
                table_id = table_ids[0]
                food = food_names[0]
                menu = get_menu_id(food)
                if menu:
                    print(f"Menu found for food: {food}, table_id: {table_id}")
                    order_id = get_order_id(table_id)
                    if order_id:
                        print(f"Order ID found for table_id {table_id}: {order_id}")
                        status_change = process_status_change(command_type, food, table_id, order_id)
                    else:
                        print(f"No order ID found for table_id {table_id}")
                else:
                    print(f"No menu found for food: {food}")
            elif len(food_names) == len(table_ids):
                print(f"Food names and table IDs match in length ({len(food_names)})")
                for i in range(len(food_names)):
                    food = food_names[i]
                    table_id = table_ids[i]
                    menu = get_menu_id(food)
                    if menu:
                        print(f"Menu found for food: {food}, table_id: {table_id}")
                        order_id = get_order_id(table_id)
                        if order_id:
                            print(f"Order ID found for table_id {table_id}: {order_id}")
                            status_change = process_status_change(command_type, food, table_id, order_id)
                        else:
                            print(f"No order ID found for table_id {table_id}")
                    else:
                        print(f"No menu found for food: {food}")
            else:
                print("The system does not support this combination of food names and table IDs.")
                status_change = 0  # ระบบไม่รองรับ

            if status_change == 1:
                print("Status change successful")
                return jsonify({"status_change": 1}), 200
            elif status_change == 0:
                print("Status change failed")
                return jsonify({"status_change": 0}), 400

        print(f"Final status change: {status_change}")
        return jsonify({"status_change": status_change}), 200

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({"message": str(e)}), 500


def get_menu_id(food_name):
    print(f"Getting menu ID for food: {food_name}")
    menu = db.session.execute(
        text("SELECT id FROM menu WHERE name = :food_name"),
        {"food_name": food_name}
    ).mappings().fetchone()

    if not menu:
        print(f"No menu found for food: {food_name}")
        return None
    print(f"Menu ID for food {food_name}: {menu['id']}")
    return menu['id']


def get_order_id(table_id):
    print(f"Getting order ID for table: {table_id}")
    order_query = db.session.query(Order).filter_by(table_id=table_id).first()
    if not order_query:
        print(f"No order found for table: {table_id}")
        return None
    print(f"Order ID for table {table_id}: {order_query.order_id}")
    return order_query.order_id


def process_status_change(command_type, food, table_id, order_id):
    print(f"Processing status change for command: {command_type}, food: {food}, table_id: {table_id}, order_id: {order_id}")

    # หา menu_id จาก food_name
    menu_id = get_menu_id(food)
    if not menu_id:
        print(f"Failed to get menu ID for food: {food}")
        return 0

    # หา status_order เดิม
    existing_status = db.session.execute(
        text("SELECT status_order FROM orderitem WHERE menu_id = :menu_id AND order_id = :order_id"),
        {"menu_id": menu_id, "order_id": order_id}
    ).mappings().fetchone()

    if not existing_status:
        print(f"No existing status found for menu_id: {menu_id}, order_id: {order_id}")
        return 0

    current_status = existing_status["status_order"]
    print(f"Existing status for menu_id {menu_id}, order_id {order_id}: {current_status}")

    status_mapping = {'COMMAND_1': 1, 'COMMAND_2': 2}
    new_status = status_mapping.get(command_type)
    if not new_status:
        print(f"Invalid command type: {command_type}")
        return 0

    print(f"New status for command {command_type}: {new_status}")

    # เช็กว่ามีการลดสถานะไหม (ไม่อนุญาต)
    if new_status <= current_status:
        print(f"New status {new_status} is less than or equal to current status {current_status}, status change not allowed")
        return 0

    # อัปเดตสถานะ
    print(f"Updating status_order to {new_status} for menu_id {menu_id}, order_id {order_id}")
    db.session.execute(
        text("UPDATE orderitem SET status_order = :status WHERE menu_id = :menu_id AND order_id = :order_id"),
        {"status": new_status, "menu_id": menu_id, "order_id": order_id}
    )
    db.session.commit()

    # ถ้า COMMAND_1 จะต้องตัดสต็อก
    if command_type == "COMMAND_1":
        print("Command is COMMAND_1, checking stock")
        qty_result = db.session.execute(
            text("SELECT qty FROM orderitem WHERE menu_id = :menu_id AND order_id = :order_id"),
            {"menu_id": menu_id, "order_id": order_id}
        ).mappings().fetchone()

        if qty_result:
            qty = qty_result["qty"]
            print(f"Quantity for menu_id {menu_id}, order_id {order_id}: {qty}")
            stock_result = stock_manager(menu_id, qty)
            if stock_result["status"] != 200:
                print(f"Failed to update stock for menu_id {menu_id}, qty {qty}")
                return 0
            print(f"Stock updated successfully for menu_id {menu_id}, qty {qty}")

    return 1



# --- Main Audio Upload Endpoint ---

@cross_origin(supports_credentials=True)
def upload_audio():
    """Handles audio file uploads, conversion, and processing."""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    temp_upload_path = os.path.join(OUTPUT_DIR, file.filename)
    fixed_wav_path = os.path.join(OUTPUT_DIR, "speech.wav")

    try:
        with open(temp_upload_path, "wb") as f:
            f.write(file.read())
        print(f"File uploaded to: {temp_upload_path}")

        # Use ffmpeg to check file type (more robust than relying on filename extension)
        ffmpeg_check_cmd = ["ffmpeg", "-i", temp_upload_path]
        result = subprocess.run(ffmpeg_check_cmd, stderr=subprocess.PIPE, text=True)

        if "matroska,webm" in result.stderr or "opus" in result.stderr:
            print("⚠️ Detected WebM/Opus file, converting to WAV...")
            convert_cmd = [
                "ffmpeg", "-y", "-i", temp_upload_path,
                "-acodec", "pcm_s16le",  # Ensure consistent WAV format
                "-ar", "44100",        # Standard sample rate
                "-ac", "2",             # Stereo (optional, but good for consistency)
                fixed_wav_path
            ]
            subprocess.run(convert_cmd, check=True)  # Raise exception on error
            print(f"✅ Converted to WAV: {fixed_wav_path}")
            audio_wav = fixed_wav_path

        elif "mp3" in result.stderr.lower():  # added .lower() to fix
             print("✅ File is a real MP3, converting MP3 to WAV...")
             audio = AudioSegment.from_file(temp_upload_path, format="mp3")
             audio.export(fixed_wav_path, format="wav", parameters=["-acodec", "pcm_s16le"])
             print(f"✅ Exported WAV file: {fixed_wav_path}")
             audio_wav = fixed_wav_path
        else:
            return jsonify({"error": "Unsupported file format"}), 400 # check support file

        text = recognize_audio(audio_wav)
        text_new = convert_text(text)
        result_data = predict_resp(text_new)

        # Call change_status_order and return its result
        return change_status_order(result_data)


    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e}")
        return jsonify({"error": "FFmpeg conversion failed", "details": str(e)}), 500
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return jsonify({"error": "An error occurred during processing", "details": str(e)}), 500
    finally:
        # Clean up temporary files (optional, but good practice)
        try:
            os.remove(temp_upload_path)
            # Only remove fixed_wav_path if it's different
            if temp_upload_path != fixed_wav_path:
                os.remove(fixed_wav_path)

        except FileNotFoundError:
            pass # If not exits, pass
