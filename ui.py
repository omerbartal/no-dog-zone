from flask import Response
from flask import Flask
from flask import render_template
from flask import request, jsonify


import capture
import cv2
import timing

from params import params, save_params
from params import lock as params_lock

from log import logger

import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask('detect')

# Initialize a counter variable
counter = 0

@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html", counter=counter)


capture_iter = None
def generate():
    global capture_iter
    capture_iter = capture.images('marked')
    for image in capture_iter:
        try:
            (flag, encodedImage) = cv2.imencode(".jpg", image)
        except Exception:
            logger.exception('imencode exception')
            flag = False

        if not flag:
            logger.error('failed encoding?')
            continue

        timing.event('stream')
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
              bytearray(encodedImage) + b'\r\n')


@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(),
		    mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/img_source", methods=['POST'])
def img_source():
    capture_iter.image_type = request.form.get('image_source')
    return ''


@app.route('/main', methods=['POST'])
def main():
    move = request.form.get('move')

    # logger.debug(move)
    
    with params_lock:

        if move == 'main_up':
            params['scale_start_y'] -= 10
            params['scale_end_y'] -= 10

        if move == 'main_down':
            params['scale_start_y'] += 10
            params['scale_end_y'] += 10

        if move == 'main_left':
            params['scale_start_x'] -= 10
            params['scale_end_x'] -= 10

        if move == 'main_right':
            params['scale_start_x'] += 10
            params['scale_end_x'] += 10

        if move == 'bigger':
            params['scale_end_x'] += 10
            params['scale_end_y'] += 10

        if move == 'smaller':
            params['scale_end_x'] -= 10
            params['scale_end_y'] -= 10

        if move == 'top1_up':
            params['hide_top'] = (params['hide_top'][0] - 10, params['hide_top'][1])
        if move == 'top1_down':
            params['hide_top'] = (params['hide_top'][0] + 10, params['hide_top'][1])
        if move == 'top2_up':
            params['hide_top'] = (params['hide_top'][0], params['hide_top'][1] - 10)
        if move == 'top2_down':
            params['hide_top'] = (params['hide_top'][0], params['hide_top'][1] + 10)

        if move == 'bottom1_up':
            params['hide_bottom'] = (params['hide_bottom'][0] + 10, params['hide_bottom'][1])
        if move == 'bottom1_down':
            params['hide_bottom'] = (params['hide_bottom'][0] - 10, params['hide_bottom'][1])
        if move == 'bottom2_up':
            params['hide_bottom'] = (params['hide_bottom'][0], params['hide_bottom'][1] + 10)
        if move == 'bottom2_down':
            params['hide_bottom'] = (params['hide_bottom'][0], params['hide_bottom'][1] - 10)

        if move == 'left1_left':
            params['hide_left'] = (params['hide_left'][0] - 10, params['hide_left'][1])
        if move == 'left1_right':
            params['hide_left'] = (params['hide_left'][0] + 10, params['hide_left'][1])
        if move == 'left2_left':
            params['hide_left'] = (params['hide_left'][0], params['hide_left'][1] - 10)
        if move == 'left2_right':
            params['hide_left'] = (params['hide_left'][0], params['hide_left'][1] + 10)


        if move == 'right1_right':
            params['hide_right'] = (params['hide_right'][0] - 10, params['hide_right'][1])
        if move == 'right1_left':
            params['hide_right'] = (params['hide_right'][0] + 10, params['hide_right'][1])
        if move == 'right2_right':
            params['hide_right'] = (params['hide_right'][0], params['hide_right'][1] - 10)
        if move == 'right2_left':
            params['hide_right'] = (params['hide_right'][0], params['hide_right'][1] + 10)

        save_params()
        
    return ''

@app.route('/get_inference', methods=['GET'])
def get_table_data():

    import detect

    detections = []

    stat_key = 'max'
    
    def prob_str(prob):
        ret = '%.1f [' % (prob[stat_key]*100)
        for p in sorted(prob['all']):
            ret += '%.1f ' % (p*100)
        ret += "]"
        return ret
            
    
    # ret = [{'cls':cls, 'prob':('%.1f' % (prob*100))} for cls, prob in sorted(detect.detections.get().items(), key=lambda x:x[1]['avg'], reverse=True)]
    ret = [{'cls':cls, 'prob':prob_str(prob)} for cls, prob in sorted(detect.detections.get().items(), key=lambda x:x[1][stat_key], reverse=True)]

    ret = ret[:5]

    return jsonify(ret)


def run():
    app.run(host='0.0.0.0', port=8000, debug=False, threaded=True, use_reloader=False)
    
