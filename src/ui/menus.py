import random

import pygame

from src.game import spriteref as spriteref
from src.items import item as item_module
from src.ui.tooltips import TooltipFactory
from src.ui.ui import HealthBarPanel, InventoryPanel, CinematicPanel, TextImage, ItemImage, DialogPanel
from src.utils.util import Utils
import src.game.events as events
import src.game.music as music
import src.game.settings as settings
import src.game.globalstate as gs
import src.utils.passwordgen as passwordgen
import src.game.sound_effects as sound_effects
from src.renderengine.engine import RenderEngine
from src.game.inputs import InputState


class MenuManager:

    DEATH_MENU = 0
    DEATH_OPTION_MENU = 0.5
    IN_GAME_MENU = 1
    START_MENU = 2
    CINEMATIC_MENU = 3
    PAUSE_MENU = 4
    CONTROLS_MENU = 5
    PASSWORD_MENU = 6
    KEYBINDING_MENU = 7
    DEBUG_OPTION_MENU = 8
    SETTINGS_MENU = 9

    def __init__(self, menu):
        self._active_menu = StartMenu()
        self._next_active_menu = menu

    def update(self, world):
        render_eng = RenderEngine.get_instance()
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
                    pygame.mouse.set_visible(False)
                else:
                    pygame.mouse.set_visible(True)
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
        return (0.5, 0.5, 0.5)

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

    def absorbs_key_inputs(self):
        return False

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
        Menu.__init__(self, menu_id)
        self.title_text = title
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

    def get_option_color(self, idx):
        if idx == self._selection:
            return (1, 0, 0)
        else:
            return (1, 1, 1)

    def get_option_text(self, idx):
        return self.options_text[idx]

    def get_num_options(self):
        return len(self.options_text)

    def build_title_img(self):
        if self.title_text is not None:
            if self._title_img is None:
                self._title_img = TextImage(0, 0, self.title_text, layer=spriteref.UI_0_LAYER,
                                            color=self.get_title_color(), scale=self.title_size)

    def build_option_imgs(self):
        if self._option_imgs is None:
            self._option_imgs = [None] * self.get_num_options()

        for i in range(0, self.get_num_options()):
            if self._option_imgs[i] is None:
                self._option_imgs[i] = TextImage(0, 0, self.get_option_text(i), layer=spriteref.UI_0_LAYER,
                                                 color=self.get_option_color(i), scale=2)

    def _layout_rects(self):
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

        y_pos = gs.get_instance().screen_size[1] // 2 - total_height // 2
        if self._title_img is not None:
            title_x = gs.get_instance().screen_size[0] // 2 - self._title_img.size()[0] // 2
            self._title_rect = (title_x, y_pos, self._title_img.size()[0], self._title_img.size()[1])
            y_pos += self._title_img.size()[1] + self.title_spacing

        for i in range(0, self.get_num_options()):
            if self._option_imgs[i] is not None:
                opt_x = gs.get_instance().screen_size[0] // 2 - self._option_imgs[i].size()[0] // 2
                self._option_rects[i] = (opt_x, y_pos, self._option_imgs[i].size()[0], self._option_imgs[i].size()[1])
                y_pos += self._option_imgs[i].size()[1] + self.spacing

    def _update_imgs(self):
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
        if idx != self._selection:
            sound_effects.play_sound(sound_effects.Effects.CLICK)
            self._selection = idx

    def handle_inputs(self, world):
        input_state = InputState.get_instance()
        if input_state.was_pressed(gs.get_instance().settings().exit_key()):
            self.esc_pressed()
        else:
            new_selection = self._selection
            up_pressed = input_state.was_pressed(gs.get_instance().settings().menu_up_key())
            if not self.absorbs_key_inputs():
                up_pressed = up_pressed or input_state.was_pressed(gs.get_instance().settings().up_key())

            if up_pressed:
                new_selection = (self._selection - 1) % self.get_num_options()

            down_pressed = input_state.was_pressed(gs.get_instance().settings().menu_down_key())
            if not self.absorbs_key_inputs():
                down_pressed = down_pressed or input_state.was_pressed(gs.get_instance().settings().down_key())

            if down_pressed:
                new_selection = (self._selection + 1) % self.get_num_options()

            self.set_selected(new_selection)

            if input_state.was_pressed(gs.get_instance().settings().enter_key()):
                self.option_activated(self._selection)

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
                        bigger_rect = Utils.rect_expand(selected_rect, 15, 15, 15, 15)
                        if Utils.rect_contains(bigger_rect, pos):
                            self.option_activated(self._selection)
                            clicked_option = self._selection

                    if clicked_option is None:
                        # if the mouse hasn't moved yet on this menu, gotta catch those clicks too
                        for i in range(0, self.get_num_options()):
                            if self._option_rects[i] is not None and Utils.rect_contains(self._option_rects[i], pos):
                                clicked_option = i
                                break

                    if clicked_option is not None:
                        self.option_activated(clicked_option)

    def update(self, world):
        self.build_title_img()
        self.build_option_imgs()
        self._layout_rects()
        self._update_imgs()

        self.handle_inputs(world)

        render_eng = RenderEngine.get_instance()
        for bun in self.all_bundles():
            render_eng.update(bun)

    def option_activated(self, idx):
        sound_effects.play_sound(sound_effects.Effects.CLICK2)

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


