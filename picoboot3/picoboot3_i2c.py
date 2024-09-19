"""
Copyright (c) 2024 Indoor Corgi
SPDX-License-Identifier: MIT
"""
from .picoboot3 import Picoboot3


class Picoboot3i2c(Picoboot3):
  """
  I2C interface bootloader

  Attributes:
    bus_address: I2C bus address
    device_address : I2C device address
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
    import smbus2
    self.i2c = smbus2.SMBus(self.bus_address)

  def receive_bytes(self, length):
    """
    Receive bytes from device
    
    Args:
      length: Number of bytes to read
    
    Returns:
      bytes: received data
    """
    import smbus2
    msg = smbus2.i2c_msg.read(self.device_address, length)
    self.i2c.i2c_rdwr(msg)
    return bytes(msg)

  def send_bytes(self, data):
    """
    Send bytes data to device

    Args:
      data: data to be sent in bytes type (e.g. bytes([0x00, 0xFF]))
    """
    import smbus2
    msg = smbus2.i2c_msg.write(self.device_address, list(data))
    self.i2c.i2c_rdwr(msg)
