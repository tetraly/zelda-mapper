import sys
from typing import List
from room_lib import LevelRoom
from zelda_rom import ZeldaRom
import zelda_constants
from zelda_constants import Direction
from zelda_constants import ITEMS

ENTRANCE_DIRECTION_MAP = {
  1: Direction.SOUTH,
  2: Direction.NORTH,
  3: Direction.EAST,
  4: Direction.WEST
}

class LevelMapper(object):

  def __init__(self, rom: ZeldaRom, decode_mode: bool = False) -> None:
    self.rooms_1_6 = []  # type: List[LevelRoom]
    self.rooms_7_9 = []  # type: List[LevelRoom]
    self.start_rooms = []  # type: List[int]
    self.stairway_rooms = []  # type: List[List[int]]
    self.entrance_directions = [] 
    self.special_items = []  # type: List[List[int]]
    self.decode_mode = decode_mode

    # Import data from the ROM classs
    for room_num in range(0, 0x80):
      self.rooms_1_6.append(rom.GetLevelRoom(room_num, is7to9=False, decode_mode=self.decode_mode))
      self.rooms_7_9.append(rom.GetLevelRoom(room_num, is7to9=True, decode_mode=self.decode_mode))
    for level_num in range(0, 9):
      self.start_rooms.append(rom.GetLevelStartRoomNumber(level_num))
      stairway_list = rom.GetLevelStairwayRoomNumberList(level_num)
      entrance_direction = Direction.NORTH
      if decode_mode:
        entrance_direction = ENTRANCE_DIRECTION_MAP[stairway_list.pop()]
      self.entrance_directions.append(entrance_direction)
      self.stairway_rooms.append(stairway_list)
      self.special_items.append([])

  def _GetRoom(self, room_num: int, level_num: int) -> LevelRoom:
    if level_num in [0, 1, 2, 3, 4, 5]:  # Levels 1-6 but zero-indexed
      return self.rooms_1_6[room_num]
    return self.rooms_7_9[room_num]

  def _ClearAllVisitMarkers(self, is7to9: bool) -> None:
    for room in self.rooms_7_9 if is7to9 else self.rooms_1_6:
      room.ClearVisitMark()

  # TODO: Refactor the two get*Offset() methods to resuse code
  def _GetLeftOffset(self, level_num: int) -> int:
    assert level_num in range(0, 9)
    left_offset = 0
    while left_offset <= 15:
      for y_coord in range(0, 8):
        # Don't count rooms that aren't in the level we're getting offsets for.
        if level_num == self._GetRoom(0x10 * y_coord + left_offset, level_num).GetLevelNumber():
          return left_offset
      left_offset = left_offset + 1
    return left_offset

  def _GetRightOffset(self, level_num: int) -> int:
    right_offset = 15
    while right_offset >= 0:
      for y_coord in range(0, 8):
        if level_num == self._GetRoom(0x10 * y_coord + right_offset, level_num).GetLevelNumber():
          return right_offset
      right_offset = right_offset - 1
    return right_offset

  def _VisitDungeonRoom(self,
                        room_num: int,
                        entry_door: int,
                        level_num: int,
                        missing_item: int,
                        is_entrance: bool=False) -> None:
    if room_num > 0x7F:
      return  # No escaping back into the overworld! :)
    room = self._GetRoom(room_num, level_num)
    if room.WasAlreadyVisited():
      return
    room.MarkAsVisited()
    room.SetLevelNumber(level_num)
    # Attempt to pick up "special" floor item and stairway item
    if (room.GetItemType() in zelda_constants.SPECIAL_ITEMS or
        room.GetItemType() == zelda_constants.TRINGLE):
      if room.CanDefeatEnemiesOrGetItemWithoutDoingSo(missing_item):
        self.special_items[level_num].append(room.GetItemType())
    if (room.HasStairwayItem() and room.CanDefeatEnemiesOrBlockClipOrRightStairs(missing_item)):
      self.special_items[level_num].append(room.GetStairwayItem())

    # Attempt to visit adjoining rooms unless blocked
    for direction in (Direction.WEST, Direction.NORTH, Direction.EAST, Direction.SOUTH):
      if room.CanMove(direction):
        # Don't leave back to the overworld
        if is_entrance and direction == -1* entry_door:
          continue
        if not (room.CanMoveWithoutOpeningShutters(direction) or
                room.CanDefeatEnemies(missing_item)):
          continue
        if (missing_item == zelda_constants.LADDER and
            not room.CanMoveWithoutLadder(entry_door, direction)):
          continue
        self._VisitDungeonRoom(
            room_num + direction,
            -1 * direction,
            level_num,
            missing_item)
    if room.HasStairwayPassageRoom() and room.CanDefeatEnemiesOrBlockClipOrRightStairs(missing_item):
        self._VisitDungeonRoom(room.GetStairwayPassageRoom(), 0, level_num, missing_item)

  # Returns True only for the stairway passage case (to increment stair #)
  def _VisitStairwayRoom(self, room_num: int, level_num: int, stairway_num: int) -> bool:

    if room_num > 0x7f:
      assert (1 == 2)
    room = self._GetRoom(room_num, level_num)
    # Set this to a non-existent level num so that it doesn't default to 0 (level 1)
    room.SetLevelNumber(0xFF)

    left_room, right_room = room.GetLeftExit(), room.GetRightExit()

    # Transport stairway case
    if left_room != right_room:
      self._GetRoom(left_room, level_num).SetStairwayPassageRoom(right_room, stairway_num)
      self._GetRoom(right_room, level_num).SetStairwayPassageRoom(left_room, stairway_num)
      return True

    # Item room case
    stairway_item = room.GetItemType()
    self._GetRoom(left_room, level_num).SetStairwayItem(stairway_item)
    return False

  def MapLevels(self) -> None:
    for level_num in range(0, 9):
      # Visit dungeon assuming we won't get blocked (i.e. have all items)
      stairway_letter = 1
      for stairway_room in self.stairway_rooms[level_num]:
        if self._VisitStairwayRoom(stairway_room, level_num, stairway_letter):
          stairway_letter = stairway_letter + 1
      self._VisitDungeonRoom(
          self.start_rooms[level_num],
          self.entrance_directions[level_num],
          level_num, missing_item=None, is_entrance=True)
      self._ClearAllVisitMarkers(level_num >= 6)
      all_items_in_level = []
      for item in self.special_items[level_num]:
        all_items_in_level.append(item)

      # Now, to find blocks!
      for missing_item in [
          zelda_constants.RECORDER, zelda_constants.BOW, zelda_constants.BLUE_RING,
          zelda_constants.LADDER
      ]:
        self.special_items[level_num] = []
        self._VisitDungeonRoom(
            self.start_rooms[level_num], self.entrance_directions[level_num], level_num, 
            missing_item=missing_item, is_entrance=True)
        for item_in_level in all_items_in_level:
          if not item_in_level in self.special_items[level_num]:
            print("Warning: %s block in level %d to get %s" % (ITEMS[missing_item], level_num,
                                                               ITEMS[item_in_level]))
        self._ClearAllVisitMarkers(level_num >= 6)

  def PrintLevelInfo(self) -> None:
    for level_num in range(0, 9):
      left_offset = self._GetLeftOffset(level_num)
      right_offset = self._GetRightOffset(level_num)
      print("")
      print("Level %d map" % (level_num + 1))
      for y_coord in range(0, 8):
        for line in range(0, 5):
          for x_coord in range(left_offset, right_offset + 1):
            room = self._GetRoom(0x10 * y_coord + x_coord, level_num)
            if level_num == room.GetLevelNumber():
              sys.stdout.write(room.GetAsciiText()[line])
            else:
              sys.stdout.write("            ")
          print("")

  def PrintLevelItems(self) -> None:
    for level_num in range(0, 9):
      for item in self.special_items[level_num]:
        # We know levels 1-8 all have tringles
        if not item == zelda_constants.TRINGLE:
          print("Level %d contains %s" % (level_num + 1, ITEMS[item]))


def main(input_filename: str, decode_mode: bool = False) -> None:
  level_mapper = LevelMapper(
      ZeldaRom(input_filename), decode_mode=decode_mode)
  level_mapper.MapLevels()
  level_mapper.PrintLevelInfo()
  level_mapper.PrintLevelItems()


if __name__ == "__main__":
  decode_mode = False
  if len(sys.argv) > 2:
    if sys.argv[2] == "--decode_mode":
      decode_mode = True

  main(sys.argv[1], decode_mode)
