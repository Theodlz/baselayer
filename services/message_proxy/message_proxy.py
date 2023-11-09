# http://zguide.zeromq.org/page:all#The-Dynamic-Discovery-Problem

import zmq
import threading

from baselayer.app.env import load_env
from baselayer.log import make_log

env, cfg = load_env()

log = make_log("message_proxy")

IN = cfg.get("ports.message_proxy_in")
OUT = cfg.get("ports.message_proxy_out")

if IN is None or OUT is None:
    IN = cfg["ports.websocket_path_in"]
    OUT = cfg["ports.websocket_path_out"]

context = zmq.Context()

def peer_run(ctx: zmq.Context):
        """ this is the run method of the PAIR thread that logs the messages
        going through the broker """
        sock: zmq.Socket = ctx.socket(zmq.PAIR)
        sock.connect("inproc://peer") # connect to the caller
        sock.send(b"") # signal the caller that we are ready
        while True:
            try:
                topic = sock.recv_string()
                obj = sock.recv_pyobj()
            except Exception:
                topic = None
                obj = sock.recv()
            print(f"\n !!! peer_run captured message with topic {topic}, obj {obj}. !!!\n")

feed_in = context.socket(zmq.PULL)
feed_in.bind(IN)

feed_out = context.socket(zmq.PUB)
feed_out.bind(OUT)

# we also want to keep a copy of the messages for debugging purposes
capture = context.socket(zmq.PAIR)
capture.bind("inproc://peer")
cap_thread = threading.Thread(target=peer_run, args=(context,))
cap_thread.start()
capture.recv() # wait for the peer to be ready
log("Peer thread ready, starting proxy")

log(f"Forwarding messages between {IN} and {OUT}")
zmq.proxy(feed_in, feed_out, capture)