TITLE_CANDIDATES = [
    "\n".join([
        "  ██████  ██ ▄█▀▓█████  ██▓    ▓█████▄▓██████▒ ██▀███   ██▒  ██████ ",
        "▒██    ▒  ██▄█▒ ▒█   ▀ ▓██▒    ▓█   ▀▓  ██▒ ▒░▓██ ▒ ██░▒██▒▒██    ▒ ",
        "░ ▓██▄   ▒███▄░ ▒███   ▒██░    ▒███  ▒ ▓██░ ░░▓██ ░▄█ ░▒██▒░ ▓██▄   ",
        "  ▒   ██▒▓██ █▄ ▒▓█  ▄ ▒██░    ▒▓█  ▄░ ▓██▓ ░ ▒██▀▀█▄  ░██░  ▒   ██▒",
        "▒██████▒▒▒██▒ █▄░▒████▒░██████▒░▒████▒ ▒██▒ ░ ░██▓ ▒██▒░██░▒██████▒▒",
        "▒ ▒▓▒ ▒ ░▒ ▒▒ ▓▒░░ ▒░ ░░ ▒░▓  ░░░ ▒░ ░ ▒ ░░   ░ ▒▓ ░▒▓░░▓  ▒ ▒▓▒ ▒ ░",
        "░ ░▒  ░ ░░ ░▒ ▒░ ░ ░  ░░ ░ ▒  ░ ░ ░  ░   ░      ░▒ ░ ▒░ ▒ ░░ ░▒  ░ ░",
        "░  ░  ░  ░ ░░ ░    ░     ░ ░      ░    ░        ░░   ░  ▒ ░░  ░  ░  ",
        "      ░  ░  ░      ░  ░    ░  ░   ░  ░           ░      ░        ░  "
    ]),
    "\n".join([
        " ▄████▄   █    ██  ▄▄▄▄   ▓█████  ██▓     ██▓ ██ ▄█▀▓█████ ",
        "▒██▀ ▀█   ██  ▓██▒▓█████▄ ▓█   ▀ ▓██▒    ▓██▒ ██▄█▒ ▓█   ▀ ",
        "▒▓█    ▄ ▓██  ▒██░▒██▒ ▄██▒███   ▒██░    ▒██▒▓███▄░ ▒███   ",
        "▒▓▓▄ ▄██▒▓▓█  ░██░▒██░█▀  ▒▓█  ▄ ▒██░    ░██░▓██ █▄ ▒▓█  ▄ ",
        "▒ ▓███▀ ░▒▒█████▓ ░▓█  ▀█▓░▒████▒░██████▒░██░▒██▒ █▄░▒████▒",
        "░ ░▒ ▒  ░░▒▓▒ ▒ ▒ ░▒▓███▀▒░░ ▒░ ░░ ▒░▓  ░░▓  ▒ ▒▒ ▓▒░░ ▒░ ░",
        "  ░  ▒   ░░▒░ ░ ░ ▒░▒   ░  ░ ░  ░░ ░ ▒  ░ ▒ ░░ ░▒ ▒░ ░ ░  ░",
        "░         ░░░ ░ ░  ░    ░    ░     ░ ░    ▒ ░░ ░░ ░    ░   ",
        "░ ░         ░      ░         ░  ░    ░  ░ ░  ░  ░      ░  ░",
        "░                       ░                                  "
    ]),
]


class StartMenu(OptionsMenu):

    START_OPT = 0
    PASSWORD_OPT = 1
    OPTIONS_OPT = 2
    SOUND_OPT = 3
    EXIT_OPT = 4

    def __init__(self):
        OptionsMenu.__init__(self, MenuManager.START_MENU,
                random.choice(TITLE_CANDIDATES), ["start", "load game", "controls", "sound", "exit"], title_size=1)

    def get_song(self):
        return music.Songs.MENU_THEME

    def option_activated(self, idx):
        OptionsMenu.option_activated(self, idx)
        if idx == StartMenu.START_OPT:
            gs.get_instance().event_queue().add(events.NewGameEvent(instant_start=True))
        elif idx == StartMenu.EXIT_OPT:
            gs.get_instance().event_queue().add(events.GameExitEvent())
        elif idx == StartMenu.PASSWORD_OPT:
            last_pw = gs.get_instance().settings().get(settings.LAST_PASSWORD)
            gs.get_instance().menu_manager().set_active_menu(PasswordEntryMenu(prefill=last_pw))
        elif idx == StartMenu.OPTIONS_OPT:
            gs.get_instance().menu_manager().set_active_menu(ControlsMenu(MenuManager.START_MENU))
        elif idx == StartMenu.SOUND_OPT:
            gs.get_instance().menu_manager().set_active_menu(SoundSettingsMenu(MenuManager.START_MENU))


