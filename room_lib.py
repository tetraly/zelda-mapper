from typing import Dict, List
from zelda_constants import Direction
import zelda_constants


class LevelRoom(object):

  def __init__(self, rom_data: List[int]) -> None:
    self.has_zola = 0
    self.enemy_type_counts = [3, 5, 6, 8]  # type: List[int]
    self.wall_type = {}  # type: Dict[int, int]
    self.rom_data = rom_data

    # Applicable to regular dungeon rooms
    self.wall_type[Direction.WEST] = (rom_data[1] >> 5) & 0x07
    self.wall_type[Direction.NORTH] = (rom_data[0] >> 5) & 0x07
    self.wall_type[Direction.EAST] = (rom_data[1] >> 2) & 0x07
    self.wall_type[Direction.SOUTH] = (rom_data[0] >> 2) & 0x07

    # Applicable to stairway rooms
    self.left_exit = rom_data[0] & 0x7F
    self.right_exit = rom_data[1] & 0x7F

    # Room atributes
    self.num_enemies = (rom_data[2] >> 6) & 0x03
    self.enemy_type = rom_data[2] & 0x3F
    self.has_mixed_enemies = True if (rom_data[3] >> 7) & 0x01 == 1 else False
    self.room_type = rom_data[3] & 0x3F
    self.has_stairway = rom_data[5] & 0x01 == 1
    self.item_type = rom_data[4] & 0x1F
    self.is_drop_item = True if (rom_data[5] >> 2) & 0x01 == 1 else False

    # Non-ROM values
    self.already_visited = False
    self.level_num = 0xff
    self.stairway_passage_room = -1
    self.stairway_passage_num = 0
    self.stairway_item = -1

  def GetEnemyText(self) -> str:
    actual_num_enemies = ""
    # TODO: Use a lookup table here instead
    if self.enemy_type > 0:
      if self.num_enemies == 0:
        actual_num_enemies = "3"
      elif self.num_enemies == 1:
        actual_num_enemies = "5"
      elif self.num_enemies == 2:
        actual_num_enemies = "6"
      elif self.num_enemies == 3:
        actual_num_enemies = "8"

    if self.has_mixed_enemies:
      if self.enemy_type in zelda_constants.MIX_ENEMY_NAME.keys():
        return zelda_constants.MIX_ENEMY_NAME[self.enemy_type]
      return "Mix: %s %x" % (actual_num_enemies, self.enemy_type)
    return ("%s %s" % (actual_num_enemies, zelda_constants.ENEMY_NAME[self.enemy_type]))

  def CanMove(self, direction: int) -> bool:
    return self.wall_type[direction] != 1  # sold wall

  def CanMoveWithoutOpeningShutters(self, direction: int) -> bool:
    return self.wall_type[direction] not in [1, 7]  # solid wall or shutter

  def CanMoveWithoutLadder(self, entry_direction: int, exit_direction: int) -> bool:
    if self.room_type == 0x12:  # T Room
      return not (entry_direction == Direction.SOUTH or exit_direction == Direction.SOUTH)
    if self.room_type == 0x13:  # "E River"
      return not (entry_direction == Direction.EAST or exit_direction == Direction.EAST)
    if self.room_type == 0x16:  # "Chevy" room
      return False
    if self.room_type == 0x18:  # TopRivr
      return not (entry_direction == Direction.NORTH or exit_direction == Direction.NORTH)
    if self.room_type == 0x19:  # = River
      return (not (entry_direction == Direction.NORTH or exit_direction == Direction.NORTH) and
              not (entry_direction == Direction.SOUTH or exit_direction == Direction.SOUTH))
    return True

  def CanDefeatEnemiesOrGetItemWithoutDoingSo(self, missing_item: int) -> bool:
    if not self.is_drop_item:
      return True
    return self.CanDefeatEnemies(missing_item)

  def CanDefeatEnemiesOrBlockClipOrRightStairs(self, missing_item: int) -> bool:
    if self.room_type in (zelda_constants.DIAMOND_ROOM_TYPE,
                          zelda_constants.RIGHT_STAIRS_ROOM_TYPE):
      return True
    return self.CanDefeatEnemies(missing_item)

  def CanDefeatEnemies(self, missing_item: int) -> bool:
    if (missing_item == zelda_constants.RECORDER and not self.has_mixed_enemies and
        self.enemy_type in zelda_constants.DIGDOGGER_ENEMY_TYPES):
      return False
    if (missing_item == zelda_constants.BOW and not self.has_mixed_enemies and
        self.enemy_type in zelda_constants.GOHMA_ENEMY_TYPES):
      return False
    if missing_item in [zelda_constants.RED_RING, zelda_constants.BLUE_RING]:
      if (not self.has_mixed_enemies and
          self.enemy_type in zelda_constants.HARD_COMBAT_ENEMY_TYPES):
        return False
    return True

  def HasStairwayItem(self) -> bool:
    return self.stairway_item > 0

  def GetStairwayItem(self) -> int:
    return self.stairway_item

  def SetStairwayItem(self, item_type: int) -> None:
    self.stairway_item = item_type

  def HasStairwayPassageRoom(self) -> bool:
    return self.stairway_passage_room >= 0x00

  def GetStairwayPassageRoom(self) -> int:
    return self.stairway_passage_room

  def SetStairwayPassageRoom(self, other_room: int, stairway_num: int) -> None:
    self.stairway_passage_room = other_room
    self.stairway_passage_num = stairway_num

  def GetLeftExit(self) -> int:
    return self.left_exit

  def GetRightExit(self) -> int:
    return self.right_exit

  def SetLevelNumber(self, level_num: int) -> None:
    self.level_num = level_num

  def GetLevelNumber(self) -> int:
    return self.level_num

  def MarkAsVisited(self) -> None:
    self.already_visited = True

  def WasAlreadyVisited(self) -> bool:
    return self.already_visited

  def ClearVisitMark(self) -> None:
    self.already_visited = False

  def GetRoomType(self) -> int:
    return self.room_type

  def GetRoomTypeText(self) -> str:
    if self.room_type in zelda_constants.ROOM_TYPES.keys():
      return zelda_constants.ROOM_TYPES[self.room_type]
    return "room %x?" % self.room_type

  def GetItemType(self) -> int:
    return self.item_type

  def GetItemText(self) -> str:
    stairway_text = ""
    room_item_text = ""
    if self.stairway_item >= 0:
      stairway_text = "S " + zelda_constants.ITEMS[self.stairway_item]
    if self.HasStairwayPassageRoom():
      stairway_text = "Stair #%s" % self.stairway_passage_num
    if (self.item_type != 0x03 and self.item_type in zelda_constants.ITEMS.keys()):
      room_item_text = "%s%s" % ("D " if self.is_drop_item else "",
                                 zelda_constants.ITEMS[self.item_type])

    if self.HasStairwayPassageRoom() and room_item_text != "":
      return "S%d,%s" % (self.stairway_passage_num, room_item_text[0:6])
    if self.stairway_item >= 0 and room_item_text != "":
      return "%s,%s" % (zelda_constants.ITEMS[self.stairway_item][0:5], room_item_text[0:4])
    return "%s%s" % (stairway_text, room_item_text)

  def GetAsciiText(self) -> List[str]:
    string_parts = []
    string_parts.append(
        "-----%s%s-----" % (zelda_constants.WALL_TYPE_CHAR[self.wall_type[Direction.NORTH]][0],
                            zelda_constants.WALL_TYPE_CHAR[self.wall_type[Direction.NORTH]][0]))
    string_parts.append("|%s|" % self.GetEnemyText().center(10, " "))
    string_parts.append(
        "%s%s%s" % (zelda_constants.WALL_TYPE_CHAR[self.wall_type[Direction.WEST]][1],
                    self.GetRoomTypeText().center(10, " "),
                    zelda_constants.WALL_TYPE_CHAR[self.wall_type[Direction.EAST]][1]))
    string_parts.append("|%s|" % str("%s" % self.GetItemText()).center(10, " "))
    string_parts.append(
        "-----%s%s-----" % (zelda_constants.WALL_TYPE_CHAR[self.wall_type[Direction.SOUTH]][0],
                            zelda_constants.WALL_TYPE_CHAR[self.wall_type[Direction.SOUTH]][0]))
    return string_parts
