"""
Copyright (c) 2024 Indoor Corgi
SPDX-License-Identifier: MIT
"""
from .picoboot3 import Picoboot3
import time


class Picoboot3uart(Picoboot3):
  """
  UART interface bootloader

  Attributes:
    port: Serial port
    baud : Baudrate
    timeout: device response timeout [sec]
    verbous: Display logs on screen if True
    activate_response : 4 Bytes of activation response. Use the value specified in the bootloader. 
    appcode_offset: App code address offset. Use the value specified in the bootloader. 
    transfer_size: Number of pages to transfer per one read or program command. 1-16. 
                   Small number is safe, large number is fast. 
  """

  def __init__(
      self,
      port=None,
      baud=500000,
      timeout=1,
      verbous=False,
      activate_response=b'pbt3',
      appcode_offset=32 * 1024,
      transfer_size=2,
  ):
    super().__init__(verbous=verbous,
                     activate_response=activate_response,
                     appcode_offset=appcode_offset,
                     transfer_size=transfer_size)
    self.port = port
    self.baud = baud
    self.timeout = timeout

  def open(self):
    """
    Open serial port
    """
    import serial

    if self.port is None:
      import serial.tools.list_ports
      detect_ports = serial.tools.list_ports.comports()
      if len(detect_ports) == 0:
        raise Exception('No serial port detected')

      if len(detect_ports) == 1:
        self._logv('Use serial port {}, {}'.format(detect_ports[0].device,
                                                   detect_ports[0].manufacturer))
        self.port = detect_ports[0].device

      else:
        for i in range(len(detect_ports)):
          print('{}: {}, {}'.format(i + 1, detect_ports[i].device, detect_ports[i].manufacturer))

        while True:
          choice = int(input('Select serial port(1-{}): '.format(len(detect_ports))))
          if int(choice) in list(range(1, len(detect_ports) + 1)):
            self.port = detect_ports[choice - 1].device
            break
          else:
            print('Invalid number')

    self.serial = serial.Serial(port=self.port, baudrate=self.baud)
    self.serial.timeout = self.timeout
    time.sleep(0.001)  # Delay may needed to clear buffer
    self.serial.read_all()  # Clear receive buffer

  def close(self):
    self.serial.close()

  def receive_bytes(self, length):
    """
    Receive bytes from device
    
    Args:
      length: Number of bytes to read
    
    Returns:
      bytes: received data
    """
    data = self.serial.read(length)
    if len(data) != length:
      raise Exception('Unable to receive expected length of data')
    return data

  def send_bytes(self, data):
    """
    Send bytes data to device

    Args:
      data: data to be sent in bytes type (e.g. bytes([0x00, 0xFF]))
    """
    self.serial.write(data)
