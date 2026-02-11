void main() {
    // UV0V1W2 is the 3D coordinate of the cube (0.0 to 1.0)
    vec3 texCoord = UV0V1W2;

    // Look up the value in our 3D texture
    float intensity = texture(volumeTexture, texCoord).r;

    // Output the color (Grayscale)
    BASE_COLOR = vec4(vec3(intensity), 1.0);
}ssr
