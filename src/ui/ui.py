import math

import src.game.stats
from src.renderengine.img import ImageBundle
import src.game.spriteref as spriteref
import src.items.item as item_module
from src.utils.util import Utils
from src.game.stats import StatTypes
import src.game.globalstate as gs
import src.utils.colors as colors
from src.renderengine.engine import RenderEngine


BG_DEPTH = 10
FG_DEPTH = 5


class ItemGridImage:

    def __init__(self, x, y, grid, layer, scale, depth):
        self.x = x
        self.y = y
        self.grid = grid
        self.layer = layer
        self.scale = scale
        self.depth = depth
        
        self.item_images = []
        
        self._build_images()
        
    def _build_images(self):
        cellsize = spriteref.Items.piece_bigs[0].size()
        for item in self.grid.all_items():
            pos = self.grid.get_pos(item)
            x_pos = self.x + pos[0] * cellsize[0] * self.scale
            y_pos = self.y + pos[1] * cellsize[1] * self.scale
            self.item_images.append(ItemImage(x_pos, y_pos, item, self.layer, self.scale, self.depth))
        
    def all_bundles(self):
        for item_img in self.item_images:
            for bun in item_img.all_bundles():
                yield bun


class InteractableImage:
    """Piece of UI that can be 'interacted with' using the mouse."""

    def contains_point(self, x, y):
        return False

    def on_click(self, x, y, button=1):
        """returns: True if click was absorbed, False otherwise"""
        for c in self.all_child_imgs():
            if c.contains_point(x, y):
                if c.on_click(x, y):
                    return True
        return False

    def get_cursor_at(self, x, y):
        for c in self.all_child_imgs():
            if c.contains_point(x, y):
                return c.get_cursor_at(x, y)
        return spriteref.UI.Cursors.arrow_cursor

    def get_tooltip_target_at(self, x, y):
        for c in self.all_child_imgs():
            if c.contains_point(x, y):
                target = c.get_tooltip_target_at(x, y)
                if target is not None:
                    return target
        return None

    def is_dirty(self):
        return True

    def all_child_imgs(self):
        """yields all the sub-InteractableImages of this one"""
        return []

    def update_images(self):
        for c in self.all_child_imgs():
            if c.is_dirty():
                c.update_images()

    def all_bundles(self):
        for c in self.all_child_imgs():
            for bun in c.all_bundles():
                yield bun
        

