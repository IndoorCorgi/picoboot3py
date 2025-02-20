#!/usr/bin/env python3

# Run test with random generated data

import random

INTERFACE = 'uart'  # uart/i2c/spi
NUM_OF_TEST_SECTORS = 0  # If 0, test all sectors except bootloader area
TRANSFER_SIZE = 2  # 1-16

# Interface selection
if INTERFACE == 'uart':
  from picoboot3 import Picoboot3uart
  picoboot3 = Picoboot3uart(transfer_size=TRANSFER_SIZE, verbous=True)
elif INTERFACE == 'i2c':
  from picoboot3 import Picoboot3i2c
  picoboot3 = Picoboot3i2c(bus_address=1,
                           device_address=0x5E,
                           transfer_size=TRANSFER_SIZE,
                           verbous=True)
elif INTERFACE == 'spi':
  from picoboot3 import Picoboot3spi
  picoboot3 = Picoboot3spi(bus_address=0,
                           device_address=0,
                           baud=10000000,
                           transfer_size=TRANSFER_SIZE,
                           verbous=True)
else:
  raise ValueError('Invalid interface')

# Open
picoboot3.open()
if not picoboot3.activate():
  raise Exception('Failed to communicate with picoboot3')

# Info commands
major_ver, minor_ver, patch_ver = picoboot3.version_command()
print('Device picoboot3 version: {}.{}.{}'.format(major_ver, minor_ver, patch_ver))
available_space = picoboot3.flash_size_command() - picoboot3.appcode_offset
print('Available space: {} Bytes'.format(available_space))

# Generate random test data
if NUM_OF_TEST_SECTORS > 0:
  data = random.randbytes(NUM_OF_TEST_SECTORS * picoboot3.FLASH_SECTOR_SIZE)
else:
  data = random.randbytes(available_space)

print('Test data size: {} Bytes'.format(len(data)))
if available_space < len(data):
  raise Exception('No enough available space in flash')

# Erase
first_erase_sector = picoboot3.appcode_offset // picoboot3.FLASH_SECTOR_SIZE
num_of_erase_sectors = (len(data) - 1) // picoboot3.FLASH_SECTOR_SIZE + 1
picoboot3.erase(range(first_erase_sector, first_erase_sector + num_of_erase_sectors))

# Print top/bottom
picoboot3.dump(picoboot3.appcode_offset, 64, show_dump=True)
picoboot3.dump(picoboot3.appcode_offset + len(data) - 64, 64, show_dump=True)

# Verify blank
if not picoboot3.verify_blank(picoboot3.appcode_offset,
                              num_of_erase_sectors * picoboot3.FLASH_SECTOR_SIZE):
  raise Exception('Verify after erase failed')

# Program with verify
if not picoboot3.program(picoboot3.appcode_offset, data):
  raise Exception('Program failed')

# Print top/bottom
picoboot3.dump(picoboot3.appcode_offset, 64, show_dump=True)
picoboot3.dump(picoboot3.appcode_offset + len(data) - 64, 64, show_dump=True)

# Verify
if not picoboot3.verify(picoboot3.appcode_offset, data):
  raise Exception('Verify after program failed')

# Dump and compare
dump_data = picoboot3.dump(picoboot3.appcode_offset, len(data))
if dump_data == data:
  print('Dump comparison passed')
else:
  raise Exception('Dump comparison failed')

picoboot3.close()
print('Test finished')
