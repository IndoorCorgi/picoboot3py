from setuptools import setup

setup(
    name='picoboot3',
    version='1.0.0',
    description=
    'Programmer for Picoboot3, allowing firmware updates to Raspberry Pi Pico via UART/I2C.',
    author='Indoor Corgi',
    author_email='indoorcorgi@gmail.com',
    url='https://github.com/IndoorCorgi/picoboot3py',
    license='MIT License',
    packages=['picoboot3'],
    install_requires=['pyserial', 'smbus2'],
    entry_points={'console_scripts': ['picoboot3=picoboot3:cli',]},
    python_requires='>=3.9',
)
