import room_lib
import struct

class ZeldaRom(object):
  # Because .nes files have an extra 16 (0x10) bytes at their beginning,
  # offset all ROM memory locations by that amount so that memory addresses
  # in our code match up with the addresses on the original NES ROMs.
  NES_FILE_OFFSET = 0x10

  LEVEL_1_6_DATA_LOCATION = 0x18700
  LEVEL_DATA_OFFSET = 0x300

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
  def __init__(self, rom_filename):
    print "Opening %s ..." % rom_filename
    self.rom_file = open(rom_filename, "rb")

  # Converts a binary byte to a unsigned short integer
  def _ToInt(self, byte):
    return struct.unpack(">B", byte)[0]

  # Reads one or more bytes from the NES ROM file
  #
  # Args:
  #   address: The starting memory address to read from (int)
  #   num_bytes: How many bytes to read (int)
  # Returns:
  #   One or more bytes from the ROM file (byte array)
  def _ReadMemory(self, address, num_bytes=1):
    assert num_bytes > 0, "num_bytes shouldn't be negative"
    self.rom_file.seek(self.NES_FILE_OFFSET + address)
    return self.rom_file.read(num_bytes)

  # Gets map data from the rom
  #
  # Args:
  #   room_num: An offset representing a room/screen number (int)
  #   is7to9: True if accessing data for levels 7-9, False for levels 1-6
  # Returns:
  #   An array of six integers containing the raw data for the room/screen.
  def _GetRawMapData(self, room_num, is7to9=False):
    data = []
    start_location = self.LEVEL_1_6_DATA_LOCATION
    if is7to9:
      start_location = start_location + self.LEVEL_DATA_OFFSET

    for a in range(0, 6):
      byte = self._ReadMemory(start_location + 0x80*a + room_num, 1)
      data.append(self._ToInt(byte))
    return data

  def GetLevelRoom(self, room_num, is7to9):
    room = room_lib.LevelRoom()
    room.InitializeFromRomData(
        self._GetRawMapData(room_num, is7to9=is7to9))
    return room

  # Gets the coordinates of the start screen for a level.
  #
  # Params:
  #   level_num: The number of the level to get info for (int)
  # Returns:
  #   The coordinates of the start room, e.g. 0x7F (int)
  def GetLevelStartRoom(self, level_num):
    # Each level contains 0xFC bytes of special data before the next one starts.
    location = (self.LEVEL_ONE_START_ROOM_LOCATION +
                self.SPECIAL_LEVEL_DATA_OFFSET*(level_num - 1))
    raw_value = self._ReadMemory(location, 1)
    return self._ToInt(raw_value)

  # Gets a list of stairway rooms for a level.
  #
  # Note that this will include not just passage stairways between two
  # dungeon rooms but also item rooms with only one passage two and
  # from a dungeon room.
  #
  # Args:
  #  level_num: The level to get information for (int)
  # Returns:
  #  Zero or more bytes containing the stairway rooms
  def GetLevelStairwayRoomList(self, level_num):
    stairway_list_location = (self.LEVEL_ONE_START_ROOM_LOCATION +
                              self.SPECIAL_LEVEL_DATA_OFFSET*(level_num - 1) +
                              self.START_ROOM_STAIRWAY_ROOM_OFSET)
    raw_bytes = self._ReadMemory(stairway_list_location, 10)
    stairway_list = []
    for byte in raw_bytes:
      if not byte == '\xFF':
        stairway_list.append(self._ToInt(byte))

    # This is a hack needed in order to make vanilla L3 work.  For some reason,
    # the vanilla ROM's data for level 3 doesn't include a stairway room even
    # though there obviously is one in vanilla level 3.
    #
    # See http://www.romhacking.net/forum/index.php?topic=18750.msg271821#msg271821
    # for more information about why this is the case and why this hack
    # is needed.
    if level_num == 3 and len(stairway_list) == 0:
      stairway_list.append(self._ToInt('\x0F'))

    return stairway_list
