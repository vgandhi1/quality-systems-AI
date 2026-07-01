ARTIFACTS_DIR: str = "artifacts"

# Data Ingestion
DATA_INGESTION_DIR_NAME: str = "data_ingestion"
DATA_INGESTION_FEATURE_STORE_DIR: str = "feature_store"
DATA_DOWNLOAD_URL: str = "https://drive.google.com/file/d/YOUR_DATASET_FILE_ID/view?usp=share_link"

# Data Validation
DATA_VALIDATION_DIR_NAME: str = "data_validation"
DATA_VALIDATION_STATUS_FILE = "status.txt"
DATA_VALIDATION_ALL_REQUIRED_FILES = ["train", "valid", "data.yaml"]

# Model Trainer
MODEL_TRAINER_DIR_NAME: str = "model_trainer"
MODEL_TRAINER_PRETRAINED_WEIGHT_NAME: str = "yolov5s.pt"
MODEL_TRAINER_NO_EPOCHS: int = 50
MODEL_TRAINER_BATCH_SIZE: int = 16
MODEL_TRAINER_IMAGE_SIZE: int = 640

# Detection categories
DETECTION_CATEGORIES = {
    "clothing": ["tear", "stain", "missing_button", "deformation", "color_fade"],
    "boxes": ["crush", "wetness", "tear", "broken_seal", "mold"],
    "electronics": ["screen_crack", "dent", "burn", "liquid_damage", "bent_port"],
    "auto_components": ["rust", "deformation", "cracks", "surface_damage", "corrosion"],
}
