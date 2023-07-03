#version 330 core

struct PointLight {
    vec3 position;
    vec3 color;
    float strength;
};

in vec2 fragmentTexCoord;
in vec3 fragmentPosition;
in vec3 fragmentNormal;

uniform PointLight Light;
uniform vec3 cameraPosition;

uniform sampler2D shadowMap;
uniform mat4 shadowMatrix;

out vec4 color;

vec3 calculatePointLight(PointLight light, vec3 fragPosition, vec3 fragNormal, float shadowFactor);

void main()
{
    vec3 temp = vec3(0);

    temp += calculatePointLight(Light, fragmentPosition, fragmentNormal, 1.0);

    color = vec4(temp, 1);
}

vec3 calculatePointLight(PointLight light, vec3 fragPosition, vec3 fragNormal, float shadowFactor)
{
    vec3 result = vec3(0);

    vec3 fragLight = light.position - fragPosition;
    float distance = length(fragLight);
    fragLight = normalize(fragLight);
    vec3 fragCamera = normalize(cameraPosition - fragPosition);
    vec3 halfVec = normalize(fragLight + fragCamera);

    result += 0.2; // Ambient

    result += light.color * light.strength * max(0.0, dot(fragNormal, fragLight)) / (distance * distance); // Diffuse

    result += light.color * light.strength * pow(max(0.0, dot(fragNormal, halfVec)), 32) / (distance * distance); // Specular

    // Shadow calculation
    vec4 fragShadowPos = shadowMatrix * vec4(fragPosition, 1.0);
    vec3 projCoords = fragShadowPos.xyz / fragShadowPos.w;
    projCoords = projCoords * 0.5 + 0.5; // Transform to [0,1] range

    float shadowDepth = texture(shadowMap, projCoords.xy).r;
    float currentDepth = projCoords.z;
    float bias = 0.005;

    // Add shadow factor based on the comparison between current depth and shadow depth
    if (currentDepth - bias > shadowDepth)
    {
        shadowFactor = 0.5;
    }

    result *= shadowFactor;

    return result;
}
