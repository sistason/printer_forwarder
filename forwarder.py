#!/usr/bin/env python

import threading
import logging
import socket
import select
import queue
import time

from printer_controller import PrinterController

logger = logging.getLogger(__name__)


class PrinterForwarder:
    PRINT_STRING = b'@PJL SET JOBNAME'

    def __init__(self, bind_address, port, destination):
        self.destination_addr = destination
        self.bind_addr = bind_address
        self.port = port

        self.interface = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.printer_controller = PrinterController()

    def run(self):
        self.interface.bind((self.bind_addr, self.port))
        self.interface.listen()
        logger.info(f"Waiting for connections on {self.bind_addr}:{self.port}")

        forwarders = []
        try:
            while True:
                conn_, addr = self.interface.accept()
                logger.info(f"Got connection from {addr}")

                initial_data = b""

                # if the printer is shut down, safeguard against turning on (in the middle of the night)
                if not self.printer_controller.is_printer_on:
                    try:
                        initial_data = conn_.recv(4096)
                        logger.info(initial_data)
                        if self.PRINT_STRING not in initial_data:
                            logger.warning(
                                f"Client {addr} sent something not a printjob, started with {initial_data[:40]}")
                            conn_.close()
                            continue
                    except ConnectionError:
                        logger.warning(f"Client {addr} opened a connection but reset instantly. Nmap?")
                        conn_.close()
                        continue

                    logger.info("Activating printer...")
                    self.printer_controller.enable()

                # if the printer is on either way, just forward whatever, to be more robust in case of errors
                forwarder = Forwarder(conn_, self.destination_addr, self.port)
                conn_t = threading.Thread(target=forwarder.forward, kwargs={"initial_data": initial_data})
                forwarder.thread = conn_t
                conn_t.start()
                forwarders.append(forwarder)

        except (KeyboardInterrupt, ConnectionError):
            self.interface.close()
            self.printer_controller.close()
            for forwarder in forwarders:
                forwarder.close()
                forwarder.thread.join()
            print('all joined')


class Forwarder:
    WAIT_TIMEOUT = 60

    def __init__(self, connection, destination_addr, destination_port):
        self.client_connection = connection
        self.printer_connection = None
        self.printer_destination = (destination_addr, destination_port)

        self.thread = None

    def _wait_for_printer(self, sock):
        start = time.time()
        while time.time()-start < self.WAIT_TIMEOUT:
            try:
                sock.connect(self.printer_destination)
                return True
            except:
                logging.debug(f"  Forwarder waiting for printer...({time.time()-start}/{self.WAIT_TIMEOUT})")

    def forward(self, initial_data=b""):
        self.printer_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_queue = queue.Queue()
        printer_queue = queue.Queue()

        if initial_data:
            printer_queue.put_nowait(initial_data)
            if not self._wait_for_printer(self.printer_connection):
                self.close()
                return
        else:
            self.printer_connection.connect(self.printer_destination)

        try:
            while True:
                readers, writers, _ = select.select([self.printer_connection, self.client_connection],
                                                    [self.printer_connection, self.client_connection], [], 60)

                if self.client_connection in readers:
                    data = self.client_connection.recv(4096)
                    if data:
                        logger.debug(f"Client wants: {data[:20]}")
                        printer_queue.put(data)
                if self.printer_connection in readers:
                    data = self.printer_connection.recv(4096)
                    if data:
                        logger.debug(f"Printer answered: {data[:20]}")
                        client_queue.put(data)

                if self.client_connection in writers:
                    if not client_queue.empty():
                        data = client_queue.get_nowait()
                        self.client_connection.sendall(data)

                if self.printer_connection in writers:
                    if not printer_queue.empty():
                        data = printer_queue.get_nowait()
                        self.printer_connection.sendall(data)

        except:
            self.close()

    def close(self):
        self.client_connection.close()
        if self.printer_connection:
            self.printer_connection.close()
        print('stopped')


def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action="store_true")
    parser.add_argument('-q', '--quiet', action="store_true")
    parser.add_argument('-p', '--port', type=int, default=9100)
    parser.add_argument('bind_address')
    parser.add_argument('target')

    _args = parser.parse_args()
    return _args


if __name__ == '__main__':
    args = parse_args()

    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.ERROR
    else:
        log_level = logging.INFO
    logging.basicConfig(level=log_level)

    pf = PrinterForwarder(args.bind_address, args.port, args.target)
    pf.run()
