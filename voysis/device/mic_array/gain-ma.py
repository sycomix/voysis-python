"""
set gain for the mic array, this tends to work better on debian jessie due to the messiness of building hidapi

pip install hidapi
"""
try:
    import hid
except ImportError:
    # there are a number of issues with this library, it appears to target very specific versions of
    # libusb, libudev and hid, it also tends to work better on debian jessie (and probably ubuntu trusty)
    print("Please do 'pip install hidapi==0.7.99.post15', note this will only work correctly on debian jessie and newer")

RESPEAKER_VENDOR_ID = 0x2886
RESPEAKER_PRODUCT_ID = 0x07
RECORD_SR = 16000

# Set up the HID driver
_dev = hid.device()
_dev.open(RESPEAKER_VENDOR_ID, RESPEAKER_PRODUCT_ID)

# Write data to a register, return how many bytes were written
def write_register(register, data):
    send_data = [0, register, 0, len(data), 0 ] + data
    return _dev.write(send_data)

# Read length data from a register, return the data
def read_register(register, length):
    # To read a register you send reg & 0x80, and then read it back
    # If you have blocking off the read will return none if it's too soon after
    send_data = [0, register, 0x80, length, 0, 0, 0]
    what = _dev.write(send_data)
    ret = _dev.read(len(send_data) + length)
    return ret[4:4+length] # Data comes in at the 4th byte

data = write_register(10, [30])
mic_gain = read_register(0x10, 1)[0]
print(f"Mic gain is set to {mic_gain}")
print(f"Wrote {data}")

#mic_gain = read_register(0x10, 1)[0]
#print "Mic gain is set to %d" % (mic_gain)
