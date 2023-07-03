"""
/*******************************************************************************
 *
 *            #, #,         CCCCCC  VV    VV MM      MM RRRRRRR
 *           %  %(  #%%#   CC    CC VV    VV MMM    MMM RR    RR
 *           %    %## #    CC        V    V  MM M  M MM RR    RR
 *            ,%      %    CC        VV  VV  MM  MM  MM RRRRRR
 *            (%      %,   CC    CC   VVVV   MM      MM RR   RR
 *              #%    %*    CCCCCC     VV    MM      MM RR    RR
 *             .%    %/
 *                (%.      Computer Vision & Mixed Reality Group
 *
 ******************************************************************************/
/**          @copyright:   Hochschule RheinMain,
 *                         University of Applied Sciences
 *              @author:   Prof. Dr. Ulrich Schwanecke
 *             @version:   0.91
 *                @date:   07.06.2022
 ******************************************************************************/
/**         oglTemplate.py
 *
 *          Simple Python OpenGL program that uses PyOpenGL + GLFW to get an
 *          OpenGL 3.2 core profile context and animate a colored triangle.
 ****
"""

import sys

import glfw
import imgui
import numpy as np
import helper
import math
import pyrr

from OpenGL.GL import *
from OpenGL.arrays.vbo import VBO
from OpenGL.GL.shaders import *

from mat4 import *

from imgui.integrations.glfw import GlfwRenderer

EXIT_FAILURE = -1

