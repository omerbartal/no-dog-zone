#!/usr/bin/env python3
import threading

lock = threading.Lock()

filename = None

params = {
    'inference':True,
    'play_audio':False,
    'store_inference':False,
    'scale_start_x':0,
    'scale_start_y':0,
    'scale_end_x':1000,
    'scale_end_y':1000,

    'hide_top':(0,0),
    'hide_left':(0,0),
    'hide_right':(0,0),
    'hide_bottom':(0,0),    
}

def save_params():
    # print('saving params')
    import json
    with open(filename, 'w') as f:
        f.write(json.dumps(params))

def load_params(fn):
    import json
    global params
    global filename
    filename = fn
    try:
        with open(fn, 'r') as f:
            with lock:
                params.clear()
                params.update(json.loads(str(f.read())))
    except (json.decoder.JSONDecodeError, FileNotFoundError):
        pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    
    parser.add_argument("-d", action="store_true", default=False, dest='print_params')
    parser.add_argument("-s", action="append", default=[], dest='set_params')
    parser.add_argument("--params", action="store", default='params.json')

    args = parser.parse_args()

    load_params(args.params)
    
    if args.set_params:
        import json
        for kv in args.set_params:
            k,v = kv.split('=',1)
            v = json.loads(v)
            params[k] = v

        save_params()

    if args.print_params:
        for k in sorted(params.keys()):
            print(f'{k:20s} {params[k]}')
    
        
            
