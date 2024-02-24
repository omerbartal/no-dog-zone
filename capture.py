print('import cv2')
import cv2
from PIL import Image

import glob
import os

import threading

import timing
import time

from params import params, save_params
from params import lock as params_lock

import numpy as np

from log import logger

FPS = 32
VIDEO_LENGTH = 30
VIDEO_BUFFER_SIZE = 20

class Timer:
    def __init__(self, rate):
        self.rate = rate
        self.next_timing = None

    def sleep(self):
        if self.next_timing is None:
            self.next_timing = time.time()
        else:
            sleep_time = max([0, self.next_timing - time.time()])
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.next_timing += (1/self.rate)
        if time.time() >= self.next_timing:
            self.next_timing = time.time() + (1/self.rate)
        

class ImageSource:
    def __init__(self, src):
        self.src = src

        if src == 'v4l2':

            self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
            # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 224)
            # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 224)
            self.cap.set(cv2.CAP_PROP_FPS, FPS)

        elif src == 'mac':

            self.cap = cv2.VideoCapture(0)
            # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 224)
            # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 224)
            self.cap.set(cv2.CAP_PROP_FPS, FPS)
            
        else:

            self.images = []

            for fn in glob.iglob(src):
                print(f'loading {fn}')
                self.images.append(cv2.imread(fn))

            self.curr_image = 0
            self.next_timing = None

    def capture(self):

        if self.src in ['mac', 'v4l2']:
            ret, image = self.cap.read()
            if not ret:
                raise RuntimeError("failed to read frame")
            timing.event('capture')
            return image
        
        if self.next_timing is None:
            self.next_timing = time.time()
        else:
            sleep_time = max([0, self.next_timing - time.time()])
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.next_timing += (1/FPS)
        if time.time() >= self.next_timing:
            timing.event('frame loss')
            self.next_timing = time.time() + (1/FPS)
            
        timing.event('capture')
        ret = self.images[self.curr_image]

        self.curr_image = (self.curr_image + 1) % len(self.images)

        return ret
            

