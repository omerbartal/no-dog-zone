import cv2
import argparse
import numpy as np
import timing  

# https://towardsdatascience.com/yolo-object-detection-with-opencv-and-python-21e50ac599e9
# https://github.com/arunponnusamy/object-detection-opencv
# https://raw.githubusercontent.com/arunponnusamy/object-detection-opencv/master/yolov3.txt

class DetectYolo3:
    image_type = 'scaled'
    resolution = (416, 416)
    
    def __init__(self):

        self.classes = None

        print('loading classes')
        with open('yolo3/yolov3.txt', 'r') as f:
            self.classes = [line.strip() for line in f.readlines()]

        self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))

        print('loading net')
        self.net = cv2.dnn.readNet('yolo3/yolov3.weights', 'yolo3/yolov3.cfg')

    def get_output_layers(self):

        layer_names = self.net.getLayerNames()
        try:
            output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
        except:
            output_layers = [layer_names[i[0] - 1] for i in self.net.getUnconnectedOutLayers()]

        return output_layers


    def draw_prediction(self, img, class_id, confidence, x, y, x_plus_w, y_plus_h):

        label = str(self.classes[class_id])

        color = self.colors[class_id]

        cv2.rectangle(img, (x,y), (x_plus_w,y_plus_h), color, 2)

        cv2.putText(img, label, (x-10,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        
    def infer(self, image):

        image = image.copy()
        
        Width = image.shape[1]
        Height = image.shape[0]
        scale = 0.00392
        
        blob = cv2.dnn.blobFromImage(image, scale, (416,416), (0,0,0), True, crop=False)

        self.net.setInput(blob)

        outs = self.net.forward(self.get_output_layers())

        class_ids = []
        confidences = []
        boxes = []
        conf_threshold = 0.5
        nms_threshold = 0.4

        detected = {}
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]

                detected[str(self.classes[class_id])] = confidence
                
                if confidence > 0.5:
                    center_x = int(detection[0] * Width)
                    center_y = int(detection[1] * Height)
                    w = int(detection[2] * Width)
                    h = int(detection[3] * Height)
                    x = center_x - w / 2
                    y = center_y - h / 2
                    class_ids.append(class_id)
                    confidences.append(float(confidence))
                    boxes.append([x, y, w, h])
                    
        import detect
        detect.detections.add(detected)


        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)

        for i in indices:
            try:
                box = boxes[i]
            except:
                i = i[0]
                box = boxes[i]

            x = box[0]
            y = box[1]
            w = box[2]
            h = box[3]
            self.draw_prediction(image, class_ids[i], confidences[i], round(x), round(y), round(x+w), round(y+h))
    
        detect.detections.add_image(image)

        timing.event('inference')

# https://github.com/Asadullah-Dal17/yolov4-opencv-python/blob/master/yolov4.py

class DetectYolo4Tiny:
    image_type = 'scaled'
    resolution = (416, 416)
    
    def __init__(self):

        print('loading classes')
        self.class_name = []
        with open('yolo4tiny/classes.txt', 'r') as f:
            self.class_name = [cname.strip() for cname in f.readlines()]
            
        print('loading net')
        self.net = cv2.dnn.readNet('yolo4tiny/yolov4-tiny.weights', 'yolo4tiny/yolov4-tiny.cfg')

        self.model = cv2.dnn_DetectionModel(self.net)
        self.model.setInputParams(size=(416, 416), scale=1/255, swapRB=True)
        
    def infer(self, image):

        image = image.copy()

        Conf_threshold = 0.4
        NMS_threshold = 0.4

        COLORS = [(0, 255, 0), (0, 0, 255), (255, 0, 0),
                  (255, 255, 0), (255, 0, 255), (0, 255, 255)]

        detected = {}

        classes, scores, boxes = self.model.detect(image, Conf_threshold, NMS_threshold)
        for (classid, score, box) in zip(classes, scores, boxes):

            detected[self.class_name[classid]] = float(score)
            
            color = COLORS[int(classid) % len(COLORS)]
            label = "%s : %f" % (self.class_name[classid], score)
            cv2.rectangle(image, box, color, 1)
            cv2.putText(image, label, (box[0], box[1]-10),
                       cv2.FONT_HERSHEY_COMPLEX, 0.3, color, 1)

        import detect
        detect.detections.add(detected)

        detect.detections.add_image(image)

        timing.event('inference')
        
Detect = DetectYolo4Tiny
