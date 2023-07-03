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
 *              @author:   Prof. Dr. Ulrich Schwanecke, Fabian Stahl
 *             @version:   2.0
 *                @date:   01.04.2023
 ******************************************************************************/
/**         nurbs.py
 *
 *          This module is used to create a ModernGL context using GLFW.
 *          It provides the functionality necessary to execute and visualize code
 *          specified by students in the according template.
 *          ModernGL is a high-level modern OpenGL wrapper package.
 ****
"""

"""
Modified by Erina Daraz 
"""

import glfw
import imgui
import numpy as np
import moderngl as mgl
import os

from imgui.integrations.glfw import GlfwRenderer


class Scene:
    """
        OpenGL 2D scene class
    """
    # initialization
    def __init__(self,
                width,
                height,
                scene_title         = "2D Scene",
                interpolation_fct   = None):

        self.width              = width
        self.height             = height
        self.scene_title        = scene_title
        self.points             = []
        self.points_on_bezier_curve = []
        self.curve_type         = 'orthographic'
        self.show_spline        = True

        # Rendering
        self.ctx                = None              # Assigned when calling init_gl()
        self.bg_color           = (0.1, 0.1, 0.1)
        self.point_size         = 7
        self.point_color        = (1.0, 0.5, 0.5)
        self.line_color         = (0.5, 0.5, 1.0)
        self.curve_color        = (1.0, 0.0, 0.0)

        #Aufgabe 3
        self.knotvector         = []
        self.ordnung            = 5
        self.degree             = 4
        self.kurvenpunkte       = 0.3
        self.controllpoints     = []

        #NURBS
        self.weights            = []
        self.rise               = False

    def determine_points_on_bezier_curve(self):
        self.points_on_bezier_curve = []
        self.calculate_knots()

        t = 0
        while t < self.knotvector[-1]:
            index = self.index(t)
            if index is not None:
                point = self.deboor(self.degree, self.controllpoints, self.knotvector, self.weights, t, index)
                self.points_on_bezier_curve.append(
                    point[:2] / point[2])  # Normalize by dividing by homogeneous coordinate
            t += self.kurvenpunkte


    def index(self, t):
        return next(i - 1 for i in range(len(self.knotvector) - 1) if self.knotvector[i] > t)

    def calculate_knots(self):
        self.knotvector = [0] * self.ordnung
        self.knotvector.extend(range(1, len(self.points) - (self.ordnung - 1)))
        self.knotvector.extend([len(self.points) - (self.ordnung - 2)] * self.ordnung)

    def deboor(self, degree, controllpoints, knotvector, weights, t, index):
        if degree == 0:
            return controllpoints[index] * weights[index]

        alpha = (t - knotvector[index]) / (knotvector[index + self.ordnung - degree] - knotvector[index])
        d = (1 - alpha) * self.deboor(degree - 1, controllpoints, knotvector, weights, t, index - 1) + alpha * self.deboor(degree - 1, controllpoints, knotvector, weights, t, index)
        return d


    def init_gl(self, ctx):
        self.ctx        = ctx

        # Create Shaders
        self.shader = ctx.program(
            vertex_shader = """
                #version 330

                uniform mat4    m_proj;
                uniform int     m_point_size;
                uniform vec3    color;

                in vec2 v_pos;

                out vec3 f_col;

                void main() {
                    gl_Position     = m_proj * vec4(v_pos, 0.0, 1.0);
                    gl_PointSize    = m_point_size;
                    f_col           = color;
                }
            """,
            fragment_shader = """
                #version 330

                in vec3 f_col;

                out vec4 color;

                void main() {
                    color = vec4(f_col, 1.0);
                }
            """
        )
        self.shader['m_point_size'] = self.point_size

        # Set projection matrix
        l, r = 0, self.width
        b, t = self.height, 0
        n, f = -2, 2
        m_proj = np.array([
            [2/(r-l),   0,          0,          -(l+r)/(r-l)],
            [0,         2/(t-b),    0,          -(b+t)/(t-b)],
            [0,         0,          -2/(f-n),    -(n+f)/(f-n)],
            [0,         0,          0,          1]
        ], dtype=np.float32)
        m_proj = np.ascontiguousarray(m_proj.T)
        self.shader['m_proj'].write(m_proj)
        self.shader['color'] = self.point_color


    def resize(self, width, height):
        self.width  = width
        self.height = height

        # Set projection matrix
        l, r = 0, self.width
        b, t = self.height, 0
        n, f = -2, 2
        m_proj = np.array([
            [2/(r-l),   0,          0,          -(l+r)/(r-l)],
            [0,         2/(t-b),    0,          -(b+t)/(t-b)],
            [0,         0,          -2/(f-n),    -(n+f)/(f-n)],
            [0,         0,          0,          1]
        ], dtype=np.float32)
        m_proj = np.ascontiguousarray(m_proj.T)
        self.shader['m_proj'].write(m_proj)

    def add_point(self, point):
        if len(self.points) == 0:
            for i in range(5):
                self.points.append(point)
                self.controllpoints.append(np.array([point[0], point[1], 1.0]))
                self.weights.append(1.0)
        else:
            for i in range(2):
                self.points.pop()
                self.controllpoints.pop()
                self.weights.pop()
            for i in range(3):
                self.points.append(point)
                self.controllpoints.append(np.array([point[0], point[1], 1.0]))
                self.weights.append(1.0)


    def rise_weight(self):
        for i in range(len(self.weights)):
            self.weights[i] += 0.1

    def rise_weight_one(self, index):
        if self.weights[index] < 10:
            self.weights[index] += 1
            print("Rising weight for point:", index, "to:", self.weights[index])
        else:
            print("Weight for point", index, "is already at the maximum value of 10.")

    def lower_weight_one(self, index):
        if self.weights[index] > 1:
            self.weights[index] -= 1
            print("Lowering weight for point:", index, "to:", self.weights[index])
        else:
            print("Weight for point", index, "is already at the minimum value of 1.")

    def clear(self):
        self.points = []
        self.points_on_bezier_curve = []
        self.controllpoints = []
        self.knotvector = []
        self.ordnung = 5
        self.degree = 4
        self.kurvenpunkte = 0.3
        self.weights = []

    def render(self):
        # Fill Background
        self.ctx.clear(*self.bg_color)

        # Render all points and connecting lines
        if len(self.points) > 0:
            vbo_polygon = self.ctx.buffer(np.array(self.points, np.float32))
            vao_polygon = self.ctx.vertex_array(self.shader, [(vbo_polygon, '2f', 'v_pos')])
            self.shader['color'] = self.line_color
            vao_polygon.render(mgl.LINE_STRIP)
            self.shader['color'] = self.point_color
            vao_polygon.render(mgl.POINTS)

        if self.show_spline and len(self.points_on_bezier_curve) > 3:
            self.shader['color'] = self.curve_color
            vbo_polygon = self.ctx.buffer(np.array(self.points_on_bezier_curve, np.float32))
            vao_polygon = self.ctx.vertex_array(self.shader, [(vbo_polygon, '2f', 'v_pos')])
            self.shader['color'] = self.curve_color
            vao_polygon.render(mgl.LINE_STRIP)
            self.shader['color'] = self.point_color
            vao_polygon.render(mgl.POINTS)

        if len(self.points) >= 2:
            self.determine_points_on_bezier_curve()

        #print(self.weights)


class RenderWindow:
    """
        GLFW Rendering window class
        YOU SHOULD NOT EDIT THIS CLASS!
    """
    def __init__(self, scene):

        self.scene = scene

        # save current working directory
        cwd = os.getcwd()

        # Initialize the library
        if not glfw.init():
            return

        # restore cwd
        os.chdir(cwd)

        # buffer hints
        glfw.window_hint(glfw.DEPTH_BITS, 32)

        # define desired frame rate
        self.frame_rate = 60

        # OS X supports only forward-compatible core profiles from 3.2
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
        glfw.window_hint(glfw.COCOA_RETINA_FRAMEBUFFER, False)

        # make a window
        self.width, self.height = scene.width, scene.height
        self.window = glfw.create_window(self.width, self.height, scene.scene_title, None, None)
        if not self.window:
            self.impl.shutdown()
            glfw.terminate()
            return

        # Make the window's context current
        glfw.make_context_current(self.window)

        # initializing imgui
        imgui.create_context()
        self.impl = GlfwRenderer(self.window)

        # set window callbacks
        glfw.set_mouse_button_callback(self.window, self.onMouseButton)
        glfw.set_key_callback(self.window, self.onKeyboard)
        glfw.set_window_size_callback(self.window, self.onSize)

        # create modernGL context and initialize GL objects in scene
        self.ctx = mgl.create_context()
        self.ctx.enable(flags=mgl.PROGRAM_POINT_SIZE)
        self.scene.init_gl(self.ctx)
        mgl.DEPTH_TEST = True

        # exit flag
        self.exitNow = False

    def onMouseButton(self, win, button, action, mods):
        # Don't react to clicks on UI controllers
        # Change the weight by clicking on the point (is working)
        """
        if not imgui.get_io().want_capture_mouse:
            if action == glfw.PRESS:
                if mods == glfw.MOD_SHIFT:
                    # check if there is a point within the radius
                    x, y = glfw.get_cursor_pos(win)
                    p = [int(x), int(y)]
                    radius = 30
                    found_point = False
                    for i in range(len(self.scene.points)):
                        point = self.scene.points[i]
                        distance = np.sqrt((point[0] - p[0]) ** 2 + (point[1] - p[1]) ** 2)
                        if distance <= radius:
                            self.scene.rise_weight_one(i)
                            found_point = True
                            break

                    if not found_point:
                        print("No Point found within radius", p)

                else:
                    x, y = glfw.get_cursor_pos(win)
                    p = [int(x), int(y)]
                    self.scene.add_point(p)
        """
        # TODO: Fix rising/lowering weight by dragging the mouse up and down

        if not imgui.get_io().want_capture_mouse:
            if action == glfw.PRESS and mods != glfw.MOD_SHIFT:
                x, y = glfw.get_cursor_pos(win)
                p = [int(x), int(y)]
                self.scene.add_point(p)
            elif action == glfw.PRESS and mods == glfw.MOD_SHIFT:
                self.scene.rise = True
                glfw.set_cursor_pos_callback(win, self.on_mouse_move)
            if action == glfw.RELEASE:
                self.scene.rise = False



    def on_mouse_move(self, win, x, y):
        p = [int(x), int(y)]
        radius = 30
        found_point = False
        for i in range(len(self.scene.points)):
            point = self.scene.points[i]
            distance = np.sqrt((point[0] - p[0]) ** 2 + (point[1] - p[1]) ** 2)
            if distance <= radius:
                if self.scene.rise:
                    if point[1] - p[1] > 0:
                        self.scene.rise_weight_one(i)
                    else:
                        self.scene.lower_weight_one(i)
                found_point = True
                break



    def onKeyboard(self, win, key, scancode, action, mods):
        #print("keyboard: ", win, key, scancode, action, mods)

        if action == glfw.PRESS:
            # ESC to quit
            if key == glfw.KEY_ESCAPE:
                self.exitNow = True
            # clear everything
            if key == glfw.KEY_C:
                self.scene.clear()
            if key == glfw.KEY_S:
                self.scene.show_spline = not self.scene.show_spline
            if key == glfw.KEY_K:
                if mods == glfw.MOD_SHIFT:
                    if self.scene.ordnung > 2:
                        self.scene.ordnung -= 1
                        self.scene.degree = self.scene.ordnung - 1
                        print("Ordnung: ", self.scene.ordnung)
                else:
                    if self.scene.ordnung < (len(self.scene.points) - int((len(self.scene.points) / 3))):
                        self.scene.ordnung += 1
                        self.scene.degree = self.scene.ordnung - 1
                        print("Ordnung: ", self.scene.ordnung)
            if key == glfw.KEY_M:
                if mods == glfw.MOD_SHIFT:
                    if self.scene.kurvenpunkte > 0.1:
                        self.scene.kurvenpunkte -= 0.05
                        print("Kurvenpunkte: ", self.scene.kurvenpunkte)
                else:
                    if self.scene.kurvenpunkte < 0.6:
                        self.scene.kurvenpunkte += 0.05
                        print("Kurvenpunkte: ", self.scene.kurvenpunkte)
            if key == glfw.KEY_W:
                print("DEBBUGING ONLY")
                self.scene.rise_weight()


    def onSize(self, win, width, height):
        #print("onsize: ", win, width, height)
        self.width          = width
        self.height         = height
        self.ctx.viewport   = (0, 0, self.width, self.height)
        self.scene.resize(width, height)


    def run(self):
        # initializer timer
        glfw.set_time(0.0)
        t = 0.0
        while not glfw.window_should_close(self.window) and not self.exitNow:
            # update every x seconds
            currT = glfw.get_time()
            if currT - t > 1.0 / self.frame_rate:
                # update time
                t = currT

                # == Frame-wise IMGUI Setup ===
                imgui.new_frame()                   # Start new frame context
                imgui.begin("Controller")     # Start new window context

                # Define UI Elements
                if imgui.button("Clear (C)"):
                    self.scene.clear()

                if imgui.button("Show Spline (S)"):
                    self.scene.show_spline = not self.scene.show_spline

                imgui.end()                         # End window context
                imgui.render()                      # Run render callback
                imgui.end_frame()                   # End frame context
                self.impl.process_inputs()          # Poll for UI events

                # == Rendering GL ===
                glfw.poll_events()                  # Poll for GLFW events
                self.ctx.clear()                    # clear viewport
                self.scene.render()                 # render scene
                self.impl.render(imgui.get_draw_data()) # render UI
                glfw.swap_buffers(self.window)      # swap front and back buffer


        # end
        self.impl.shutdown()
        glfw.terminate()


if __name__ == '__main__':
    print("nurbs.py")
    print("pressing 'C' should clear the everything\nOrdnung can be rised or lowered by pressing k or K\nKurvenpunkte can be rised or lowered by pressing m or M\nYou can also rise or lower the weight of each point by clicking and holding shift above the desired point and moving the mouse up or down (1-10)\npressing 'S' will show the spline\npressing 'W' will rise the weight of all points by 1 (Used for debugging)\npressing 'ESC' will close the window")

    # set size of render viewport
    width, height = 640, 480

    # instantiate a scene
    scene = Scene(width, height, "B-Spline Curve")

    rw = RenderWindow(scene)
    rw.run()