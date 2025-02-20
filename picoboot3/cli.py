"""
Copyright (c) 2024 Indoor Corgi
SPDX-License-Identifier: MIT
"""
description = """
Picoboot3 custom bootloader should be written on your board in advance.
For more information about Picoboot3, see https://github.com/IndoorCorgi/picoboot3.git.
"""

from argparse import ArgumentParser, RawTextHelpFormatter, RawDescriptionHelpFormatter
from .picoboot3_uart import Picoboot3uart
from .picoboot3_i2c import Picoboot3i2c
from .picoboot3_spi import Picoboot3spi


def cli():

  class CustomFormatter(RawTextHelpFormatter, RawDescriptionHelpFormatter):

    def __init__(self, prog, indent_increment=2, max_help_position=30, width=None):
      super().__init__(prog, indent_increment, max_help_position, width)

  parser = ArgumentParser(description=description, formatter_class=CustomFormatter)
  parser.add_argument('--command',
                      '-c',
                      choices=['program', 'verify', 'erase'],
                      default='program',
                      help='program(default): Erase required area, program fimware and verify\n'
                      'verify: Verify the firmware data against the data in flash\n'
                      'erase: Erase whole flash except bootloader space')
  parser.add_argument('--file', '-f', help='Firmware .bin file to program or verify')
  parser.add_argument('--interface',
                      '-i',
                      choices=['uart', 'i2c', 'spi'],
                      default='uart',
                      help='Default is uart.')
  parser.add_argument('--port',
                      '-p',
                      help='UART port e.g. COM1 or /dev/ttyACM0. Autodetect if not specified.\n'
                      'Raspberry Pi mini UART port may not be autodetected.')
  parser.add_argument('--baud',
                      type=int,
                      default=500000,
                      help='UART/SPI baudrate [bps/Hz]. Default is 500000.')
  parser.add_argument('--bus', type=int, default=1, help='I2C/SPI bus address. Default is 1.')
  parser.add_argument('--device',
                      '-d',
                      type=lambda x: int(x, 0),
                      default=0x5E,
                      help='I2C/SPI device address. Default is 0x5E.')
  parser.add_argument('--app',
                      '-a',
                      action='store_true',
                      help='Start application after program or verify.')
  parser.add_argument('--offset',
                      type=int,
                      default=32,
                      help='Offset address in KB. Must be multiple of 4. Default is 32.')
  parser.add_argument('--transfer_size',
                      '-t',
                      type=int,
                      default=2,
                      help='Number of pages to transfer per one read or program command. 1-16.\n'
                      'Small number is safe, large number is fast. Default is 2.')
  args = parser.parse_args()

  if args.command in ['program', 'verify']:
    if args.file is None:
      print('--file option is required for program and verify command. ')
      return 1

  if not args.transfer_size in range(1, 17):
    print('--transfer-size {} is out of range'.format(args.transfer_size))
    return 1

  if args.interface == 'uart':
    picoboot3 = Picoboot3uart(
        port=args.port,
        baud=args.baud,
        verbous=True,
        appcode_offset=args.offset * 1024,
        transfer_size=args.transfer_size,
    )
    picoboot3.open()
  elif args.interface == 'i2c':
    picoboot3 = Picoboot3i2c(
        bus_address=args.bus,
        device_address=args.device,
        verbous=True,
        appcode_offset=args.offset * 1024,
        transfer_size=args.transfer_size,
    )
    picoboot3.open()
  elif args.interface == 'spi':
    picoboot3 = Picoboot3spi(
        bus_address=args.bus,
        device_address=args.device,
        baud=args.baud,
        verbous=True,
        appcode_offset=args.offset * 1024,
        transfer_size=args.transfer_size,
    )
    picoboot3.open()

  if not picoboot3.activate():
    print('Failed to communicate with picoboot3')
    return 1

  major_ver, minor_ver, patch_ver = picoboot3.version_command()
  print('Device picoboot3 version: {}.{}.{}'.format(major_ver, minor_ver, patch_ver))
  available_space = picoboot3.flash_size_command() - picoboot3.appcode_offset
  print('Available space: {}Bytes'.format(available_space))
  first_erase_sector = picoboot3.appcode_offset // picoboot3.FLASH_SECTOR_SIZE

  if args.command in ['program', 'verify']:
    with open(args.file, 'rb') as f:
      fw_data = f.read()
    print('Firmware size: {}Bytes'.format(len(fw_data)))
    if available_space < len(fw_data):
      print('No enough space in flash')
      return 1
    num_of_erase_sectors = (len(fw_data) - 1) // picoboot3.FLASH_SECTOR_SIZE + 1

  if args.command == 'erase':
    num_of_erase_sectors = available_space // picoboot3.FLASH_SECTOR_SIZE
    picoboot3.erase(range(first_erase_sector, first_erase_sector + num_of_erase_sectors))
    if not picoboot3.verify_blank(picoboot3.appcode_offset,
                                  num_of_erase_sectors * picoboot3.FLASH_SECTOR_SIZE):
      print('Verify after erase failed')
      return 1

  if args.command == 'program':
    picoboot3.erase(range(first_erase_sector, first_erase_sector + num_of_erase_sectors))
    if not picoboot3.program(picoboot3.appcode_offset, fw_data):
      print('Program failed')
      return 1

    if args.app:
      print('Start application code')
      picoboot3.go_to_appcode_command()

  if args.command == 'verify':
    if not picoboot3.verify(picoboot3.appcode_offset, fw_data):
      print('Verify failed')
      return 1

    if args.app:
      print('Start application code')
      picoboot3.go_to_appcode_command()

  picoboot3.close()
  return 0
