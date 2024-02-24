import time
import timing
import threading

print('importing torch')
import torch

# https://pytorch.org/tutorials/intermediate/realtime_rpi.html

print('importing numpy')
import numpy as np

print('importing torchvision')
from torchvision import models, transforms


import ast
classes = ast.literal_eval(open('imagenet1000_clsidx_to_labels.txt','r').read())
dog = [x for x in range(151, 268)] + [268] + [x for x in range(281, 294)]

class Detect:
    image_type = 'scaled_rgb'
    resolution = (224, 224)
    
    def __init__(self):

        print('init nn')

        torch.backends.quantized.engine = 'qnnpack'

        self.preprocess = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        self.net = models.quantization.mobilenet_v2(pretrained=True, quantize=True)
        # jit model to take it from ~20fps to ~30fps
        self.net = torch.jit.script(self.net)

    def infer(self, image):
        
        with torch.no_grad():

            # preprocess
            # print('preprocess')
            input_tensor = self.preprocess(image)

            # create a mini-batch as expected by the model
            # print('unsqueeze')
            input_batch = input_tensor.unsqueeze(0)

            # run model
            # print('run model')
            output = self.net(input_batch)
            # do something with output ...

            # print('output:')
            # print(output)

            top = list(enumerate(output[0].softmax(dim=0)))
            top.sort(key=lambda x: x[1], reverse=True)
            curr = {}
            for idx, val in top[:10]:
                # print(f"{val.item()*100:.2f}% {classes[idx]}")

                s = f'{idx} {classes[idx]}'
                
                curr[s] = val.item()

                if idx in dog:
                    curr['dog'] = curr.get('dog', 0) + val.item()
                
            import detect
            detect.detections.add(curr)

            # top = list(enumerate(output[0].softmax(dim=0)))
            # top.sort(key=lambda x: x[1], reverse=True)
            # ret = {}
            # for idx, val in top[:10]:
            #     # print(f"{val.item()*100:.2f}% {classes[idx]}")
            #     ret[classes[idx]] = val.item()

            timing.event('inference')

            # return ret

