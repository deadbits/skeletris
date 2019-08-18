from OpenGL.GL import *
from OpenGL.GLU import *

import numpy


def assert_int(val):
    if not isinstance(val, int):
        raise ValueError("value is not an int: {}".format(val))


def pad_or_trunc(l, length):
    if len(l) < length:
        return l + [0] * (length - len(l))
    else:
        return l[:length]


def remove_all_in_place(l, elements):
    if len(l) == 0:
        return l

    rem_set = set(elements)
    last_element = len(l) - 1
    i = 0

    while i <= last_element:
        if l[i] in rem_set:
            while i <= last_element and l[last_element] in rem_set:
                last_element -= 1
            if i > last_element:
                break
            else:
                l[i] = l[last_element]
                last_element -= 1
        i += 1

    del l[(last_element+1):]


class _Layer:
    def __init__(self, name, layer_id, z_order, sort_sprites, use_color):
        """
            name: str -- used for logging
            z_order: number -- used to decide layer draw order
            sort_sprites: bool -- true if layer should sort sprites by depth
            use_color: bool -- true if layer respects sprites' color value
        """
        self.name = name
        self.layer_id = layer_id
        self.images = []  # ordered list of image ids
        self._image_set = set()
        self._offset = (0, 0)
        self._z_order = z_order
        self.sort_sprites = sort_sprites

        # these are the pointers the layer passes to gl
        self.vertices = numpy.array([], dtype=float)
        self.tex_coords = numpy.array([], dtype=float)
        self.indices = numpy.array([], dtype=float)
        self.colors = numpy.array([], dtype=float) if use_color else None
        
        self._dirty_sprites = []
        self._to_remove = []
        self._to_add = []
    
    def set_offset(self, x, y):
        self._offset = (x, y)

    def offset(self):
        return self._offset
    
    def update(self, bundle_id):
        assert_int(bundle_id)
        if bundle_id in self._image_set:
            self._dirty_sprites.append(bundle_id)
        else:
            self._image_set.add(bundle_id)
            self._to_add.append(bundle_id)
        
    def remove(self, bundle_id):
        assert_int(bundle_id)
        if bundle_id in self._image_set:
            self._image_set.remove(bundle_id)
            self._to_remove.append(bundle_id)
        
    def is_dirty(self):
        return len(self._dirty_sprites) + len(self._to_add) + len(self._to_remove) > 0
        
    def uses_color(self):
        return self.colors is not None
        
    def rebuild(self, bundle_lookup): 
        if len(self._to_remove) > 0:
            for bun_id in self._to_remove:
                if bun_id in self._image_set:
                    self._image_set.remove(bun_id)

            remove_all_in_place(self.images, self._to_remove)
            remove_all_in_place(self._to_add, self._to_remove)
            self._to_remove.clear()

        if len(self._to_add) > 0:
            self.images.extend(self._to_add)
            self._to_add.clear()

        self._dirty_sprites.clear()
        
        if self.sort_sprites:
            self.images.sort(key=lambda x: -bundle_lookup[x].depth())

        n_sprites = len(self.images)

        # need refcheck to be false or else Pycharm's debugger can cause this to fail (due to holding a ref)
        self.vertices.resize(8 * n_sprites, refcheck=False)
        self.tex_coords.resize(8 * n_sprites, refcheck=False)
        self.indices.resize(6 * n_sprites, refcheck=False)
        if self.uses_color():
            self.colors.resize(4 * 3 * n_sprites, refcheck=False)

        for i in range(0, n_sprites):
            bundle = bundle_lookup[self.images[i]]
            bundle.add_urself(
                    i,
                    self.vertices, 
                    self.tex_coords, 
                    self.colors, 
                    self.indices)
            
    def render(self):
        # split up like this to make it easier to find performance bottlenecks
        self._set_client_states(True)
        self._set_pointers()
        self._draw_elements()
        self._set_client_states(False)

    def _set_client_states(self, enable):
        if enable:
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)
            if self.uses_color():
                glEnableClientState(GL_COLOR_ARRAY)
        else:
            if self.uses_color():
                glDisableClientState(GL_COLOR_ARRAY)
            glDisableClientState(GL_TEXTURE_COORD_ARRAY)
            glDisableClientState(GL_VERTEX_ARRAY)

    def _set_pointers(self):
        glVertexPointer(2, GL_FLOAT, 0, self.vertices)
        glTexCoordPointer(2, GL_FLOAT, 0, self.tex_coords)
        if self.uses_color():
            glColorPointer(3, GL_FLOAT, 0, self.colors)

    def _draw_elements(self):
        glDrawElements(GL_TRIANGLES, len(self.indices), GL_UNSIGNED_INT, self.indices)

    def __len__(self):
        return len(self.images)   
        
    def __contains__(self, uid):
        return uid in self._image_set
        
    def z_order(self):
        return self._z_order

    def num_sprites(self):
        return len(self.images)


def printOpenGLError():
    err = glGetError()
    if (err != GL_NO_ERROR):
        print("GLERROR: {}".format(gluErrorString(err)))


