from app.models.ingredientpackitems import IngredientPackItems
from app.models.ingredientpack import IngredientPack
from app.models.ingredients import Ingredients
from app import db
from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError

# Validate Input Function
def validate_input(data, required_keys):
    for key in required_keys:
        if key not in data or not data[key]:
            return False, f"{key} is required!"
    return True, ""

# Create IngredientPackItem
def create_ingredient_pack_item():
    try:
        data = request.get_json()

        required_keys = ["ingredient_pack_id", "ingredient_id", "qty"]
        is_valid, message = validate_input(data, required_keys)
        if not is_valid:
            return jsonify({"message": message}), 400

        # ตรวจสอบค่า qty
        if not isinstance(data["qty"], int) or data["qty"] < 0:
            return jsonify({"message": "qty must be a non-negative integer!"}), 400

        # สร้าง IngredientPackItem ใหม่
        new_ingredient_pack_item = IngredientPackItems(
            ingredient_pack_id=data["ingredient_pack_id"],
            ingredient_id=data["ingredient_id"],
            qty=data["qty"]
        )
        db.session.add(new_ingredient_pack_item)
        db.session.commit()

        # หา IngredientPack ที่ตรงกับ ingredient_pack_id
        ingredient_pack = IngredientPack.query.get(data["ingredient_pack_id"])
        if not ingredient_pack:
            return jsonify({"message": "IngredientPack not found!"}), 404

        # หาทุก ingredient_pack_item ที่มี ingredient_pack_id ตรงกับ ingredient_pack_id ที่เรากำหนด
        ingredient_pack_items = IngredientPackItems.query.filter_by(
            ingredient_pack_id=data["ingredient_pack_id"]
        ).all()

        # ตัด stock ของวัตถุดิบที่เกี่ยวข้องทั้งหมด
        for item in ingredient_pack_items:
            ingredient = Ingredients.query.get(item.ingredient_id)
            if not ingredient:
                return jsonify({"message": f"Ingredient with ID {item.ingredient_id} not found!"}), 404

            # คำนวณจำนวนที่ต้องตัดจาก main_stock
            total_deduction = item.qty * ingredient_pack.stock

            # ตรวจสอบว่า main_stock ของ ingredient มีมากพอหรือไม่
            if ingredient.main_stock < total_deduction:
                return jsonify({
                    "message": f"ไม่สามารถตัด stock ของ {ingredient.Ingredients_name} ได้ เนื่องจาก main_stock มีไม่พอ!"
                }), 400

            # ตัด stock ใน main_stock ของ ingredients
            ingredient.main_stock -= total_deduction

        # Commit การอัพเดททุกครั้ง
        db.session.commit()

        return jsonify({"message": "IngredientPackItem created successfully and stock updated!"}), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": f"Database Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Get All IngredientPackItems
def get_all_ingredient_pack_items():
    try:
        ingredient_pack_items = IngredientPackItems.query.all()
        return jsonify([ingredient_pack_item.as_dict() for ingredient_pack_item in ingredient_pack_items]), 200
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Get IngredientPackItem by ID
def get_ingredient_pack_item_by_id(ingredient_pack_item_id):
    try:
        ingredient_pack_item = IngredientPackItems.query.get(ingredient_pack_item_id)
        if ingredient_pack_item:
            return jsonify(ingredient_pack_item.as_dict()), 200
        return jsonify({"message": "IngredientPackItem not found!"}), 404
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Update IngredientPackItem
def update_ingredient_pack_item(ingredient_pack_item_id):
    try:
        data = request.get_json()
        ingredient_pack_item = IngredientPackItems.query.get(ingredient_pack_item_id)

        if ingredient_pack_item:
            ingredient_pack_item.ingredient_pack_id = data.get("ingredient_pack_id", ingredient_pack_item.ingredient_pack_id)
            ingredient_pack_item.ingredient_id = data.get("ingredient_id", ingredient_pack_item.ingredient_id)
            ingredient_pack_item.qty = data.get("qty", ingredient_pack_item.qty)

            # Input Validation
            if "qty" in data and (not isinstance(data["qty"], int) or data["qty"] < 0):
                return jsonify({"message": "qty must be a non-negative integer!"}), 400

            db.session.commit()
            return jsonify({"message": "IngredientPackItem updated successfully!"}), 200
        return jsonify({"message": "IngredientPackItem not found!"}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": f"Database Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Delete IngredientPackItem
def delete_ingredient_pack_item(ingredient_pack_item_id):
    try:
        ingredient_pack_item = IngredientPackItems.query.get(ingredient_pack_item_id)
        if ingredient_pack_item:
            db.session.delete(ingredient_pack_item)
            db.session.commit()
            return jsonify({"message": "IngredientPackItem deleted successfully!"}), 200
        return jsonify({"message": "IngredientPackItem not found!"}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": f"Database Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

def get_ingredient_pack_items_by_pack_id(ingredient_pack_id):
    try:
        items = IngredientPackItems.query.filter_by(ingredient_pack_id=ingredient_pack_id).all()
        if items:
            return jsonify([item.as_dict() for item in items]), 200
        return jsonify({"message": "No items found for this ingredient pack ID!"}), 404
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500