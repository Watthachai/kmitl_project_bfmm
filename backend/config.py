import os
import hashlib

class Config:
    # ถ้าไม่มีตัวแปรใน environment จะใช้คีย์ที่สุ่มขึ้น
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())  # หรือใช้ hashlib ได้เช่นกัน
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', hashlib.sha256(os.urandom(24)).hexdigest())
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 1 day

    # Database configuration using environment variables
    DB_USER = os.environ.get('DB_USER', 'kmitl_project')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'kmitl_project')
    DB_NAME = os.environ.get('DB_NAME', 'kmitl_project')

    # เปลี่ยน DB_HOST จาก 'db' เป็นการเข้าถึงภายนอก
    DB_HOST = os.environ.get('DB_HOST', '0.0.0.0')  # ใช้ 0.0.0.0 เพื่อให้สามารถเข้าถึงจากภายนอกได้

    # SQLALCHEMY_DATABASE_URI ที่ปรับให้เข้าถึงได้จากภายนอก
    SQLALCHEMY_DATABASE_URI = (f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")