class InventoryPanel(InteractableImage):

    def __init__(self):
        self.player_state = gs.get_instance().player_state()
        self.state = self.player_state.inventory()
        self.layer = spriteref.UI_0_LAYER

        self.top_img = None
        self.mid_imgs = []
        self.bot_img = None

        self.title_colors = colors.LIGHT_GRAY
        self.eq_title_text = None
        self.inv_title_text = None

        self.sc = 2
        self.text_sc = 1
        
        self.total_rect = [0, 0,
                           spriteref.UI.inv_panel_top.width() * self.sc,
                           (128 + 16 * self.state.rows) * self.sc]

        self.equip_grid_rect = [8*self.sc, 16*self.sc, 80*self.sc, 80*self.sc]
        self.inv_grid_rect = [8*self.sc, 112*self.sc, 144*self.sc, 16*self.state.rows*self.sc]
        self.stats_rect = [96*self.sc, 16*self.sc, 56*self.sc, 80*self.sc]

        self.eq_title_rect = [8*self.sc, 0*self.sc + 4, 80*self.sc, 16*self.sc - 4]
        self.inv_title_rect = [8*self.sc, 96*self.sc + 4, 80*self.sc, 16*self.sc - 4]

        self.lvl_text = None
        self.att_text = None
        self.def_text = None
        self.vit_text = None
        self.hp_text = None
        self.spd_text = None
        
        self.equip_img = None
        self.inv_img = None
        
        self._build_images()
        self.state.set_clean()

    def get_rect(self):
        return self.total_rect

    def get_grid_and_cell_at_pos(self, x, y):
        pos_in_panel = (x - self.total_rect[0],
                        y - self.total_rect[1])

        eq_rect = self.equip_grid_rect
        if Utils.rect_contains(eq_rect, pos_in_panel):
            grid = self.state.equip_grid
            x = int((pos_in_panel[0] - eq_rect[0])/eq_rect[2]*grid.size[0])
            y = int((pos_in_panel[1] - eq_rect[1])/eq_rect[3]*grid.size[1])
            return (grid, (x, y))

        inv_rect = self.inv_grid_rect
        if Utils.rect_contains(inv_rect, pos_in_panel):
            grid = self.state.inv_grid
            x = int((pos_in_panel[0] - inv_rect[0])/inv_rect[2]*grid.size[0])
            y = int((pos_in_panel[1] - inv_rect[1])/inv_rect[3]*grid.size[1])
            return (grid, (x, y))

        return (None, None)

    def get_item_at_pos(self, x, y):
        grid, cell = self.get_grid_and_cell_at_pos(x, y)
        if grid is None or cell is None:
            return None
        else:
            return grid.item_at_position(cell)

    def _build_title_img(self, text, rect):
        res = TextImage(rect[0], 0, text, self.layer, scale=self.text_sc, color=self.title_colors)
        new_y = rect[1] + (rect[3] - res.line_height()) // 2
        return res.update(new_y=new_y)
        
    def _build_images(self):
        self.top_img = ImageBundle(spriteref.UI.inv_panel_top, 0, 0, layer=self.layer, scale=self.sc, depth=BG_DEPTH)
        for i in range(0, self.state.rows - 1):
            y = (128 + i*16)*self.sc
            self.mid_imgs.append(ImageBundle(spriteref.UI.inv_panel_mid, 0, y, layer=self.layer, scale=self.sc, depth=BG_DEPTH))
        y = (128 + self.state.rows*16 - 16)*self.sc
        self.bot_img = ImageBundle(spriteref.UI.inv_panel_bot, 0, y, layer=self.layer, scale=self.sc, depth=BG_DEPTH)
        
        self.inv_title_text = self._build_title_img("Inventory", self.inv_title_rect)
        self.eq_title_text = self._build_title_img("Equipment", self.eq_title_rect)

        self.lvl_text = TextImage(0, 0, "lvl", self.layer, scale=self.text_sc, depth=FG_DEPTH)
        self.att_text = TextImage(0, 0, "att", self.layer, scale=self.text_sc, color=StatTypes.ATT.get_color(), depth=FG_DEPTH)
        self.def_text = TextImage(0, 0, "def", self.layer, scale=self.text_sc, color=StatTypes.DEF.get_color(), depth=FG_DEPTH)
        self.vit_text = TextImage(0, 0, "vit", self.layer, scale=self.text_sc, color=StatTypes.VIT.get_color(), depth=FG_DEPTH)
        self.spd_text = TextImage(0, 0, "spd", self.layer, scale=self.text_sc, color=StatTypes.SPEED.get_color(), depth=FG_DEPTH)
        self.hp_text = TextImage(0, 0, "hp", self.layer, scale=self.text_sc, color=colors.LIGHT_GRAY, depth=FG_DEPTH)

        self.update_stats_imgs()
        self.update_item_grid_imgs()

    def update_item_grid_imgs(self):
        if self.state.is_dirty():
            if self.equip_img is not None:
                for bun in self.equip_img.all_bundles():
                    RenderEngine.get_instance().remove(bun)
                self.equip_img = None
            if self.inv_img is not None:
                for bun in self.inv_img.all_bundles():
                    RenderEngine.get_instance().remove(bun)
                self.inv_img = None

        if self.equip_img is None:
            e_xy = (self.equip_grid_rect[0], self.equip_grid_rect[1])
            self.equip_img = ItemGridImage(*e_xy, self.state.equip_grid, self.layer, self.sc, FG_DEPTH)

        if self.inv_img is None:
            inv_xy = (self.inv_grid_rect[0], self.inv_grid_rect[1])
            self.inv_img = ItemGridImage(*inv_xy, self.state.inv_grid, self.layer, self.sc, FG_DEPTH)

        self.state.set_clean()

    def update_stats_imgs(self):
        s_xy = [self.stats_rect[0], self.stats_rect[1]]

        render_eng = RenderEngine.get_instance()

        lvl_txt = "LVL:{}".format(gs.get_instance().get_zone_level())
        if lvl_txt != self.lvl_text.get_text():
            self.lvl_text = self.lvl_text.update(new_text=lvl_txt, new_x=s_xy[0], new_y=s_xy[1])
            render_eng.update(self.lvl_text)
        s_xy[1] += self.lvl_text.line_height()

        att_value = (self.player_state.stat_value(StatTypes.ATT) +
                     self.player_state.stat_value(StatTypes.UNARMED_ATT))
        att_str = "ATT:{}".format(att_value)
        if att_str != self.att_text.get_text():
            self.att_text = self.att_text.update(new_text=att_str, new_x=s_xy[0], new_y=s_xy[1])
            render_eng.update(self.att_text)
        s_xy[1] += self.att_text.line_height()

        def_str = "DEF:{}".format(self.player_state.stat_value(StatTypes.DEF))
        if def_str != self.def_text.get_text():
            self.def_text = self.def_text.update(new_text=def_str, new_x=s_xy[0], new_y=s_xy[1])
            render_eng.update(self.def_text)
        s_xy[1] += self.def_text.line_height()

        vit_str = "VIT:{}".format(self.player_state.stat_value(StatTypes.VIT))
        if vit_str != self.vit_text.get_text():
            self.vit_text = self.vit_text.update(new_text=vit_str, new_x=s_xy[0], new_y=s_xy[1])
            render_eng.update(self.vit_text)
        s_xy[1] += self.vit_text.line_height()

        spd_str = "SPD:{}".format(self.player_state.stat_value(StatTypes.SPEED))
        if spd_str != self.spd_text.get_text():
            self.spd_text = self.spd_text.update(new_text=spd_str, new_x=s_xy[0], new_y=s_xy[1])
            render_eng.update(self.spd_text)
        s_xy[1] += self.spd_text.line_height()

        hp_str = "HP: {}/{}".format(self.player_state.hp(), self.player_state.max_hp())
        if hp_str != self.hp_text.get_text():
            self.hp_text = self.hp_text.update(new_text=hp_str, new_x=s_xy[0], new_y=s_xy[1])
            render_eng.update(self.hp_text)
        s_xy[1] += self.hp_text.line_height()

    def all_stat_text_bundles(self):
        for bun in self.lvl_text.all_bundles():
            yield bun
        for bun in self.att_text.all_bundles():
            yield bun
        for bun in self.def_text.all_bundles():
            yield bun
        for bun in self.vit_text.all_bundles():
            yield bun
        for bun in self.spd_text.all_bundles():
            yield bun
        for bun in self.hp_text.all_bundles():
            yield bun

    def contains_point(self, x, y):
        r = self.get_rect()
        return r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]

    def on_click(self, x, y, button=1):
        """returns: True if click was absorbed, False otherwise"""
        if super().on_click(x, y, button=button):
            return True

        ps = gs.get_instance().player_state()
        screen_pos = (x, y)

        if button == 1:
            if ps.held_item is not None:
                # when holding an item, gotta offset the click to the top left corner
                item_size = ItemImage.calc_size(ps.held_item, 2)
                grid_click_pos = Utils.add(screen_pos, (-item_size[0] // 2, -item_size[1] // 2))
                grid_click_pos = Utils.add(grid_click_pos, (16, 16))  # plus some fudge XXX
            else:
                grid_click_pos = screen_pos

            grid, cell = self.get_grid_and_cell_at_pos(*grid_click_pos)

            if grid is not None and cell is not None:
                if ps.held_item is not None:
                    if grid.can_place(ps.held_item, cell):
                        grid.place(ps.held_item, cell)
                        ps.held_item = None
                    else:
                        replaced_with = grid.try_to_replace(ps.held_item, cell)
                        if replaced_with is not None:
                            ps.held_item = replaced_with
                else:
                    clicked_item = grid.item_at_position(cell)
                    if clicked_item is not None:
                        grid.remove(clicked_item)
                        gs.get_instance().player_state().held_item = clicked_item

        elif button == 3:
            if ps.held_item is None:
                clicked_item = self.get_item_at_pos(x, y)
                if clicked_item is not None:
                    import src.game.gameengine as gameengine
                    consume_aciton = gameengine.ConsumeItemAction(None, clicked_item)
                    pc = gs.get_instance().player_controller()
                    pc.add_requests(consume_aciton, priority=pc.HIGHEST_PRIORITY)

        return True  # need to prevent clicks from falling through to world

    def get_cursor_at(self, x, y):
        if self.get_item_at_pos(x, y) is not None:
            return spriteref.UI.Cursors.hand_cursor
        else:
            return super().get_cursor_at(x, y)

    def get_tooltip_target_at(self, x, y):
        if self.get_item_at_pos(x, y) is not None:
            return self.get_item_at_pos(x, y)
        else:
            return super().get_cursor_at(x, y)

    def is_dirty(self):
        return True

    def all_child_imgs(self):
        """yields all the sub-InteractableImages of this one"""
        return []

    def update_images(self):
        super().update_images()
        self.update_stats_imgs()

    def all_bundles(self):
        yield self.top_img
        for img in self.mid_imgs:
            yield img
        yield self.bot_img
        for bun in self.inv_title_text.all_bundles():
            yield bun
        for bun in self.eq_title_text.all_bundles():
            yield bun
        for bun in self.all_stat_text_bundles():
            yield bun
        for bun in self.equip_img.all_bundles():
            yield bun 
        for bun in self.inv_img.all_bundles():
            yield bun
        for bun in super().all_bundles():
            yield bun


class DialogPanel:

    BORDER_SIZE = 8, 8
    TEXT_SCALE= 1
    SIZE = (256 * 2 - 16 * 2, 48 * 2 - 16)

    def __init__(self, dialog):
        self._dialog = dialog
        self._border_imgs = []
        self._speaker_img = None
        self._text_displaying = ""
        self._option_selected = None
        self._text_img = None
        self._bg_imgs = []

    def get_dialog(self):
        return self._dialog

    def update_images(self, text, sprite, left_side):
        """
            returns: True if needs a full render engine update, else False
        """
        needs_update = False

        x = gs.get_instance().screen_size[0] // 2 - DialogPanel.SIZE[0] // 2
        y = gs.get_instance().screen_size[1] - HealthBarPanel.SIZE[1] - DialogPanel.SIZE[1]
        lay = spriteref.UI_0_LAYER

        if len(self._border_imgs) == 0:
            bw, bh = DialogPanel.BORDER_SIZE
            right_x = x + DialogPanel.SIZE[0]
            border_sprites = spriteref.UI.text_panel_edges

            for i in range(0, DialogPanel.SIZE[0] // bw):
                top_bord = ImageBundle(border_sprites[1], x + bw * i, y - bh, layer=lay, scale=2, depth=BG_DEPTH)
                self._border_imgs.append(top_bord)
            for i in range(0, DialogPanel.SIZE[1] // bh):
                l_bord = ImageBundle(border_sprites[3], x - bw, y + bh * i, layer=lay, scale=2, depth=BG_DEPTH)
                self._border_imgs.append(l_bord)
                r_bord = ImageBundle(border_sprites[5], right_x, y + bh * i,  layer=lay, scale=2, depth=BG_DEPTH)
                self._border_imgs.append(r_bord)
            self._border_imgs.append(ImageBundle(border_sprites[0], x - bw, y - bh, layer=lay, scale=2, depth=BG_DEPTH))
            self._border_imgs.append(ImageBundle(border_sprites[2], right_x, y - bh, layer=lay, scale=2, depth=BG_DEPTH))
            needs_update = True

        if len(self._bg_imgs) == 0:
            bg_sprite = spriteref.UI.text_panel_edges[4]
            bg_w, bg_h = bg_sprite.size()
            sc = min(DialogPanel.SIZE[0] // bg_w, DialogPanel.SIZE[1] // bg_h)
            bg_w *= sc
            bg_h *= sc
            for x1 in range(0, DialogPanel.SIZE[0] // bg_w):
                for y1 in range(0, DialogPanel.SIZE[1] // bg_h):
                    self._bg_imgs.append(ImageBundle(bg_sprite, x + x1 * bg_w, y + y1 * bg_h, layer=lay, scale=sc, depth=BG_DEPTH))
            needs_update = True

        text_buffer = 6, 6
        text_area = [x + text_buffer[0], y + text_buffer[1],
                     DialogPanel.SIZE[0] - text_buffer[0] * 2,
                     DialogPanel.SIZE[1] - text_buffer[1] * 2]

        if sprite is not None:
            sprite_buffer = 6, 4
            if self._speaker_img is None:
                y_pos = y + DialogPanel.SIZE[1] // 2 - sprite.height() * 2 // 2
                if left_side:
                    x_pos = x + sprite_buffer[0]
                else:
                    x_pos = x + DialogPanel.SIZE[0] - sprite.width() * 2 - sprite_buffer[0]
                self._speaker_img = ImageBundle(sprite, x_pos, y_pos, layer=lay, scale=2, depth=FG_DEPTH)
            self._speaker_img = self._speaker_img.update(new_model=sprite)

            if left_side:
                text_x = x + self._speaker_img.width() + sprite_buffer[0] + text_buffer[0]
            else:
                text_x = x + text_buffer[0]

            text_area = [text_x, y + text_buffer[0],
                         DialogPanel.SIZE[0] - self._speaker_img.width() - text_buffer[0] - sprite_buffer[0],
                         DialogPanel.SIZE[1] - text_buffer[1] * 2]
            # gets updated automatically

        if len(text) > 0 and self._text_img is None:
            wrapped_text = TextImage.wrap_words_to_fit(text, DialogPanel.TEXT_SCALE, text_area[2])
            custom_colors = {}
            if self._option_selected is not None:
                opt_text = self._dialog.get_options()[self._option_selected]

                try:
                    pos = wrapped_text.index(opt_text)
                    for i in range(pos, pos + len(opt_text)):
                        custom_colors[i] = (255, 0, 0)
                    print("custom_colors={}".format(custom_colors))
                except ValueError:
                    print("ERROR: option \"{}\" missing from dialog \"{}\"".format(opt_text, wrapped_text))

            self._text_img = TextImage(text_area[0], text_area[1], wrapped_text, layer=lay, scale=DialogPanel.TEXT_SCALE,
                                       y_kerning=3,
                                       custom_colors=custom_colors,
                                       depth=FG_DEPTH)
            needs_update = True

        return needs_update

    def update(self):
        do_text_rebuild = False

        new_text = self._dialog.get_visible_text(invisible_sub=TextImage.INVISIBLE_CHAR)
        if self._text_displaying != new_text and self._text_img is not None:
            do_text_rebuild = True

        self._text_displaying = new_text

        option_idx = None
        if len(self._dialog.get_options()) > 0 and self._dialog.is_done_scrolling():
            option_idx = self._dialog.get_selected_opt_idx()

        if option_idx != self._option_selected:
            do_text_rebuild = True
            self._option_selected = option_idx

        render_eng = RenderEngine.get_instance()

        new_sprite = self._dialog.get_visible_sprite()
        if new_sprite is None and self._speaker_img is not None:
            render_eng.remove(self._speaker_img)
            self._speaker_img = None

        if do_text_rebuild:
            for bun in self._text_img.all_bundles():
                render_eng.remove(bun)
            self._text_img = None

        full_update = self.update_images(self._text_displaying, new_sprite,
                                         self._dialog.get_sprite_side())

        if full_update:
            for bun in self.all_bundles():
                render_eng.update(bun)
        elif self._speaker_img is not None:
            render_eng.update(self._speaker_img)

    def all_bundles(self):
        for bg in self._bg_imgs:
            yield bg
        for bord in self._border_imgs:
            yield bord
        if self._speaker_img is not None:
            yield self._speaker_img
        if self._text_img is not None:
            for bun in self._text_img.all_bundles():
                yield bun


class MappedActionImage(InteractableImage):

    def __init__(self, action_prov, rect):
        self.action_prov = action_prov
        self.rect = rect

        self._border_img = None
        self._icon_img = None

    def contains_point(self, x, y):
        if self.action_prov is None:
            return False
        else:
            return (self.rect[0] <= x < self.rect[0] + self.rect[2] and
                    self.rect[1] <= y < self.rect[1] + self.rect[3])

    def on_click(self, x, y, button=1):
        """returns: True if click was absorbed, False otherwise"""
        if self.action_prov is not None:
            targeting_action = gs.get_instance().get_targeting_action_provider()
            if self.action_prov == targeting_action:
                gs.get_instance().set_targeting_action_provider(None)
            else:
                gs.get_instance().set_targeting_action_provider(self.action_prov)
            return True
        return False

    def get_cursor_at(self, x, y):
        # return spriteref.UI.Cursors.hand_cursor
        return super().get_cursor_at(x, y)

    def get_tooltip_target_at(self, x, y):
        return self.action_prov

    def is_dirty(self):
        return True

    def update_images(self):
        if self.action_prov is None:
            RenderEngine.get_instance().remove(self._border_img)
            RenderEngine.get_instance().remove(self._icon_img)
            self._border_img = None
            self._icon_img = None
        else:
            targeting_action = gs.get_instance().get_targeting_action_provider()
            color = gs.get_instance().get_targeting_action_color() if self.action_prov == targeting_action else (1, 1, 1)

            if self._icon_img is None:
                self._icon_img = ImageBundle.new_bundle(spriteref.UI_0_LAYER, scale=4, depth=FG_DEPTH)
            self._icon_img = self._icon_img.update(new_model=self.action_prov.get_icon(), new_color=color,
                                                   new_x=self.rect[0] + 8, new_y=self.rect[1] + 8)
            if self._border_img is None:
                self._border_img = ImageBundle.new_bundle(spriteref.UI_0_LAYER, scale=2, depth=FG_DEPTH)
            self._border_img = self._border_img.update(new_model=spriteref.UI.status_bar_action_border, new_color=color,
                                                       new_x=self.rect[0], new_y=self.rect[1])

    def all_bundles(self):
        if self._border_img is not None:
            yield self._border_img
        if self._icon_img is not None:
            yield self._icon_img


class HealthBarPanel(InteractableImage):

    SIZE = (400 * 2, 53 * 2)

    def __init__(self):
        self._top_img = None
        self._bar_img = None
        self._floating_bars = []  # list of [img, duration]

        self._rect = [0, 0, 0, 0]
        self._bar_rect = [0, 0, 0, 0]

        self._float_dur = 30
        self._float_height = 30

        self._action_imgs = [None] * 6  # list of MappedActionImages

    def contains_point(self, x, y):
        if super().contains_point(x, y):
            return True
        else:
            return Utils.rect_contains(self._rect, (x, y)) or Utils.rect_contains(self._bar_rect, (x, y))

    def get_tooltip_target_at(self, x, y):
        if Utils.rect_contains(self._bar_rect, (x, y)):
            ps = gs.get_instance().player_state()
            target = TextBuilder()
            target.add_line("HP: {}/{}".format(ps.hp(), ps.max_hp()), color=colors.LIGHT_GRAY)
            return target
        else:
            return super().get_tooltip_target_at(x, y)

    def update_images(self):
        render_eng = RenderEngine.get_instance()
        if len(self._floating_bars) > 0:
            new_bars = []
            for fb in self._floating_bars:
                if fb[1] >= self._float_dur:
                    render_eng.remove(fb[0])
                else:
                    new_bars.append([fb[0], fb[1] + 1])
            self._floating_bars = new_bars

        p_state = gs.get_instance().player_state()
        cur_hp = p_state.hp()
        max_hp = p_state.max_hp()
        new_damage = 0

        if self._top_img is None:
            self._top_img = ImageBundle(spriteref.UI.status_bar_base, 0, 0,
                                        layer=spriteref.UI_0_LAYER, scale=2, depth=BG_DEPTH)
        if self._bar_img is None:
            self._bar_img = ImageBundle.new_bundle(spriteref.UI_0_LAYER, scale=2, depth=BG_DEPTH + 1)

        x = gs.get_instance().screen_size[0] // 2 - self._top_img.width() // 2
        y = gs.get_instance().screen_size[1] - self._top_img.height()

        self._rect = [x, y, self._top_img.width(), self._top_img.height()]

        hp_pcnt_full = Utils.bound(cur_hp / max_hp, 0.0, 1.0)
        bar_w = spriteref.UI.health_bar_full.width() * 2
        bar_x = gs.get_instance().screen_size[0] // 2 - bar_w // 2

        self._bar_rect = [bar_x, y, bar_w, 16 * 2]

        if new_damage > 0:
            pcnt_full = Utils.bound(new_damage / max_hp, 0.0, 1.0)
            dmg_x = int(bar_x + hp_pcnt_full * bar_w)
            dmg_sprite = spriteref.UI.get_health_bar(pcnt_full)
            dmg_img = ImageBundle(dmg_sprite, dmg_x, 0, layer=spriteref.UI_0_LAYER, scale=2, depth=0)
            self._floating_bars.append([dmg_img, 0])

        bar_color = (1.0, 0.25, 0.25)

        for i in range(0, len(self._floating_bars)):
            img, cur_dur = self._floating_bars[i]
            prog = Utils.bound(cur_dur / self._float_dur, 0.0, 1.0)
            h_offs = int(self._float_height * prog)
            g = bar_color[1] * (1 - prog)
            b = bar_color[2] * (1 - prog)

            self._floating_bars[i][0] = img.update(new_y=(y - h_offs), new_color=(1.0, g, b))

        self._top_img = self._top_img.update(new_x=x, new_y=y)
        bar_sprite = spriteref.UI.get_health_bar(hp_pcnt_full)

        glow_factor = (1 - hp_pcnt_full) * 0.2 * math.cos(((gs.get_instance().anim_tick % 6) / 6) * 2 * (3.1415))
        color = (bar_color[0], bar_color[1] + glow_factor, bar_color[2] + glow_factor)

        self._bar_img = self._bar_img.update(new_model=bar_sprite, new_x=bar_x, new_y=y, new_color=color)

        x_start = [x + 87 * 2 + i*40*2 for i in range(0, 3)] + [x + 205*2 + i*40*2 for i in range(0, 3)]
        y_start = y + 19 * 2
        for i in range(0, 6):
            action_prov = gs.get_instance().get_mapped_action(i)
            rect = [x_start[i], y_start, 28*2, 28*2]

            if self._action_imgs[i] is None:
                self._action_imgs[i] = MappedActionImage(action_prov, rect)
            else:
                self._action_imgs[i].action_prov = action_prov
                self._action_imgs[i].rect = rect

            if self._action_imgs[i].is_dirty():
                self._action_imgs[i].update_images()

    def all_child_imgs(self):
        for i in self._action_imgs:
            if i is not None:
                yield i

    def is_dirty(self):
        return True

    def all_bundles(self):
        for bun in super().all_bundles():
            yield bun
        if self._bar_img is not None:
            yield self._bar_img
        if self._top_img is not None:
            yield self._top_img
        for floating_bar in self._floating_bars:
            yield floating_bar[0]


class TextBuilder:
    def __init__(self):
        self._text = ""
        self._custom_colors = {}

    def add(self, text, color=None):
        if color is not None:
            for i in range(0, len(text)):
                self._custom_colors[len(self._text) + i] = color
        self._text += text

        return self

    def add_line(self, text, color=None):
        self.add(text + "\n", color=color)

    def text(self):
        return self._text

    def custom_colors(self):
        return self._custom_colors

    def __eq__(self, other):
        if isinstance(other, TextBuilder):
            return self.text() == other.text() and self.custom_colors() == other.custom_colors()
        else:
            return False

    def __hash__(self):
        return hash((self.text(), self.custom_colors()))


class TextImage:

    INVISIBLE_CHAR = "`"

    X_KERNING = 0
    Y_KERNING = 0

    def __init__(self, x, y, text, layer, color=(1, 1, 1), scale=1, depth=0, center_w=None, y_kerning=None,
                 custom_colors=None):
        self.x = x
        self.center_w = center_w
        self.y = y
        self.text = text
        self.layer = layer
        self.color = color
        self.depth = depth
        self.custom_colors = {} if custom_colors is None else custom_colors  # int index -> (int, int, int) color
        self.scale = scale
        self._letter_images = []
        self._letter_image_indexes = []
        self.y_kerning = TextImage.Y_KERNING if y_kerning is None else y_kerning

        self._build_images()

        self.actual_size = self._recalc_size()

    def _recalc_size(self):
        x_range = [None, None]
        y_range = [None, None]
        for img in self.all_bundles():
            x_range[0] = img.x() if x_range[0] is None else min(x_range[0], img.x())
            x_range[1] = img.x() + img.width() if x_range[1] is None else max(x_range[1], img.x() + img.width())
            y_range[0] = img.y() if y_range[0] is None else min(y_range[0], img.y())
            y_range[1] = img.y() + img.height() if y_range[1] is None else max(y_range[1], img.y() + img.height())

        if x_range[0] is None:
            return (0, 0)

        return (x_range[1] - x_range[0], y_range[1] - y_range[0])

    @staticmethod
    def calc_width(text, scale):
        max_line_w = 0
        cur_line_w = 0
        char_w = (spriteref.Font.get_char("a").width() + TextImage.X_KERNING) * scale
        for c in text:
            if c == "\n":
                cur_line_w = 0
            else:
                cur_line_w += char_w
                max_line_w = max(max_line_w, cur_line_w)
        return max_line_w

    def get_text(self):
        return self.text

    def size(self):
        return self.actual_size

    def line_height(self):
        return (spriteref.Font.get_char("a").height() + self.y_kerning) * self.scale

    def _build_images(self):
        ypos = TextImage.Y_KERNING

        if self.center_w is not None:
            true_width = TextImage.calc_width(self.text, self.scale)
            x_shift = self.x + self.center_w // 2 - true_width // 2
        else:
            x_shift = TextImage.X_KERNING

        xpos = x_shift

        a_sprite = spriteref.Font.get_char("a")
        idx = 0

        text_chunks = spriteref.split_text(self.text)

        for chunk in text_chunks:
            if chunk == " " or chunk == TextImage.INVISIBLE_CHAR:
                xpos += (TextImage.X_KERNING + a_sprite.width()) * self.scale
            elif chunk == "\n":
                xpos = x_shift
                ypos += (self.y_kerning + a_sprite.height()) * self.scale
            else:
                if len(chunk) == 1:
                    sprite = spriteref.Font.get_char(chunk)
                else:
                    sprite = spriteref.cached_text_imgs[chunk]

                if idx in self.custom_colors:
                    color = self.custom_colors[idx]
                else:
                    color = self.color

                img = ImageBundle(sprite, self.x + xpos, self.y + ypos, layer=self.layer,
                                  scale=self.scale, color=color, depth=self.depth)

                self._letter_images.append(img)
                self._letter_image_indexes.append(idx)
                xpos += (TextImage.X_KERNING + sprite.width()) * self.scale

            idx += len(chunk)

    def update(self, new_text=None, new_x=None, new_y=None, new_depth=None, new_color=None, new_custom_colors=None):
        dx = 0 if new_x is None else new_x - self.x
        dy = 0 if new_y is None else new_y - self.y
        self.custom_colors = new_custom_colors if new_custom_colors is not None else self.custom_colors
        self.color = new_color if new_color is not None else self.color

        if new_text is not None and new_text != self.text:
            render_eng = RenderEngine.get_instance()
            for bun in self._letter_images:
                if bun is not None:
                    render_eng.remove(bun)
            self._letter_images.clear()
            self._letter_image_indexes.clear()

            self.text = new_text
            self._build_images()

        new_imgs = []
        for letter, idx in zip(self._letter_images, self._letter_image_indexes):
            letter_new_x = letter.x() + dx
            letter_new_y = letter.y() + dy
            if idx in self.custom_colors:
                color = self.custom_colors[idx]
            else:
                color = self.color
            new_imgs.append(letter.update(new_x=letter_new_x, new_y=letter_new_y,
                                          new_depth=new_depth, new_color=color))

        self._letter_images = new_imgs
        self.x = new_x if new_x is not None else self.x
        self.y = new_y if new_y is not None else self.y
        self.actual_size = self._recalc_size()

        return self

    def all_bundles(self):
        for b in self._letter_images:
            if b is not None:
                yield b

    @staticmethod
    def wrap_words_to_fit(text, scale, width):
        split_on_newlines = text.split("\n")
        if len(split_on_newlines) > 1:
            """if it's got newlines, split it, call this method again, and re-combine"""
            wrapped_substrings = [TextImage.wrap_words_to_fit(line, scale, width) for line in split_on_newlines]
            return "\n".join(wrapped_substrings)

        text = text.replace("\n", " ")  # shouldn't be any at this point, but just to be safe~
        words = text.split(" ")
        lines = []
        cur_line = []
        while len(words) > 0:
            if len(cur_line) == 0:
                cur_line.append(words[0])
                words = words[1:]
            if len(words) == 0 or TextImage.calc_width(" ".join(cur_line + [words[0]]), scale) > width:
                lines.append(" ".join(cur_line))
                cur_line.clear()
            elif len(words) > 0:
                cur_line.append(words[0])
                words = words[1:]
                if len(words) == 0:
                    lines.append(" ".join(cur_line))

        return "\n".join(lines)


class ItemImage:

    def __init__(self, x, y, item, layer, scale, depth):
        self.x = x
        self.y = y
        self.item = item
        self.scale = scale
        self.depth = depth
        self._bundles = []
        self.layer = layer

        self._build_images()

    def _build_images(self):
        if isinstance(self.item, item_module.StatCubesItem):
            for cube in self.item.cubes:
                # pretty special-casey but.. it's fine
                art = 0 if cube not in self.item.cube_art else self.item.cube_art[cube]
                sprite = spriteref.Items.piece_bigs[art]
                xpos = self.x + sprite.width()*self.scale*cube[0]
                ypos = self.y + sprite.height()*self.scale*cube[1]
                img = ImageBundle(sprite, xpos, ypos, layer=self.layer, scale=self.scale, color=self.item.color, depth=self.depth)
                self._bundles.append(img)
        elif isinstance(self.item, item_module.SpriteItem):
            sprite = self.item.big_sprite()
            img = ImageBundle(sprite, self.x, self.y, layer=self.layer, rotation=self.item.sprite_rotation(), scale=self.scale, depth=self.depth, color=self.item.color)
            self._bundles.append(img)

    def all_bundles(self):
        for b in self._bundles:
            yield b

    @staticmethod
    def calc_size(item, scale):
        if isinstance(item, item_module.StatCubesItem):
            sprite = spriteref.Items.piece_bigs[0]
            return (scale*sprite.width()*item.w(), scale*sprite.height()*item.h())
        elif isinstance(item, item_module.SpriteItem):
            sprite_rot = item.sprite_rotation()
            sprite = item.big_sprite()
            if sprite_rot % 2 == 0:
                return (scale * sprite.width(), scale * sprite.height())
            else:
                return (scale * sprite.height(), scale * sprite.width())


class CinematicPanel:

    IMAGE_SCALE = 6
    TEXT_SCALE = 2

    def __init__(self):
        self.current_image_img = None
        self.current_text = ""
        self.text_img = None
        self.border = 32

    def update(self, new_sprite, new_text):
        scale = CinematicPanel.IMAGE_SCALE
        if self.current_image_img is None:
            self.current_image_img = ImageBundle.new_bundle(spriteref.UI_0_LAYER, scale=scale)

        image_w = new_sprite.width() * scale
        new_x = gs.get_instance().screen_size[0] // 2 - image_w // 2
        new_y = 0 + self.border
        self.current_image_img = self.current_image_img.update(new_model=new_sprite, new_x=new_x, new_y=new_y)

        if new_text != self.current_text:
            if self.text_img is not None:
                render_eng = RenderEngine.get_instance()
                for bun in self.text_img.all_bundles():
                    render_eng.remove(bun)
                self.text_img = None

        if self.text_img is None and new_text != "":
            text_scale = CinematicPanel.TEXT_SCALE
            text_w = gs.get_instance().screen_size[0] - self.border*2
            text_x = self.border
            text_h = gs.get_instance().screen_size[1] // 5 - self.border
            text_y = gs.get_instance().screen_size[1] - text_h - self.border
            wrapped_text = TextImage.wrap_words_to_fit(new_text, text_scale, text_w)
            self.text_img = TextImage(text_x, text_y, wrapped_text, spriteref.UI_0_LAYER, scale=text_scale, y_kerning=2)
            self.current_text = new_text

    def all_bundles(self):
        if self.current_image_img is not None:
            yield self.current_image_img
        if self.text_img is not None:
            for bun in self.text_img.all_bundles():
                yield bun
