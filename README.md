# Sửa các giá trị HOUR và MINUTE trong file configx để lấy lịch thi ngày hôm đó 
# Trước đó, cần phải thêm room và scheduler
# Ví dụ:

# - Thêm lịch thi: `/add-schedule`


## Exam Schedule Example

```json
{
    "room": "sccfererd",
    "exam_date": "2025-02-24",
    "exam_time": "14:40:00"
}
```
# - Thêm phòng: `/add-room`


## Room Configuration Example

```json
{
    "name_room": "sccfererd",
    "camera_links": [
        "rtsp://idg:Idg123312@123.25.21.211:554/Streaming/Channels/101/",
        "rtsp://viewer:It2@2024@123.25.190.36:553/Streaming/channels/101"
    ]
}
```
