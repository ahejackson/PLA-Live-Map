"""Abstraction that wraps the nxreader class to allow for mocking values when no switch is connected"""
import nxreader
import struct
from pa8 import Pa8

PLAYER_LOCATION_PTR = "[[[[[[main+42B3558]+88]+90]+1F0]+18]+80]+90"
SPAWNER_PTR = "[[main+4268ee0]+330]"
PARTY_PTR = "[[[main+4269000]+d0]+58]"
WILD_PTR = "[[[[main+4268f00]+b0]+e0]+d0]"
OUTBREAK_PTR = "[[[[main+427C470]+2B0]+58]+18]"

MOCK_DATA = {
    'generator_seed': 0x863cd775b9f871f5,
    'spawn_count': 10,
}

class Switch:
    reader = None
    connected = False
    allow_writing = True

    def __init__(self, ip_address):
        try:
            self.reader = nxreader.NXReader(ip_address)
            self.connected = True
        except:
            self.connected = False

    def is_connected(self):
        return self.connected

    def read_generator_seed(self, group_id):
        if self.connected:
            return self.reader.read_pointer_int(f"{SPAWNER_PTR}+{0x70 + group_id * 0x440 + 0x20:X}", 8)
        else:
            return MOCK_DATA['generator_seed']

    def read_group_seed(self, group_id):
        if self.connected:
            return self.reader.read_pointer_int(f"{SPAWNER_PTR}+{0x70 + group_id * 0x440 + 0x408:X}", 8)
        else:
            return 0
    
    def read_outbreak_spawn_count(self, index):
        if self.connected:
            return self.reader.read_pointer_int(f"{OUTBREAK_PTR}+{0x60 + index * 0x50:X}", 1)
        else:
            return MOCK_DATA['spawn_count']

    def read_party_count(self):
        return self.reader.read_pointer_int(f"{PARTY_PTR}+88", 1)

    def read_wild_count(self, party_count):
        return self.reader.read_pointer_int(f"{WILD_PTR}+1a0", 1) - party_count

    def read_pa8(self, index):
        return Pa8(
            self.reader.read_pointer(
                f"{WILD_PTR}+{0xb0+8*(index):X}]+70]+60]+98]+10]",
                Pa8.STOREDSIZE
            )
        )

    def read_player_coordinates(self):
        if not self.connected:
            return { 'x': 0, 'y': 0, 'z': 0 }
        
        pos = struct.unpack('fff', self.reader.read_pointer(PLAYER_LOCATION_PTR, 12))
        return { 'x': pos[0], 'y': pos[1], 'z': pos[2] }

    def read_map_spawn_count(self):
        return int(self.reader.read_pointer_int(f"{SPAWNER_PTR}+18", 4)//0x40 - 1) if self.connected else 0
    
    def read_map_spawn(self, index):
        if not self.connected:
            return None
        
        position_bytes = self.reader.read_pointer(f"{SPAWNER_PTR}+{0x70 + index * 0x40:X}", 12)
        seed = self.reader.read_pointer_int(f"{SPAWNER_PTR}+{0x90 + index * 0x40:X}", 12)
        pos = struct.unpack('fff', position_bytes)

        if not (seed == 0 or pos[0] < 1 or pos[1] < 1 or pos[2] < 1):
            return { "x": pos[0], "y":pos[1], "z":pos[2], "seed": seed }
        else:
            return None

    def teleport_player(self, coordinates):
        position_bytes = struct.pack('fff', *coordinates)

        if self.connected and self.allow_writing:
            self.reader.write_pointer(PLAYER_LOCATION_PTR, f"{int.from_bytes(position_bytes,'big'):024X}")
