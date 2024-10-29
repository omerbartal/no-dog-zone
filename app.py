#!/usr/bin/env python3

import threading
import params
import time
import glob
import os
import sys
import signal
import subprocess

import telegram_bot
import detect

import log

class TelegramBot(telegram_bot.BotThread):
    def __init__(self):
        super(TelegramBot, self).__init__()
        telegram_bot.get_chat().menu = ['Trigger', 'Hard Stop', 'Status', 'IP', 'Die']
        telegram_bot.get_chat().send_menu(text='started')
        
    def button_pressed(self, data):
        if data == 'Trigger':
            log.logger.info('triggered')
            detect.trigger.trigger('manual_trigger', start_audio=False, metadata={'fake':1})
        elif data == 'Hard Stop':
            log.logger.info('hard stopping')
            detect.trigger.hard_stop()
        elif data == 'Status':
            import timing
            telegram_bot.get_chat().send_message(timing.stats_string())
        elif data == 'IP':
            telegram_bot.get_chat().send_message(os.popen('ifconfig', 'r').read())
        elif data == 'Die':
            os.kill(os.getpid(), signal.SIGINT)
        else:
            log.logger.error(f'unknown button {data}')

class Upload(threading.Thread):
    def __init__(self):
        super(Upload, self).__init__()
        self.daemon = True

        self.unconverted_path = params.params['output_path']
        self.converted_path = os.path.join(params.params['output_path'], 'x264')
        
        if not os.path.exists(self.converted_path):
            os.mkdir(self.converted_path)
        
        self.start()

    def convert(self, src_fn):
        basename = os.path.basename(src_fn)
        dirname = os.path.dirname(src_fn)

        if basename.endswith('.avi'):
            basename = basename[:-4]

        basename += '.mp4'
        
        dst_fn = os.path.join(self.converted_path, basename)
        
        if os.path.exists(dst_fn):
            os.remove(dst_fn)

        log.logger.info(f'converting {src_fn}')
        p = subprocess.Popen(['ffmpeg',
                              '-i', src_fn,
                              '-c:v', 'h264',
                              # '-c:a', 'aac',
                              '-movflags', '+faststart',
                              dst_fn],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        try:
            stdout, stderr = p.communicate(timeout=None)
        # except TimeoutExpired:
        #     return False
        finally:
            if p.poll() is None:
                p.kill()

        os.remove(src_fn)
                
        if p.poll() != 0:
            log.logger.error(f'failed converting {src_fn}')
            if os.path.exists(dst_fn):
                os.remove(dst_fn)
        
    def run(self):
        while True:
            for fn in sorted(glob.iglob(os.path.join(self.unconverted_path, '*.' + capture.video_ext))):
                self.convert(fn)
                
            for fn in sorted(glob.iglob(os.path.join(self.converted_path, '*.mp4'))):
                if telegram_bot.get_chat().upload_video(fn):
                    log.logger.info(f'uploaded {fn} successfully')
                    os.remove(fn)
                else:
                    log.logger.error(f'failed uploading {fn}')
                    
                    
            time.sleep(1)
            


    
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--src", action="store", default=None)
    parser.add_argument("--dst", action="store", default=None)
    parser.add_argument("--params", action="store", default='params.json')
    parser.add_argument("--mode", action="store", help="inference, time_lapse", default=None)
    parser.add_argument("--no-timing", action="store_false", default=True, dest='print_timing')
    parser.add_argument("-v", dest='verbose', action="count", default=0)
    parser.add_argument("--log", action="store", default=None)

    args = parser.parse_args()

    if args.src is None:
        parser.error('src missing')

    if args.dst is None:
        parser.error('dst missing')

    if args.params is None:
        parser.error('params missing')

    if args.verbose > 0:
        log.log_to_console(args.verbose)

    if args.log is not None:
        log.log_to_file(args.log)
        
    params.load_params(args.params)

    params.params['output_path'] = args.dst
    params.params['print_timing'] = args.print_timing
    
    import capture
        
    capture.start(src=args.src, video_base_dir=args.dst)
    # capture.start_recording_video()

    TelegramBot()
    Upload()

    if args.mode == 'inference':
        # inference_thread_fn()
        detect.start_inference()
    elif args.mode == 'time_lapse':
        detect.start_time_lapse()

    import ui
    ui.run()

        
