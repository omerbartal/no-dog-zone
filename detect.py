import threading
import time
from params import params
import json
import os
import subprocess
import select
import datetime
import telegram_bot
import timing

from log import logger

# model = 'pytorch'
model = 'yolo'

INFERENCE_WINDOW_TIME = 5

class DetectedClasses:
    def __init__(self):
        self.window = []
        self.lock = threading.Lock()
        self.image = None
        self.past_dog_detections = []

    def add(self, curr):

        metadata = {'ts':time.time(), 'dt':datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'), 'model':model, 'detection':curr}
                
        with self.lock:

            # used for the ui only
            
            self.window.append({'time':time.time(), 'detections':curr})

            self.window = [x for x in self.window if x['time'] >= time.time() - INFERENCE_WINDOW_TIME]


        if curr.get('person', 0) > 0.2:
            timing.event('person')
            trigger.hard_stop()

        self.past_dog_detections.append(curr.get('dog', 0))
        self.past_dog_detections = self.past_dog_detections[-5:]

        metadata['history'] = self.past_dog_detections
        if ( (len([x for x in self.past_dog_detections if x > 0.4]) >= 3) ):
            timing.event('dog')
            if ( (len([x for x in self.past_dog_detections if x > 0.6]) >= 1) ):
                metadata['audio'] = True
                trigger.trigger('dog', start_audio=True, metadata=metadata)
            else:
                metadata['audio'] = False
                trigger.trigger('dog', start_audio=False, metadata=metadata)
            
        # if curr.get('797 sleeping bag', 0) > 0.2:
        #     trigger.trigger('sleeping bag')            

        if params['store_inference']:
            with open(os.path.join(params['output_path'], 'inference.json'), 'a') as f:
                f.write(json.dumps(metadata) + '\n')
        
    def get(self):
        with self.lock:
            if not self.window:
                return {}

            classes = []
            for w in self.window:
                classes.extend([k for k in w['detections'].keys()])

            classes = set(classes)

            ret = {c:{'all':[]} for c in classes}
            for w in self.window:
                for c in classes:
                    if c in w['detections']:
                        ret[c]['all'].append(w['detections'][c])


            for c in classes:
                ret[c]['avg'] = sum(ret[c]['all']) / len(self.window)
                ret[c]['max'] = max(ret[c]['all'])

            return ret

    def add_image(self, image):
        self.image = image
                
detections = DetectedClasses()


inference_thread = None
inference_obj = None
Detect = None

def inference_thread_fn():
    global inference_obj

    while True:
        if not params['inference']:
            time.sleep(1)
            continue
    
        import detect

        if model == 'yolo':
            import detect_yolo as detect_model
        elif model == 'pytorch':
            import detect_pytorch as detect_model
        else:
            raise NotImplementedError(f'unknown model {model}')

        global Detect
        Detect = detect_model.Detect
        
        if inference_obj is None:
            inference_obj = detect.Detect()

        import capture
        capture.ImageAdaptation.scaled_resolution = detect.Detect.resolution
            
        for image in capture.images(detect.Detect.image_type):
            if image is None:
                continue

            try:
                inference_obj.infer(image)
            except Exception:
                logger.exception('infer failed')
                continue

            if not params['inference']:
                break
            
def start_inference():
    global inference_thread

    if inference_thread is not None:
        return
    
    inference_thread = threading.Thread(target=inference_thread_fn)
    inference_thread.daemon = True
    inference_thread.start()


    
class PostponedTimer:
    def __init__(self, postpone_time):
        self.postpone_time = postpone_time
        self.end_time = None

    def postpone(self):
        # logger.debug(f'postponing {self.postpone_time} seconds')
        self.end_time = time.time() + self.postpone_time
            
    def is_active(self):
        if self.end_time is None:
            return False
        
        ret = time.time() < self.end_time
        if not ret:
            self.end_time = None
        # else:
        #     logger.debug(f'{self.end_time - time.time()} seconds left')
            
        return ret

    def stop(self):
        self.end_time = None

class GPIO:
    def __init__(self, pin):
        self.pin = pin
        self.init_done = False
        self.base_dir = f'/sys/class/gpio/gpio{self.pin}'
        self.lock = threading.Lock()

    def do_init(self):
        with self.lock:
            if self.init_done:
                return
            try:
                if not os.path.exists(self.base_dir):
                    open('/sys/class/gpio/export', 'w').write(str(self.pin))
                open(self.base_dir + '/direction', 'w').write('out')
                self.init_done = True
            except Exception:
                logger.exception('failed gpio init')

    def set(self, value):
        self.do_init()
        if self.init_done:
            try:
                open(self.base_dir + '/value', 'w').write(str(value))
            except Exception:
                logger.exception('failed gpio init')
                
    

        
TRIGGER_TIME = 10
HARD_STOP_TIME = 60
AUDIO_TIME = 3

class Trigger(threading.Thread):
    def __init__(self):
        self.trigger_timer = PostponedTimer(TRIGGER_TIME)
        self.hard_stop_timer = PostponedTimer(HARD_STOP_TIME)
        self.audio_timer = PostponedTimer(AUDIO_TIME)
        self.lock = threading.RLock()
        self.audio = None
        self.audio_playing = False
        self.gpio = GPIO(21)
        
        # os.system('amixer -D hw set PCM 100%')
        
        super(Trigger, self).__init__()
        self.daemon = True
        self.start()

    def is_hard_stopped(self):
        with self.lock:
            return self.hard_stop_timer.is_active()
        
    def trigger(self, label, start_audio, metadata=None):
        with self.lock:
            if self.is_hard_stopped():
                logger.info('ignoring trigger while hard stopped')
                return
            self.trigger_timer.postpone()

            if self.audio_timer.is_active() or start_audio:
                self.audio_timer.postpone()
                self.play_audio()

            import capture
            capture.start_recording_video(label)
            
        if metadata is not None:
            telegram_bot.get_chat().send_message(f'triggered: label={label}, metadata={json.dumps(metadata)}')
            
    def hard_stop(self):
        import capture
        with self.lock:
            if not self.hard_stop_timer.is_active():
                logger.info('hard stop')
            capture.stop_recording_video(hard=True)
            self.stop_audio()
            self.trigger_timer.stop()
            self.audio_timer.stop()
            self.hard_stop_timer.postpone()

    def is_triggered(self):
        with self.lock:
            return not self.is_hard_stopped() and self.trigger_timer.is_active()

    def play_audio(self):

        timing.event('audio')
        
        with self.lock:
            if params.get('play_audio', False):
                self.gpio.set(1)

            if not self.audio_playing:
                msg = '%sstarting audio' % ('' if params.get('play_audio', False) else '(not) ')
                telegram_bot.get_chat().send_message(msg)
                logger.info(msg)
            
            self.audio_playing = True
            
            # if self.audio is not None:
            #     if self.audio.poll() is not None:
            #         self.audio = None

            # if self.audio is None:
            #     self.audio = subprocess.Popen(['aplay',
            #                                    '-D', 'hw',
            #                                    '/home/joe/test_audio.wav'],
            #                                   stdout=subprocess.PIPE,
            #                                   stderr=subprocess.PIPE)

            # r,w,x = select.select([self.audio.stdout, self.audio.stderr], [], [], 0)
            # while r:
            #     for p in r:
            #         p.read(1)
            #     r,w,x = select.select([self.audio.stdout, self.audio.stderr], [], [], 0)
            

                
    def stop_audio(self):
        with self.lock:
            self.gpio.set(0)
            if self.audio_playing:
                telegram_bot.get_chat().send_message('stopping audio')
                logger.info('stopping audio')
            self.audio_playing = False
            
            # if self.audio is not None:
            #     self.audio.kill()

            #     if self.audio.poll() is not None:
            #         self.audio = None
        
            
    def run(self):
        import capture
        while True:
            time.sleep(1)
            try:
                
                with self.lock:
                    if not self.trigger_timer.is_active():
                        capture.stop_recording_video()
                        self.stop_audio()
                        self.audio_timer.stop()

                    if self.audio_timer.is_active():
                        self.play_audio()
                    else:
                        self.stop_audio()

            except Exception:
                logger.exception('trigger loop raised an exception')

            finally:
                self.gpio.set(0)
                    
trigger = Trigger()                