class PauseMenu(OptionsMenu):

    CONTINUE_IDX = 0
    HELP_IDX = 1
    SOUND_IDX = 2
    EXIT_IDX = 3

    def __init__(self):
        OptionsMenu.__init__(self, MenuManager.PAUSE_MENU, "paused", ["back", "controls", "sound", "quit"])

    def option_activated(self, idx):
        OptionsMenu.option_activated(self, idx)
        if idx == PauseMenu.EXIT_IDX:
            gs.get_instance().menu_manager().set_active_menu(StartMenu())
        elif idx == PauseMenu.HELP_IDX:
            gs.get_instance().menu_manager().set_active_menu(ControlsMenu(MenuManager.IN_GAME_MENU))
        elif idx == PauseMenu.CONTINUE_IDX:
            gs.get_instance().menu_manager().set_active_menu(InGameUiState())
        elif idx == PauseMenu.SOUND_IDX:
            gs.get_instance().menu_manager().set_active_menu(SoundSettingsMenu(MenuManager.PAUSE_MENU))

    def esc_pressed(self):
        gs.get_instance().menu_manager().set_active_menu(InGameUiState())


class PasswordEntryMenu(OptionsMenu):

    ENTER_IDX = 0
    BACK_IDX = 1

    def __init__(self, prefill=None):
        OptionsMenu.__init__(self, MenuManager.PASSWORD_MENU, "Enter password", ["enter", "back"])

        self._max_size = 6
        self._pw_text = ""
        if passwordgen.is_valid(prefill):
            self._pw_text = prefill

        self._all_valid_passwords = gs.SaveDataBlob.get_current_passwords_from_disk()

        self._pw_text_img = None
        self._pw_text_rect = None

        self.red_countdown = 0
        self.green_countdown = 0
        self.max_color_countdown = 45

    def get_song(self):
        return music.Songs.CONTINUE_CURRENT

    def absorbs_key_inputs(self):
        return True

    def get_option_color(self, idx):
        if self.green_countdown > 0:
            return (1, 1, 1)
        else:
            return OptionsMenu.get_option_color(self, idx)

    def option_activated(self, idx):
        if idx == PasswordEntryMenu.ENTER_IDX:
            if self._pw_text in self._all_valid_passwords:
                sound_effects.play_sound(sound_effects.Effects.LOAD)
                self.green_countdown = round(self.max_color_countdown * 1.5)
            else:
                sound_effects.play_sound(sound_effects.Effects.NEGATIVE_2)
                self.red_countdown = self.max_color_countdown
        elif idx == PasswordEntryMenu.BACK_IDX:
            OptionsMenu.option_activated(self, idx)
            gs.get_instance().menu_manager().set_active_menu(StartMenu())

    def esc_pressed(self):
        gs.get_instance().menu_manager().set_active_menu(StartMenu())

    def build_pw_img(self):
        display_text = self._pw_text

        if len(display_text) < self._max_size:
            if (gs.get_instance().anim_tick // 3) % 2 == 0:
                display_text += "_"
            else:
                display_text += " "

        if len(display_text) < self._max_size:
            missing_spaces = "_" * (self._max_size - len(display_text))
            display_text += missing_spaces

        if self._pw_text_img is not None and self._pw_text_img.text != display_text:
            render_eng = RenderEngine.get_instance()
            for bun in self._pw_text_img.all_bundles():
                render_eng.remove(bun)
            self._pw_text_img = None

        if self._pw_text_img is None:
            self._pw_text_img = TextImage(0, 0, display_text, spriteref.UI_0_LAYER, scale=self.title_size)

    def _update_pw_img(self):
        if self._pw_text_img is not None and self._pw_text_rect is not None:
            x = self._pw_text_rect[0]
            y = self._pw_text_rect[1]

            if self.green_countdown > 0:
                greenness = Utils.bound(self.green_countdown / self.max_color_countdown, 0.0, 1.0)
                color = (1 - greenness, 1, 1 - greenness)
            else:
                redness = Utils.bound(self.red_countdown / self.max_color_countdown, 0.0, 1.0)
                color = (1, 1 - redness, 1 - redness)

            self._pw_text_img = self._pw_text_img.update(new_x=x, new_y=y, new_color=color)

    def _layout_rects(self):
        # XXX mostly cannibalized from OptionMenu._layout_rects
        if self._title_rect is None:
            self._title_rect = (0, 0, 0, 0)
        if self._option_rects is None:
            self._option_rects = [(0, 0, 0, 0)] * self.get_num_options()
        if self._pw_text_rect is None:
            self._pw_text_rect = (0, 0, 0, 0)

        total_height = 0
        if self._title_img is not None:
            total_height += self._title_img.size()[1] + self.title_spacing
        if self._pw_text_img is not None:
            total_height += self._pw_text_img.line_height() + self.title_spacing
        for opt in self._option_imgs:
            if opt is not None:
                total_height += opt.size()[1] + self.spacing
        total_height -= self.spacing

        y_pos = gs.get_instance().screen_size[1] // 2 - total_height // 2
        if self._title_img is not None:
            title_x = gs.get_instance().screen_size[0] // 2 - self._title_img.size()[0] // 2
            self._title_rect = (title_x, y_pos, self._title_img.size()[0], self._title_img.size()[1])
            y_pos += self._title_img.size()[1] + self.title_spacing

        if self._pw_text_img is not None:
            pw_width = TextImage.calc_width("x" * self._max_size, self._pw_text_img.scale)
            pw_height = self._pw_text_img.line_height()
            pw_x = gs.get_instance().screen_size[0] // 2 - pw_width // 2
            self._pw_text_rect = (pw_x, y_pos, pw_width, pw_height)
            y_pos += pw_height + self.title_spacing

        for i in range(0, self.get_num_options()):
            if self._option_imgs[i] is not None:
                opt_x = gs.get_instance().screen_size[0] // 2 - self._option_imgs[i].size()[0] // 2
                self._option_rects[i] = (opt_x, y_pos, self._option_imgs[i].size()[0], self._option_imgs[i].size()[1])
                y_pos += self._option_imgs[i].size()[1] + self.spacing

    def all_bundles(self):
        for bun in OptionsMenu.all_bundles(self):
            yield bun
        if self._pw_text_img is not None:
            for bun in self._pw_text_img.all_bundles():
                yield bun

    def handle_inputs(self, world):
        if self.green_countdown > 0:
            # pw is solved, we're just watching the animation now
            pass

        input_state = InputState.get_instance()
        if input_state.was_pressed(pygame.K_BACKSPACE):
            if len(self._pw_text) > 0:
                sound_effects.play_sound(sound_effects.Effects.CLICK)
                self._pw_text = self._pw_text[:(len(self._pw_text)-1)]
        for key in input_state.all_pressed_keys():
            as_ascii = Utils.stringify_key(key)
            if len(self._pw_text) < self._max_size and as_ascii in "abcdefghijklmnopqrstuvwxyz0123456789":
                sound_effects.play_sound(sound_effects.Effects.CLICK)
                self._pw_text += as_ascii

        OptionsMenu.handle_inputs(self, world)

    def update(self, world):
        # XXX mostly cannibalized from OptionMenu.update
        self.build_title_img()
        self.build_option_imgs()
        self.build_pw_img()

        self._layout_rects()
        self._update_imgs()
        self._update_pw_img()

        if self.red_countdown > 0:
            self.red_countdown -= 1

        if self.green_countdown == 1:
            gs.get_instance().event_queue().add(events.NewGameEvent(from_pw=self._pw_text))
        elif self.green_countdown > 0:
            self.green_countdown -= 1

        self.handle_inputs(world)

        render_eng = RenderEngine.get_instance()
        for bun in self.all_bundles():
            render_eng.update(bun)


class SoundSettingsMenu(OptionsMenu):
    MUSIC_VOLUME_IDX = 0
    EFFECTS_VOLUME_IDX = 1
    BACK_IDX = 2

    def __init__(self, prev_id):
        OptionsMenu.__init__(self, MenuManager.SETTINGS_MENU, "sound", ["~music~", "~effects~", "back"])
        self.prev_id = prev_id
        self.music_enabled = gs.get_instance().settings().get(settings.MUSIC_VOLUME) > 0
        self.effects_enabled = gs.get_instance().settings().get(settings.EFFECTS_VOLUME) > 0

    def get_option_text(self, idx):
        if idx == SoundSettingsMenu.MUSIC_VOLUME_IDX:
            if self.music_enabled:
                return "music: ON"
            else:
                return "music: OFF"
        elif idx == SoundSettingsMenu.EFFECTS_VOLUME_IDX:
            if self.effects_enabled:
                return "effects: ON"
            else:
                return "effects: OFF"
        else:
            return OptionsMenu.get_option_text(self, idx)

    def option_activated(self, idx):
        OptionsMenu.option_activated(self, idx)
        rebuild = False
        if idx == SoundSettingsMenu.MUSIC_VOLUME_IDX:
            new_val = 0 if self.music_enabled else 100
            gs.get_instance().settings().set(settings.MUSIC_VOLUME, new_val)
            gs.get_instance().save_settings_to_disk()
            rebuild = True
        elif idx == SoundSettingsMenu.EFFECTS_VOLUME_IDX:
            new_val = 0 if self.effects_enabled else 100
            gs.get_instance().settings().set(settings.EFFECTS_VOLUME, new_val)
            gs.get_instance().save_settings_to_disk()
            rebuild = True
        elif idx == SoundSettingsMenu.BACK_IDX:
            if self.prev_id == MenuManager.START_MENU:
                gs.get_instance().menu_manager().set_active_menu(StartMenu())
            else:
                gs.get_instance().menu_manager().set_active_menu(PauseMenu())

        if rebuild:
            # rebuilding so the option text will change
            rebuilt = SoundSettingsMenu(self.prev_id)
            rebuilt.set_selected(idx)
            gs.get_instance().menu_manager().set_active_menu(rebuilt)

    def esc_pressed(self):
        if self.prev_id == MenuManager.START_MENU:
            gs.get_instance().menu_manager().set_active_menu(StartMenu())
        else:
            gs.get_instance().menu_manager().set_active_menu(PauseMenu())


class ControlsMenu(OptionsMenu):

    OPTS = [
        ("move up", settings.KEY_UP),
        ("move left", settings.KEY_LEFT),
        ("move down", settings.KEY_DOWN),
        ("move right", settings.KEY_RIGHT),
        ("inventory", settings.KEY_INVENTORY),
        ("rotate item", settings.KEY_ROTATE_CW)
    ]
    BACK_OPT_IDX = len(OPTS)

    def __init__(self, prev_id):
        OptionsMenu.__init__(self, MenuManager.CONTROLS_MENU, "controls", ["~unused~"])
        self.prev_id = prev_id

    def _layout_rects(self):
        OptionsMenu._layout_rects(self)

    def get_option_text(self, idx):
        if idx == ControlsMenu.BACK_OPT_IDX:
            return "back"
        else:
            opt = ControlsMenu.OPTS[idx]

            cur_value = gs.get_instance().settings().get(opt[1])
            if isinstance(cur_value, list):
                cur_value = cur_value[0]

            return opt[0] + " [{}]".format(Utils.stringify_key(cur_value))

    def get_num_options(self):
        return len(ControlsMenu.OPTS) + 1  # extra one is the "back" option

    def option_activated(self, idx):
        OptionsMenu.option_activated(self, idx)
        if idx == ControlsMenu.BACK_OPT_IDX:
            if self.prev_id == MenuManager.START_MENU:
                gs.get_instance().menu_manager().set_active_menu(StartMenu())
            else:
                gs.get_instance().menu_manager().set_active_menu(PauseMenu())
        else:
            opt = ControlsMenu.OPTS[idx]
            gs.get_instance().menu_manager().set_active_menu(KeybindingEditMenu(opt[1], opt[0], lambda: ControlsMenu(self.prev_id)))

    def esc_pressed(self):
        if self.prev_id == MenuManager.START_MENU:
            gs.get_instance().menu_manager().set_active_menu(StartMenu())
        else:
            gs.get_instance().menu_manager().set_active_menu(PauseMenu())


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

    def handle_inputs(self, world):
        input_state = InputState.get_instance()
        if input_state.was_pressed(gs.get_instance().settings().exit_key()):
            sound_effects.play_sound(sound_effects.Effects.NEGATIVE_2)
            self.esc_pressed()
        else:
            pressed = input_state.all_pressed_keys()
            pressed = [x for x in pressed if self._is_valid_binding(x)]
            if len(pressed) > 0:
                key = random.choice(pressed)  # TODO - better way to handle this?
                gs.get_instance().settings().set(self._setting, [key])
                gs.get_instance().save_settings_to_disk()
                gs.get_instance().menu_manager().set_active_menu(self._return_menu_builder())

                sound_effects.play_sound(sound_effects.Effects.CLICK2)

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

            if self.active_tick_count > 10 and InputState.get_instance().was_pressed(gs.get_instance().settings().interact_key()):
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


class DeathMenu(OptionsMenu):
    """Displays some flavor text, then becomes a death option menu"""

    ALL_FLAVOR = [
        "you'll do better next time!",
        "epic run!",
        "ouch!"
    ]

    def get_clear_color(self):
        return (0, 0, 0)

    def _get_flavor_text(self):
        idx = int(random.random() * len(DeathMenu.ALL_FLAVOR))
        return DeathMenu.ALL_FLAVOR[idx]

    def get_flavor_progress(self):
        return Utils.bound(self._flavor_tick / self._flavor_full_brightness_duration, 0.0, 1.0)

    def get_title_color(self):
        # fade in
        return Utils.linear_interp(self.get_clear_color(), (1, 1, 1), self.get_flavor_progress())

    def get_option_color(self, idx):
        return self.get_clear_color()

    def __init__(self):
        OptionsMenu.__init__(self, MenuManager.DEATH_MENU, self._get_flavor_text(), ["~hidden~"], title_size=3)
        self._flavor_full_brightness_duration = 100
        self._total_duration = 120
        self._flavor_tick = 0

    def update(self, world):
        OptionsMenu.update(self, world)

        self._flavor_tick += 1
        if self._flavor_tick >= self._total_duration:
            gs.get_instance().menu_manager().set_active_menu(DeathOptionMenu())

    def get_song(self):
        return None

    def option_activated(self, idx):
        pass


class DeathOptionMenu(OptionsMenu):

    CONTINUE = 0
    EXIT_OPT = 1

    def __init__(self):
        OptionsMenu.__init__(self, MenuManager.DEATH_OPTION_MENU, "game over", ["continue", "quit"])

    def get_song(self):
        return None

    def option_activated(self, idx):
        OptionsMenu.option_activated(self, idx)
        if idx == DeathOptionMenu.EXIT_OPT:
            gs.get_instance().event_queue().add(events.NewGameEvent(instant_start=False))
        elif idx == DeathOptionMenu.CONTINUE:
            last_pw = gs.get_instance().settings().get(settings.LAST_PASSWORD)
            gs.get_instance().event_queue().add(events.NewGameEvent(instant_start=True, from_pw=last_pw))


class DebugMenu(OptionsMenu):

    ZONE_JUMP = 0
    EXIT_OPT = 1

    def __init__(self):
        OptionsMenu.__init__(self, MenuManager.DEBUG_OPTION_MENU, "debug menu", ["zone select", "back"])

    def get_song(self):
        return music.Songs.CONTINUE_CURRENT

    def option_activated(self, idx):
        OptionsMenu.option_activated(self, idx)
        if idx == DebugMenu.ZONE_JUMP:
            gs.get_instance().menu_manager().set_active_menu(DebugZoneSelectMenu(0))
        elif idx == DebugMenu.EXIT_OPT:
            gs.get_instance().menu_manager().set_active_menu(InGameUiState())


class DebugZoneSelectMenu(OptionsMenu):
    ZONES_PER_PAGE = 8

    def __init__(self, page):
        import src.worldgen.zones as zones

        self.page = page
        all_zones = zones.all_zone_ids()
        all_zones.sort(key=lambda z_id: zones.get_zone(z_id).get_level())
        start_idx = DebugZoneSelectMenu.ZONES_PER_PAGE * page
        first_page = (page == 0)

        if start_idx >= len(all_zones):
            # hmm..
            self.opts = []
            last_page = True
        elif start_idx + DebugZoneSelectMenu.ZONES_PER_PAGE < len(all_zones):
            self.opts = all_zones[start_idx:start_idx + DebugZoneSelectMenu.ZONES_PER_PAGE]
            last_page = False
        else:
            self.opts = all_zones[start_idx:]
            last_page = True

        if not first_page:
            self.opts.append("next page")
            self.next_page_idx = len(self.opts) - 1
        else:
            self.next_page_idx = None

        if not last_page:
            self.opts.append("prev page")
            self.prev_page_idx = len(self.opts) - 1
        else:
            self.prev_page_idx = None

        self.opts.append("back")
        self.back_idx = len(self.opts) - 1

        OptionsMenu.__init__(self, MenuManager.DEBUG_OPTION_MENU, "zone select", self.opts)

    def option_activated(self, idx):
        OptionsMenu.option_activated(self, idx)
        if idx == self.back_idx:
            gs.get_instance().menu_manager().set_active_menu(DebugMenu())
        elif idx == self.next_page_idx:
            gs.get_instance().menu_manager().set_active_menu(DebugZoneSelectMenu(self.page + 1))
        elif idx == self.prev_page_idx:
            gs.get_instance().menu_manager().set_active_menu(DebugZoneSelectMenu(self.page - 1))
        elif 0 <= idx < len(self.opts):
            selected_opt = self.opts[idx]
            print("INFO: used debug menu to jump to zone: {}".format(selected_opt))
            gs.get_instance().event_queue().add(events.NewZoneEvent(selected_opt, gs.get_instance().current_zone))
            gs.get_instance().menu_manager().set_active_menu(InGameUiState())


class InGameUiState(Menu):

    def __init__(self):
        Menu.__init__(self, MenuManager.IN_GAME_MENU)
        self.inventory_panel = None
        self.health_bar_panel = None
        self.dialog_panel = None
        self.top_right_info_panel = None

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
            vary depending on the state of the UI. For example, when the inventory is open, the world will
            be pushed to the right so that the player's visibily is restricted evenly between the left and right.
        """

        screen_w, screen_h = gs.get_instance().screen_size
        if self.inventory_panel is not None:
            inv_w = self.inventory_panel.get_rect()[2]
        else:
            inv_w = 0

        hb_height = HealthBarPanel.SIZE[1]

        cx = inv_w + (screen_w - inv_w) // 2
        cy = (screen_h - hb_height) // 2

        return (cx, cy)

    def _get_entity_at_world_coords(self, world, world_pos, visible_only=True, cond=None):
        hover_rad = 32
        hover_over = world.entities_in_circle(world_pos, hover_rad)
        if visible_only:
            hover_over = list(filter(lambda ent: ent.is_visible_in_world(world), hover_over))
        if cond is not None:
            hover_over = list(filter(cond, hover_over))
        if len(hover_over) > 0:
            return hover_over[0]
        else:
            return None

    def _get_top_right_info_obj(self, world):
        return gs.get_instance().player_state().held_item

    def _update_top_right_info_panel(self, world):
        obj_to_display = self._get_top_right_info_obj(world)
        render_eng = RenderEngine.get_instance()

        if self.top_right_info_panel is not None:
            if obj_to_display is None or self.top_right_info_panel.get_target() is not obj_to_display:
                for bun in self.top_right_info_panel.all_bundles():
                    render_eng.remove(bun)
                self.top_right_info_panel = None

        if self.top_right_info_panel is None and obj_to_display is not None:
            new_panel = TooltipFactory.build_tooltip(obj_to_display, layer=spriteref.UI_0_LAYER)
            w = new_panel.get_rect()[2] if new_panel is not None else 0
            xy = (gs.get_instance().screen_size[0] - w - 16, 16)

            # XXX building it twice because we don't know how wide it will be beforehand...
            new_panel = TooltipFactory.build_tooltip(obj_to_display, xy=xy, layer=spriteref.UI_0_LAYER)
            self.top_right_info_panel = new_panel
            if self.top_right_info_panel is not None:
                for bun in self.top_right_info_panel.all_bundles():
                    render_eng.update(bun)

    def _get_obj_at_screen_pos(self, world, xy):
        """returns: Item, ItemEntity, EnemyEntity, Entity, or None"""
        if xy is None:
            return None
        else:
            if self.in_inventory_panel(xy):
                grid, cell = self.inventory_panel.get_grid_and_cell_at_pos(*xy)
                if grid is not None and cell is not None:
                    return grid.item_at_position(cell)
            else:
                world_pos = gs.get_instance().screen_to_world_coords(xy)
                item_entity = self._get_entity_at_world_coords(world, world_pos, cond=lambda x: x.is_item())
                if item_entity is not None:
                    return item_entity

                enemy_entity = self._get_entity_at_world_coords(world, world_pos, cond=lambda x: x.is_enemy())
                if enemy_entity is not None:
                    return enemy_entity

                return self._get_entity_at_world_coords(world, world_pos)

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
                if isinstance(obj_at_xy, entities.PickupEntity):
                    if obj_at_xy.can_pickup(world, world.get_player()):
                        return spriteref.UI.Cursors.hand_cursor

            return super().cursor_style_at(world, xy)

    def _top_level_interactable_imgs(self):
        if self.health_bar_panel is not None:
            yield self.health_bar_panel
        if self.inventory_panel is not None:
            yield self.inventory_panel

    def _update_tooltip(self, world):
        input_state = InputState.get_instance()
        screen_pos = input_state.mouse_pos() if input_state.mouse_in_window() else None

        if screen_pos is None:
            obj_to_display = None
        else:
            # when you're holding an item, we show the info in the top right, so there's
            # no need for a tooltip.
            if self.item_on_cursor_info is None:
                obj_to_display = self._get_obj_at_screen_pos(world, screen_pos)
            else:
                obj_to_display = None

            if self.item_on_cursor_info is None and obj_to_display is None and screen_pos is not None:
                for ui_img in self._top_level_interactable_imgs():
                    if ui_img.contains_point(*screen_pos):
                        tt_target = ui_img.get_tooltip_target_at(*screen_pos)
                        if tt_target is not None:
                            obj_to_display = tt_target
                            break

        if obj_to_display is None:
            self.set_active_tooltip(None)
        else:
            needs_update = False
            current_tooltip = self.get_active_tooltip()

            if obj_to_display is not None:
                if current_tooltip is None or current_tooltip.get_target() is not obj_to_display:
                    new_tooltip = TooltipFactory.build_tooltip(obj_to_display)
                    self.set_active_tooltip(new_tooltip)
                    needs_update = True

            current_tooltip = self.get_active_tooltip()

            render_eng = RenderEngine.get_instance()
            if current_tooltip is not None:
                offs = (-screen_pos[0], -screen_pos[1] - 24)
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

    def _update_inventory_panel(self):
        if not gs.get_instance().player_state().is_alive():
            if self.inventory_panel is not None:
                self._destroy_panel(self.inventory_panel)
                self.inventory_panel = None

        elif InputState.get_instance().was_pressed(gs.get_instance().settings().inventory_key()):
            if self.inventory_panel is None:
                self.rebuild_inventory()
            else:
                self._destroy_panel(self.inventory_panel)
                self.inventory_panel = None

        if self.inventory_panel is not None:
            if self.inventory_panel.state.is_dirty():
                print("rebuilding inventory")
                self.rebuild_inventory()
            else:
                self.inventory_panel.update_stats_imgs()

    def _update_health_bar_panel(self):
        if self.health_bar_panel is None:
            self.health_bar_panel = HealthBarPanel()

        if self.health_bar_panel.is_dirty():
            self.health_bar_panel.update_images()
            for bun in self.health_bar_panel.all_bundles():
                RenderEngine.get_instance().update(bun)

    def in_inventory_panel(self, screen_pos):
        rect = self.get_inventory_rect()
        if rect is None:
            return False
        else:
            return Utils.rect_contains(rect, screen_pos)

    def get_inventory_rect(self):
        if self.inventory_panel is None:
            return None
        else:
            return self.inventory_panel.total_rect

    def handle_click_in_world(self, world, x, y, button=1):
        screen_pos = (x, y)
        world_pos = gs.get_instance().screen_to_world_coords(screen_pos)

        player = world.get_player()
        ps = gs.get_instance().player_state()

        print("handling click in world")

        if button != 1:
            return

        if ps.held_item is None:
            can_pickup = lambda i: i.is_item() and i.can_pickup(world, player)
            clicked_item = self._get_entity_at_world_coords(world, world_pos, cond=can_pickup)
            if clicked_item is not None:
                world.remove(clicked_item)
                ps.held_item = clicked_item.get_item()
        else:
            print("dropping item..?")
            if player is not None:
                p_center = player.center()  # drop position
                drop_dir = Utils.sub(world_pos, p_center)

                item = ps.held_item
                ps.held_item = None

                world.add_item_as_entity(item, p_center, direction=drop_dir)

    def _update_item_on_cursor_info(self):
        destroy_image = False
        create_image = False

        ps = gs.get_instance().player_state()

        if not InputState.get_instance().mouse_in_window():
            destroy_image = True

        elif ps.held_item is not None and self.item_on_cursor_info is None:
            create_image = True
        elif ps.held_item is None and self.item_on_cursor_info is not None:
            destroy_image = True
        elif (ps.held_item is not None and self.item_on_cursor_info is not None
              and ps.held_item != self.item_on_cursor_info[0]):
                destroy_image = True
                create_image = True

        if InputState.get_instance().was_pressed(gs.get_instance().settings().rotate_cw_key()):
            if ps.held_item is not None and ps.held_item.can_rotate():
                ps.held_item = ps.held_item.rotate()
                create_image = True
                destroy_image = True

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

    def rebuild_inventory(self):
        render_eng = RenderEngine.get_instance()
        if self.inventory_panel is not None:
            for bun in self.inventory_panel.all_bundles():
                render_eng.remove(bun)

        self.inventory_panel = InventoryPanel()
        for bun in self.inventory_panel.all_bundles():
            render_eng.update(bun)

    def update(self, world):
        input_state = InputState.get_instance()
        screen_pos = input_state.mouse_pos()

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
                    self.handle_click_in_world(world, screen_pos[0], screen_pos[1], button=button)

        self._update_item_on_cursor_info()
        self._update_tooltip(world)
        self._update_top_right_info_panel(world)
        self._update_inventory_panel()

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

        if len(gs.get_instance().get_cinematics_queue()) > 0:
            gs.get_instance().menu_manager().set_active_menu(CinematicMenu())

        elif input_state.was_pressed(gs.get_instance().settings().exit_key()):
            gs.get_instance().menu_manager().set_active_menu(PauseMenu())

        p = world.get_player()
        if p is not None and not gs.get_instance().world_updates_paused():
            self.send_player_action_requests(p, world)

    def send_player_action_requests(self, player, world):
        pos = world.to_grid_coords(player.center()[0], player.center()[1])
        input_state = InputState.get_instance()
        import src.game.gameengine as gameengine

        dx = 0
        dy = 0
        if input_state.is_held(gs.get_instance().settings().left_key()):
            dx -= 1
        elif input_state.is_held(gs.get_instance().settings().up_key()):
            dy -= 1
        elif input_state.is_held(gs.get_instance().settings().right_key()):
            dx += 1
        elif input_state.is_held(gs.get_instance().settings().down_key()):
            dy += 1

        target_pos = None
        if dx != 0:
            target_pos = (pos[0] + dx, pos[1])
        elif dy != 0:
            target_pos = (pos[0], pos[1] + dy)

        res_list = []

        action_prov = gs.get_instance().get_targeting_action_provider()
        if action_prov is not None:
            action_targets = action_prov.get_targets(pos=pos)
            if target_pos is not None:
                for i in range(0, 5):
                    extended_target_pos = (target_pos[0] + dx * i, target_pos[1] + dy * i)
                    if extended_target_pos in action_targets:
                        res_list.append(action_prov.get_action(player, position=extended_target_pos))

        if target_pos is not None:
            res_list.append(gameengine.AttackAction(player, None, target_pos))
            res_list.append(gameengine.OpenDoorAction(player, target_pos))
            res_list.append(gameengine.InteractAction(player, target_pos))
            res_list.append(gameengine.MoveToAction(player, target_pos))

        if input_state.is_held(gs.get_instance().settings().enter_key()):
            res_list.append(gameengine.SkipTurnAction(player, position=pos))

        pc = gs.get_instance().player_controller()

        pc.set_requests(res_list)
        pc.add_requests(gameengine.PlayerWaitAction(player, position=target_pos), pc.LOWEST_PRIORITY)

    def cleanup(self):
        Menu.cleanup(self)
        self.inventory_panel = None
        self.item_on_cursor_info = None
        self.top_right_info_panel = None

    def all_bundles(self):
        for bun in Menu.all_bundles(self):
            yield bun
        if self.inventory_panel is not None:
            for bun in self.inventory_panel.all_bundles():
                yield bun
        if self.health_bar_panel is not None:
            for bun in self.health_bar_panel.all_bundles():
                yield bun
        if self.top_right_info_panel is not None:
            for bun in self.top_right_info_panel.all_bundles():
                yield bun
        if self.item_on_cursor_info is not None:
            for bun in self.item_on_cursor_info[1].all_bundles():
                yield bun
        if self.dialog_panel is not None:
            for bun in self.dialog_panel.all_bundles():
                yield bun