class Scene:
    def __init__(self, width, height, scenetitle=sys.argv[1]):
        self.scenetitle         = scenetitle
        self.width              = width
        self.height             = height
        self.angle              = 0
        self.angleY             = 0
        self.angleX             = 0
        self.angleZ             = 0
        self.angle_increment    = 1
        self.animate            = False
        self.animateX           = False
        self.animateZ           = False
        self.center             = np.array([0.0, 0.0, 0.0])
        self.max_len            = 1.0
        self.prev_mouse_y       = height / 2
        self.prev_mouse_x       = height / 2
        self.rotateAround       = False
        self.dragged            = False
        self.currentShader      = "Wireframe"

        # ---
        self.shading = 0
        self.perspective = 1

        # -- Shadows
        self.shadow_map_resolution = 2048
        self.shadow_map_framebuffer = None
        self.shadow_map_texture = None
        self.shadow_map_shader = None

        self.size = 1.0

        self.zoom = False
        self.zoom_start = 0.0

        ##hehe
        self.move_start = np.array([0.0, 0.0])

        self.posX = 0.0
        self.posY = 0.0

        self.lights = [
            Light(
                position=[4, 0, 2],
                color=[255, 255, 224],
                strength=2
            ),
        ]


    def init_GL(self):

        # setup buffer (vertices, colors, normals, ...)
        self.gen_buffers()

        glBindVertexArray(self.vertex_array)

        self.shaders = helper.initShaders()
        self.vertexShader = self.shaders[0]
        self.gouradShader = self.shaders[1]
        self.phongShader = self.shaders[2]
        self.shadowShader = self.shaders[3]

        self.init_shadow_map()


        # unbind vertex array to bind it again in method draw
        glBindVertexArray(0)

    def gen_buffers(self):
        # TODO:
        # 1. Load geometry from file and calc normals if not available
        positions, normals, indices = helper.read_obj(sys.argv[1])

        # -- Center around origin
        positions, self.max_len = helper.center_obj(positions, self.max_len)

        # 2. Load geometry and normals in buffer objects

        # generate vertex array object
        self.vertex_array = glGenVertexArrays(1)
        glBindVertexArray(self.vertex_array)

        positions = np.array(positions, dtype=np.float32)

        pos_buffer = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, pos_buffer)
        glBufferData(GL_ARRAY_BUFFER, positions.nbytes, positions, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(0)


        # --- NORMALS

        normals_A = np.array(normals, dtype=np.float32)
        norm_buffer = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, norm_buffer)
        glBufferData(GL_ARRAY_BUFFER, normals.nbytes, normals_A, GL_STATIC_DRAW)
        glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(2)

        # ---


        # generate and fill buffer with vertex colors (attribute 1)
        colors = np.array(normals, dtype=np.float32)

        col_buffer = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, col_buffer)
        glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(1)


        self.indices = np.array(indices, dtype=np.int32)

        ind_buffer_object = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ind_buffer_object)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.indices.nbytes, self.indices, GL_STATIC_DRAW)


        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)



    def set_size(self, width, height):
        self.width = width
        self.height = height

    def zoomIN(self):
        self.size += 0.1

    def zoomOUT(self):
        self.size -= 0.1

    def init_shadow_map(self):
        self.shadow_map_framebuffer = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.shadow_map_framebuffer)

        self.shadow_map_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.shadow_map_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT, self.shadow_map_resolution, self.shadow_map_resolution, 0,
                     GL_DEPTH_COMPONENT, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER)
        glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, (1.0, 1.0, 1.0, 1.0))

        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, self.shadow_map_texture, 0)
        glDrawBuffer(GL_NONE)
        glReadBuffer(GL_NONE)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)


    # TODO CHANGE THIS !
    def draw(self):

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self.animate:
            # increment rotation angle in each frame
            self.angleY += self.angle_increment

        if self.animateX:
            self.angleX += self.angle_increment

        if self.animateZ:
            self.angleZ += self.angle_increment

        # switch between orthographic and perspective projection
        if self.perspective == 0:
            projection = perspective(45.0, self.width / self.height, 1.0, 5.0)
        elif self.perspective == 1:
            projection = ortho((self.width / self.height) * -1, (self.width / self.height) * 1, -1, 1, 0, 10)

        view = look_at(0, 0, 2, 0, 0, 0, 0, 1, 0)
        rotation = rotate_y(self.angleY) @ rotate_x(self.angleX) @ rotate_z(self.angleZ)
        translation = translate(-self.center[0] + self.posX, -self.center[1] + self.posY, -self.center[2])

        scaling = scale((1 / self.max_len) * self.size, (1 / self.max_len) * self.size,
                        (1 / self.max_len) * self.size)

        model = rotation @ scaling @ translation
        mvp_matrix = projection @ view @ model

        # switch between wifeframe, gouraud and phong shading
        if self.shading == 0:
            self.currentShader = "Wireframe"
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

            glUseProgram(self.vertexShader)
            varLocation = glGetUniformLocation(self.vertexShader, 'modelview_projection_matrix')

            glUniformMatrix4fv(varLocation, 1, GL_TRUE, mvp_matrix)

            glBindVertexArray(self.vertex_array)
            glDrawElements(GL_TRIANGLES, self.indices.nbytes // 4, GL_UNSIGNED_INT, None)

            glUseProgram(0)
            glBindVertexArray(0)

        elif self.shading == 1:
            self.currentShader = "Gouraud-Shading"
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glUseProgram(self.gouradShader)

            varLocation = glGetUniformLocation(self.gouradShader, 'modelview_projection_matrix')

            glUniformMatrix4fv(varLocation, 1, GL_TRUE, mvp_matrix)

            self.modelMatrixLocation = glGetUniformLocation(self.gouradShader, "model")
            self.viewMatrixLocation = glGetUniformLocation(self.gouradShader, "view")

            self.lightLocation = {
                "position": glGetUniformLocation(self.gouradShader, "Light.position"),
                "color": glGetUniformLocation(self.gouradShader, "Light.color"),
                "strength": glGetUniformLocation(self.gouradShader, "Light.strength")
            }
            self.cameraPosLoc = glGetUniformLocation(self.gouradShader, "cameraPostion")

            light = scene.lights[0]
            glUniform3fv(self.lightLocation["position"], 1, light.position)
            glUniform3fv(self.lightLocation["color"], 1, light.color)
            glUniform1f(self.lightLocation["strength"], light.strength)

            glBindVertexArray(self.vertex_array)
            glDrawElements(GL_TRIANGLES, self.indices.nbytes // 4, GL_UNSIGNED_INT, None)

            glBindVertexArray(0)
            glUseProgram(0)

        elif self.shading == 2:
            self.currentShader = "Phong-Shading"
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glUseProgram(self.phongShader)

            varLocation = glGetUniformLocation(self.phongShader, 'modelview_projection_matrix')

            glUniformMatrix4fv(varLocation, 1, GL_TRUE, mvp_matrix)

            self.modelMatrixLocation = glGetUniformLocation(self.phongShader, "model")
            self.viewMatrixLocation = glGetUniformLocation(self.phongShader, "view")

            self.lightLocation = {
                "position": glGetUniformLocation(self.phongShader, "Light.position"),
                "color": glGetUniformLocation(self.phongShader, "Light.color"),
                "strength": glGetUniformLocation(self.phongShader, "Light.strength")
            }
            self.cameraPosLoc = glGetUniformLocation(self.phongShader, "cameraPostion")

            light = scene.lights[0]
            glUniform3fv(self.lightLocation["position"], 1, light.position)
            glUniform3fv(self.lightLocation["color"], 1, light.color)
            glUniform1f(self.lightLocation["strength"], light.strength)

            glBindVertexArray(self.vertex_array)
            glDrawElements(GL_TRIANGLES, self.indices.nbytes // 4, GL_UNSIGNED_INT, None)

            glBindVertexArray(0)
            glUseProgram(0)
        elif self.shading == 3:
            self.currentShader = "Shadow Mapping"

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

            # -- SHADOW

            glUseProgram(self.shadowShader)
            glBindFramebuffer(GL_FRAMEBUFFER, self.shadow_map_framebuffer)
            glViewport(0, 0, self.shadow_map_resolution, self.shadow_map_resolution)
            glClear(GL_DEPTH_BUFFER_BIT)

            glBindFramebuffer(GL_FRAMEBUFFER, 0)

            glUseProgram(self.shadowShader)
            glUniform1i(glGetUniformLocation(self.shadowShader, "shadowMap"),
                        1)
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, self.shadow_map_texture)

            # -- SHADOW

            varLocation = glGetUniformLocation(self.gouradShader, 'modelview_projection_matrix')

            glUniformMatrix4fv(varLocation, 1, GL_TRUE, mvp_matrix)

            self.modelMatrixLocation = glGetUniformLocation(self.gouradShader, "model")
            self.viewMatrixLocation = glGetUniformLocation(self.gouradShader, "view")

            self.lightLocation = {
                "position": glGetUniformLocation(self.gouradShader, "Light.position"),
                "color": glGetUniformLocation(self.gouradShader, "Light.color"),
                "strength": glGetUniformLocation(self.gouradShader, "Light.strength")
            }
            self.cameraPosLoc = glGetUniformLocation(self.gouradShader, "cameraPostion")

            light = scene.lights[0]
            glUniform3fv(self.lightLocation["position"], 1, light.position)
            glUniform3fv(self.lightLocation["color"], 1, light.color)
            glUniform1f(self.lightLocation["strength"], light.strength)

            glBindVertexArray(self.vertex_array)
            glDrawElements(GL_TRIANGLES, self.indices.nbytes // 4, GL_UNSIGNED_INT, None)

            glBindVertexArray(0)
            glUseProgram(0)



class Light:
    def __init__(self, position, color, strength):

        self.position = np.array(position, dtype=np.float32)
        self.color = np.array(color, dtype=np.float32)
        self.strength = strength

class RenderWindow:
    """
        GLFW Rendering window class
    """

    def __init__(self, scene):
        # initialize GLFW
        if not glfw.init():
            sys.exit(EXIT_FAILURE)

        # request window with old OpenGL 3.2
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 2)

        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE)

        # make a window
        self.width, self.height = scene.width, scene.height
        self.aspect = self.width / self.height
        self.window = glfw.create_window(self.width, self.height, scene.scenetitle, None, None)
        if not self.window:
            glfw.terminate()
            sys.exit(EXIT_FAILURE)

        # Make the window's context current
        glfw.make_context_current(self.window)

        # initializing imgui
        imgui.create_context()
        self.impl = GlfwRenderer(self.window)

        # initialize GL
        self.init_GL()

        # set window callbacks
        glfw.set_mouse_button_callback(self.window, self.on_mouse_button)
        glfw.set_scroll_callback(self.window, self.on_mouse_scroll)
        glfw.set_key_callback(self.window, self.on_keyboard)
        glfw.set_window_size_callback(self.window, self.on_size)

        # create scene
        self.scene = scene
        if not self.scene:
            glfw.terminate()
            sys.exit(EXIT_FAILURE)

        self.scene.init_GL()

        # exit flag
        self.exitNow = False

    def init_GL(self):
        # debug: print GL and GLS version
        # print('Vendor       : %s' % glGetString(GL_VENDOR))
        # print('OpenGL Vers. : %s' % glGetString(GL_VERSION))
        # print('GLSL Vers.   : %s' % glGetString(GL_SHADING_LANGUAGE_VERSION))
        # print('Renderer     : %s' % glGetString(GL_RENDERER))

        # set background color to grey
        glClearColor(0, 0, 0, 1.0)

        # Enable depthtest
        glEnable(GL_DEPTH_TEST)

    def on_mouse_button(self, win, button, action, mods):
        print("mouse button: ", win, button, action, mods)
        # TODO: realize arcball metaphor for rotations as well as
        #       scaling and translation paralell to the image plane,
        #       with the mouse.
        if not imgui.get_io().want_capture_mouse:
            # print("mouse button: ", win, button, action, mods)
            pass

        if button == glfw.MOUSE_BUTTON_LEFT:
            if action == glfw.PRESS:
                glfw.set_cursor_pos_callback(win, self.on_mouse_move)
                self.scene.rotateAround = True
            elif action == glfw.RELEASE:
                self.scene.rotateAround = False

        if button == glfw.MOUSE_BUTTON_RIGHT:
            if action == glfw.PRESS:
                glfw.set_cursor_pos_callback(win, self.on_mouse_move)
                self.scene.dragged = True
            elif action == glfw.RELEASE:
                self.scene.dragged = False

        if button == glfw.MOUSE_BUTTON_MIDDLE:
            if action == glfw.PRESS:
                self.scene.zoom = True
                glfw.set_cursor_pos_callback(win, self.on_mouse_move)
            elif action == glfw.RELEASE:
                self.scene.zoom = False

    def on_mouse_move(self, win, x, y):
        if self.scene.zoom:
            if y > self.scene.prev_mouse_y:  # Mouse moved up
                self.scene.zoomIN()
            elif y < self.scene.prev_mouse_y:  # Mouse moved down
                self.scene.zoomOUT()

            self.prev_mouse_y = y

        if self.scene.rotateAround:
            self.scene.angleX += (y - self.scene.prev_mouse_y) * 0.1
            self.scene.angleY += (x - self.scene.prev_mouse_x) * 0.1

        if self.scene.dragged:
            dx = x - self.scene.prev_mouse_x
            dy = y - self.scene.prev_mouse_y

            self.scene.posX += dx * 0.01
            self.scene.posY -= dy * 0.01

        self.scene.prev_mouse_x = x
        self.scene.prev_mouse_y = y

    def on_mouse_scroll(self, win, xoffset, yoffset):
        if yoffset > 0:
            self.scene.zoomIN()  # Zoom in
        elif yoffset < 0:
            self.scene.zoomOUT()

    def on_keyboard(self, win, key, scancode, action, mods):
        print("keyboard: ", win, key, scancode, action, mods)
        if action == glfw.PRESS:
            # ESC to quit
            if key == glfw.KEY_ESCAPE:
                self.exitNow = True
            if key == glfw.KEY_A:
                self.scene.animate = not self.scene.animate
            if key == glfw.KEY_P:
                print("toggle projection: orthographic / perspective ")
                self.scene.perspective = (self.scene.perspective + 1) % 2
            if key == glfw.KEY_S:
                self.scene.shading = (self.scene.shading + 1) % 3
                print("toggle shading: wireframe, grouraud, phong")
            if key == glfw.KEY_X:
                print("rotate: around x-axis")
                self.scene.animateX = not self.scene.animateX
            if key == glfw.KEY_Y:
                print("rotate: around y-axis")
                self.scene.animate = not self.scene.animate
            if key == glfw.KEY_Z:
                print("rotate: around z-axis")
                self.scene.animateZ = not self.scene.animateZ

    def on_size(self, win, width, height):
        self.scene.set_size(width, height)

    def run(self):
        while not glfw.window_should_close(self.window) and not self.exitNow:
            # == Frame-wise IMGUI Setup ===

            imgui.new_frame()  # Start new frame context


            imgui.begin("Controller")  # Start new window context
            imgui.text(self.scene.currentShader)

            if imgui.button("Toggle Shadows"):
                glClearColor(255, 255, 255, 255)
                self.scene.shading = 3

            imgui.end()  # End window context
            imgui.render()  # Run render callback
            imgui.end_frame()  # End frame context
            self.impl.process_inputs()  # Poll for UI events

            # poll for and process events
            glfw.poll_events()

            # setup viewport
            width, height = glfw.get_framebuffer_size(self.window)
            glViewport(0, 0, width, height);

            # call the rendering function
            self.scene.draw()

            self.impl.render(imgui.get_draw_data())  # render UI

            # swap front and back buffer
            glfw.swap_buffers(self.window)

        # end
        glfw.terminate()


# main function
if __name__ == '__main__':
    print("presse 'a' to toggle animation...")

    # set size of render viewport
    width, height = 640, 480

    scene = Scene(width, height)

    # pass the scene to a render window ...
    rw = RenderWindow(scene)

    # ... and start main loop
    rw.run()

