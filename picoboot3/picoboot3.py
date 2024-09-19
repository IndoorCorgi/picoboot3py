"""
Copyright (c) 2024 Indoor Corgi
SPDX-License-Identifier: MIT
"""
import time


class Picoboot3:
  """
  Base class for interface-independent functionality

  Attributes:
    verbous: Display logs on screen if True
    activate_response : 4 Bytes of activation response. Use the value specified in the bootloader. 
    appcode_offset: App code address offset. Use the value specified in the bootloader. 
    transfer_size: Number of pages to transfer per one read or program command. 1-16. 
                   Small number is safe, large number is fast. 
  """

  # Command
  READY_BUSY_COMMAND = 0x1
  VERSION_COMMAND = 0x2
  READ_COMMAND = 0x10
  PROGRAM_COMMAND = 0x20
  ERASE_COMMAND = 0x30
  GO_TO_APPCODE_COMMAND = 0x40
  FLASH_SIZE_COMMAND = 0x50
  ACTIVATE_COMMAND = 0xA5

  # Bootloader response
  READY = 1

  # Flash
  FLASH_SECTOR_SIZE = 4096
  FLASH_PAGE_SIZE = 256

  def __init__(self,
               verbous=False,
               activate_response=b'pbt3',
               appcode_offset=32 * 1024,
               transfer_size=2):
    self.verbous = verbous
    self.activate_response = activate_response
    self.appcode_offset = appcode_offset
    self.transfer_size = transfer_size

  """
  Interface related methods
  """

  def __enter__(self):
    self.open()
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.close()

  def open(self):
    """
    To override in subclasses
    """
    pass

  def close(self):
    """
    To override in subclasses
    """
    pass

  def receive_bytes(self, length):
    """
    To override in subclasses
    Receive bytes from device
    
    Args:
      length: Number of bytes to read
    
    Returns:
      bytes: received data
    """
    pass

  def send_bytes(self, data):
    """
    To override in subclasses
    Send bytes data to device

    Args:
      data: data to be sent in bytes type (e.g. bytes([0x00, 0xFF]))
    """
    pass

  """
  Command methods
  """

  def activate_command(self):
    """
    Send activate command and return response

    Returns:
      bytes: response
    """
    self.send_bytes(bytes([self.ACTIVATE_COMMAND]))
    return self.receive_bytes(4)

  def is_ready(self):
    """
    Send reasy/busy command and check response

    Returns: True if ready
    """
    self.send_bytes(bytes([self.READY_BUSY_COMMAND]))
    data = self.receive_bytes(1)
    if (data[0] == 1):
      return True
    return False

  def version_command(self):
    """
    Get version
    
    Returns:
      int: Major version
      int: Minor version
      int: Patch version
    """
    self.send_bytes(bytes([self.VERSION_COMMAND]))
    data = self.receive_bytes(3)
    return data[0], data[1], data[2]

  def read_command(self, start_address, length):
    """
    Read command
    
    Args:
      start_address: Offset address in the flash
      length: Number of bytes to read. Max=4096

    Returns: 
      bytes: Read data
    """
    self.send_bytes(
        bytes([self.READ_COMMAND]) + start_address.to_bytes(4, 'little') +
        length.to_bytes(2, 'little'))
    return self.receive_bytes(length)

  def program_command(self, start_address, data):
    """
    Program command
    
    Args:
      start_address: Offset address in the flash. Must be multiple of page size
      data: bytes data to program. Max=4096
    """
    if start_address % self.FLASH_PAGE_SIZE != 0:
      raise ValueError('start_address must be multiple of {}'.format(self.FLASH_PAGE_SIZE))

    if len(data) > self.FLASH_SECTOR_SIZE:
      raise ValueError('data length exceeds {}'.format(self.FLASH_SECTOR_SIZE))

    send_data = bytes([self.PROGRAM_COMMAND])
    send_data += start_address.to_bytes(4, 'little')

    # Fill by 0xFF if data length is not multiple of page size
    rem = len(data) % self.FLASH_PAGE_SIZE
    if rem > 0:
      data += bytes([0xFF] * (self.FLASH_PAGE_SIZE - rem))
    send_data += len(data).to_bytes(2, 'little')
    send_data += data
    self.send_bytes(send_data)
    while (not self.is_ready()):
      time.sleep(0.001)

  def erase_command(self, sector):
    """
    Erase command
    
    Args:
      sector: Sector# in the flash, starting from #0
    """
    self.send_bytes(bytes([self.ERASE_COMMAND]) + sector.to_bytes(2, 'little'))
    while (not self.is_ready()):
      time.sleep(0.01)

  def flash_size_command(self):
    """
    Get flash size
    
    Returns: Flash size [Bytes]
    """
    self.send_bytes(bytes([self.FLASH_SIZE_COMMAND]))
    data = self.receive_bytes(4)
    return int.from_bytes(data, 'little')

  def go_to_appcode_command(self):
    self.send_bytes(bytes([self.GO_TO_APPCODE_COMMAND]))

  """
  High level operations
  """

  def activate(self, delay=10):
    """
    Send activate command and check response

    Args:
      delay: Insert delay [ms] to wait for Picoboot3 initialization after reset

    Returns: True on success
    """
    time.sleep(delay / 1000)
    try:
      if (self.activate_command() == self.activate_response):
        return True
    except:
      return False
    return False

  def erase(self, sectors):
    """
    Erase selected sectors

    Args:
      sectors: list of sectors to be erased
    """
    sectors = sorted(sectors)
    total_loop = len(sectors)
    if len(sectors) == 1:
      test_name = 'Erase page#{}'.format(sectors[0])
    else:
      test_name = 'Erase {}sectors #{}..#{}'.format(len(sectors), sectors[0], sectors[-1])
    self._logv('\r{}   0%'.format(test_name), end='')

    for i in range(total_loop):
      self.erase_command(sectors[i])
      progress = round((i + 1) / total_loop * 100)
      self._logv('\r{} {:3d}%'.format(test_name, progress), end='')

    self._logv('')

  def verify_blank(self, start_address, length, exp_data=0xFF, fail_stop=True):
    """
    Read flash and confirm data is blank (erased)

    Args:
      start_address: Offset address in the flash
      length: Number of bytes to verify
      exp_data: Expected data after erase
      fail_stop: Stop at the 1st fail address

    Returns: Ture on pass
    """
    blank_data = [exp_data] * length
    return self._verify_loop(
        name='Verify blank',
        perform_program=False,
        data=blank_data,
        start_address=start_address,
        fail_stop=fail_stop,
    )

  def verify(self, start_address, data, fail_stop=True):
    """
    Verify data

    Args:
      start_address: Offset address in the flash
      data: Expected data in bytes
      fail_stop: Stop at the 1st fail address

    Returns: Ture on pass
    """
    return self._verify_loop(
        name='Verify',
        perform_program=False,
        data=data,
        start_address=start_address,
        fail_stop=fail_stop,
    )

  def program(self, start_address, data, fail_stop=True):
    """
    Program and verify data

    Args:
      start_address: Offset address in the flash. Must be multiple of page size
      data: bytes data to be written. Max=4096
      fail_stop: Stop at the 1st fail address

    Returns: Ture on pass
    """
    return self._verify_loop(
        name='Program and verify',
        perform_program=True,
        start_address=start_address,
        data=data,
        fail_stop=fail_stop,
    )

  def _verify_loop(self, name, start_address, data, perform_program, fail_stop):
    """
    A sequence to program / verify

    Args:
      name: For logging
      start_address: Offset address in the flash
      data: For verify and program
      perform_program: Perform program if True
      fail_stop: Stop at the 1st fail address
      
    Returns: Ture on pass
    """
    length = len(data)
    stop_address = start_address + length - 1
    length_per_loop = self.FLASH_PAGE_SIZE * self.transfer_size
    total_loop = (length - 1) // length_per_loop + 1
    result = True
    test_name = '{}@0x{:X} {}Bytes'.format(name, start_address, length)
    self._logv('\r{}   0%'.format(test_name), end='')

    for i in range(total_loop):
      current_address = start_address + length_per_loop * i
      num_of_bytes = stop_address - current_address + 1
      if num_of_bytes > length_per_loop:
        num_of_bytes = length_per_loop

      progress = round((i + 1) / total_loop * 100)

      if perform_program:
        self.program_command(current_address,
                             data[length_per_loop * i:length_per_loop * i + num_of_bytes])
      read_data = self.read_command(current_address, num_of_bytes)
      self._logv('\r{} {:3d}%'.format(test_name, progress), end='')

      for j in range(len(read_data)):
        rd = read_data[j]
        exp = data[length_per_loop * i + j]
        if rd != exp:
          self._logv(' Fail@0x{:X} Exp:0x{:02X} Read:0x{:02X}'.format(current_address + j, exp, rd),
                     end='')
          result = False

          if fail_stop:
            self._logv('')
            return False
          else:
            self._logv('\n{} {:3d}%'.format(test_name, progress), end='')

    if result:
      self._logv(' Pass')
    else:
      self._logv(' Fail')
    return result

  def dump(self, start_address, length, show_dump=False):
    """
    Read and dump data

    Args:
      start_address: Offset address in the flash
      length: Number of bytes to read
      show_dump: Show read data on the screen
      
    Returns:
      bytes: Read data
    """
    return self._dump_loop(
        name='Dump',
        start_address=start_address,
        length=length,
        show_dump=show_dump,
    )

  def _dump_loop(self, name, start_address, length, show_dump):
    """
    A sequence for dump

    Args:
      name: For logging
      start_address: Offset address in the flash
      length: Number of bytes to read
      show_dump: Show read data on the screen
      
    Returns:
      bytes: Read data
    """
    stop_address = start_address + length - 1
    length_per_loop = self.FLASH_SECTOR_SIZE
    total_loop = (length - 1) // length_per_loop + 1
    num_per_line = 16
    data = bytearray()

    if show_dump:
      self._logv('Address: ', end='')
      for n in range(num_per_line):
        self._logv('{:02X} '.format(n), end='')

      s = start_address % num_per_line
      if s > 0:
        self._logv('{:X}: '.format(start_address - s), end='')
        for _ in range(s):
          self._logv('-- ', end='')
    else:
      test_name = '{}@0x{:X} {}Bytes'.format(name, start_address, length)
      self._logv('\r{}   0%'.format(test_name), end='')

    for i in range(total_loop):
      current_address = start_address + length_per_loop * i
      num_of_bytes = stop_address - current_address + 1
      if num_of_bytes > length_per_loop:
        num_of_bytes = length_per_loop

      read_data = self.read_command(current_address, num_of_bytes)
      data += read_data

      if show_dump:
        for j in range(len(read_data)):
          if (current_address + j) % num_per_line == 0:
            self._logv('\n {:06X}: '.format(current_address + j), end='')
          self._logv('{:02X} '.format(read_data[j]), end='')
      else:
        progress = round((i + 1) / total_loop * 100)
        self._logv('\r{} {:3d}%'.format(test_name, progress), end='')
    self._logv('')

    return data

  """
  Internal methods
  """

  def _logv(self, string='', end='\n'):
    """
    Show message on the screen if verbous is True
    """
    if self.verbous:
      print(string, end=end)
