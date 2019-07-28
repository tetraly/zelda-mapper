from typing import List
from room_lib import LevelRoom


class ZeldaRom(object):
  # Because .nes files have an extra 16 (0x10) bytes at their beginning,
  # offset all ROM memory locations by that amount so that memory addresses
  # in our code match up with the addresses on the original NES ROMs.
  NES_HEADER_OFFSET = 0x10

  DATA_START_LOCATION = 0x18400
  LEVEL_1_6_DATA_LOCATION = 0x18700
  LEVEL_DATA_OFFSET = 0x300
  
  OVERWORLD_POINTER_OFFSET_LOCATION = 0x18000
  LEVEL_1_6_POINTER_OFFSET_LOCATION = 0x18002
  LEVEL_7_9_POINTER_OFFSET_LOCATION = 0x18012

  LEVEL_ONE_START_ROOM_LOCATION = 0x1942B

  # In a level's data, the byte where the stairway room list starts is always
  # exactly five bytes after the memory location of the start room.
  START_ROOM_STAIRWAY_ROOM_OFSET = 5

  # The specialized data for levels (starting around 0x1942B) is exactly this
  # number of bytes long.
  SPECIAL_LEVEL_DATA_OFFSET = 0xFC

  # Reads a Nintendo ROM file from disk and opens it as a binary file.
  #
  # Args:
  #  rom_filename: Full path/filename of the ROM to open (string)
  def __init__(self, rom_filename: str, write_mode: bool=False) -> None:
    print("Opening %s ..." % rom_filename)
    mode_string = "r+b" if write_mode else "rb"
    self.rom_file = open(rom_filename, mode_string)

  # Reads one or more bytes from the NES ROM file
  #
  # Args:
  #   address: The starting memory address to read from (int)
  #   num_bytes: How many bytes to read (int)
  # Returns:
  #   One or more bytes from the ROM file (byte array)
  def _ReadMemory(self, address: int, num_bytes: int = 1) -> List[int]:
    assert num_bytes > 0, "num_bytes shouldn't be negative"
    self.rom_file.seek(self.NES_HEADER_OFFSET + address)
    data = []  # type: List[int]
    for raw_byte in self.rom_file.read(num_bytes):
      data.append(int(raw_byte))
    return data

  def WriteBytes(self, address: int, data: List[int]) -> None:
    """Writes one or more bytes (represented as Python ints) to the ROM file."""
    assert self.rom_file, "Need to run OpenFile(write_mode=True) first."
    assert data is not None, "Need at least one byte to write."

    offset = 0
    for byte in data:
      self.rom_file.seek((address + self.NES_HEADER_OFFSET) + offset)
      self.rom_file.write(bytes([byte]))
      offset = offset + 1

  # Gets map data from the rom
  #
  # Args:
  #   room_num: An offset representing a room/screen number (int)
  #   is7to9: True if accessing data for levels 7-9, False for levels 1-6
  # Returns:
  #   An array of six integers containing the raw data for the room/screen.
  def _GetRawMapData(self, room_num: int, is7to9: bool = False) -> List[int]:
    data = []  # type: List[int]
    start_location = self.LEVEL_1_6_DATA_LOCATION
    if is7to9:
      start_location = start_location + self.LEVEL_DATA_OFFSET

    for table_num in range(0, 6):
      byte = self._ReadMemory(start_location + 0x80 * table_num + room_num, 1)[0]
      data.append(byte)
    return data

  def _GetEncodedMapData(self, room_num: int, is_overworld: bool=False, is7to9: bool = False) -> List[int]:
    data = []  # type: List[int]
    offset_overworld = self._ReadMemory(self.OVERWORLD_POINTER_OFFSET_LOCATION, 1)[0]
    offset_1to6 = self._ReadMemory(self.LEVEL_1_6_POINTER_OFFSET_LOCATION, 1)[0]
    offset_7to9 = self._ReadMemory(self.LEVEL_7_9_POINTER_OFFSET_LOCATION, 1)[0]

    maybe_offset = offset_7to9 if is7to9 else offset_1to6
    offset = offset_overworld if is_overworld else maybe_offset
    start_location = self.DATA_START_LOCATION + offset

    for table_num in range(0, 6):
      byte_1 = self._ReadMemory(start_location + (5 * (0x80 * table_num + room_num)), 1)[0]
      byte_2 = self._ReadMemory(start_location + (5 * (0x80 * table_num + room_num)) + 1, 1)[0]
      data.append(byte_1 ^ byte_2)
    return data

  def GetLevelRoom(self, room_num: int,  is_overworld: bool=False, is7to9: bool=False, decode_mode: bool = False) -> LevelRoom:
    if decode_mode:
      return LevelRoom(self._GetEncodedMapData(room_num, is_overworld=is_overworld, is7to9=is7to9))
    return LevelRoom(self._GetRawMapData(room_num, is_overworld=is_overworld, is7to9=is7to9))

  def WriteRoomItemCode(self, room_num: int, is7to9: bool, item_code: int) -> None:
    address = self.LEVEL_1_6_DATA_LOCATION + 0x80 * 4 + room_num
    if is7to9:
      address += self.LEVEL_DATA_OFFSET
    existing_high_bits = self._ReadMemory(address)[0] & 0xE0

    self.rom_file.seek(self.NES_HEADER_OFFSET + address)
    self.rom_file.write(bytes([existing_high_bits + item_code]))

  # Gets the coordinates of the start screen for a level.
  #
  # Params:
  #   level_num: The number of the level to get info for (int)
  # Returns:
  #   The coordinates of the start room, e.g. 0x7F (int)
  def GetLevelStartRoomNumber(self, level_num: int) -> int:
    assert level_num in range(0, 9)
    # Each level contains 0xFC bytes of special data before the next one starts.
    location = (self.LEVEL_ONE_START_ROOM_LOCATION + self.SPECIAL_LEVEL_DATA_OFFSET * (level_num))
    raw_value = self._ReadMemory(location, 1)[0]

    # return self._ToInt(raw_value)
    return raw_value

  # Gets a list of stairway rooms for a level.
  #
  # Note that this will include not just passage stairways between two
  # dungeon rooms but also item rooms with only one passage two and
  # from a dungeon room.
  #
  # Args:
  #  level_num: The level to get information for (int)
  # Returns:
  #  Zero or more bytes containing the stairway room numbers
  def GetLevelStairwayRoomNumberList(self,
                                     level_num: int) -> List[int]:
    assert level_num in range(0, 9)
    stairway_list_location = (self.LEVEL_ONE_START_ROOM_LOCATION + self.SPECIAL_LEVEL_DATA_OFFSET *
                              (level_num) + self.START_ROOM_STAIRWAY_ROOM_OFSET)
    assert level_num in range(0, 9)
    raw_bytes = self._ReadMemory(stairway_list_location, 10)
    stairway_list = []  # type: List[int]
    for byte in raw_bytes:
      if not byte == 0xFF:
        stairway_list.append(byte)

    # This is a hack needed in order to make vanilla L3 work.  For some reason,
    # the vanilla ROM's data for level 3 doesn't include a stairway room even
    # though there obviously is one in vanilla level 3.
    #
    # See http://www.romhacking.net/forum/index.php?topic=18750.msg271821#msg271821
    # for more information about why this is the case and why this hack
    # is needed.
    if level_num == 2 and not stairway_list:
      stairway_list.append(0x0F)

    return stairway_list
