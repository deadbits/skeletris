import random

import pygame

import src.game.spriteref as spriteref
import src.game.soundref as soundref
from src.items import item as item_module
from src.ui.tooltips import TooltipFactory
from src.ui.ui import HealthBarPanel, InventoryPanel, MapPanel, SidePanelTypes, CinematicPanel, TextImage, ItemImage, DialogPanel
from src.renderengine.img import ImageBundle
from src.utils.util import Utils
import src.game.events as events
import src.game.music as music
import src.game.settings as settings
import src.game.globalstate as gs
import src.game.sound_effects as sound_effects
from src.renderengine.engine import RenderEngine
from src.game.inputs import InputState
import src.utils.colors as colors
import src.game.gameengine as gameengine
from src.game.windowstate import WindowState
import src.game.version as version


class MenuManager:

    DEATH_MENU = 0
    DEATH_OPTION_MENU = 0.5
    IN_GAME_MENU = 1
    START_MENU = 2
    CINEMATIC_MENU = 3
    PAUSE_MENU = 4
    CONTROLS_MENU = 5
    KEYBINDING_MENU = 7
    DEBUG_OPTION_MENU = 8
    SETTINGS_MENU = 9
    TEXT_MENU = 10
    TITLE_MENU = 11
    REALLY_QUIT = 12
    YOU_WIN_MENU = 13
    CREDITS_MENU = 14

    def __init__(self, menu):
        self._active_menu = TitleMenu()
        self._next_active_menu = menu

    def update(self):
        render_eng = RenderEngine.get_instance()
        world = gs.get_instance().get_world()

        if self._next_active_menu is not None:
            for bun in self._active_menu.all_bundles():
                render_eng.remove(bun)

            self._active_menu.cleanup()

            self._active_menu = self._next_active_menu

            new_song = self._active_menu.get_song()
            if new_song is not None:
                music.play_song(new_song)

            self._next_active_menu = None

            if not self.should_draw_world():
                render_eng.set_clear_color(*self._active_menu.get_clear_color())
                for layer in spriteref.WORLD_LAYERS:
                    render_eng.hide_layer(layer)
            else:
                for layer in spriteref.WORLD_LAYERS:
                    render_eng.show_layer(layer)
                c_xy = self.get_active_menu().get_camera_center_point_on_screen()
                if c_xy is not None:
                    gs.get_instance().set_camera_center_on_screen(c_xy[0], c_xy[1])

        else:
            if world is None and self.should_draw_world():
                # expected sometimes~
                pass
            else:
                self.get_active_menu().update(world)

                c_xy = self.get_active_menu().get_camera_center_point_on_screen()
                if c_xy is not None:
                    cur_center = gs.get_instance().get_camera_center_on_screen()
                    if cur_center != c_xy:
                        if Utils.dist(c_xy, cur_center) <= 2:
                            gs.get_instance().set_camera_center_on_screen(c_xy[0], c_xy[1])
                        else:
                            new_center = Utils.round(Utils.linear_interp(cur_center, c_xy, 0.12))
                            gs.get_instance().set_camera_center_on_screen(new_center[0], new_center[1])

                input_state = InputState.get_instance()
                if input_state.mouse_in_window():
                    xy = input_state.mouse_pos()
                    cursor = self.get_active_menu().cursor_style_at(world, xy)
                else:
                    cursor = None
                if cursor is None:
                    pygame.mouse.set_cursor(*spriteref.UI.Cursors.invisible_cursor)
                else:
                    pygame.mouse.set_cursor(*cursor)

    def should_draw_world(self):
        return self._active_menu.keep_drawing_world_underneath()

    def pause_world_updates(self):
        return self.get_active_menu_id() != MenuManager.IN_GAME_MENU

    def get_active_menu(self):
        return self._active_menu

    def get_active_menu_id(self):
        if self._active_menu is not None:
            return self._active_menu.get_type()
        else:
            return None

    def set_active_menu(self, menu):
        if menu is None:
            raise ValueError("Can't set null menu")

        self._next_active_menu = menu

    def get_world_menu_if_active(self):
        active = self.get_active_menu()
        if active is not None and active.get_type() == MenuManager.IN_GAME_MENU:
            return active
        else:
            return None


class Menu:

    def __init__(self, menu_type):
        self._menu_type = menu_type
        self._active_tooltip = None

    def get_clear_color(self):
        return (0, 0, 0)

    def get_type(self):
        return self._menu_type

    def update(self, world):
        pass

    def get_song(self):
        return None

    def all_bundles(self):
        tooltip = self.get_active_tooltip()
        if tooltip is not None:
            for bun in tooltip.all_bundles():
                yield bun
        else:
            return []

    def cleanup(self):
        pass

    def keep_drawing_world_underneath(self):
        return False

    def get_camera_center_point_on_screen(self):
        return None

    def get_active_tooltip(self):
        return self._active_tooltip

    def set_active_tooltip(self, tooltip):
        if self._active_tooltip is not None:
            self._destroy_panel(self._active_tooltip)
        self._active_tooltip = tooltip

    def _destroy_panel(self, panel):
        if panel is not None:
            bundles = panel.all_bundles()
            RenderEngine.get_instance().clear_bundles(bundles)

    def cursor_style_at(self, world, xy):
        return pygame.cursors.arrow


