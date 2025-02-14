# After the model is trained, model_final.pth is generated in the output file.
import os
import cv2
import random
import detectron2
import numpy as np
from detectron2.utils.logger import setup_logger

setup_logger()

from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.engine import DefaultTrainer, DefaultPredictor
from detectron2.data import MetadataCatalog, DatasetCatalog
from detectron2.utils.visualizer import Visualizer
from detectron2.data.datasets import register_coco_instances
import matplotlib.pyplot as plt


class FishRecogModel():
    def __init__(self, mode='train'):
        if mode == 'train':
            self.cfg = get_cfg()
            self.register_coco()
            self.model_config()
            self.train()
        elif mode == 'use':
            self.cfg = get_cfg()
            self.predictor = self.load_model()

    def register_coco(self):
        img_path = r"./../labelme/dataset"
        json_path = r"./trainval.json"

        register_coco_instances("fishdata", {}, json_path, img_path)
        fishdata_metadata = MetadataCatalog.get("finshdata")
        dataset_dicts = DatasetCatalog.get("fishdata")
        print("Register Successul, Metadata: " + str(fishdata_metadata))

        for d in random.sample(dataset_dicts, 3):
            img = cv2.imread(d["file_name"])
            visualizer = Visualizer(img[:, :, ::-1], metadata=fishdata_metadata, scale=0.5)
            vis = visualizer.draw_dataset_dict(d)
            cv2.imshow('train', vis.get_image()[:, :, ::-1])
            cv2.waitKey(0)
        cv2.destroyAllWindows()

    def model_config(self):
        # write the model configuration by using the mask-rcnn model
        # first load the pre-trained model from github
        self.cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
        self.cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
        self.cfg.DATASETS.TRAIN = ("fishdata",)
        self.cfg.DATASETS.TEST = ()
        self.cfg.MODEL.ROI_HEADS.NUM_CLASSES = 5  # number of class (exclude background)
        self.cfg.DATALOADER.NUM_WORKERS = 0
        self.cfg.SOLVER.IMS_PER_BATCH = 2  # image per gpu
        self.cfg.SOLVER.BASE_LR = 0.0001
        self.cfg.SOLVER.MAX_ITER = 100  # 12 epochs，

    def train(self):
        os.makedirs(self.cfg.OUTPUT_DIR, exist_ok=True)
        trainer = DefaultTrainer(self.cfg)
        trainer.resume_or_load(resume=False)
        trainer.train()

    def load_model(self):
        try:
            self.cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
            self.cfg.MODEL.ROI_HEADS.NUM_CLASSES = 5
            self.cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.8
            self.cfg.MODEL.WEIGHTS = os.path.join(self.cfg.OUTPUT_DIR, "model_final.pth")

            return DefaultPredictor(self.cfg)
        except:
            print('There is no model exist, please train the model first.')
            return -1

    def predict(self, frame):
        try:
            outputs = self.predictor(frame)
            # print position info
            result = self.fish_position(outputs)
            print(result)
            # draw the mask
            v = self.draw_predict_position(frame, outputs)
            print(len(outputs['instances']))

            img = v.get_image()[:, :, ::-1]
            img = cv2.resize(img, (960, 540))
            cv2.imshow('frame', img)

            return v.get_image()[:, :, ::-1]
        except:
            print('Please load the model first.')

    def fish_position(self, outputs):
        # the rough position of the fish
        result_txt = ''
        if len(outputs['instances'].pred_boxes) > 1:
            pred_boxes = np.asarray(outputs['instances'].pred_boxes.to("cpu"))
            class_ids = np.asarray(outputs['instances'].pred_classes.to("cpu"))
            fish_head_txt = ''
            fish_body_txt = ''
            fish_txt = ''
            fish_mouse_txt = ''
            finger_txt = ''

            fish_mouse_bbox_area = 0
            for i in range(len(pred_boxes)):
                y_middle = round((pred_boxes[i][3].item() + pred_boxes[i][1].item()) / 2)
                x_middle = round((pred_boxes[i][2].item() + pred_boxes[i][0].item()) / 2)

                if class_ids[i] == 0:
                    fish_head_txt = 'Fish Head Pos: (' + str(x_middle) + ',' + str(y_middle) + ')\n'
                elif class_ids[i] == 1:
                    fish_body_txt = 'Fish Body Pos: (' + str(x_middle) + ',' + str(y_middle) + ')\n'
                elif class_ids[i] == 2:
                    fish_txt = 'Fish Pos: (' + str(x_middle) + ',' + str(y_middle) + ')\n'
                elif class_ids[i] == 3:
                    fish_mouse_txt = 'Fish Mouse Pos: (' + str(x_middle) + ',' + str(y_middle) + ')\n'
                    fish_mouse_bbox_area = round(
                        abs((pred_boxes[i][3].item() - pred_boxes[i][1].item())) *
                        abs((pred_boxes[i][2].item() - pred_boxes[i][0].item()))
                    )
                elif class_ids[i] == 4:
                    finger_txt = 'Finger Pos: (' + str(x_middle) + ',' + str(y_middle) + ')\n'

            # check tired
            if 0 not in class_ids and 4 in class_ids:
                # todo: say something
                aaa = 1

            # check hungry
            if fish_mouse_bbox_area > 10000 and 4 in class_ids:
                # todo: say something
                aaa = 1

            result_txt = fish_txt + fish_head_txt + fish_body_txt + fish_mouse_txt + finger_txt
        return result_txt

    def draw_predict_position(self, frame, outputs):
        v = Visualizer(frame[:, :, ::-1], scale=1)
        v = v.draw_instance_predictions(outputs["instances"].to("cpu"))
        return v


if __name__ == "__main__":
    # train model
    # model = FishRecogModel("train")
    # load model
    model = FishRecogModel("use")
    model.register_coco()

    cap = cv2.VideoCapture('fish_hungry.mp4')  # loading video place
    while (True):
        ret, frame = cap.read()
        model.predict(frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
