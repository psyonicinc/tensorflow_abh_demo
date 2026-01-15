import time
from ah_wrapper.ah_serial_client import AHSerialClient
import queue

def send_positions_thread(q, stop_event):
    client = AHSerialClient(write_thread=False, baud_rate=460800)
    try:
        while not stop_event.is_set():
            try:
                pos = q.get(timeout=1.0)
                client.set_position(positions=pos, reply_mode=2)
                client.send_command()
                time.sleep(1 / client.rate_hz)
            except queue.Empty:
                continue
    finally:
        client.close()