class OptionsMenu(Menu):

    def __init__(self, menu_id, title, options, title_size=5):
        """
        title: text or sprite
        options: list of strings
        title_size: scale of title text or sprite
        """
        Menu.__init__(self, menu_id)

        if isinstance(title, str):
            self.title_text = title
            self.title_sprite = None
        else:
            self.title_sprite = title
            self.title_text = None

        self.title_size = title_size
        self.options_text = options

        self.spacing = 8
        self.title_spacing = self.spacing * 4

        self._title_img = None
        self._title_rect = None    # tuple(x, y, w, h)
        self._option_rects = None  # list of tuple(x, y, w, h)
        self._option_imgs = None   # list of ImgBundle
        self._selection = 0

    def get_clear_color(self):
        return (0, 0, 0)

    def get_song(self):
        return music.Songs.CONTINUE_CURRENT

    def get_title_color(self):
        return (1, 1, 1)

    def get_enabled(self, idx):
        return True

    def get_option_color(self, idx):
        if self.get_enabled(idx):
            if idx == self._selection:
                return (1, 0, 0)
            else:
                return colors.WHITE
        else:
            return colors.DARK_GRAY

    def get_option_text(self, idx):
        return self.options_text[idx]

    def get_num_options(self):
        return len(self.options_text)

    def build_images(self):
        self.build_title_img()
        self.build_option_imgs()

    def build_title_img(self):
        if self.title_text is not None:
            if self._title_img is None:
                self._title_img = TextImage(0, 0, self.title_text, layer=spriteref.UI_0_LAYER,
                                            color=self.get_title_color(), scale=self.title_size)
        elif self.title_sprite is not None:
            if self._title_img is None:
                self._title_img = ImageBundle(self.title_sprite, 0, 0, spriteref.UI_0_LAYER,
                                              color=self.get_title_color(), scale=self.title_size)

    def build_option_imgs(self):
        if self._option_imgs is None:
            self._option_imgs = [None] * self.get_num_options()

        for i in range(0, self.get_num_options()):
            if self._option_imgs[i] is None:
                self._option_imgs[i] = TextImage(0, 0, self.get_option_text(i), layer=spriteref.UI_0_LAYER,
                                                 color=self.get_option_color(i), scale=2)

    def layout_rects(self):
        if self._title_rect is None:
            self._title_rect = (0, 0, 0, 0)
        if self._option_rects is None:
            self._option_rects = [(0, 0, 0, 0)] * self.get_num_options()

        total_height = 0
        if self._title_img is not None:
            total_height += self._title_img.size()[1] + self.title_spacing
        for opt in self._option_imgs:
            if opt is not None:
                total_height += opt.size()[1] + self.spacing
        total_height -= self.spacing

        y_pos = WindowState.get_instance().get_screen_size()[1] // 2 - total_height // 2
        if self._title_img is not None:
            title_x = WindowState.get_instance().get_screen_size()[0] // 2 - self._title_img.size()[0] // 2
            self._title_rect = (title_x, y_pos, self._title_img.size()[0], self._title_img.size()[1])
            y_pos += self._title_img.size()[1] + self.title_spacing

        for i in range(0, self.get_num_options()):
            if self._option_imgs[i] is not None:
                opt_x = WindowState.get_instance().get_screen_size()[0] // 2 - self._option_imgs[i].size()[0] // 2
                self._option_rects[i] = (opt_x, y_pos, self._option_imgs[i].size()[0], self._option_imgs[i].size()[1])
                y_pos += self._option_imgs[i].size()[1] + self.spacing

    def update_imgs(self):
        if self._title_img is not None:
            x = self._title_rect[0]
            y = self._title_rect[1]
            self._title_img = self._title_img.update(new_x=x, new_y=y, new_color=self.get_title_color())

        for i in range(0, self.get_num_options()):
            color = self.get_option_color(i)
            x = self._option_rects[i][0]
            y = self._option_rects[i][1]
            self._option_imgs[i] = self._option_imgs[i].update(new_x=x, new_y=y, new_color=color)

    def set_selected(self, idx):
        if idx != self._selection and self.get_enabled(idx):
            sound_effects.play_sound(soundref.menu_move)
            self._selection = idx

    def handle_inputs(self, world):
        input_state = InputState.get_instance()
        if input_state.was_pressed(gs.get_instance().settings().exit_key()):
            self.esc_pressed()
        else:
            new_selection = self._selection
            dy = 0
            up_pressed = input_state.was_pressed(gs.get_instance().settings().menu_up_key())
            up_pressed = up_pressed or input_state.was_pressed(gs.get_instance().settings().up_key())
            if up_pressed:
                dy -= 1

            down_pressed = input_state.was_pressed(gs.get_instance().settings().menu_down_key())
            down_pressed = down_pressed or input_state.was_pressed(gs.get_instance().settings().down_key())
            if down_pressed:
                dy += 1

            if dy != 0:
                for i in range(1, self.get_num_options() + 1):
                    new_selection = (self._selection + i*dy) % self.get_num_options()
                    if self.get_enabled(new_selection):
                        break

            self.set_selected(new_selection)

            if input_state.was_pressed(gs.get_instance().settings().enter_key()):
                if self.get_enabled(self._selection):
                    self.option_activated(self._selection)
                else:
                    sound_effects.play_sound(soundref.menu_back)

            if self._option_rects is None:
                return

            if input_state.mouse_in_window():
                pos = input_state.mouse_pos()
                if input_state.mouse_moved():
                    for i in range(0, self.get_num_options()):
                        if self._option_rects[i] is not None and Utils.rect_contains(self._option_rects[i], pos):
                            self.set_selected(i)

                if input_state.mouse_was_pressed():
                    clicked_option = None

                    selected_rect = self._option_rects[self._selection]
                    if selected_rect is not None:
                        # give click priority to the thing that's selected
                        bigger_rect = Utils.rect_expand(selected_rect,
                                                        left_expand=15, right_expand=15,
                                                        up_expand=15, down_expand=15)
                        if Utils.rect_contains(bigger_rect, pos):
                            clicked_option = self._selection

                    if clicked_option is None:
                        # if the mouse hasn't moved yet on this menu, gotta catch those clicks too
                        for i in range(0, self.get_num_options()):
                            if self._option_rects[i] is not None and Utils.rect_contains(self._option_rects[i], pos):
                                clicked_option = i
                                break

                    if clicked_option is not None:
                        if self.get_enabled(clicked_option):
                            self.option_activated(self._selection)
                        else:
                            pass  # TODO sound effect

    def update(self, world):
        self.build_images()
        self.layout_rects()
        self.update_imgs()

        self.handle_inputs(world)

        render_eng = RenderEngine.get_instance()
        for bun in self.all_bundles():
            render_eng.update(bun)

    def get_back_idx(self):
        return -1

    def option_activated(self, idx):
        pass

    def esc_pressed(self):
        pass

    def keep_drawing_world_underneath(self):
        return False

    def all_bundles(self):
        if self._title_img is not None:
            for bun in self._title_img.all_bundles():
                yield bun
        if self._option_imgs is not None:
            for opt in self._option_imgs:
                if opt is not None:
                    for bun in opt.all_bundles():
                        yield bun

    def cursor_style_at(self, world, xy):
        return super().cursor_style_at(world, xy)


class StartMenu(OptionsMenu):

    START_OPT = 0
    OPTIONS_OPT = 1
    SOUND_OPT = 2
    EXIT_OPT = 3

    def __init__(self):
        OptionsMenu.__init__(self,
                             MenuManager.START_MENU,
                             spriteref.title_img,
                             ["start", "controls", "sound", "exit"],
                             title_size=6)

        self.version_text = "[{}]".format(version.get_pretty_version_string())
        self.version_img = None
        self.version_rect = [0, 0, 0, 0]

    def build_images(self):
        super().build_images()

        if self.version_text is not None:
            if self.version_img is None:
                self.version_img = TextImage(0, 0, self.version_text, spriteref.UI_0_LAYER)

    def layout_rects(self):
        super().layout_rects()

        if self.version_img is not None:
            scr_w, scr_h = WindowState.get_instance().get_screen_size()
            x = scr_w - self.version_img.w() - 4
            y = scr_h - self.version_img.h() - 4
            self.version_rect = [x, y, self.version_img.w(), self.version_img.h()]

    def update_imgs(self):
        super().update_imgs()

        if self.version_img is not None:
            self.version_img = self.version_img.update(new_x=self.version_rect[0],
                                                       new_y=self.version_rect[1],
                                                       new_color=colors.LIGHT_GRAY)

    def get_song(self):
        return music.Songs.MENU_THEME

    def option_activated(self, idx):
        if idx == StartMenu.START_OPT:
            gs.get_instance().event_queue().add(events.NewGameEvent(instant_start=True))
            sound_effects.play_sound(soundref.newgame_start)
        elif idx == StartMenu.EXIT_OPT:
            gs.get_instance().event_queue().add(events.GameExitEvent())
        elif idx == StartMenu.OPTIONS_OPT:
            gs.get_instance().menu_manager().set_active_menu(ControlsMenu(MenuManager.START_MENU))
            sound_effects.play_sound(soundref.menu_select)
        elif idx == StartMenu.SOUND_OPT:
            gs.get_instance().menu_manager().set_active_menu(SoundSettingsMenu(MenuManager.START_MENU))
            sound_effects.play_sound(soundref.menu_select)

    def esc_pressed(self):
        gs.get_instance().menu_manager().set_active_menu(TitleMenu())
        sound_effects.play_sound(soundref.menu_back)

    def all_bundles(self):
        for bun in super().all_bundles():
            yield bun
        if self.version_img is not None:
            for bun in self.version_img.all_bundles():
                yield bun


class PauseMenu(OptionsMenu):

    CONTINUE_IDX = 0
    CONTROLS_IDX = 1
    SOUND_IDX = 2
    EXIT_IDX = 3

    def __init__(self):
        OptionsMenu.__init__(self, MenuManager.PAUSE_MENU, "paused", ["resume", "controls", "sound", "quit"])

    def option_activated(self, idx):
        if idx == PauseMenu.EXIT_IDX:
            gs.get_instance().menu_manager().set_active_menu(ReallyQuitMenu())
            sound_effects.play_sound(soundref.menu_select)
        elif idx == PauseMenu.CONTROLS_IDX:
            gs.get_instance().menu_manager().set_active_menu(ControlsMenu(MenuManager.IN_GAME_MENU))
            sound_effects.play_sound(soundref.menu_select)
        elif idx == PauseMenu.CONTINUE_IDX:
            gs.get_instance().menu_manager().set_active_menu(InGameUiState())
            sound_effects.play_sound(soundref.pause_out)
        elif idx == PauseMenu.SOUND_IDX:
            gs.get_instance().menu_manager().set_active_menu(SoundSettingsMenu(MenuManager.PAUSE_MENU))
            sound_effects.play_sound(soundref.menu_select)

    def esc_pressed(self):
        self.option_activated(PauseMenu.CONTINUE_IDX)


