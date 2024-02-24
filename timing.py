import time
import threading
import sys
from params import params

PRINT_RATE = 0.2

MAX_AGE = 5
MAX_EVENTS = 10

class Timing:
    def __init__(self):
        self.event_times = {}
        self.total_events = {}
        self.lock = threading.Lock()
        self.next_print = None

    def event(self, name):
        with self.lock:
            self.event_times.setdefault(name, [])
            self.total_events.setdefault(name, 0)
            self.event_times[name].append(time.time())
            self.total_events[name] += 1

            self.event_times[name] = [x for x in self.event_times[name] if ((time.time() - x) < MAX_AGE)]
            self.event_times[name] = self.event_times[name][-MAX_EVENTS:]

        self.print_stats()

    def stats(self, name):
        with self.lock:
            curr_events = self.event_times.get(name, [])
            if not curr_events:
                return 0
            
            start = curr_events[0]
            end = curr_events[-1]
            
            t = end - start
            count = len(curr_events)

            if t == 0:
                return 0
            
            return count / t

    def stats_string(self):
        s = ''
        
        for event in sorted(self.event_times.keys()):
            s += (f'{event} {self.total_events[event]} {self.stats(event):.1f}/s ')

        return s
            
    def print_stats(self):

        if not params['print_timing']:
            return

        if self.next_print is None:
            self.next_print = time.time() + PRINT_RATE
        elif time.time() < self.next_print:
            return
        else:
            self.next_print += PRINT_RATE
            if time.time() >= self.next_print:
                self.next_print = time.time() + PRINT_RATE

        s = self.stats_string()

        sys.stdout.write('\r' + s + '     ')
        sys.stdout.flush()
            
timing = Timing()
event = timing.event
print_stats = timing.print_stats
stats = timing.stats
stats_string = timing.stats_string
