"""
Application class
"""


import os
import arcade
import arcade.gl
from pyglet.event import EVENT_HANDLE_STATE
from source.world import *
from source.classes import *
from source.options import *


class Application(arcade.Window):
    """
    Arcade application class
    """

    def __init__(
            self,
            width: int = 1440,
            height: int = 810,
            title: str = "window",
            gl_ver: tuple[int, int] = (4, 3)):

        super().__init__(
            width, height, title,
            gl_version=gl_ver)

        # center the window
        self.center_window()

        # shader related things
        self.buffer: arcade.context.Framebuffer | None = None
        self.quad: arcade.context.Geometry | None = None
        self.program: arcade.context.Program | None = None
        self.load_shaders()

        # make graphs
        arcade.enable_timings()
        self.perf_graph_list = arcade.SpriteList()

        # add fps graph
        graph = arcade.PerfGraph(200, 120, graph_data="FPS")
        graph.position = 100, self.height - 60
        self.perf_graph_list.append(graph)

        # player
        self.player: Player = Player(Vec3(WORLD_CENTER, WORLD_CENTER, WORLD_CENTER), Vec2(0, 90))

        # player movement
        self.keys: set[int] = set()
        self.set_mouse_visible(False)
        self.set_exclusive_mouse()

        # world
        debug_world_name = f"{SAVES_DIR}/debug.npy"
        self.world: World = World()
        if not os.path.isfile(debug_world_name):
            self.world: World = WorldGen.generate_landscape(WORLD_SIZE // 2, 32)
            self.world.save(debug_world_name)
        else:
            self.world.load(debug_world_name)
        self.world.buffer = self.ctx.buffer(data=self.world.voxels)

    def load_shaders(self):
        """
        Loads shaders
        """

        # window size
        window_size = self.get_size()

        # rendering
        self.quad = arcade.gl.geometry.quad_2d_fs()
        self.buffer = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture(window_size, components=4)],
            depth_attachment=self.ctx.depth_texture(window_size))

        # load shaders
        self.program = self.ctx.load_program(
            vertex_shader=f"{SHADER_DIR}/vert.glsl",
            fragment_shader=f"{SHADER_DIR}/main.glsl")

    # noinspection PyTypeChecker
    def on_draw(self):
        # clear buffer
        self.clear()

        # set uniforms that remain the same for on_draw call
        self.program.set_uniform_safe("u_playerFov", self.player.fov)
        self.program.set_uniform_array_safe("u_Resolution", (*self.size, 1.0))
        self.program.set_uniform_array_safe("u_playerPosition", self.player.pos)
        self.program.set_uniform_array_safe("u_playerDirection", self.player.rot)
        self.program.set_uniform_array_safe("u_worldSun", self.world.sun)

        # bind storage buffer with chunk data
        self.world.buffer.bind_to_storage_buffer(binding=0)

        # render image to quad
        self.quad.render(self.program)

        # draw performance graphs
        self.perf_graph_list.draw()

    def on_key_press(self, symbol: int, modifiers: int) -> EVENT_HANDLE_STATE:
        self.keys.add(symbol)

    def on_key_release(self, symbol: int, modifiers: int) -> EVENT_HANDLE_STATE:
        self.keys.discard(symbol)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> EVENT_HANDLE_STATE:
        self.player.rotate(Vec2(dy, -dx) * self.player.sensitivity)

    def on_update(self, delta_time: float):
        # keyboard movement
        looking_direction: Vec2 = Vec2(math.cos(self.player.rot[1]), math.sin(self.player.rot[1]))
        movement = looking_direction * delta_time * self.player.movement_speed

        if arcade.key.W in self.keys:
            self.player.move(Vec3(-movement.y, movement.x, 0))
        if arcade.key.S in self.keys:
            self.player.move(Vec3(movement.y, -movement.x, 0))
        if arcade.key.A in self.keys:
            self.player.move(Vec3(-movement.x, -movement.y, 0))
        if arcade.key.D in self.keys:
            self.player.move(Vec3(movement.x, movement.y, 0))
        if arcade.key.SPACE in self.keys:
            self.player.move(Vec3(0, 0, delta_time * self.player.movement_speed))
        if arcade.key.LSHIFT in self.keys or arcade.key.RSHIFT in self.keys:
            self.player.move(Vec3(0, 0, -delta_time * self.player.movement_speed))
        if arcade.key.ESCAPE in self.keys:
            arcade.exit()
