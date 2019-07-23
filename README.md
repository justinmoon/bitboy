# BitBoy

### Setup

Create virtual environment

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Download the firmware (how can i have this always fetch the latest release?)

```
wget <github release>
```

Figure out which port your m5stack is running on

```
python3 -m serial.tools.list_ports
```

Flash firmware -- it's just a modded version of micropython with modules for working with bitcoin and m5stack display / buttons.

```
esptool.py --chip esp32 --port <port> --baud 460800 erase_flash
esptool.py --chip esp32 --port <port> --baud 460800 write_flash -z 0x1000 build/firmware.bin
``
