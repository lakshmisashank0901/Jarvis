// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Jarvis",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(
            name: "Jarvis",
            path: "Sources/Jarvis",
            exclude: ["Info.plist"],
            linkerSettings: [
                .linkedFramework("AppKit"),
                .linkedFramework("SwiftUI"),
                .linkedFramework("EventKit"),
                .linkedFramework("Carbon"),
                .linkedFramework("Network"),
            ]
        )
    ]
)
