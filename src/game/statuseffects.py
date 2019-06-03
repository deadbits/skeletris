from src.game.stats import StatProvider, BasicStatLookup
from src.game.stats import StatTypes
from src.items.item import AppliedStat
import src.utils.colors as colors
import src.game.spriteref as spriteref
import src.game.balance as balance

_UNIQUE_KEY = 0
def _new_unique_key():
    global _UNIQUE_KEY
    _UNIQUE_KEY += 1
    return _UNIQUE_KEY - 1


class StatusEffect(StatProvider):

    def __init__(self, name, duration, color, icon, applied_stats, unique_key=None, player_text=None):
        self.name = name
        self.duration = duration
        self.color = color
        self.icon = icon
        self.applied_stats = applied_stats
        self.player_text = player_text
        self.unique_key = unique_key if unique_key is not None else _new_unique_key()

    def stat_value(self, stat_type, local=False):
        res = 0
        for stat in self.all_applied_stats():
            if stat.stat_type == stat_type and stat.local == local:
                res += stat.value
        return res

    def set_stat_value(self, stat_type, val):
        raise ValueError("can't change stat values of a StatusEffect after the fact.")

    def get_player_text(self):
        """returns: dialog that's shown when the player becomes afflicted with this status."""
        return self.player_text

    def all_applied_stats(self):
        return self.applied_stats

    def get_name(self):
        return self.name

    def get_duration(self):
        return self.duration

    def get_color(self):
        return self.color

    def get_icon(self):
        return self.icon

    def get_unique_key(self):
        return self.unique_key

    def __str__(self):
        return "{}({})".format(self.name, self.duration)

    def __eq__(self, other):
        if isinstance(other, StatusEffect):
            return self.unique_key == other.unique_key
        else:
            return False

    def __hash__(self):
        return hash(self.unique_key)


def new_night_vision_effect(val, duration, player_text=None):
    stats = [AppliedStat(StatTypes.LIGHT_LEVEL, val)]
    return StatusEffect("Night Vision", duration, StatTypes.LIGHT_LEVEL.get_color(),
                        spriteref.status_eye_icon, stats, unique_key="vision",
                        player_text=player_text)


def new_plus_defenses_effect(duration, player_text=None):
    stats = [AppliedStat(StatTypes.DEF, balance.STATUS_EFFECT_PLUS_DEFENSE_VAL)]
    return StatusEffect("Increased Defenses", duration, StatTypes.DEF.get_color(),
                        spriteref.status_shield_icon, stats, unique_key="shield_def_bonus",
                        player_text=player_text)


def new_regen_effect(val, duration, player_text=None):
    stats = [AppliedStat(StatTypes.HP_REGEN, val)]
    return StatusEffect("Regeneration", duration, StatTypes.HP_REGEN.get_color(),
                        spriteref.status_sparkles_icon, stats,
                        player_text=player_text)


def new_poison_effect(val, duration, player_text=None):
    stats = [AppliedStat(StatTypes.POISON, val)]
    return StatusEffect("Poison", duration, StatTypes.POISON.get_color(),
                        spriteref.status_drop_icon, stats,
                        player_text=player_text)


def new_speed_effect(val, duration, player_text=None):
    stats = [AppliedStat(StatTypes.SPEED, val)]
    return StatusEffect("Increased Speed", duration, StatTypes.SPEED.get_color(),
                        spriteref.status_up_arrow_icon, stats,
                        player_text=player_text)


def new_slow_effect(val, duration, player_text=None):
    stats = [AppliedStat(StatTypes.SPEED, val)]
    return StatusEffect("Reduced Speed", duration, colors.DARK_YELLOW,
                        spriteref.status_diagonal_lines_icon, stats,
                        player_text=player_text)