from app.models.ingredients import Ingredients
from app import db
from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'images', 'ingredients')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Validate Input Function
def validate_input(data, required_keys):
    for key in required_keys:
        if key not in data or not data[key]:
            return False, f"{key} is required!"
    return True, ""

# Create Ingredient
def create_ingredient():
    try:
        data = request.form
        required_keys = ["Ingredients_name"]
        is_valid, message = validate_input(data, required_keys)
        if not is_valid:
            return jsonify({"message": message}), 400

        if 'Ingredients_image' not in request.files:
            return jsonify({"message": "Image file is required!"}), 400

        image_file = request.files['Ingredients_image']
        if image_file.filename == '' or not allowed_file(image_file.filename):
            return jsonify({"message": "Invalid image file!"}), 400

        filename = secure_filename(image_file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(image_path)

        main_stock = data.get("main_stock", "0")
        sub_stock = data.get("sub_stock", "0")

        if not main_stock.isdigit() or int(main_stock) < 0:
            return jsonify({"message": "main_stock must be a non-negative integer!"}), 400
        if not sub_stock.isdigit() or int(sub_stock) < 0:
            return jsonify({"message": "sub_stock must be a non-negative integer!"}), 400

        new_ingredient = Ingredients(
            Ingredients_name=data["Ingredients_name"],
            Ingredients_image=filename,
            Ingredients_des=data.get("Ingredients_des"),
            main_stock=int(main_stock),
            sub_stock=int(sub_stock),
            unit=data.get("unit", "unit")
        )

        db.session.add(new_ingredient)
        db.session.commit()

        return jsonify({"message": "Ingredient created successfully!"}), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": f"Database Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Get All Ingredients
def get_all_ingredients():
    try:
        ingredients = Ingredients.query.all()
        return jsonify([ingredient.as_dict() for ingredient in ingredients]), 200
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Get Ingredient by ID
def get_ingredient_by_id(ingredients_id):
    try:
        ingredient = Ingredients.query.get(ingredients_id)
        if ingredient:
            return jsonify(ingredient.as_dict()), 200
        return jsonify({"message": "Ingredient not found!"}), 404
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Update Ingredient
def update_ingredient(ingredients_id):
    try:
        data = request.form
        ingredient = Ingredients.query.get(ingredients_id)

        if not ingredient:
            return jsonify({"message": "Ingredient not found!"}), 404

        old_main = ingredient.main_stock
        old_sub = ingredient.sub_stock

        try:
            new_main = int(data.get("main_stock", old_main))
            new_sub = int(data.get("sub_stock", old_sub))
        except ValueError:
            return jsonify({"message": "main_stock และ sub_stock ต้องเป็นตัวเลขจำนวนเต็ม!"}), 400

        if new_main < 0 or new_sub < 0:
            return jsonify({"message": "Stock ต้องเป็นค่ามากกว่าหรือเท่ากับ 0"}), 400

        if new_main > old_main:
            increase_amount = new_main - old_main
            if old_sub < increase_amount:
                return jsonify({
                    "message": f"ไม่สามารถเพิ่ม Main Stock ได้ เนื่องจาก Sub Stock มีไม่พอ! "
                               f"ต้องการ {increase_amount} แต่เหลือเพียง {old_sub} หน่วย"
                }), 400
            new_sub = old_sub - increase_amount

        ingredient.Ingredients_name = data.get("Ingredients_name", ingredient.Ingredients_name)
        ingredient.Ingredients_des = data.get("Ingredients_des", ingredient.Ingredients_des)
        ingredient.main_stock = new_main
        ingredient.sub_stock = new_sub
        ingredient.unit = data.get("unit", ingredient.unit)

        if 'Ingredients_image' in request.files:
            image_file = request.files['Ingredients_image']
            if image_file and allowed_file(image_file.filename):
                # ลบภาพเก่า
                if ingredient.Ingredients_image:
                    old_path = os.path.join(UPLOAD_FOLDER, ingredient.Ingredients_image)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                filename = secure_filename(image_file.filename)
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                image_file.save(image_path)
                ingredient.Ingredients_image = filename

        db.session.commit()
        return jsonify({"message": "Ingredient updated successfully!"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": f"Database Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Delete Ingredient
def delete_ingredient(ingredients_id):
    try:
        ingredient = Ingredients.query.get(ingredients_id)
        if ingredient:
            db.session.delete(ingredient)
            db.session.commit()
            return jsonify({"message": "Ingredient deleted successfully!"}), 200
        return jsonify({"message": "Ingredient not found!"}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": f"Database Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Show/Update Ingredient enable status
def show_ingredient():
    try:
        # รับข้อมูล JSON
        data = request.get_json()
        
        # ตรวจสอบว่า id และ enable ถูกต้อง
        if "id" not in data or "enable" not in data:
            return jsonify({"message": "Both 'id' and 'enable' are required!"}), 400
        
        # ค้นหาวัตถุดิบที่มี Ingredients_id ที่ระบุ
        ingredient = Ingredients.query.get(data["id"])
        if not ingredient:
            return jsonify({"message": "Ingredient not found!"}), 404
        
        # อัปเดตสถานะ enable ของวัตถุดิบ
        enable_value = data["enable"]
        
        # ตรวจสอบว่า enable มีค่าเป็น 0 หรือ 1 เท่านั้น
        if enable_value not in [0, 1]:
            return jsonify({"message": "'enable' must be either 0 or 1!"}), 400

        ingredient.enable = enable_value

        # บันทึกการเปลี่ยนแปลงในฐานข้อมูล
        db.session.commit()

        return jsonify({"message": "Ingredient enable status updated successfully!"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": f"Database Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500
