# imx500_detector.py
import time
import libcamera
import sys
from functools import lru_cache
import cv2
import numpy as np
from picamera2 import MappedArray, Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics, postprocess_nanodet_detection

class ObjectFrame:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

class IMX500Detector:
    def __init__(self, model_path="/usr/share/imx500-models/imx500_network_yolov8n_pp.rpk"):
        self.last_detections = []
        self.last_results = None
        self.zone_list: list[ObjectFrame] = []
        
        # Initialize IMX500
        self.imx500 = IMX500(model_path)
        self.intrinsics = self.imx500.network_intrinsics
                        
        if not self.intrinsics:
            self.intrinsics = NetworkIntrinsics()
            self.intrinsics.task = "object detection"
        elif self.intrinsics.task != "object detection":
            raise ValueError("Network is not an object detection task")

        # Set default labels if none provided
        if self.intrinsics.labels is None:
            with open("assets/coco_labels.txt", "r") as f:
                self.intrinsics.labels = f.read().splitlines()

        # Set additional options
        self.intrinsics.ignore_dash_labels = True
        self.intrinsics.preserve_aspect_ratio = True
        self.intrinsics.update_with_defaults()
        
        # Initialize camera
        self.picam2 = Picamera2(self.imx500.camera_num)
        
    def start(self, show_preview=True):
        """Start the detector"""
        config = self.picam2.create_preview_configuration(
            controls={"FrameRate": self.intrinsics.inference_rate}, 
            buffer_count=12
        )
        
        config["transform"] = libcamera.Transform(hflip=1, vflip=1)
        
        self.imx500.show_network_fw_progress_bar()
        self.picam2.start(config, show_preview=show_preview)
        
        if self.intrinsics.preserve_aspect_ratio:
            self.imx500.set_auto_aspect_ratio()
            
        self.picam2.pre_callback = self._draw_detections
        
    def stop(self):
        """Stop the detector"""
        self.picam2.stop()
        
    def get_detections(self):
        """Get the latest detections"""
        self.last_results = self._parse_detections(self.picam2.capture_metadata())
        return self.last_results
    
    def get_labels(self):
        """Get the list of detection labels"""
        labels = self.intrinsics.labels
        if self.intrinsics.ignore_dash_labels:
            labels = [label for label in labels if label and label != "-"]
        return labels

    def set_zone(self, x, y, w, h):
        self.zone_list.append(ObjectFrame(x,y,w,h))

    def _parse_detections(self, metadata):
        """Internal method to parse detections"""
        bbox_normalization = self.intrinsics.bbox_normalization
        threshold = 0.55
        iou = 0.65
        max_detections = 10

        np_outputs = self.imx500.get_outputs(metadata, add_batch=True)
        input_w, input_h = self.imx500.get_input_size()
        
        if np_outputs is None:
            return self.last_detections

        if self.intrinsics.postprocess == "nanodet":
            boxes, scores, classes = postprocess_nanodet_detection(
                outputs=np_outputs[0], 
                conf=threshold, 
                iou_thres=iou,
                max_out_dets=max_detections
            )[0]
            from picamera2.devices.imx500.postprocess import scale_boxes
            boxes = scale_boxes(boxes, 1, 1, input_h, input_w, False, False)
        else:
            boxes, scores, classes = np_outputs[0][0], np_outputs[1][0], np_outputs[2][0]
            if bbox_normalization:
                boxes = boxes / input_h
            boxes = np.array_split(boxes, 4, axis=1)
            boxes = zip(*boxes)

        self.last_detections = [
            Detection(box, category, score, metadata, self.imx500, self.picam2)
            for box, score, category in zip(boxes, scores, classes)
            if score > threshold
        ]
        return self.last_detections

    def _draw_detections(self, request, stream="main"):
        """Internal method to draw detections"""
        if self.last_results is None:
            return
            
        labels = self.get_labels()
        with MappedArray(request, stream) as m:
            cv2.rectangle(m.array, (self.zone_list[0].x, self.zone_list[0].y), (self.zone_list[0].x + self.zone_list[0].w, self.zone_list[0].y + self.zone_list[0].h), (255, 255, 0, 0), thickness=5)
            for detection in self.last_results:
                x, y, w, h = detection.box
                label = labels[int(detection.category)]
                target = ObjectFrame(x,y,w,h)

                if label == "bottle":
                        (text_width, text_height), baseline = cv2.getTextSize(
                            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                        )
                        text_x = x
                        text_y = y - 10

                        # HACK
                        zone = self.zone_list[0]
                        if self.is_in_danger(target, zone) > 50:
                                cv2.putText(
                                        m.array, "Warning!", (text_x, text_y),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1
                                        )
                                cv2.rectangle(m.array, (x, y), (x + w, y + h), (255, 0, 0, 0), thickness=5)
                        else:
                                cv2.rectangle(m.array, (x, y), (x + w, y + h), (0, 255, 0, 0), thickness=2)
    
    def is_in_danger(self, target: ObjectFrame, area: ObjectFrame) -> float:
            # Calculate the edges of the object
            object_left = target.x
            object_top = target.y
            object_right = target.x + target.w
            object_bottom = target.y + target.h

            # Calculate the edges of the area
            area_left = area.x
            area_top = area.y
            area_right = area.x + area.w
            area_bottom = area.y + area.h

            # Find overlap boundaries
            overlap_left = max(object_left, area_left)
            overlap_top = max(object_top, area_top)
            overlap_right = min(object_right, area_right)
            overlap_bottom = min(object_bottom, area_bottom)

            # Calculate overlap dimensions
            overlap_width = max(0, overlap_right - overlap_left)
            overlap_height = max(0, overlap_bottom - overlap_top)

            # Calculate overlap area
            overlap_area = overlap_width * overlap_height
            object_area = target.w * target.h

            # Avoid division by zero
            if object_area == 0:
                return 0.0

            # Return percentage overlap
            print(f"{object_area / overlap_area *100}%")
            return object_area / overlap_area *100

class Detection:
    def __init__(self, coords, category, conf, metadata, imx500, picam2):
        """Create a Detection object, recording the bounding box, category and confidence."""
        self.category = category
        self.conf = conf
        self.box = imx500.convert_inference_coords(coords, metadata, picam2)
