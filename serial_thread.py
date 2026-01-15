import logging
import time
import threading
import queue
import serial
from serial.tools import list_ports
from ability_hand_api_local.python.ah_wrapper.ah_serial_client import AHSerialClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

class SerialWriter(threading.Thread):
    """
    Thread that pulls (ser_idx, pos_list, raw_bytes) tuples off pos_queue
    and writes them to the correct AHSerialClient.
    """
    def __init__(self, pos_queue: queue.Queue, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.pos_queue = pos_queue
        self.stop_event = stop_event
        self.clients = []           # list of AHSerialClient
        self.num_hands = 0
        self.rate_hz = 30           # fallback
        self._setup_clients()

    def _setup_clients(self):
        ports = list_ports.comports()
        for p in ports:
            # only hook up the FT232R-based AbilityHands
            if "FT232R" in p.description:
                client = AHSerialClient(write_thread=False, baud_rate=460800)
                # give us a finite write timeout
                try:
                    client._serial.write_timeout = 0.5
                except Exception:
                    pass
                self.clients.append(client)
                logging.info(f"▶ Connected AHSerialClient on {p.device}")
        self.num_hands = len(self.clients)
        if self.clients:
            self.rate_hz = self.clients[0].rate_hz
        logging.info(f"SerialWriter managing {self.num_hands} hand(s)")

    def run(self):
        logging.info("SerialWriter starting main loop")
        while not self.stop_event.is_set():
            try:
                ser_idx, pos, raw = self.pos_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if ser_idx < 0 or ser_idx >= self.num_hands:
                logging.error(f"Invalid hand index {ser_idx}")
                continue

            client = self.clients[ser_idx]
            try:
                if pos is not None:
                    client.set_position(positions=pos)
                    client.send_command()
                elif raw is not None:
                    client._serial.write(raw)
            except serial.SerialTimeoutException as e:
                logging.error(f"Write timeout on hand {ser_idx}: {e} — reconnecting")
                client.close()
                time.sleep(0.5)
                self.clients[ser_idx] = AHSerialClient(write_thread=False, baud_rate=460800)
            except Exception as e:
                logging.exception(f"Unexpected error on hand {ser_idx}: {e}")

            # pace ourselves to the client's own update rate
            time.sleep(1.0 / self.rate_hz)

        logging.info("SerialWriter stopping, closing clients")
        for c in self.clients:
            c.close()
        logging.info("SerialWriter exited")
