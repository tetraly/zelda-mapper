import sys
import zelda_rom
import zelda_constants
from zelda_constants import Direction
from zelda_constants import ITEMS

class LevelMapper(object):
  def __init__(self, rom):
    self.rooms_1_6 = []
    self.rooms_7_9 = []
    self.start_rooms = []
    self.stairway_rooms = []
    self.special_items = []

    # Import data from the ROM classs
    for room_num in range(0, 0x80):
      self.rooms_1_6.append(rom.GetLevelRoom(room_num, is7to9=False))
      self.rooms_7_9.append(rom.GetLevelRoom(room_num, is7to9=True))
    for level_num in range(0, 10):
      self.start_rooms.append(rom.GetLevelStartRoom(level_num))
      self.stairway_rooms.append(rom.GetLevelStairwayRoomList(level_num))
      self.special_items.append([])
  def _GetRoom(self, room_num, level_num):
    if level_num < 7:
      return self.rooms_1_6[room_num]
    return self.rooms_7_9[room_num]

  def _ClearAllVisitMarkers(self, is7to9):
    for room in self.rooms_7_9 if is7to9 else self.rooms_1_6:
      room.ClearVisitMark()

  # TODO: Refactor the two get*Offset() methods to resuse code
  def _GetLeftOffset(self, level_num):
    offset = 0
    while True:
      for y in range(0, 8):
        # Don't count rooms that aren't in the level we're getting offsets for.
        if level_num == self._GetRoom(
            0x10*y + offset, level_num).GetLevelNumber():
          return offset
      offset = offset + 1
    return offset

  def _GetRightOffset(self, level_num):
    right_offset = 15
    while True:
      for y in range(0, 8):
        if level_num == self._GetRoom(
            0x10*y + right_offset, level_num).GetLevelNumber():
          return right_offset
      right_offset = right_offset - 1
    return right_offset

  def _VisitDungeonRoom(self, room_num, entry_door, level_num, missing_item):
    if room_num > 0x7F:
      return  # No escaping back into the overworld! :)
    room = self._GetRoom(room_num, level_num)
    if room.WasAlreadyVisited():
      return
    room.MarkAsVisited()
    room.SetLevelNumber(level_num)

    # Attempt to pick up "special" floor item and stairway item
    if (room.GetItem() in zelda_constants.SPECIAL_ITEMS or
        room.GetItem() == zelda_constants.TRINGLE):
      if room.CanDefeatEnemiesOrGetItemWithoutDoingSo(missing_item):
        self.special_items[level_num].append(room.GetItem())
    if (room.HasStairwayItem() and
        room.CanDefeatEnemiesOrBlockClipOrRightStairs(missing_item)):
      self.special_items[level_num].append(room.GetStairwayItem())

    # Attempt to visit adjoining rooms unless blocked
    for direction in (Direction.WEST, Direction.NORTH,
                      Direction.EAST, Direction.SOUTH):
      if room.CanMove(direction):
        if not (room.CanMoveWithoutOpeningShutters(direction) or
                room.CanDefeatEnemies(missing_item)):
          continue
        if (missing_item == zelda_constants.LADDER and
            not room.CanMoveWithoutLadder(entry_door, direction)):
          continue
        self._VisitDungeonRoom(room_num + direction, -1*direction,
                               level_num, missing_item)
    if room.HasStairwayPassageRoom():
      if room.CanDefeatEnemiesOrBlockClipOrRightStairs(missing_item):
        self._VisitDungeonRoom(room.GetStairwayPassageRoom(), 0,
                               level_num, missing_item)

  # Returns True only for the stairway passage case (to increment stair #)
  def _VisitStairwayRoom(self, room_num, level_num, stairway_letter):
    room = self._GetRoom(room_num, level_num)
    left_room, right_room = room.GetLeftExit(), room.GetRightExit()

    # Transport stairway case
    if left_room != right_room:
      self._GetRoom(left_room, level_num).SetStairwayPassageRoom(
          right_room, str(stairway_letter))
      self._GetRoom(right_room, level_num).SetStairwayPassageRoom(
          left_room, str(stairway_letter))
      return True

    # Item room case
    stairway_item = room.GetItem()
    self._GetRoom(left_room, level_num).SetStairwayItem(stairway_item)
    return False

  def MapLevels(self):
    for level_num in range(1, 10):
      print level_num
      # Visit dungeon assuming we won't get blocked (i.e. have all items)
      stairway_letter = 1
      for stairway_room in self.stairway_rooms[level_num]:
        if self._VisitStairwayRoom(stairway_room, level_num, stairway_letter):
          stairway_letter = stairway_letter + 1
      self._VisitDungeonRoom(self.start_rooms[level_num], Direction.NORTH,
                             level_num, None)
      self._ClearAllVisitMarkers(level_num >= 7)
      all_items_in_level = []
      for item in self.special_items[level_num]:
        all_items_in_level.append(item)

      # Now, to find blocks!
      for missing_item in [zelda_constants.RECORDER, zelda_constants.BOW,
                           zelda_constants.BLUE_RING, zelda_constants.LADDER]:
        self.special_items[level_num] = []
        self._VisitDungeonRoom(self.start_rooms[level_num], Direction.NORTH,
                               level_num, missing_item=missing_item)
        for item_in_level in all_items_in_level:
          if not item_in_level in self.special_items[level_num]:
            print "Warning: %s block in level %d to get %s" % (
                ITEMS[missing_item], level_num, ITEMS[item_in_level])
        self._ClearAllVisitMarkers(level_num >= 7)

  def PrintLevelInfo(self):
    for level_num in range(1, 10):
      left_offset = self._GetLeftOffset(level_num)
      right_offset = self._GetRightOffset(level_num)
      print ""
      print "Level %d map" % level_num
      for y in range(0, 8):
        for line in range(0, 5):
          for x in range(left_offset, right_offset + 1):
            room = self._GetRoom(0x10*y + x, level_num)
            if level_num == room.GetLevelNumber():
              sys.stdout.write(room.GetAsciiTest()[line])
            else:
              sys.stdout.write("            ")
          print ""

  def PrintLevelItems(self):
    for level_num in range(1, 10):
      for item in self.special_items[level_num]:
        # We know levels 1-8 all have tringles
        if not item == zelda_constants.TRINGLE:
          print "Level %d contains %s" % (level_num, ITEMS[item])

if __name__ == "__main__":
  zeldarom = zelda_rom.ZeldaRom(sys.argv[1])
  level_mapper = LevelMapper(zeldarom)
  level_mapper.MapLevels()
  level_mapper.PrintLevelInfo()
  level_mapper.PrintLevelItems()
