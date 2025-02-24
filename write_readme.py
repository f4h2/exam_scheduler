json_data1 = """\n\n## Exam Schedule Example\n\n```json\n{
    "room": "sccfererd",
    "exam_date": "2025-02-24",
    "exam_time": "14:40:00"
}\n```\n"""

json_data2 = """\n\n## Room Configuration Example\n\n```json\n{
    "name_room": "sccfererd",
    "camera_links": [
        "rtsp://idg:Idg123312@123.25.21.211:554/Streaming/Channels/101/",
        "rtsp://viewer:It2@2024@123.25.190.36:553/Streaming/channels/101"
    ]
}\n```\n"""

with open("README.md", "w", encoding="utf-8") as file:
    file.write("# Sửa các giá trị HOUR và MINUTE trong file configx để lấy lịch thi ngày hôm đó \n")
    file.write("# Trước đó, cần phải thêm room và scheduler\n")
    file.write("# Ví dụ:\n\n")

    file.write("# - Thêm lịch thi: `/add-schedule`\n")
    file.write(json_data1)
    file.write("# - Thêm phòng: `/add-room`\n")
    file.write(json_data2)

