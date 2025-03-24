from app.models.menu import Menu
from app import db
from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'images', 'menus')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# ตรวจสอบว่าไฟล์มีนามสกุลที่อนุญาตไหม
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Utility function for input validation
def validate_input(data, required_keys):
    for key in required_keys:
        if key not in data or not data[key]:
            return False, f"{key} is required!"
    return True, ""

def create_menu():
    try:
        data = request.form
        required_keys = ["type_id", "name"]
        is_valid, message = validate_input(data, required_keys)

        if not is_valid:
            return jsonify({"message": message}), 400

        if 'image' not in request.files:
            return jsonify({"message": "Image file is required!"}), 400

        image_file = request.files['image']
        if image_file.filename == '' or not allowed_file(image_file.filename):
            return jsonify({"message": "Invalid image file!"}), 400

        # บันทึกไฟล์
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(image_path)

        # เตรียมข้อมูล
        new_menu = Menu(
            type_id=data["type_id"],
            name=data["name"],
            image=filename,  # เก็บแค่ชื่อไฟล์
            des=data.get("des"),
            price=data.get("price"),
            tag=data.get("tag"),
            warning=data.get("warning")
        )

        # ตรวจสอบ price
        if new_menu.price and (not str(new_menu.price).replace('.', '', 1).isdigit() or float(new_menu.price) < 0):
            return jsonify({"message": "Price must be a positive number!"}), 400

        db.session.add(new_menu)
        db.session.commit()

        return jsonify({"message": "Menu created successfully!", "menu_id": new_menu.id}), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": f"Database Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Get All menus
def get_all_menus():
    try:
        menus = Menu.query.all()
        return jsonify([menu.as_dict() for menu in menus]), 200
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Get menu by ID
def get_menu_by_id(menu_id):
    try:
        menu = Menu.query.get(menu_id)
        if menu:
            return jsonify(menu.as_dict()), 200
        return jsonify({"message": "Menu not found!"}), 404
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Get menus by type_id
def get_menus_by_type(type_id):
    try:
        menus = Menu.query.filter_by(type_id=type_id).all()
        if menus:
            return jsonify([menu.as_dict() for menu in menus]), 200
        return jsonify({"message": "No menus found for this type_id!"}), 404
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

def update_menu(menu_id):
    try:
        data = request.form
        menu = Menu.query.get(menu_id)

        if not menu:
            return jsonify({"message": "Menu not found!"}), 404

        menu.type_id = data.get("type_id", menu.type_id)
        menu.name = data.get("name", menu.name)
        menu.des = data.get("des", menu.des)
        menu.price = data.get("price", menu.price)
        menu.tag = data.get("tag", menu.tag)
        menu.warning = data.get("warning", menu.warning)

        if "price" in data and (not str(data["price"]).replace('.', '', 1).isdigit() or float(data["price"]) < 0):
            return jsonify({"message": "Price must be a positive number!"}), 400

        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and allowed_file(image_file.filename):
                # ลบไฟล์เก่า (ถ้ามี)
                if menu.image:
                    old_path = os.path.join(UPLOAD_FOLDER, menu.image)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                filename = secure_filename(image_file.filename)
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                image_file.save(image_path)
                menu.image = filename

        db.session.commit()
        return jsonify({"message": "Menu updated successfully!"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": f"Database Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Delete menu
def delete_menu(menu_id):
    try:
        menu = Menu.query.get(menu_id)
        if menu:
            db.session.delete(menu)
            db.session.commit()
            return jsonify({"message": "Menu deleted successfully!"}), 200
        return jsonify({"message": "Menu not found!"}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": f"Database Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500

# Change enable status of a menu
def show_mnenu():
    try:
        # รับข้อมูล JSON จาก request
        data = request.get_json()

        # ตรวจสอบว่าในข้อมูลมี 'id' และ 'enable' หรือไม่
        if "id" not in data or "enable" not in data:
            return jsonify({"message": "'id' and 'enable' are required!"}), 400
        
        # ดึงค่า id และ enable จากข้อมูล
        menu_id = data["id"]
        enable_status = data["enable"]

        # ตรวจสอบว่า 'enable' ต้องเป็น 0 หรือ 1 เท่านั้น
        if enable_status not in [0, 1]:
            return jsonify({"message": "'enable' must be either 0 or 1!"}), 400

        # ค้นหาเมนูจากฐานข้อมูลโดยใช้ id
        menu = Menu.query.get(menu_id)

        if menu:
            # อัปเดตค่า enable ในฐานข้อมูล
            menu.enable = enable_status

            # บันทึกการเปลี่ยนแปลงในฐานข้อมูล
            db.session.commit()

            return jsonify({"message": "Menu enable status updated successfully!"}), 200
        else:
            return jsonify({"message": "Menu not found!"}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": f"Database Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected Error: {str(e)}"}), 500
