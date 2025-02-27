import json
import sched
import psycopg2
import logging
import requests
import time

from pytz import timezone
from datetime import datetime, timedelta
from psycopg2.extras import RealDictCursor, DictCursor
from multiprocessing import Process, Queue, Manager
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

from db.room_py import RoomPy
import configs

app = Flask(__name__)

ACCESS_TOKEN = None
TOKEN_EXPIRE_TIME = None
ROOMS_CAMERAS = {}
HEADERS = {
    "Content-Type": "application/json"
}


def add_roompy_to_postgresql(room):
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(
            dbname=configs.POSTGRES_DB,
            user=configs.POSTGRES_USER,
            password=configs.POSTGRES_PASSWORD,
            host=configs.POSTGRES_HOST,
            port=configs.POSTGRES_PORT
        )
        cursor = connection.cursor(cursor_factory=DictCursor)

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roompys (
                uuidLocation SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT ,
                uuidOrganization TEXT NOT NULL,
                CONSTRAINT unique_room UNIQUE (name, description, uuidOrganization)
            )
        ''')
        connection.commit()

        cursor.execute('''
            INSERT INTO roompys (name, description, uuidOrganization)
            VALUES (%s, %s, %s)
            ON CONFLICT (name, description, uuidOrganization) DO NOTHING
            RETURNING uuidLocation
        ''', (
            room["name"], room["description"], room["uuidOrganization"]
        ))

        result = cursor.fetchone()
        connection.commit()

        if result:
            return {
                "status": "success",
                "message": "room_py added successfully",
                "room_id": result["uuidLocation"]
            }
        else:
            return {
                "status": "error",
                "message": "Room_py already exists"
            }

    except Exception as e:
        logging.info(f"PostgreSQL error: {e}")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def add_rule_to_camera(result,
                       camera_code="TEST1",
                       ai_rule_code="IOC-000-003-test8",
                       restream=True,
                       fps_handle=5,
                       type_ai=["AI0210", "AI0211"],
                       service_name="IOC-SI",
                       detect_phone_level=3):
    logging.info("add_rule_to_camera")
    camera_links = json.loads(result["camera_links"])
    for link in camera_links:
        payload = {
            "action": "add",
            "ai_rule_code": ai_rule_code,
            "camera_code": camera_code,
            "camera_link": link,
            "restream": restream,
            "fps_handle": fps_handle,
            "type_ai": type_ai,
            "service_name": service_name,
            "config":
                {
                    "detect_phone_level": detect_phone_level
                }
        }

        try:
            ai_response = requests.post(configs.API_STREAM, json=payload, headers=HEADERS)
            logging.info(f" Gửi AI rule cho TEST1. Status: {ai_response.status_code}")
            # logging.info(f"Body: {ai_response.text}")
        except Exception as e:
            logging.info(f" Lỗi khi gửi AI rule: {e}")
            continue


def get_access_token():
    global ACCESS_TOKEN, TOKEN_EXPIRE_TIME

    data = {
        "appId": configs.APP_ID,
        "appSecret": configs.APP_SECRET
    }

    try:
        response = requests.post(configs.TOKEN_URL, json=data, headers=HEADERS)
        if response.status_code == 200:

            raw_text = response.text
            # logging.info("Raw response:", raw_text)
            if isinstance(response.json(), str):
                logging.info("Dữ liệu trả về là chuỗi, cần chuyển đổi thành dictionary.")
                result = json.loads(raw_text)
            else:
                result = response.json()

            ACCESS_TOKEN = result["object"]["accessToken"]
            expire_in = result["object"]["expireIn"]
            TOKEN_EXPIRE_TIME = datetime.now() + timedelta(seconds=expire_in - 60)
            logging.info(f" Access Token: {ACCESS_TOKEN}")
            logging.info(f" Token hết hạn lúc: {TOKEN_EXPIRE_TIME}")
        else:
            logging.info(f" Lỗi lấy token: {response.text}")
    except Exception as e:
        logging.info(f" Exception khi lấy token: {e}")


def update_headers():
    if not ACCESS_TOKEN:
        get_access_token()
    return {"Content-Type": "application/json", "Authorization": f"Bearer {ACCESS_TOKEN}"}


def get_camera(api_url, headers):
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logging.info(f"Lỗi khi lấy danh sách camera: {response.status_code}")
    except Exception as e:
        logging.info(f"Lỗi khi gửi yêu cầu APIcamera: {e}")

    return None


def get_location(api_url, headers):
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logging.info(f"Lỗi khi lấy danh sách location: {response.status_code}")
    except Exception as e:
        logging.info(f"Lỗi khi gửi yêu cầu APIlocation: {e}")

    return None


def call_api():
    global TOKEN_EXPIRE_TIME

    # Nếu token hết hạn, lấy token mới
    if not ACCESS_TOKEN or datetime.now() >= TOKEN_EXPIRE_TIME:
        get_access_token()

    try:
        headers = update_headers()
        response = requests.get(configs.API_URL1, headers=headers)
        logging.info(f"Đã gọi API lúc 1 giờ sáng. Status: {response.status_code}")
    except Exception as e:
        logging.info(f"Lỗi khi gọi API: {e}")
        return
    raw_text = response.text

    if isinstance(response.json(), str):
        logging.info("Dữ liệu trả về là chuỗi, cần chuyển đổi thành dictionary.")
        schedules = json.loads(raw_text)
    else:
        schedules = response.json()

    if response.status_code == 200:
        if not schedules:
            logging.info(" Không có lịch nào hôm nay.")
            return

    num_schedules = len(schedules["object"]["data"])
    logging.info(f"Số lượng sự kiện trong schedules: {num_schedules}")
    # logging.info(f"data : {schedules}")
    for schedule in schedules["object"]["data"]:
        room_id = schedule["uuidLocation"]
        target_time = schedule["startTime"]
        now = datetime.now()
        # logging.info(f"schedule : {schedule}")
        try:

            today_date = datetime.today().strftime('%Y-%m-%d')
            target_datetime = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
            target_date = target_datetime.strftime('%Y-%m-%d')

            # kiểm tra tất cả các lịch , xem có thời gian bắt đầu sự kiện nằm trong ngày hôm nay không.
            if target_date == today_date:
                # if target_date == "2025-01-01":
                logging.info(f"Sự kiện vào hôm nay: {target_time}")

                # lấy tất cả camera rồi lọc camera có uuidLocation giống scheduler.
                result_camera = get_camera(configs.API_URL2, headers)

                cameras = result_camera["object"]["data"]
                for camera in cameras:
                    if room_id == camera["uuidLocation"]:
                        # logging.info(f"result_camera : {result_camera}")
                        if room_id not in ROOMS_CAMERAS:
                            ROOMS_CAMERAS[room_id] = []
                        ROOMS_CAMERAS[room_id].append(camera)

                        # # lấy tất cả room rồi lọc room có uuidLocation giống scheduler.
                        result_return = get_location(configs.API_URL3, headers)
                        locations = result_return["object"]["data"]
                        for location in locations:
                            if room_id == location["uuidLocation"]:
                                add_roompy_to_postgresql(location)

                        if camera["status"] == 1:
                            target_datetime = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                            wait_time = (target_datetime - now).total_seconds()

                            if wait_time > 0:
                                logging.info(f"Lên lịch thực hiện sau {wait_time:.2f} giây...")
                                scheduler.enter(wait_time, 1, add_rule_to_camera, argument=(camera["encodeDev"],))
                                scheduler.run()
                            else:
                                logging.info("Thời gian đã trôi qua!")

                    else:
                        logging.info(f"Camera {camera['cameraName']} không hoạt động")
                        continue

            else:
                logging.info(f"Sự kiện không phải hôm nay: {target_time}")
        except Exception as e:
            logging.info(f"Lỗi xxx : {e}")
            return


def start_scheduler():
    scheduler_x = BackgroundScheduler(timezone=timezone("Asia/Ho_Chi_Minh"))
    scheduler_x.add_job(call_api, 'cron', hour=configs.HOUR, minute=configs.MINUTE)
    # scheduler_x.add_job(call_api, 'date', run_date=datetime.now() + timedelta(seconds=10))

    scheduler_x.start()
    try:
        while True:
            logging.info(" Hệ thống đang chạy, chờ đến 1 giờ sáng...")
            time.sleep(10)
    except KeyboardInterrupt:
        scheduler_x.shutdown()


if __name__ == '__main__':
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler_process = Process(target=start_scheduler, daemon=True)
    scheduler_process.start()
    app.run(host="0.0.0.0", debug=False, port=5032)
