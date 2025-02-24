from datetime import datetime

import psycopg2
from psycopg2.extras import DictCursor

from db.Exam_schedule import ExamSchedule
from db.Room import Room
import json
from flask import Blueprint, logging, jsonify, request
import copy
from configx import configx

rtsp_hls = Blueprint('rtsp_hls', __name__)
RESPONSE = {
    "status": "OK",
    "version": "ccvss",
    "message":"xxcvc"
}


def get_db_connection():
    return psycopg2.connect(
        dbname=configx.POSTGRES_DB,
        user=configx.POSTGRES_USER,
        password=configx.POSTGRES_PASSWORD,
        host=configx.POSTGRES_HOST,
        port=configx.POSTGRES_PORT
    )



###### add room

def add_room_to_postgresql(room):
    try:
        with get_db_connection() as connection:
            with connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS Rooms (
                        id SERIAL PRIMARY KEY,
                        name_room TEXT NOT NULL,
                        camera_links TEXT NOT NULL,
                        UNIQUE (name_room, camera_links)
                    )
                ''')
                connection.commit()

                cursor.execute('''
                    INSERT INTO Rooms (name_room, camera_links)
                    VALUES (%s, %s)
                    ON CONFLICT (name_room, camera_links) DO NOTHING
                    RETURNING id
                ''', (room.name_room, json.dumps(room.camera_links)))

                result = cursor.fetchone()
                connection.commit()

                if result:
                    return {
                        "status": "success",
                        "message": "room added successfully",
                        "room_id": result["id"]
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Room already exists"
                    }

    except Exception as e:
        print(f"PostgreSQL error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


@rtsp_hls.route("/add-room", methods=['POST'])
def add_exam_room():
    try:
        content = request.data
        r_dict = json.loads(content.decode('utf-8'))
        res = copy.deepcopy(RESPONSE)

        room = Room()
        room.name_room = r_dict.get("name_room", None)
        room.camera_links = r_dict.get("camera_links", [])

        add_room_to_postgresql(room)

        res["status"] = "success"
        res["message"] = "Room schedule added successfully"
        res["data"] = room.to_dict()

        return jsonify(res)

    except Exception as e:
        res = copy.deepcopy(RESPONSE)
        res["message"] = str(e)
        return jsonify(res), 400




########## add schedule

def add_schedule_to_postgresql(examSchedule):
    try:
        with get_db_connection() as connection:
            with connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ExamSchedules (
                        id SERIAL PRIMARY KEY,
                        room TEXT,
                        exam_date TEXT,
                        exam_time TEXT,
                        UNIQUE (room, exam_date,exam_time )
                    )
                ''')
                connection.commit()

                cursor.execute('''
                    INSERT INTO ExamSchedules (room, exam_date, exam_time)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (room, exam_date, exam_time) DO NOTHING
                    RETURNING id
                ''', (
                    examSchedule.room, examSchedule.exam_date, examSchedule.exam_time
                ))

                schedule = cursor.fetchone()
                connection.commit()

                if schedule:
                    return {
                        "status": "success",
                        "message": "schedule added successfully",
                        "room_id": schedule["id"]
                    }
                else:
                    return {
                        "status": "error",
                        "message": "schedule already exists"
                    }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@rtsp_hls.route("/add-schedule", methods=['POST'])
def add_exam_schedule():
    try:
        content = request.data
        r_dict = json.loads(content.decode('utf-8'))
        res = copy.deepcopy(RESPONSE)

        examSchedule = ExamSchedule()
        examSchedule.room = r_dict.get("room", None)
        examSchedule.exam_date = r_dict.get("exam_date", None)
        examSchedule.exam_time = r_dict.get("exam_time", None)

        add_schedule_to_postgresql(examSchedule)

        res["status"] = "success"
        res["message"] = "Exam schedule added successfully"
        res["data"] = examSchedule.to_dict()

        return jsonify(res)

    except Exception as e:
        res = copy.deepcopy(RESPONSE)
        res["message"] = str(e)
        return jsonify(res), 400


@rtsp_hls.route("/get-schedule-by-time", methods=['GET'])
def exam_schedule():
    try:
        today_date = datetime.today().strftime('%Y-%m-%d')

        with get_db_connection() as connection:
            with connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("SELECT * FROM ExamSchedules WHERE exam_date = %s", (today_date,))
                results = cursor.fetchall()

        return jsonify(results), 200

    except Exception as e:
        print(f"Lỗi kết nối database: {e}")
        return jsonify([]), 500
