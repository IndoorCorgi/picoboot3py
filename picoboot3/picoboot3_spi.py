"""
Copyright (c) 2024 Indoor Corgi
SPDX-License-Identifier: MIT
"""
from .picoboot3 import Picoboot3


class Picoboot3spi(Picoboot3):
  """
  SPI interface bootloader

  Attributes:
    bus_address: SPI bus address
    device_address : SPI device address (CS#)
    baud : Baudrate
    verbous: Display logs on screen if True
    activate_response : 4 Bytes of activation response. Use the value specified in the bootloader. 
    appcode_offset: App code address offset. Use the value specified in the bootloader. 
    transfer_size: Number of pages to transfer per one read or program command. 1-16. 
                   Small number is safe, large number is fast. 
  """

  def __init__(
      self,
      bus_address,
      device_address,
      baud,
      verbous=False,
      activate_response=b'pbt3',
      appcode_offset=32 * 1024,
      transfer_size=2,
  ):
    super().__init__(verbous=verbous,
                     activate_response=activate_response,
                     appcode_offset=appcode_offset,
                     transfer_size=transfer_size)
    self.bus_address = bus_address
    self.device_address = device_address
    self.baud = baud
    import spidev
    self.spi = spidev.SpiDev()

  def open(self):
    self.spi.open(self.bus_address, self.device_address)
    self.spi.max_speed_hz = self.baud
    self.spi.mode = 3

  def close(self):
    self.spi.close()

  def receive_bytes(self, length):
    """
    Receive bytes from device
    
    Args:
      length: Number of bytes to read
    
    Returns:
      bytes: received data
    """

    data = self.spi.xfer3([0] * length)
    return bytes(data)

  def send_bytes(self, data):
    """
    Send bytes data to device

    Args:
      data: data to be sent in bytes type (e.g. bytes([0x00, 0xFF]))
    """
    self.spi.xfer3(list(data))