class ReallyQuitMenu(OptionsMenu):

    EXIT_IDX = 0
    BACK = 1

    def __init__(self):
        OptionsMenu.__init__(self, MenuManager.REALLY_QUIT, "really quit?", ["quit", "back"])

    def option_activated(self, idx):
        OptionsMenu.option_activated(self, idx)
        if idx == ReallyQuitMenu.EXIT_IDX:
            gs.get_instance().menu_manager().set_active_menu(StartMenu())
            sound_effects.play_sound(soundref.game_quit)
        elif idx == ReallyQuitMenu.BACK:
            gs.get_instance().menu_manager().set_active_menu(PauseMenu())
            sound_effects.play_sound(soundref.menu_back)

    def esc_pressed(self):
        self.option_activated(ReallyQuitMenu.BACK)


class TextOnlyMenu(OptionsMenu):

    def __init__(self, text, next_menu, auto_advance_duration=None, fade_back_to_world_duration=30):
        OptionsMenu.__init__(self, MenuManager.TEXT_MENU, text, ["~hidden~"])

        self.fade_back_to_world_duration = fade_back_to_world_duration
        self.next_menu = next_menu

        # to automatically advance the text menu
        self.count = 0
        self.auto_advance_duration = auto_advance_duration

    def get_clear_color(self):
        return (0, 0, 0)

    def get_option_color(self, idx):
        return self.get_clear_color()

    def handle_inputs(self, world):
        do_advance = InputState.get_instance().was_anything_pressed()

        if self.auto_advance_duration is not None:
            self.count += 1
            if self.count > self.auto_advance_duration:
                do_advance = True

        if do_advance:
            gs.get_instance().menu_manager().set_active_menu(self.next_menu)

            if self.fade_back_to_world_duration > 0 and self.next_menu.get_type() == MenuManager.IN_GAME_MENU:
                gs.get_instance().do_fade_sequence(1.0, 0.0, self.fade_back_to_world_duration)
                gs.get_instance().pause_world_updates(self.fade_back_to_world_duration // 2)


class SoundSettingsMenu(OptionsMenu):
    MUSIC_TOGGLE_IDX = 0
    MUSIC_VOLUME_UP_IDX = 1
    MUSIC_VOLUME_DOWN_IDX = 2

    EFFECTS_TOGGLE_IDX = 3
    EFFECTS_VOLUME_UP_IDX = 4
    EFFECTS_VOLUME_DOWN_IDX = 5

    BACK_IDX = 6

    def __init__(self, prev_id):
        OptionsMenu.__init__(self, MenuManager.SETTINGS_MENU, "sound", ["~music toggle~",
                                                                        "+10% music", "-10% music",
                                                                        "~effects toggle~",
                                                                        "+10% effects", "-10% effects",
                                                                        "back"])
        self.prev_id = prev_id

        self.music_pcnt = gs.get_instance().settings().get(settings.MUSIC_VOLUME)
        self.music_muted = self.music_pcnt == 0 or gs.get_instance().settings().get(settings.MUSIC_MUTED)

        self.effects_pcnt = gs.get_instance().settings().get(settings.EFFECTS_VOLUME)
        self.effects_muted = self.effects_pcnt == 0 or gs.get_instance().settings().get(settings.EFFECTS_MUTED)

    def get_option_text(self, idx):
        if idx == SoundSettingsMenu.MUSIC_TOGGLE_IDX:
            if not self.music_muted:
                return "music: {}%".format(self.music_pcnt)
            else:
                return "music: OFF"
        elif idx == SoundSettingsMenu.EFFECTS_TOGGLE_IDX:
            if not self.effects_muted:
                return "effects: {}%".format(self.effects_pcnt)
            else:
                return "effects: OFF"
        else:
            return OptionsMenu.get_option_text(self, idx)

    def option_activated(self, idx):
        rebuild = False
        if idx == SoundSettingsMenu.MUSIC_TOGGLE_IDX:
            new_val = not self.music_muted
            gs.get_instance().settings().set(settings.MUSIC_MUTED, new_val)

            if new_val is False and self.music_pcnt == 0:
                gs.get_instance().settings().set(settings.MUSIC_VOLUME, 10)

            gs.get_instance().save_settings_to_disk()
            rebuild = True
            sound_effects.play_sound(soundref.menu_select)

        elif idx == SoundSettingsMenu.EFFECTS_TOGGLE_IDX:
            new_val = not self.effects_muted
            gs.get_instance().settings().set(settings.EFFECTS_MUTED, new_val)

            if new_val is False and self.effects_pcnt == 0:
                gs.get_instance().settings().set(settings.EFFECTS_VOLUME, 10)

            gs.get_instance().save_settings_to_disk()
            rebuild = True
            sound_effects.play_sound(soundref.menu_select)

        elif idx == SoundSettingsMenu.MUSIC_VOLUME_UP_IDX or idx == SoundSettingsMenu.MUSIC_VOLUME_DOWN_IDX:
            change = 10 if idx == SoundSettingsMenu.MUSIC_VOLUME_UP_IDX else -10
            new_vol = Utils.bound(self.music_pcnt + change, 0, 100)
            if new_vol == 0:
                gs.get_instance().settings().set(settings.MUSIC_MUTED, True)
            else:
                gs.get_instance().settings().set(settings.MUSIC_MUTED, False)
            gs.get_instance().settings().set(settings.MUSIC_VOLUME, new_vol)

            gs.get_instance().save_settings_to_disk()
            rebuild = True
            sound_effects.play_sound(soundref.menu_select)

        elif idx == SoundSettingsMenu.EFFECTS_VOLUME_UP_IDX or idx == SoundSettingsMenu.EFFECTS_VOLUME_DOWN_IDX:
            change = 10 if idx == SoundSettingsMenu.EFFECTS_VOLUME_UP_IDX else -10
            new_vol = Utils.bound(self.effects_pcnt + change, 0, 100)
            if new_vol == 0:
                gs.get_instance().settings().set(settings.EFFECTS_MUTED, True)
            else:
                gs.get_instance().settings().set(settings.EFFECTS_MUTED, False)
            gs.get_instance().settings().set(settings.EFFECTS_VOLUME, new_vol)

            gs.get_instance().save_settings_to_disk()
            rebuild = True
            sound_effects.play_sound(soundref.menu_select)

        elif idx == SoundSettingsMenu.BACK_IDX:
            if self.prev_id == MenuManager.START_MENU:
                gs.get_instance().menu_manager().set_active_menu(StartMenu())
            else:
                gs.get_instance().menu_manager().set_active_menu(PauseMenu())
            sound_effects.play_sound(soundref.menu_back)

        if rebuild:
            # rebuilding so the option text will change
            rebuilt = SoundSettingsMenu(self.prev_id)
            rebuilt.set_selected(idx)
            gs.get_instance().menu_manager().set_active_menu(rebuilt)

    def esc_pressed(self):
        self.option_activated(SoundSettingsMenu.BACK_IDX)


class ControlsMenu(OptionsMenu):

    OPTS = [
        ("move up", settings.KEY_UP),
        ("move left", settings.KEY_LEFT),
        ("move down", settings.KEY_DOWN),
        ("move right", settings.KEY_RIGHT),
        ("skip turn", settings.KEY_SKIP_TURN),
        ("rotate item", settings.KEY_ROTATE_CW),
        ("inventory", settings.KEY_INVENTORY),
        ("map", settings.KEY_MAP),
        # ("help", settings.KEY_HELP)
    ]
    BACK_OPT_IDX = len(OPTS)

    def __init__(self, prev_id):
        OptionsMenu.__init__(self, MenuManager.CONTROLS_MENU, "controls", ["~unused~"])
        self.prev_id = prev_id

    def get_option_text(self, idx):
        if idx == ControlsMenu.BACK_OPT_IDX:
            return "back"
        else:
            opt = ControlsMenu.OPTS[idx]
            cur_values = gs.get_instance().settings().get(opt[1])

            if len(cur_values) == 0:
                return "{} [None]".format(opt[0])
            else:
                cur_value_strings = [Utils.stringify_key(k) for k in cur_values]
                value_str = "[" + ", ".join(cur_value_strings) + "]"

                return "{} {}".format(opt[0], value_str)

    def get_num_options(self):
        return len(ControlsMenu.OPTS) + 1  # extra one is the "back" option

    def option_activated(self, idx):
        if idx == ControlsMenu.BACK_OPT_IDX:
            if self.prev_id == MenuManager.START_MENU:
                gs.get_instance().menu_manager().set_active_menu(StartMenu())
            else:
                gs.get_instance().menu_manager().set_active_menu(PauseMenu())
            sound_effects.play_sound(soundref.menu_back)
        else:
            opt = ControlsMenu.OPTS[idx]
            gs.get_instance().menu_manager().set_active_menu(KeybindingEditMenu(opt[1], opt[0], lambda: ControlsMenu(self.prev_id)))
            sound_effects.play_sound(soundref.menu_select)

    def esc_pressed(self):
        self.option_activated(ControlsMenu.BACK_OPT_IDX)


class KeybindingEditMenu(OptionsMenu):

    def __init__(self, setting, setting_name, return_menu_builder):
        """
        return_menu_builder: lambda () -> Menu
        """
        OptionsMenu.__init__(self, MenuManager.KEYBINDING_MENU, "edit " + setting_name,
                             ["press new key"])

        self._setting = setting
        self._return_menu_builder = return_menu_builder

    def option_activated(self, idx):
        pass

    def get_option_color(self, idx):
        return (1, 1, 1)

    def esc_pressed(self):
        gs.get_instance().menu_manager().set_active_menu(self._return_menu_builder())
        sound_effects.play_sound(soundref.menu_back)

    def handle_inputs(self, world):
        input_state = InputState.get_instance()
        if input_state.was_pressed(gs.get_instance().settings().exit_key()):
            self.esc_pressed()
        else:
            pressed = input_state.all_pressed_keys()
            pressed = [x for x in pressed if self._is_valid_binding(x)]
            if len(pressed) > 0:
                key = random.choice(pressed)  # TODO - better way to handle this?
                gs.get_instance().settings().set(self._setting, [key])
                gs.get_instance().save_settings_to_disk()
                gs.get_instance().menu_manager().set_active_menu(self._return_menu_builder())

                sound_effects.play_sound(soundref.menu_select)

    def _is_valid_binding(self, key):
        if key in (pygame.K_RETURN, pygame.K_ESCAPE, "MOUSE_BUTTON_1"):
            return False

        return True


class CinematicMenu(Menu):

    def __init__(self):
        Menu.__init__(self, MenuManager.CINEMATIC_MENU)
        self.active_scene = None

        self.letter_reveal_speed = 3
        self.active_tick_count = 0  # how many ticks the current cinematic has been showing

        self.cinematic_panel = None

    def get_song(self):
        # each scene will specify its song
        return music.Songs.CONTINUE_CURRENT

    def update(self, world):
        if self.active_scene is None:
            cine_queue = gs.get_instance().get_cinematics_queue()
            if len(cine_queue) == 0:
                gs.get_instance().menu_manager().set_active_menu(InGameUiState())
                return
            else:
                self.active_scene = cine_queue.pop(0)
                self.active_tick_count = 0
                music.play_song(self.active_scene.music_id)

        if self.active_scene is not None:
            if self.cinematic_panel is None:
                self.cinematic_panel = CinematicPanel()

            img_idx = (gs.get_instance().anim_tick // 2) % len(self.active_scene.images)
            current_image = self.active_scene.images[img_idx]
            num_chars_to_display = 1 + self.active_tick_count // self.letter_reveal_speed
            text_finished_scrolling = len(self.active_scene.text) <= num_chars_to_display
            full_text = self.active_scene.text

            if text_finished_scrolling:
                current_text = full_text
            else:
                vis_text = full_text[0:num_chars_to_display]
                invis_text = full_text[num_chars_to_display:]
                invis_text = Utils.replace_all_except(invis_text, TextImage.INVISIBLE_CHAR, except_for=(" ", "\n"))

                current_text = vis_text + invis_text

            self.cinematic_panel.update(current_image, current_text)

            dismiss_keys = gs.get_instance().settings().all_dialog_dismiss_keys()

            if self.active_tick_count > 10 and InputState.get_instance().was_pressed(dismiss_keys):
                if text_finished_scrolling:
                    self.active_scene = None
                else:
                    self.active_tick_count = len(full_text) * self.letter_reveal_speed

            self.active_tick_count += 1

        render_eng = RenderEngine.get_instance()
        for bun in self.all_bundles():
            render_eng.update(bun)

    def get_clear_color(self):
        return (0.0, 0.0, 0.0)

    def keep_drawing_world_underneath(self):
        return False

    def all_bundles(self):
        for bun in Menu.all_bundles(self):
            yield bun
        if self.cinematic_panel is not None:
            for bun in self.cinematic_panel.all_bundles():
                yield bun


class FadingInFlavorMenu(OptionsMenu):
    """Displays some flavor text, then becomes a new menu"""

    def __init__(self, menu_type, flavor_text, next_menu, auto_next=False):
        OptionsMenu.__init__(self, menu_type, flavor_text, ["~hidden~"], title_size=3)
        self._flavor_full_brightness_duration = 100
        self._total_duration = 120
        self._flavor_tick = 0
        self._auto_next = auto_next

        self._next_menu = next_menu

    def get_clear_color(self):
        return (0, 0, 0)

    def get_flavor_progress(self):
        return Utils.bound(self._flavor_tick / self._flavor_full_brightness_duration, 0.0, 1.0)

    def get_title_color(self):
        return Utils.linear_interp(self.get_clear_color(), (1, 1, 1), self.get_flavor_progress())

    def get_option_color(self, idx):
        return self.get_clear_color()

    def update(self, world):
        OptionsMenu.update(self, world)

        self._flavor_tick += 1

        if self._flavor_tick > 5 and InputState.get_instance().was_anything_pressed():
            sound_effects.play_sound(soundref.menu_select)
            if self._flavor_tick >= self._total_duration - 10:
                gs.get_instance().menu_manager().set_active_menu(self._next_menu)
            else:
                self._flavor_tick = self._total_duration - 10
                self._auto_next = True

        elif self._flavor_tick >= self._total_duration and self._auto_next:
            gs.get_instance().menu_manager().set_active_menu(self._next_menu)

    def get_song(self):
        return None

    def option_activated(self, idx):
        pass


class DeathMenu(FadingInFlavorMenu):

    ALL_FLAVOR = [
        "pain!",
        "fail!",
        "dead!",
        "bad!",
        "no!",
        "you died!",
        "epic run!",
        "ouch!"
    ]

    def get_flavor_text(self):
        idx = int(random.random() * len(DeathMenu.ALL_FLAVOR))
        return DeathMenu.ALL_FLAVOR[idx]

    def __init__(self):
        FadingInFlavorMenu.__init__(self, MenuManager.DEATH_MENU, self.get_flavor_text(),
                                    DeathOptionMenu(), auto_next=True)


class DeathOptionMenu(OptionsMenu):

    RETRY = 0
    EXIT_OPT = 1

    def __init__(self):
        OptionsMenu.__init__(self, MenuManager.DEATH_OPTION_MENU, "game over", ["retry", "quit"])

    def get_song(self):
        return None

    def option_activated(self, idx):
        if idx == DeathOptionMenu.EXIT_OPT:
            gs.get_instance().event_queue().add(events.NewGameEvent(instant_start=False))
            sound_effects.play_sound(soundref.game_quit)
        elif idx == DeathOptionMenu.RETRY:
            gs.get_instance().event_queue().add(events.NewGameEvent(instant_start=True))
            sound_effects.play_sound(soundref.newgame_start)


class DebugMenu(OptionsMenu):

    STORYLINE_ZONE_JUMP = 0
    SPECIAL_ZONE_JUMP = 1
    LOOT_ZONE_JUMP = 2
    EXIT_OPT = 3

    def __init__(self):
        OptionsMenu.__init__(self, MenuManager.DEBUG_OPTION_MENU, "debug menu",
                             ["storyline zones", "special zones", "loot zones", "back"])

    def get_song(self):
        return music.Songs.CONTINUE_CURRENT

    def esc_pressed(self):
        self.option_activated(DebugMenu.EXIT_OPT)

    def option_activated(self, idx):
        if idx == DebugMenu.STORYLINE_ZONE_JUMP:
            gs.get_instance().menu_manager().set_active_menu(DebugZoneSelectMenu(0, DebugZoneSelectMenu.STORYLINE))
            sound_effects.play_sound(soundref.menu_select)
        elif idx == DebugMenu.SPECIAL_ZONE_JUMP:
            gs.get_instance().menu_manager().set_active_menu(DebugZoneSelectMenu(0, DebugZoneSelectMenu.HANDBUILT))
            sound_effects.play_sound(soundref.menu_select)
        elif idx == DebugMenu.LOOT_ZONE_JUMP:
            gs.get_instance().menu_manager().set_active_menu(DebugZoneSelectMenu(0, DebugZoneSelectMenu.LOOT))
            sound_effects.play_sound(soundref.menu_select)
        elif idx == DebugMenu.EXIT_OPT:
            gs.get_instance().menu_manager().set_active_menu(InGameUiState())
            sound_effects.play_sound(soundref.menu_back)


class YouWinMenu(FadingInFlavorMenu):

    def __init__(self, total_time, turn_count, kill_count):
        FadingInFlavorMenu.__init__(self, MenuManager.YOU_WIN_MENU, "You Win!",
                                    YouWinStats(total_time, turn_count, kill_count),
                                    auto_next=True)

    def get_song(self):
        return music.Songs.CONTINUE_CURRENT


class YouWinStats(FadingInFlavorMenu):

    def __init__(self, total_time, turn_count, kill_count):
        text = ["Time:  {}".format(Utils.ticks_to_time_string(total_time, 60)),
                "Turns: {}".format(turn_count),
                "Kills: {}".format(kill_count)]

        FadingInFlavorMenu.__init__(self, MenuManager.YOU_WIN_MENU, "\n".join(text), CreditsMenu(), auto_next=False)

    def get_song(self):
        return music.Songs.CONTINUE_CURRENT


class CreditsMenu(Menu):

    SMALL = 2
    NORMAL = 3

    SLIDE_TEXT = [
        ("created by", SMALL),
        "David Pendergast",
        ("2019", SMALL),
        "",
        ("art, coding, design, and music by", SMALL),
        "David Pendergast",
        "",
        ("twitter", SMALL),
        "@Ghast_NEOH",
        "",
        ("github", SMALL),
        "davidpendergast",
        "",
        # why does the name have to be sooo long omg
        #("sound effects from", SMALL),
        #("The Essential Retro Video Game ", NORMAL),
        #("Sound Effects Collection", NORMAL),
        #("by Juhani Junkala", SMALL),
        #("released under CC0", SMALL),
        #"",
        ("made with pygame <3", SMALL)
    ]

    def __init__(self):
        Menu.__init__(self, MenuManager.CREDITS_MENU)
        self.scroll_speeds = (1.5, 4)  # pixels per tick
        self.scroll_speed_idx = 0
        self.tick_count = 0
        self.empty_line_height = 160
        self.text_y_spacing = 10

        self.scroll_y_pos = 0  # distance from bottom of screen

        self._text_lines = [l for l in CreditsMenu.SLIDE_TEXT]
        self._all_images = []

        self._onscreen_img_indexes = set()

        self.build_images()

    def _scroll_speed(self):
        return self.scroll_speeds[self.scroll_speed_idx]

    def build_images(self):
        for line in self._text_lines:
            if line == "":
                self._all_images.append(None)
            else:
                if isinstance(line, tuple):
                    text = line[0]
                    size = line[1]
                else:
                    text = line
                    size = CreditsMenu.NORMAL

                self._all_images.append(TextImage(0, 0, text, spriteref.UI_0_LAYER, scale=size))

    def update(self, world):
        self.tick_count += 1

        enter_keys = gs.get_instance().settings().enter_key()
        if self.tick_count > 5 and InputState.get_instance().was_pressed(enter_keys):
            self.scroll_speed_idx = (self.scroll_speed_idx + 1) % len(self.scroll_speeds)

        self.scroll_y_pos += self._scroll_speed()

        screen_size = WindowState.get_instance().get_screen_size()
        y_pos = screen_size[1] - int(self.scroll_y_pos)

        for i in range(0, len(self._all_images)):
            text_img = self._all_images[i]
            if text_img is None:
                y_pos += self.empty_line_height
            else:
                w = text_img.w()
                x_pos = screen_size[0] // 2 - w // 2
                text_img = text_img.update(new_x=x_pos, new_y=y_pos)
                self._all_images[i] = text_img

                RenderEngine.get_instance().update(text_img)

                y_pos += text_img.h() + self.text_y_spacing

        if y_pos < 0:
            gs.get_instance().menu_manager().set_active_menu(StartMenu())

    def all_bundles(self):
        for bun in super().all_bundles():
            yield bun
        for text_img in self._all_images:
            if text_img is not None:
                for bun in text_img.all_bundles():
                    yield bun

    def get_song(self):
        return music.Songs.CONTINUE_CURRENT


class DebugZoneSelectMenu(OptionsMenu):
    ZONES_PER_PAGE = 8

    STORYLINE = "storyline"
    HANDBUILT = "hand_built"
    LOOT = "loot"

    def __init__(self, page, zone_types):

        self.page = page
        self.zone_types = zone_types

        all_zones = self._zones_to_show()
        start_idx = DebugZoneSelectMenu.ZONES_PER_PAGE * page
        self.first_page = (page == 0)

        if start_idx >= len(all_zones):
            # hmm..
            self.opts = []
            self.last_page = True
        elif start_idx + DebugZoneSelectMenu.ZONES_PER_PAGE < len(all_zones):
            self.opts = all_zones[start_idx:start_idx + DebugZoneSelectMenu.ZONES_PER_PAGE]
            self.last_page = False
        else:
            self.opts = all_zones[start_idx:]
            self.last_page = True

        self.opts.append("next page")
        self.next_page_idx = len(self.opts) - 1

        self.opts.append("prev page")
        self.prev_page_idx = len(self.opts) - 1

        self.opts.append("back")
        self.back_idx = len(self.opts) - 1

        OptionsMenu.__init__(self, MenuManager.DEBUG_OPTION_MENU, "zone select", self.opts)

    def _zones_to_show(self):
        import src.worldgen.zones as zones
        if self.zone_types == DebugZoneSelectMenu.HANDBUILT:
            all_zones = zones.all_handbuilt_zone_ids()
        elif self.zone_types == DebugZoneSelectMenu.STORYLINE:
            all_zones = zones.all_storyline_zone_ids()
        elif self.zone_types == DebugZoneSelectMenu.LOOT:
            all_zones = zones.all_loot_zone_ids()
        else:
            all_zones = []

        all_zones.sort(key=lambda z_id: zones.get_zone(z_id).get_level())
        return all_zones

    def get_enabled(self, idx):
        if idx == self.prev_page_idx and self.first_page:
            return False
        elif idx == self.next_page_idx and self.last_page:
            return False
        else:
            return True

    def esc_pressed(self):
        self.option_activated(self.back_idx)

    def option_activated(self, idx):
        if idx == self.back_idx:
            gs.get_instance().menu_manager().set_active_menu(DebugMenu())
            sound_effects.play_sound(soundref.menu_back)
        elif idx == self.next_page_idx:
            gs.get_instance().menu_manager().set_active_menu(DebugZoneSelectMenu(self.page + 1, self.zone_types))
            sound_effects.play_sound(soundref.menu_select)
        elif idx == self.prev_page_idx:
            gs.get_instance().menu_manager().set_active_menu(DebugZoneSelectMenu(self.page - 1, self.zone_types))
            sound_effects.play_sound(soundref.menu_select)
        elif 0 <= idx < len(self.opts):
            selected_opt = self.opts[idx]
            print("INFO: used debug menu to jump to zone: {}".format(selected_opt))
            new_zone_evt = events.NewZoneEvent(selected_opt, gs.get_instance().current_zone, show_zone_title_menu=False)
            gs.get_instance().event_queue().add(new_zone_evt)
            sound_effects.play_sound(soundref.menu_select)


class TitleMenu(Menu):

    def __init__(self):
        Menu.__init__(self, MenuManager.TITLE_MENU)

        self.tick_count = 0

        self.title_fade_range = (60, 80)
        self.world_fade_range = (0, 30)
        self.show_press_any_tick = 120

        self.title_img = None

        self.title_fade_img = None
        self.world_fade_img = None

        self.press_any_key_img = None
        self.press_any_key_outlines = []

    def get_song(self):
        return music.Songs.MENU_THEME

    def keep_drawing_world_underneath(self):
        return False

    def update(self, world):

        if self.tick_count > 15 and InputState.get_instance().was_anything_pressed():
            if self.tick_count > self.show_press_any_tick:
                gs.get_instance().menu_manager().set_active_menu(StartMenu())
                return
            else:
                self.tick_count = max(self.tick_count, self.show_press_any_tick)

        if self.title_img is None:
            self.title_img = ImageBundle.new_bundle(spriteref.UI_0_LAYER, scale=4)
        idx = (gs.get_instance().anim_tick // 4) % len(spriteref.TitleScene.frames)
        model = spriteref.TitleScene.frames[idx]

        x = WindowState.get_instance().get_screen_size()[0] // 2 - model.size()[0] * self.title_img.scale() // 2
        y = WindowState.get_instance().get_screen_size()[1] // 2 - model.size()[1] * self.title_img.scale() // 2

        self.title_img = self.title_img.update(new_model=model, new_x=x, new_y=y, new_depth=50)

        title_fade_dur = self.title_fade_range[1] - self.title_fade_range[0]
        title_alpha = Utils.bound((self.tick_count - self.title_fade_range[0]) / title_fade_dur, 0, 1)
        if title_alpha == 1:
            if self.title_fade_img is not None:
                RenderEngine.get_instance().remove(self.title_fade_img)
                self.title_fade_img = None
        else:
            if self.title_fade_img is None:
                self.title_fade_img = ImageBundle.new_bundle(spriteref.UI_0_LAYER, depth=-10)

            sprite = spriteref.get_floor_lighting(title_alpha)
            ratio = (int(0.5 + self.title_img.width() / sprite.width()),
                     int(0.5 + (self.title_img.height() // 3) / sprite.height()))

            self.title_fade_img = self.title_fade_img.update(new_model=sprite, new_x=x, new_y=y,
                                                             new_ratio=ratio, new_color=(0, 0, 0))

        world_fade_dur = self.world_fade_range[1] - self.world_fade_range[0]
        world_alpha = Utils.bound((self.tick_count - self.world_fade_range[0]) / world_fade_dur, 0, 1)
        if world_alpha == 1:
            if self.world_fade_img is not None:
                RenderEngine.get_instance().remove(self.world_fade_img)
                self.world_fade_img = None
        else:
            if self.world_fade_img is None:
                self.world_fade_img = ImageBundle.new_bundle(spriteref.UI_0_LAYER, depth=-10)

            sprite = spriteref.get_floor_lighting(world_alpha)
            scr_size = WindowState.get_instance().get_screen_size()
            ratio = (int(0.5 + scr_size[0] / sprite.width()), int(0.5 + ((scr_size[1] * 2) // 3) / sprite.height()))

            self.world_fade_img = self.world_fade_img.update(new_model=sprite, new_x=0, new_y=scr_size[1] // 3,
                                                             new_ratio=ratio, new_color=(0, 0, 0))

        press_any_text_scale = 3

        if self.press_any_key_img is None and self.tick_count > self.show_press_any_tick:
            self.press_any_key_img = TextImage(0, 0, "press any key", spriteref.UI_0_LAYER, scale=press_any_text_scale)

        if self.press_any_key_img is not None:
            text_w = self.press_any_key_img.w()
            text_h = self.press_any_key_img.h()
            text_x = x + self.title_img.width() // 2 - text_w // 2
            text_y = y + (self.title_img.height() * 15) // 16 - text_h // 2
            text_color = gs.get_instance().get_pulsing_color(colors.RED)

            self.press_any_key_img = self.press_any_key_img.update(new_x=text_x, new_y=text_y, new_color=text_color)

            if len(self.press_any_key_outlines) == 0:
                for _ in range(0, 4):
                    self.press_any_key_outlines.append(TextImage(0, 0, self.press_any_key_img.get_text(),
                                                                 spriteref.UI_0_LAYER, scale=press_any_text_scale,
                                                                 depth=10, color=(0, 0, 0)))

            outline_positions = [n for n in Utils.neighbors(text_x, text_y, dist=press_any_text_scale)]
            for i in range(0, len(self.press_any_key_outlines)):
                outline_text = self.press_any_key_outlines[i]
                outline_x = outline_positions[i][0]
                outline_y = outline_positions[i][1]
                self.press_any_key_outlines[i] = outline_text.update(new_x=outline_x, new_y=outline_y)

        self.tick_count += 1

        render_eng = RenderEngine.get_instance()
        for bun in self.all_bundles():
            render_eng.update(bun)

    def all_bundles(self):
        if self.title_img is not None:
            yield self.title_img
        if self.title_fade_img is not None:
            yield self.title_fade_img
        if self.world_fade_img is not None:
            yield self.world_fade_img
        for outline_img in self.press_any_key_outlines:
            for bun in outline_img.all_bundles():
                yield bun
        if self.press_any_key_img is not None:
            for bun in self.press_any_key_img.all_bundles():
                yield bun


class InGameUiState(Menu):

    def __init__(self):
        Menu.__init__(self, MenuManager.IN_GAME_MENU)

        self.sidepanel = None
        self.health_bar_panel = None
        self.dialog_panel = None

        self.item_on_cursor_info = None  # tuple (item, ItemImage, offset)

        self.current_cursor_override = None

    def get_song(self):
        # zones specify their songs
        return music.Songs.CONTINUE_CURRENT

    def keep_drawing_world_underneath(self):
        return True

    def get_camera_center_point_on_screen(self):
        """
            Returns the point (x, y) on screen where the camera center should be drawn. This position will
            vary depending on the state of the UI. For example, when a sidebar is open, the world will
            be pushed to the right so that the player's visibily is restricted evenly between the left and right.
        """

        screen_w, screen_h = WindowState.get_instance().get_screen_size()
        if self.sidepanel is not None:
            inv_w = self.sidepanel.get_rect()[2]
        else:
            inv_w = 0

        hb_height = HealthBarPanel.SIZE[1]

        cx = inv_w + (screen_w - inv_w) // 2
        cy = (screen_h - hb_height) // 2

        return (cx, cy)

    def _get_obj_at_screen_pos(self, world, xy):
        """returns: Item, ItemEntity, EnemyEntity, Entity, or None"""
        if xy is None:
            return None
        else:
            inv_open = self.sidepanel is not None and self.sidepanel.get_panel_type() == SidePanelTypes.INVENTORY
            if inv_open and self.sidepanel.contains_point(xy[0], xy[1]):
                inv_panel = self.sidepanel
                grid, cell = inv_panel.get_grid_and_cell_at_pos(*xy)
                if grid is not None and cell is not None:
                    return grid.item_at_position(cell)
            else:
                world_pos = gs.get_instance().screen_to_world_coords(xy)
                item_entity = world.get_entity_for_mouseover(world_pos, cond=lambda x: x.is_item())
                if item_entity is not None:
                    return item_entity

                enemy_entity = world.get_entity_for_mouseover(world_pos, cond=lambda x: x.is_enemy())
                if enemy_entity is not None:
                    return enemy_entity

                return world.get_entity_for_mouseover(world_pos)

    def cursor_style_at(self, world, xy):
        if self.item_on_cursor_info is not None:
            return None
        else:
            for image in self._top_level_interactable_imgs():
                if image.contains_point(*xy):
                    return image.get_cursor_at(*xy)

            obj_at_xy = self._get_obj_at_screen_pos(world, xy)
            if obj_at_xy is not None:
                if isinstance(obj_at_xy, item_module.Item):
                    return spriteref.UI.Cursors.hand_cursor

                import src.world.entities as entities
                if isinstance(obj_at_xy, entities.ItemEntity):
                    player = world.get_player()
                    if player is not None:
                        pos = world.to_grid_coords(*obj_at_xy.center())
                        pickup_action = gameengine.PickUpItemAction(player, obj_at_xy.get_item(), pos)
                        if pickup_action.is_possible(world):
                            return spriteref.UI.Cursors.hand_cursor

            return super().cursor_style_at(world, xy)

    def _top_level_interactable_imgs(self):
        if self.dialog_panel is not None:
            yield self.dialog_panel
        if self.health_bar_panel is not None:
            yield self.health_bar_panel
        if self.sidepanel is not None:
            yield self.sidepanel

    def _update_tooltip(self, world):
        input_state = InputState.get_instance()
        screen_pos = input_state.mouse_pos() if input_state.mouse_in_window() else None
        obj_to_display = None

        if screen_pos is not None and self.item_on_cursor_info is None:
            cursor_in_world = True
            for ui_img in self._top_level_interactable_imgs():
                if ui_img.contains_point(*screen_pos):
                    cursor_in_world = False
                    tt_target = ui_img.get_tooltip_target_at(*screen_pos)
                    if tt_target is not None:
                        obj_to_display = tt_target
                        break

            if cursor_in_world:
                obj_to_display = self._get_obj_at_screen_pos(world, screen_pos)

        if obj_to_display is None:
            self.set_active_tooltip(None)
        else:
            needs_update = False
            current_tooltip = self.get_active_tooltip()

            if obj_to_display is not None:
                obj_text = TooltipFactory.get_tooltip_text(obj_to_display)

                if obj_text is None:
                    self.set_active_tooltip(None)

                elif TooltipFactory.needs_rebuild(obj_text, current_tooltip):
                    new_tooltip = TooltipFactory.build_tooltip(obj_to_display, text_builder=obj_text, xy=(0, 0))
                    self.set_active_tooltip(new_tooltip)
                    needs_update = True

            current_tooltip = self.get_active_tooltip()

            render_eng = RenderEngine.get_instance()
            if current_tooltip is not None:
                tt_width = current_tooltip.get_rect()[2]
                tt_height = current_tooltip.get_rect()[3]
                tt_x = min(screen_pos[0], WindowState.get_instance().get_screen_size()[0] - tt_width)

                y_offs = 24
                if screen_pos[1] + y_offs + tt_height > WindowState.get_instance().get_screen_size()[1]:
                    if screen_pos[1] - y_offs - tt_height >= 0:
                        tt_y = screen_pos[1] - y_offs - tt_height
                    else:
                        tt_y = screen_pos[1] + 24  # if it's too tall to fit on the screen at all, we've got a problem
                else:
                    tt_y = screen_pos[1] + 24

                offs = (-tt_x, -tt_y)
                render_eng.set_layer_offset(spriteref.UI_TOOLTIP_LAYER, *offs)

            if needs_update and current_tooltip is not None:
                for bun in current_tooltip.all_bundles():
                    render_eng.update(bun)

    def _update_dialog_panel(self):
        should_destroy = (self.dialog_panel is not None and (not gs.get_instance().dialog_manager().is_active() or
                          self.dialog_panel.get_dialog() is not gs.get_instance().dialog_manager().get_dialog()))

        if should_destroy:
            self._destroy_panel(self.dialog_panel)
            self.dialog_panel = None

        if gs.get_instance().dialog_manager().is_active():
            if self.dialog_panel is None:
                dialog = gs.get_instance().dialog_manager().get_dialog()
                self.dialog_panel = DialogPanel(dialog)

        if self.dialog_panel is not None:
            self.dialog_panel.update()

    def _update_sidepanel(self, world):
        if not gs.get_instance().player_state().is_alive():
            gs.get_instance().set_active_sidepanel(None, play_sound=False)

        elif InputState.get_instance().was_pressed(gs.get_instance().settings().inventory_key()):
            gs.get_instance().toggle_sidepanel(SidePanelTypes.INVENTORY)
        elif InputState.get_instance().was_pressed(gs.get_instance().settings().map_key()):
            gs.get_instance().toggle_sidepanel(SidePanelTypes.MAP)
        #elif InputState.get_instance().was_pressed(gs.get_instance().settings().help_key()):
        #    gs.get_instance().toggle_sidepanel(SidePanelTypes.HELP)

        # TODO - add 'close' key

        expected_id = gs.get_instance().get_active_sidepanel()
        actual_id = None if self.sidepanel is None else self.sidepanel.get_panel_type()

        if expected_id != actual_id:
            self.rebuild_and_set_sidepanel(expected_id)
        else:
            if self.sidepanel is not None:
                self.sidepanel.update(world)

                if self.sidepanel.needs_rebuild():
                    self.rebuild_and_set_sidepanel(self.sidepanel.get_panel_type())
                elif self.sidepanel.is_dirty():
                    self.sidepanel.update_images()

    def _update_health_bar_panel(self):
        if not gs.get_instance().player_state().is_alive():
            if self.health_bar_panel is not None:
                self._destroy_panel(self.health_bar_panel)
                self.health_bar_panel = None

        else:
            if self.health_bar_panel is None:
                self.health_bar_panel = HealthBarPanel()

            if self.health_bar_panel.is_dirty():
                self.health_bar_panel.update_images()
                for bun in self.health_bar_panel.all_bundles():
                    RenderEngine.get_instance().update(bun)

    def _get_mouse_pos_in_world(self):
        if not InputState.get_instance().mouse_in_window():
            return None
        else:
            screen_pos = InputState.get_instance().mouse_pos()
            for i in self._top_level_interactable_imgs():
                if i.contains_point(*screen_pos):
                    return None

            return gs.get_instance().screen_to_world_coords(screen_pos)

    def _update_item_on_cursor_info(self):
        destroy_image = False
        create_image = False

        ps = gs.get_instance().player_state()

        if not ps.is_alive() or not InputState.get_instance().mouse_in_window():
            destroy_image = True

        elif ps.held_item is not None and self.item_on_cursor_info is None:
            create_image = True
        elif ps.held_item is None and self.item_on_cursor_info is not None:
            destroy_image = True
        elif (ps.held_item is not None and self.item_on_cursor_info is not None
              and ps.held_item != self.item_on_cursor_info[0]):
                destroy_image = True
                create_image = True

        # TODO - this ought to be an action probably
        did_rotate_input = InputState.get_instance().was_pressed(gs.get_instance().settings().rotate_cw_key())
        if did_rotate_input and not gs.get_instance().world_updates_paused():
            if ps.held_item is not None and ps.held_item.can_rotate():
                ps.held_item = ps.held_item.rotate()

                if not destroy_image:  # so you can't flicker the image after death basically
                    create_image = True
                destroy_image = True

                gs.get_instance().event_queue().add(events.RotatedItemEvent(ps.held_item))
                sound_effects.play_sound(soundref.item_rotate)

        if destroy_image and self.item_on_cursor_info is not None:
            self._destroy_panel(self.item_on_cursor_info[1])
            self.item_on_cursor_info = None

        if create_image:
            size = ItemImage.calc_size(ps.held_item, 2)
            item_img = ItemImage(0, 0, ps.held_item, spriteref.UI_TOOLTIP_LAYER, 2, 0)
            item_offs = (-size[0] // 2, -size[1] // 2)
            self.item_on_cursor_info = (ps.held_item, item_img, item_offs)
            render_eng = RenderEngine.get_instance()
            for bun in self.item_on_cursor_info[1].all_bundles():
                render_eng.update(bun)

        if self.item_on_cursor_info is not None:
            screen_pos = InputState.get_instance().mouse_pos()
            if screen_pos is not None:
                x_offs = -screen_pos[0] - self.item_on_cursor_info[2][0]
                y_offs = -screen_pos[1] - self.item_on_cursor_info[2][1]
                RenderEngine.get_instance().set_layer_offset(spriteref.UI_TOOLTIP_LAYER, x_offs, y_offs)

    def rebuild_and_set_sidepanel(self, panel_id):
        render_eng = RenderEngine.get_instance()
        if self.sidepanel is not None:
            for bun in self.sidepanel.all_bundles():
                render_eng.remove(bun)

        if panel_id == SidePanelTypes.INVENTORY:
            self.sidepanel = InventoryPanel()
        elif panel_id == SidePanelTypes.MAP:
            self.sidepanel = MapPanel()
        else:
            self.sidepanel = None

        if self.sidepanel is not None:
            for bun in self.sidepanel.all_bundles():
                render_eng.update(bun)

    def update(self, world):
        input_state = InputState.get_instance()
        screen_pos = input_state.mouse_pos()

        click_actions = []

        if screen_pos is not None:
            button1 = input_state.mouse_was_pressed(button=1)
            button3 = input_state.mouse_was_pressed(button=3)
            if button1 or button3:
                button = 1 if button1 else 3

                absorbed_click = False
                for image in self._top_level_interactable_imgs():
                    if image.contains_point(*screen_pos):
                        absorbed_click = image.on_click(*screen_pos, button=button)
                    if absorbed_click:
                        break

                if not absorbed_click:
                    # do click in world then
                    world_pos = gs.get_instance().screen_to_world_coords(screen_pos)
                    click_actions = gameengine.get_actions_from_click(world, world_pos, button=button)

        self._update_item_on_cursor_info()
        self._update_tooltip(world)
        self._update_sidepanel(world)

        # these inputs are allowed to bleed through world_updates_paused because they're
        # sorta "meta-inputs" (i.e. they don't affect the world).
        for i in range(0, 6):
            cur_targeting_action = gs.get_instance().get_targeting_action_provider()
            if input_state.was_pressed(gs.get_instance().settings().action_key(i)):
                new_targeting_action = gs.get_instance().get_mapped_action(i)
                if cur_targeting_action == new_targeting_action:
                    gs.get_instance().set_targeting_action_provider(None)
                else:
                    gs.get_instance().set_targeting_action_provider(new_targeting_action)

        self._update_health_bar_panel()
        self._update_dialog_panel()

        gs.get_instance().set_targetable_coords_in_world(None)

        if len(gs.get_instance().get_cinematics_queue()) > 0:
            gs.get_instance().menu_manager().set_active_menu(CinematicMenu())

        elif input_state.was_pressed(gs.get_instance().settings().exit_key()):
            gs.get_instance().menu_manager().set_active_menu(PauseMenu())
            sound_effects.play_sound(soundref.pause_in)

        else:
            target_coords = self.calc_visually_targetable_coords_in_world(world)
            gs.get_instance().set_targetable_coords_in_world(target_coords)

            p = world.get_player()
            if p is not None and not gs.get_instance().world_updates_paused():
                self.send_action_requests(p, world, click_actions=click_actions)

        # processing dialog last so that it'll block other things from getting inputs this frame
        # (because gs.world_updates_paused will get flipped to false when we interact).
        if gs.get_instance().dialog_manager().is_active():
            keys = gs.get_instance().settings().all_dialog_dismiss_keys()
            if input_state.was_pressed(keys):
                gs.get_instance().dialog_manager().interact()

    def send_action_requests(self, player, world, click_actions=None):
        dx = 0
        dy = 0
        input_state = InputState.get_instance()
        if input_state.is_held(gs.get_instance().settings().left_key()):
            dx -= 1
        elif input_state.is_held(gs.get_instance().settings().up_key()):
            dy -= 1
        elif input_state.is_held(gs.get_instance().settings().right_key()):
            dx += 1
        elif input_state.is_held(gs.get_instance().settings().down_key()):
            dy += 1

        pos = world.to_grid_coords(*player.center())
        target_pos = None
        if dx != 0:
            target_pos = (pos[0] + dx, pos[1])
        elif dy != 0:
            target_pos = (pos[0], pos[1] + dy)

        res_list = []
        if target_pos is not None:
            res_list.extend(gameengine.get_keyboard_action_requests(world, player, target_pos))

        if input_state.was_pressed(gs.get_instance().settings().skip_turn_key()):
            res_list.append(gameengine.SkipTurnAction(player, pos))

        pc = gs.get_instance().player_controller()

        if click_actions is not None:
            pc.add_requests(click_actions, pc.HIGHEST_PRIORITY)

        pc.add_requests(res_list)
        pc.add_requests(gameengine.PlayerWaitAction(player, position=target_pos), pc.LOWEST_PRIORITY)

    def calc_visually_targetable_coords_in_world(self, world):
        """:returns: map: (x, y) -> color"""

        if gs.get_instance().dialog_manager().is_active():
            return {}

        p = world.get_player()

        if p is None:
            return {}

        target_coords = {}

        pos = world.to_grid_coords(*p.center())
        for n in Utils.neighbors(pos[0], pos[1]):
            for act in gameengine.get_keyboard_action_requests(world, p, n):
                if act.is_possible(world):
                    position = act.get_position()
                    color = act.get_targeting_color(for_mouse=False)
                    if position is not None and color is not None:
                        target_coords[position] = color
                    break

        mouse_pos = self._get_mouse_pos_in_world()
        if mouse_pos is not None:
            for act in gameengine.get_actions_from_click(world, mouse_pos):
                if act.is_possible(world):
                    position = act.get_position()

                    if position is None:
                        # some actions have no positions (like applying items to the player).
                        position = world.to_grid_coords(*mouse_pos)

                    color = act.get_targeting_color(for_mouse=True)
                    if position is not None and color is not None:
                        target_coords[position] = color
                    break

        return target_coords

    def cleanup(self):
        Menu.cleanup(self)

        # TODO - not sure whether this feels right.
        # should the inv always close when you pause or change zones?
        gs.get_instance().set_active_sidepanel(None, play_sound=False)

        self.sidepanel = None
        self.item_on_cursor_info = None

    def all_bundles(self):
        for bun in Menu.all_bundles(self):
            yield bun
        if self.sidepanel is not None:
            for bun in self.sidepanel.all_bundles():
                yield bun
        if self.health_bar_panel is not None:
            for bun in self.health_bar_panel.all_bundles():
                yield bun
        if self.item_on_cursor_info is not None:
            for bun in self.item_on_cursor_info[1].all_bundles():
                yield bun
        if self.dialog_panel is not None:
            for bun in self.dialog_panel.all_bundles():
                yield bun