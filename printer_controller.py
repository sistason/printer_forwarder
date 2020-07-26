import threading
import logging
from gpiozero import Button, OutputDevice
import time

logger = logging.getLogger(__name__)
PRINTER_ACTIVE_TIME = 30*60

PIN_MANUAL_BUTTON = 17
PIN_RELAIS = 18


class PrinterController:
    def __init__(self):
        self.timer = None

        self.manual_button = Button(PIN_MANUAL_BUTTON)
        self.relais = OutputDevice(PIN_RELAIS, active_high=True, initial_value=False)

        self.shutdown = False
        self.manual_button_thread = threading.Thread(target=self.manual_operation)
        self.manual_button_thread.start()

        self.is_printer_on = self.relais.is_active

    def manual_operation(self):
        while not self.shutdown:
            pressed = self.manual_button.wait_for_press(1)
            if pressed:
                logger.info("Manual Button pressed")
                if self.timer:
                    self.timer.cancel()
                if self.is_printer_on:
                    self.timer = threading.Timer(PRINTER_ACTIVE_TIME, self.disable)
                    self.timer.start()
                else:
                    self.enable()

    def enable(self):
        if self.is_printer_on or self.shutdown:
            return
        self.is_printer_on = True
        logger.info("Enabled Printer!")
        self.relais.on()
        self.timer = threading.Timer(PRINTER_ACTIVE_TIME, self.disable)
        self.timer.start()

    def disable(self):
        if not self.is_printer_on:
            return
        self.relais.off()
        self.is_printer_on = False
        logger.info("Disabled Printer!")

    def close(self):
        self.shutdown = True
        if self.timer:
            self.timer.cancel()

        self.relais.close()
        self.manual_button_thread.join(10)
        self.manual_button.close()


