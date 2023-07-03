from oglTemplate import *

def initShaders():
    shaders = []
    # Create shaders
    vertShader = createShader("shaders/shader.vert", "shaders/shader.frag")
    shaders.append(vertShader)
    glUseProgram(vertShader)

    gouradShader = createShader("shaders/gourad.vert", "shaders/gourad.frag")
    shaders.append(gouradShader)
    glUseProgram(gouradShader)

    phongShader = createShader("shaders/gourad.vert", "shaders/phong.frag")
    shaders.append(phongShader)
    glUseProgram(phongShader)

    shadowShader = createShader("shaders/shadow.vert", "shaders/shadow.frag")
    shaders.append(shadowShader)
    glUseProgram(shadowShader)

    return shaders

def createShader(vertexFilepath, fragmentFilepath):
    with open(vertexFilepath, 'r') as f:
        vertex_src = f.readlines()

    with open(fragmentFilepath, 'r') as f:
        fragment_src = f.readlines()

    shader = compileProgram(compileShader(vertex_src, GL_VERTEX_SHADER),
                            compileShader(fragment_src, GL_FRAGMENT_SHADER))

    return shader



def read_obj(file_path):
    positions = []
    normals = []
    indices = []

    with open(f"{file_path}", "r") as file:
        for line in file:
            if line.startswith('v '):
                # vertex position
                vertex = line.strip().split()[1:]
                positions.append([float(coord) for coord in vertex])
            elif line.startswith('vn '):
                # Parse vertex normal
                normal = line.strip().split()[1:]
                normals.append([float(coord) for coord in normal])
            elif line.startswith('f '):
                # Parse face (vertex indices and normals)
                face = line.strip().split()[1:]
                for vertex in face:
                    index_data = vertex.split('/')
                    vertex_index = int(index_data[0]) - 1
                    indices.append(vertex_index)

    positions = np.array(positions, dtype=np.float32)
    normals = np.array(normals, dtype=np.float32)
    indices = np.array(indices, dtype=np.uint32)

    return positions, calculate_vertex_normals_NEU(positions, indices), indices


def calculate_vertex_normals_NEU(positions, indices):
    # Initialize an empty array to store the vertex normals
    vertex_normals = np.zeros_like(positions)

    # Iterate over each face (triangle) defined by the indices
    for i in range(0, len(indices), 3):
        face_indices = indices[i:i + 3]
        v0, v1, v2 = positions[face_indices[0]], positions[face_indices[1]], positions[face_indices[2]]

        # Calculate the face normal using cross product
        face_normal = np.cross(v1 - v0, v2 - v0)

        # Accumulate the face normal to the corresponding vertices
        vertex_normals[face_indices[0]] += face_normal
        vertex_normals[face_indices[1]] += face_normal
        vertex_normals[face_indices[2]] += face_normal

    # vertex_normals /= np.linalg.norm(vertex_normals, axis=1)[:, np.newaxis]
    # return vertex_normals

    # Calculate the norms of the vertex normals
    norms = np.linalg.norm(vertex_normals, axis=1)

    # Check for non-zero norms to avoid division by zero
    non_zero_norms = norms > 0

    # Divide only for non-zero norms
    vertex_normals[non_zero_norms] /= norms[non_zero_norms][:, np.newaxis]

    return vertex_normals

def center_obj(positions, max_len):
    total_positions = np.zeros(3)

    for position in positions:
        total_positions += position
    average_position = total_positions / len(positions)

    # Translate the positions
    for i in range(len(positions)):
        positions[i] -= average_position

    for position in positions:
        length = np.linalg.norm(position)
        if length > max_len:
            max_len = length

    return positions, max_len