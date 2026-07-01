import os
import sys
import yaml

from gradeVision.utils.main_utils import read_yaml_file
from gradeVision.logger import logging
from gradeVision.exception import AppException
from gradeVision.entity.config_entity import ModelTrainerConfig
from gradeVision.entity.artifacts_entity import ModelTrainerArtifact


class ModelTrainer:
    def __init__(self, model_trainer_config: ModelTrainerConfig):
        self.model_trainer_config = model_trainer_config

    def initiate_model_trainer(self) -> ModelTrainerArtifact:
        logging.info("Entered initiate_model_trainer method of ModelTrainer class")
        try:
            logging.info("Unzipping data")
            os.system("unzip data.zip")
            os.system("rm -f data.zip")

            with open("data.yaml", "r") as stream:
                num_classes = str(yaml.safe_load(stream)["nc"])

            model_config_file_name = self.model_trainer_config.weight_name.split(".")[0]
            config = read_yaml_file(f"yolov5/models/{model_config_file_name}.yaml")
            config["nc"] = int(num_classes)

            with open(f"yolov5/models/custom_{model_config_file_name}.yaml", "w") as f:
                yaml.dump(config, f)

            os.system(
                f"cd yolov5/ && python train.py "
                f"--img {self.model_trainer_config.image_size} "
                f"--batch {self.model_trainer_config.batch_size} "
                f"--epochs {self.model_trainer_config.no_epochs} "
                f"--data ../data.yaml "
                f"--cfg ./models/custom_{model_config_file_name}.yaml "
                f"--weights {self.model_trainer_config.weight_name} "
                f"--name gradevisio n_results  --cache"
            )

            os.system("cp yolov5/runs/train/gradevisio n_results/weights/best.pt yolov5/")
            os.makedirs(self.model_trainer_config.model_trainer_dir, exist_ok=True)
            os.system(
                f"cp yolov5/runs/train/gradevisio n_results/weights/best.pt "
                f"{self.model_trainer_config.model_trainer_dir}/"
            )

            os.system("rm -rf yolov5/runs")
            os.system("rm -rf train valid data.yaml")

            model_trainer_artifact = ModelTrainerArtifact(
                trained_model_file_path="yolov5/best.pt",
            )
            logging.info("Exited initiate_model_trainer method of ModelTrainer class")
            logging.info(f"Model trainer artifact: {model_trainer_artifact}")
            return model_trainer_artifact
        except Exception as e:
            raise AppException(e, sys)