class ImageAdaptation:

    scaled_resolution = None
    
    def __init__(self, base_image):
        self.base_image = base_image
        self.processed = False
        self.lock = threading.Lock()

    def fix_scale(self, width, height):

        with params_lock:
            scale_width = params['scale_end_x'] - params['scale_start_x']
            scale_height = params['scale_end_y'] - params['scale_start_y']

            if scale_width != scale_height:
                scale_width = scale_height
            
            if scale_width > width or scale_height > height:
                scale_width = min([width, height])
                scale_height = min([width, height])

            params['scale_end_x'] = params['scale_start_x'] + scale_width
            params['scale_end_y'] = params['scale_start_y'] + scale_height
                
            if params['scale_start_x'] < 0:
                params['scale_start_x'] = 0
                params['scale_end_x'] = params['scale_start_x'] + scale_width

            if params['scale_start_y'] < 0:
                params['scale_start_y'] = 0
                params['scale_end_y'] = params['scale_start_y'] + scale_height

            if params['scale_end_x'] >= width:
                params['scale_end_x'] = width
                params['scale_start_x'] = params['scale_end_x'] - scale_width

            if params['scale_end_y'] >= height:
                params['scale_end_y'] = height
                params['scale_start_y'] = params['scale_end_y'] - scale_height

            params['hide_top'] = [max([min([x, scale_height]), 0]) for x in params['hide_top']]
            params['hide_bottom'] = [max([min([x, scale_height]), 0]) for x in params['hide_bottom']]
            params['hide_left'] = [max([min([x, scale_width]), 0]) for x in params['hide_left']]
            params['hide_right'] = [max([min([x, scale_width]), 0]) for x in params['hide_right']]
                
    def _import_params(self):
        with params_lock:
            self.x1 = params['scale_start_x']
            self.y1 = params['scale_start_y']
            self.x2 = params['scale_end_x']
            self.y2 = params['scale_end_y']
            self.scale_start = (self.x1, self.y1)
            self.scale_end = (self.x2, self.y2)

            self.hide_top = params['hide_top']
            self.hide_left = params['hide_left']
            self.hide_right = params['hide_right']
            self.hide_bottom = params['hide_bottom']
        
    def process(self):

        with self.lock:
            if self.processed:
                return
            
            height, width, channels = self.base_image.shape
            self.fix_scale(width, height)
            self._import_params()
            
            self.marked = self.base_image.copy()

            cv2.rectangle(self.marked, self.scale_start, self.scale_end, (255,0,0), 5)
            
            self.cropped = self.base_image[self.y1:self.y2, self.x1:self.x2]

            self.hidden = self.cropped.copy()

            for img, x1, y1, x2, y2, color in [
                    [self.marked, self.x1, self.y1, self.x2, self.y2, (255, 0, 0)],
                    [self.hidden, 0, 0, self.x2 - self.x1, self.y2 - self.y1, (255,255,255)]
                    ]:
                
                cv2.fillPoly(img, [np.array([[x1,y1], [x1, y1 + self.hide_top[0]], [x2, y1 + self.hide_top[1]], [x2, y1]])], color)
                cv2.fillPoly(img, [np.array([[x1,y2], [x1, y2 - self.hide_bottom[0]], [x2, y2 - self.hide_bottom[1]], [x2, y2]])], color)

                cv2.fillPoly(img, [np.array([[x1,y1], [x1 + self.hide_left[0], y1], [x1 + self.hide_left[1], y2], [x1, y2]])], color)
                cv2.fillPoly(img, [np.array([[x2,y1], [x2 - self.hide_right[0], y1], [x2 - self.hide_right[1], y2], [x2, y2]])], color)
                
            
            # print('scaling')
            if self.scaled_resolution is None:
                self.scaled = None
                self.scaled_rgb = None

            else:
                self.scaled = cv2.resize(self.hidden, self.scaled_resolution, interpolation = cv2.INTER_AREA)

                ### cv2.imshow("Resized image", resized)

                # print('formatting image')

                # convert opencv output from BGR to RGB
                self.scaled_rgb = self.scaled[:, :, [2, 1, 0]]

            self.processed = True

fourcc = cv2.VideoWriter_fourcc(*'MJPG')
video_ext = 'avi'
# fourcc = cv2.VideoWriter_fourcc(*"XVID")
# fourcc = cv2.VideoWriter_fourcc(*"MPV4")
            
class VideoStore:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.start_time = None
        self.curr_video = None
        self.filename = None
        self.temp_filename = None

        if not os.path.exists(os.path.join(self.base_dir, 'temp')):
            os.mkdir(os.path.join(self.base_dir, 'temp'))

        os.system(f"rm -f {os.path.join(self.base_dir, 'temp')}/*.{video_ext}")
        
    def start(self, image, labels):
        height, width, channels = image.shape

        base_name = time.strftime('%Y-%m-%d %H-%M-%S') + '_' + ('_'.join([x for x in labels])) + '.' + video_ext
        
        self.filename = os.path.join(self.base_dir, base_name)
        self.temp_filename = os.path.join(self.base_dir, 'temp', base_name)

        fps = params.get('video_fps', FPS)
        logger.info(f'saving video to {self.filename}, resolution {(width, height, channels)}, fps {fps}')
        
        self.curr_video = cv2.VideoWriter(self.temp_filename, 
                                          fourcc,
                                          fps, (height, width))



        self.start_time = time.time()

    def stop(self, hard=False):
        if self.curr_video is None:
            return

        self.curr_video.release()
        if hard:
            os.remove(self.temp_filename)
        else:
            os.rename(self.temp_filename, self.filename)
        self.curr_video = None
        self.start_time = None
        self.filename = None
        self.temp_filename = None

    def store(self, image, labels):

        if self.start_time is not None:
            if time.time() >= self.start_time + VIDEO_LENGTH:
                self.stop()
                params['video_fps'] = int(timing.stats('video'))
                save_params()

        if self.curr_video is None:
            self.start(image, labels)

        timing.event('video')
        
        height, width, channels = image.shape
        image = cv2.putText(image, ', '.join([x for x in labels]), (0, height-24), cv2.FONT_HERSHEY_SIMPLEX, 
                            0.4, (255, 0, 0), 1, cv2.LINE_AA)

        image = cv2.putText(image, time.strftime('%Y-%m-%d %H:%M:%S'), (0, height-8), cv2.FONT_HERSHEY_SIMPLEX, 
                            0.3, (255, 0, 0), 1, cv2.LINE_AA)

        
        self.curr_video.write(image)