class Shader:

    def __init__(self, vertex_shader_source, fragment_shader_source):
        print("INFO: creating program...")
        self.program=glCreateProgram()
        printOpenGLError()

        print("INFO: compile vertex shader...")
        self.vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(self.vs, [vertex_shader_source])
        glCompileShader(self.vs)
        glAttachShader(self.program, self.vs)
        printOpenGLError()
        info_log = glGetShaderInfoLog(self.vs)
        if len(info_log) > 0:
            print("INFO: vertex shader has non-empty info log: {}".format(info_log))

        print("INFO: compile fragment shader...")
        self.fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(self.fs, [fragment_shader_source])
        glCompileShader(self.fs)
        glAttachShader(self.program, self.fs)
        printOpenGLError()
        info_log = glGetShaderInfoLog(self.fs)
        if len(info_log) > 0:
            print("INFO: fragment shader has non-empty info log: {}".format(info_log))

        print("INFO: link program...")
        glLinkProgram(self.program)
        printOpenGLError()

    def get_program(self):
        return self.program

    def begin(self):
        if glUseProgram(self.program):
            printOpenGLError()

    def end(self):
        glUseProgram(0)


class RenderEngine:

    _SINGLETON = None

    @staticmethod
    def create_instance():
        """intializes the RenderEngine singleton."""
        if RenderEngine._SINGLETON is not None:
            raise ValueError("There is already a RenderEngine initialized.")
        else:
            RenderEngine._SINGLETON = RenderEngine()
            return RenderEngine._SINGLETON

    @staticmethod
    def get_instance():
        """after init is called, returns the RenderEngine singleton."""
        return RenderEngine._SINGLETON

    def __init__(self):
        self.bundles = {}  # (int) id -> bundle
        self.camera_pos = [0, 0]
        self.size = (0, 0)
        self.layers = {}  # layer_id -> layer
        self.hidden_layers = {} # layer_id -> None
        self.ordered_layers = []
        self.shader = None
        self.tex_id = None
        
    def add_layer(self, layer_id, layer_name, z_order, sort_sprites, use_color):
        l = _Layer(layer_name, layer_id, z_order, sort_sprites, use_color)
        self.layers[layer_id] = l
        
        self.ordered_layers = list(self.layers.values())
        self.ordered_layers.sort(key=lambda x: x.z_order())
        
    def remove_layer(self, layer_id):
        del self.layers[layer_id]
        
        self.ordered_layers = list(self.layers.values())
        self.ordered_layers.sort(key=lambda x: x.z_order())

    def hide_layer(self, layer_id):
        self.hidden_layers[layer_id] = None

    def show_layer(self, layer_id):
        if layer_id in self.hidden_layers:
            del self.hidden_layers[layer_id]
        
    def set_layer_offset(self, layer_id, offs_x, offs_y):
        self.layers[layer_id].set_offset(offs_x, offs_y)
        
    def clear_all_sprites(self):
        for uid in self.bundles:
            for l in self.layers.values():
                l.remove(uid)
        self.bundles.clear()
        
    def clear_bundles(self, bundles):
        for bun in bundles:
            self.remove(bun)

    def resize(self, width, height):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, height, 0, 1, -1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glViewport(0, 0, width, height)
        self.size = (width, height)

    def set_clear_color(self, r, g, b):
        """
            params: ints r,g,b in range [0, 255]
        """
        glClearColor(r / 255, g / 255, b / 255, 0.0)

    def init(self, w, h):
        self.resize(w, h)
        glShadeModel(GL_FLAT)
        glClearColor(0.5, 0.5, 0.5, 0.0)
        
        vstring = glGetString(GL_VERSION)
        vstring = vstring.decode() if vstring is not None else None
        print("INFO: running OpenGL version: {}".format(vstring))
        
        self.shader = Shader(
            '''
            varying vec2 vTexCoord;

            void main() {
	            vTexCoord = gl_MultiTexCoord0.st;
	            gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
                gl_FrontColor = gl_Color;
            }
            ''',
            '''
            uniform sampler2D tex0;

            varying vec2 vTexCoord;

            void main() {
                vec4 tcolor = texture2D(tex0, vTexCoord);
                for (int i = 0; i < 3; i++) {
                    if (tcolor[i] >= 0.99) {
                        gl_FragColor[i] = tcolor[i] * gl_Color[i];
                    } else {
                        gl_FragColor[i] = tcolor[i] * gl_Color[i] * gl_Color[i];                    
                    }
                }
                gl_FragColor.w = tcolor.w * gl_Color.w;
                
            }
            ''')
            
        self.shader.begin()    
        texLoc = glGetUniformLocation(self.shader.program, "tex0")
        glUniform1i(texLoc, 0)

    def set_texture(self, img_data, width, height):
        """
            img_data: image data in string RGBA format.
        """
        self.tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glEnable(GL_TEXTURE_2D)    
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 
                0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        
    def set_camera_pos(self, x, y, center=False):
        self.camera_pos[0] = x - (self.size[0] // 2) if center else 0
        self.camera_pos[1] = y - (self.size[1] // 2) if center else 0
        
    def remove(self, img_bundle):
        if img_bundle is None:
            return
            
        uid = img_bundle.uid()
        if uid in self.bundles:
            del self.bundles[img_bundle.uid()]

        self.layers[img_bundle.layer()].remove(uid)
        
    def update(self, img_bundle):
        if img_bundle is None:
            return

        for bun in img_bundle.all_bundles():
            uid = bun.uid()
            self.bundles[uid] = bun

            layer = self.layers[bun.layer()]
            layer.update(uid)
        
    def __contains__(self, key):
        try:
            return key.uid() in self.bundles
        except ValueError:
            return False
        
    def render_layers(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        for layer in self.ordered_layers:
            if layer.is_dirty():
                layer.rebuild(self.bundles)

            if layer.layer_id in self.hidden_layers:
                continue

            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            
            offs = layer.offset()
            if offs != (0, 0):
                glTranslatef(-offs[0], -offs[1], 0.0)
            
            layer.render()

    def cleanup(self):
        self.shader.end()

    def count_sprites(self):
        res = 0
        for layer in self.layers.values():
            res += layer.num_sprites()
        return res
