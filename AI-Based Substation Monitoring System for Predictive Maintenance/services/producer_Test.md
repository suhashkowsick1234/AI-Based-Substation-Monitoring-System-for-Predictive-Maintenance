Test Without ESP32 (Important)

Open new terminal (paste below code):
```
curl -X POST http://127.0.0.1:8000/data ^
-H "Content-Type: application/json" ^
-d "{\"temperature\":30,\"humidity\":50,\"vibration\":1.2,\"voltage\":220,\"timestamp\":123456}"
```
Expected response:
```
{"status":"sent to kafka"}
```