import AppKit
import SwiftUI

@main
struct DeskPetApp: App {
    @StateObject private var store = PetStore()

    var body: some Scene {
        WindowGroup("DeskPet", id: "control") {
            ControlView()
                .environmentObject(store)
                .frame(minWidth: 650, minHeight: 570)
                .onAppear { PetWindowController.shared.show(store: store) }
        }
        .defaultSize(width: 760, height: 680)
    }
}
