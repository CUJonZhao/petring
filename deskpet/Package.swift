// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "DeskPet",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(name: "DeskPet", path: "Sources/deskpet"),
    ]
)
