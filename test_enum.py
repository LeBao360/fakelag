import ctypes
from enum import IntEnum

class Layer(IntEnum): NETWORK=0

libc = ctypes.cdll.msvcrt
libc.abs.argtypes = [ctypes.c_int]
print(libc.abs(Layer.NETWORK))
