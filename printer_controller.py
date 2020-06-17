import threading
import logging

logger = logging.getLogger(__name__)
PRINTER_ACTIVE_TIME = 30*60


class PrinterController:
    def __init__(self):
        self.is_printer_on = self.check_state()
        self.timer = None

    def check_state(self):
        # TODO: check relais state
        return False

    def enable(self):
        # TODO: enable relais
        self.is_printer_on = True
        logger.info("Enabled Printer!")
        self.timer = threading.Timer(PRINTER_ACTIVE_TIME, self.disable)
        self.timer.start()

    def disable(self):
        # TODO: disable relais
        self.is_printer_on = False
        logger.info("Disabled Printer!")

    def close(self):
        if self.timer:
            self.timer.cancel()