import time
import threading
from ah_wrapper.ah_serial_client import AHSerialClient

def position_sender(pos, lock, stop_event, client, rate_hz=100):
    try:
        while not stop_event.is_set():
            with lock:
                current_pos = pos.copy()  # Safe copy under lock
            current_pos[5] = -current_pos[5]
            client.set_position(positions=current_pos, reply_mode=2)
            client.send_command()
            time.sleep(1 / rate_hz)
    finally:
        client.close()