class CaptureIter:
    def __init__(self, image_type):
        self.image_adaptation = None
        self.image_type = image_type
        
    def __iter__(self):
        return self

    def __next__(self):
        if not cap_thread.running:
            raise StopIteration()

        it = self.image_type
        
        if it in ['inferred']:
            import detect
            
            while self.image_adaptation is detect.detections.image:
                time.sleep(0.1)

            self.image_adaptation = detect.detections.image
            return detect.detections.image
                
        else:
            while self.image_adaptation is cap_thread.image_adaptation:
                time.sleep(0.1)

            self.image_adaptation = cap_thread.image_adaptation
            if it != 'base_image':
                self.image_adaptation.process()
            return getattr(self.image_adaptation, it)
        
class Capture(threading.Thread):
    def __init__(self, src):
        self.image_src = ImageSource(src)
        self.image_adaptation = None

        super(Capture, self).__init__()
        self.daemon = True
        self.running = True
        self.start()

    def run(self):
        logger.info('starting to capture')

        try:
        
            while True:
                img = ImageAdaptation(self.image_src.capture())
                
                self.image_adaptation = img

        finally:
            self.running = False


class VideoThread(threading.Thread):
    def __init__(self, video_base_dir):
        super(VideoThread, self).__init__()
        self.to_store_video = False
        self.video_store = VideoStore(video_base_dir)
        self.daemon = True
        self.buffered = []
        self.labels = set()
        self.lock = threading.Lock()
        self.timer = Timer(params.get('video_fps', FPS))
        self.start()

    def start_recording_video(self, label):
        if not self.to_store_video:
            logger.info('starting to store video')
        self.labels.add(label)
        self.to_store_video = True

    def stop_recording_video(self, hard=False):
        if self.to_store_video:
            logger.info('stopping to store video')

        self.labels = set()
            
        if hard:
            with self.lock:
                self.video_store.stop(hard=True)
                self.to_store_video = False
                self.buffered = []
        else:
            self.to_store_video = False

    def store(self, image):
        self.video_store.store(image, self.labels)
            
    def run(self):
        self.capture_iter = images('hidden')
        for image in self.capture_iter:
            with self.lock:
                if self.to_store_video:
                    while self.buffered:
                        self.store(self.buffered.pop(0))

                    self.store(image)

                else:
                    self.video_store.stop()

                    self.timer.rate = params.get('video_fps', FPS)
                    self.timer.sleep()

                    timing.event('video_buffer')
                    
                    self.buffered.append(image)
                    while len(self.buffered) > VIDEO_BUFFER_SIZE:
                        self.buffered.pop(0)
                
        
            
cap_thread = None
video_thread = None
def start(src, video_base_dir):
    global cap_thread
    global video_thread
    
    if cap_thread is not None:
        return

    cap_thread = Capture(src)
    video_thread = VideoThread(video_base_dir)

# def get_image():
#     cap_thread.image_adaptation.process()
#     return cap_thread.image_adaptation

def is_running():
    if cap_thread is None:
        return False
    
    return cap_thread.running

def images(image_type):
    return CaptureIter(image_type)

def start_recording_video(*p, **d):
    video_thread.start_recording_video(*p, **d)

def stop_recording_video(*p, **d):
    video_thread.stop_recording_video(*p, **d)

    
