"""
Pixel Artist 3D Enums and Constants.

Extracted from pixel_artist_3d.py for single responsibility.
Contains: Direction, Faction, InfantryType, TankType, InfantryAnimState.
"""

from __future__ import annotations

from enum import Enum, auto



class InfantryType(Enum):
    """步兵类型枚举"""
    RIFLEMAN = "rifleman"
    MG = "mg"
    AT = "at"
    OFFICER = "officer"
    SNIPER = "sniper"
    MEDIC = "medic"
    ENGINEER = "engineer"
    SCOUT = "scout"


class TankType(Enum):
    """坦克类型枚举 - 基于二战诺曼底战役历史参考"""
    SHERMAN_M4 = "sherman_m4"       # 美军M4谢尔曼中型坦克
    PANTHER_AUSFG = "panther_ausfg"  # 德军豹式G型坦克
    TIGER_I = "tiger_i"              # 德军虎式I型重型坦克


class InfantryAnimState(Enum):
    """步兵动画状态枚举 - 支持多帧行走/射击/死亡动画"""
    IDLE = auto()       # 站立静止
    WALK_1 = auto()     # 左脚前迈
    WALK_2 = auto()     # 右脚前迈
    SHOOT = auto()      # 射击姿态
    PRONE = auto()      # 趴下/匍匐
    DIE_1 = auto()      # 倒地中
    DIE_2 = auto()      # 已倒地
    DEAD = auto()       # 死亡精灵
