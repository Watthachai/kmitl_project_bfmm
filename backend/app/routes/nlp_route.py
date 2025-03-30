from flask import Blueprint, jsonify
from flask_cors import CORS  # ✅ Import CORS
from app.middleware.auth_middleware import auth_required
from app.nlp.model import upload_audio , test_predict
# import resp_from_model as resp_model
from app.nlp.model import convert_predictions_to_json, convert_text


nlp_db = Blueprint('nlp', __name__)
CORS(nlp_db, resources={r"/*": {"origins": "*", "methods": ["POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"], "supports_credentials": True}})

# Protected routes (auth required)
@nlp_db.route('/', methods=['OPTIONS'])
def handle_options():
    """Handle preflight requests"""
    return jsonify({"message": "CORS Preflight OK"}), 200

# ใช้ฟังก์ชัน upload_audio สำหรับ POST
@nlp_db.route('/', methods=['POST'])
def upload_audio_api():
    return upload_audio()

@nlp_db.route("/crf/test_predict", methods=['POST'])
def test_predict_api():
    return test_predict()
    # เพิ่มจากโค้ดเก่าได้เลย
    # text = "หมึกผัดไข่เค็มโต๊ะ 4 เตรียมแล้ว" #ตรงนี้มาจาก text = recognize_audio(audio_wav)
    # text_new = convert_text(text)
    # predictions = resp_model.predict_resp(text_new,1)
    # print("predictts:", predictions)
    # text_json = convert_predictions_to_json(predictions, text)
    # print("text_json", text_json)

    # return jsonify({"resp": text_json})