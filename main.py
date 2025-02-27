
import json
from pytz import timezone
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor, DictCursor
from multiprocessing import Process, Queue, Manager
from flask import Flask, jsonify
from configx import configx
import logging

from apscheduler.schedulers.background import BackgroundScheduler
import requests
import time

import sched


from db.room_py import RoomPy

app = Flask(__name__)

restreaming_status = []
manager = Manager()
proc_streaming_is_valid_v2 = manager.dict()
proc_restream_list = {}
log_queue = Queue(-1)


def add_roompy_to_postgresql(room):
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(
            dbname=configx.POSTGRES_DB,
            user=configx.POSTGRES_USER,
            password=configx.POSTGRES_PASSWORD,
            host=configx.POSTGRES_HOST,
            port=configx.POSTGRES_PORT
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
        print(f"PostgreSQL error: {e}")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def add_rule_to_camera(result):

    print("add_rule_to_camera")
    camera_links = json.loads(result["camera_links"])
    for link in camera_links:
        payload = {
            "action": "add",
            "ai_rule_code": "IOC-000-003-test8",
            "camera_code": "TEST1",
            "camera_link": link,
            "restream": True,
            "fps_handle": 5,
            "type_ai": ["AI0210", "AI0211"],
            "service_name": "IOC-SI",
            "config": {"detect_phone_level": 3}
        }

        try:
            ai_response = requests.post(configx.API_STREAM, json=payload, headers=HEADERS)
            print(f" Gửi AI rule cho TEST1. Status: {ai_response.status_code}")
            # print(f"Body: {ai_response.text}")
        except Exception as e:
            print(f" Lỗi khi gửi AI rule: {e}")
            continue


ACCESS_TOKEN = None
TOKEN_EXPIRE_TIME = None


def get_access_token():
    global ACCESS_TOKEN, TOKEN_EXPIRE_TIME

    headers = {"Content-Type": "application/json"}
    data = {
        "appId": configx.APP_ID,
        "appSecret": configx.APP_SECRET
    }

    try:
        response = requests.post(configx.TOKEN_URL, json=data, headers=headers)
        if response.status_code == 200:

            raw_text = response.text
            # print("Raw response:", raw_text)
            if isinstance(response.json(), str):
                print("Dữ liệu trả về là chuỗi, cần chuyển đổi thành dictionary.")
                result = json.loads(raw_text)
            else:
                result = response.json()

            ACCESS_TOKEN = result["object"]["accessToken"]
            expire_in = result["object"]["expireIn"]
            TOKEN_EXPIRE_TIME = datetime.now() + timedelta(seconds=expire_in - 60)
            print(f" Access Token: {ACCESS_TOKEN}")
            print(f" Token hết hạn lúc: {TOKEN_EXPIRE_TIME}")
        else:
            print(f" Lỗi lấy token: {response.text}")
    except Exception as e:
        print(f" Exception khi lấy token: {e}")

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
            print(f"Lỗi khi lấy danh sách camera: {response.status_code}")
    except Exception as e:
        print(f"Lỗi khi gửi yêu cầu APIcamera: {e}")

    return None

def get_location(api_url, headers):

    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Lỗi khi lấy danh sách location: {response.status_code}")
    except Exception as e:
        print(f"Lỗi khi gửi yêu cầu APIlocation: {e}")

    return None



HEADERS = {"Content-Type": "application/json"}
room_cameras = {}
def call_api():

    global TOKEN_EXPIRE_TIME

    # Nếu token hết hạn, lấy token mới
    if not ACCESS_TOKEN or datetime.now() >= TOKEN_EXPIRE_TIME:
        get_access_token()

    try:

        headers = update_headers()
        response = requests.get(configx.API_URL1, headers=headers)
        print(f"Đã gọi API lúc 1 giờ sáng. Status: {response.status_code}")
    except Exception as e:
        print(f"Lỗi khi gọi API: {e}")
        return
    raw_text = response.text

    if isinstance(response.json(), str):
        print("Dữ liệu trả về là chuỗi, cần chuyển đổi thành dictionary.")
        schedules = json.loads(raw_text)
    else:
        schedules = response.json()

    if response.status_code == 200:
        if not schedules:
            print(" Không có lịch nào hôm nay.")
            return

    num_schedules = len(schedules["object"]["data"])
    print(f"Số lượng sự kiện trong schedules: {num_schedules}")
    # print(f"data : {schedules}")
    for schedule in schedules["object"]["data"]:
        room_id = schedule["uuidLocation"]
        target_time = schedule["startTime"]
        now = datetime.now()
        # print(f"schedule : {schedule}")
        try:

            today_date = datetime.today().strftime('%Y-%m-%d')
            target_datetime = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
            target_date = target_datetime.strftime('%Y-%m-%d')

            # kiểm tra tất cả các lịch , xem có thời gian bắt đầu sự kiện nằm trong ngày hôm nay không.
            if target_date == today_date:
            # if target_date == "2025-01-01":
                print(f"Sự kiện vào hôm nay: {target_time}")

                # lấy tất cả camera rồi lọc camera có uuidLocation giống scheduler.
                result_camera = get_camera(configx.API_URL2, headers)

                cameras = result_camera["object"]["data"]
                for camera in cameras:
                    if room_id == camera["uuidLocation"]:
                        # print(f"result_camera : {result_camera}")
                        if room_id not in room_cameras:
                            room_cameras[room_id] = []
                        room_cameras[room_id].append(camera)

                        # # lấy tất cả room rồi lọc room có uuidLocation giống scheduler.
                        result_return = get_location(configx.API_URL3, headers)
                        locations = result_return["object"]["data"]
                        for location in locations:
                            if room_id == location["uuidLocation"]:
                                add_roompy_to_postgresql(location)

                        if camera["status"] == 1:
                            target_datetime = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                            wait_time = (target_datetime - now).total_seconds()

                            if wait_time > 0:
                                print(f"Lên lịch thực hiện sau {wait_time:.2f} giây...")
                                scheduler.enter(wait_time, 1, add_rule_to_camera, argument=(camera["encodeDev"],))
                                scheduler.run()
                            else:
                                print("Thời gian đã trôi qua!")

                    else:
                        print(f"Camera {camera['cameraName']} không hoạt động")
                        continue

            else:
                print(f"Sự kiện không phải hôm nay: {target_time}")
        except Exception as e:
            print(f"Lỗi xxx : {e}")
            return

def start_scheduler():

    scheduler_x = BackgroundScheduler(timezone=timezone("Asia/Ho_Chi_Minh"))
    scheduler_x.add_job(call_api, 'cron', hour=configx.HOUR, minute=configx.MINUTE)
    # scheduler_x.add_job(call_api, 'date', run_date=datetime.now() + timedelta(seconds=10))

    scheduler_x.start()
    try:
        while True:
            print(" Hệ thống đang chạy, chờ đến 1 giờ sáng...")
            time.sleep(10)
    except KeyboardInterrupt:
        scheduler_x.shutdown()


if __name__ == '__main__':
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler_process = Process(target=start_scheduler, daemon=True)
    scheduler_process.start()
    app.run(host="0.0.0.0", debug=False, port=5032)