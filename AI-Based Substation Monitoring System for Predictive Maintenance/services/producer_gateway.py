from fastapi import FastAPI
from pydantic import BaseModel
from kafka import KafkaProducer
import json

app = FastAPI()

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

class SensorData(BaseModel):
    temperature: float
    humidity: float
    vibration: float
    voltage: float
    timestamp: float


@app.post("/data")
def receive_data(data: SensorData):
    producer.send("sensor-topic", data.dict())
    return {"status": "sent to kafka"}