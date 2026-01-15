from fastapi import APIRouter, HTTPException
from services.kafka_service import KafkaService
import onnxruntime as ort
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    status = {"api": "healthy", "kafka": "unknown", "model": {}}

    #Check Kafka
    try:
        kafka = KafkaService()
        kafka.create_producer()
        kafka.close()
        status["kafka"] = "healthy"
    except Exception as e:
        status["kafka"] = f"unhealthy: {str(e)}"
    
    # Check model health
    models_dir = "api/exported_models"
    if os.path.exists(models_dir):
        for root, dirs, files in os.walk(models_dir):
            for file in files:
                if file.endswith(".onnx"):
                    print(root)
                    model_path = os.path.join(root, file)
                    model_name = os.path.relpath(model_path)
                    try:
                        session = ort.InferenceSession(model_path)
                        status["models"][model_name] = "healthy"
                    except Exception as e:
                        status["models"][model_name] = f"unhealthy: {str(e)}"
    else:
        status["models"] = {"error": "exported_models directory not found"}

    overall_status = 200 if (status["kafka"] == "healthy" and 
                             all(s == "healthy" for s in status["models"].values())) else 503
    return {"status": status, "code": overall_status}
        