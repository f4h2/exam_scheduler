import datetime
import json
from pytz import timezone
import psutil
import psycopg2
from psycopg2.extras import RealDictCursor, DictCursor
from multiprocessing import Process, Queue, Manager
from create_room_api import rtsp_hls
from flask import Flask, jsonify
from configx import configx
import logging

from apscheduler.schedulers.background import BackgroundScheduler
import requests
import time

import sched
from datetime import datetime

from db.room_py import RoomPy

app = Flask(__name__)
app.register_blueprint(rtsp_hls)

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
                id SERIAL PRIMARY KEY,
                name_room TEXT,
                camera_links TEXT,
                UNIQUE (name_room, camera_links)
            )''')
        connection.commit()

        cursor.execute('''
            INSERT INTO roompys (
                name_room, camera_links
            ) VALUES ( %s, %s)
            ON CONFLICT (name_room, camera_links) DO NOTHING
                    RETURNING id
        ''', (
            room.name_room, json.dumps(room.camera_links) if isinstance(room.camera_links, list) else room.camera_links
        ))
        result = cursor.fetchone()
        connection.commit()

        if result:
            return {
                "status": "success",
                "message": "room_py added successfully",
                "room_id": result["id"]
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
            ai_response = requests.post(API_URL2, json=payload, headers=HEADERS)
            print(f" Gửi AI rule cho TEST1. Status: {ai_response.status_code}")
            # print(f"Body: {ai_response.text}")
        except Exception as e:
            print(f" Lỗi khi gửi AI rule: {e}")
            continue



API_URL1 = "http://127.0.0.1:5032/get-schedule-by-time"
API_URL2 = "http://192.168.0.35:4067/api/ai/v2/stream"

HEADERS = {"Content-Type": "application/json"}
def call_api():
    try:
        response = requests.get(API_URL1)
        print(f"Đã gọi API lúc 1 giờ sáng. Status: {response.status_code}")
    except Exception as e:
        print(f"Lỗi khi gọi API: {e}")
        return

    if response.status_code == 200:
        schedules = response.json()
        if not schedules:
            print(" Không có lịch thi nào hôm nay.")
            return

        for schedule in schedules:
            print("schedule:{}".format(schedule))
            room_name = schedule[1]
            target_time = schedule[3]
            now = datetime.now()
            target = datetime.strptime(f"{now.date()} {target_time}", "%Y-%m-%d %H:%M:%S")

            try:
                connection = psycopg2.connect(
                    dbname=configx.POSTGRES_DB,
                    user=configx.POSTGRES_USER,
                    password=configx.POSTGRES_PASSWORD,
                    host=configx.POSTGRES_HOST,
                    port=configx.POSTGRES_PORT
                )
                cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

                cursor.execute("SELECT * FROM rooms WHERE name_room = %s", (room_name,))
                result = cursor.fetchone()

                if result:
                    wait_time = (target - now).total_seconds()

                    if wait_time > 0:
                        print(f"Lên lịch thực hiện sau {wait_time:.2f} giây...")
                        scheduler.enter(wait_time, 1, add_rule_to_camera, argument=(result,))
                        scheduler.run()
                    else:
                        print("Thời gian đã trôi qua!")
                else:
                    print(f"Phòng '{room_name}' chưa tồn tại.")

                camera_links = result["camera_links"]
                print(f"giá trị của camera_link1 : {camera_links}")
                roompy = RoomPy()
                roompy.name_room = room_name
                roompy.camera_links = camera_links
                print(f"giá trị của camera_link2 : {json.dumps(camera_links)}")
                add_roompy_to_postgresql(roompy)
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()
            except Exception as e:
                print(f"Lỗi : {e}")
                continue


def start_scheduler():
    while True:
        scheduler_x = BackgroundScheduler(timezone=timezone("Asia/Ho_Chi_Minh"))
        scheduler_x.add_job(call_api, 'cron', hour=configx.HOUR, minute=configx.MINUTE)
        # scheduler.add_job(call_api, 'date', run_date=datetime.datetime.now() + datetime.timedelta(seconds=10))
        scheduler_x.start()
        print(" Hệ thống đang chạy, chờ đến 1 giờ sáng...")
        time.sleep(10)


if __name__ == '__main__':
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler_process = Process(target=start_scheduler, daemon=True)
    scheduler_process.start()
    app.run(host="0.0.0.0", debug=False, port=5032)