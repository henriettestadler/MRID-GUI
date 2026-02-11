import QtQuick 2.15
import QtQuick3D
import QtQuick3D.Helpers

Model {
    id: volumeModel
    source: "#Cube"
    scale: Qt.vector3d(5, 5, 5)

    materials: [
        CustomMaterial {
            shadingMode: CustomMaterial.Shaded
            fragmentShader: "volume.frag" // We will create this file below
            property TextureInput volumeTexture: TextureInput {
                texture: Texture {
                    textureData: volTexture
                }
            }
        }
    ]
}

CustomMaterial {
    shadingMode: CustomMaterial.Unshaded // No lights needed
    fragmentShader: "volume.frag"
    property TextureInput volumeTexture: TextureInput {
        texture: Texture {
            textureData: volTexture
            // Force these settings for 3D textures
            tilingModeHorizontal: Texture.ClampToEdge
            tilingModeVertical: Texture.ClampToEdge
            // If supported by your hardware:
            // tilingModeDepth: Texture.ClampToEdge
        }
    }
}

#Item {
#    anchors.fill: parent
#
#    View3D {
#        id: view
#        anchors.fill: parent
#
#        environment: SceneEnvironment {
#            clearColor: "black"
#            backgroundMode: SceneEnvironment.Color
#        }
#
#        // 1. Define the 3D Texture using the Python properties
#        TextureData {
#            id: volTexture
#            format: TextureData.R32F // Matches float32 from Python
#            width: Visualization3D.sizeX
#            height: Visualization3D.sizeY
#            depth: Visualization3D.sizeZ
#            textureData: Visualization3D.volumeData
#        }
#
#        Node {
#            id: sceneRoot
#
#            Model {
#                id: volumeModel
#                source: "#Cube"
#                scale: Qt.vector3d(5, 5, 5) // Scale as needed
#
#                materials: [
#                    // For a simple start, we use the texture as a diffuse map
#                    // Note: True volume rendering (transparency) requires a CustomMaterial
#                    DefaultMaterial {
#                        diffuseMap: Texture {
#                            textureData: volTexture
#                        }
#                    }
#                ]
#            }
#        }
#
#        PerspectiveCamera {
#            id: camera
#            position: Qt.vector3d(0, 0, 15)
#            clipNear: 0.1
#            clipFar: 1000
#        }
#
#        OrbitCameraController {
#            origin: sceneRoot
#            camera: camera
#        }
#    }
#}

/*
    Volume {
        scale: Qt.vector3d(1,1,1)
        source: VolumeTexture {
            data: VolumeProvider.volumeData
            size: Qt.size(VolumeProvider.sizeX,
                          VolumeProvider.sizeY,
                          VolumeProvider.sizeZ)
            format: VolumeTexture.R32F
        }
    }
}*/
