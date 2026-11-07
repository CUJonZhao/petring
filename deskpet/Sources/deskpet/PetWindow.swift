import AppKit
import SwiftUI

final class PetWindowController {
    static let shared = PetWindowController()
    private var panel: NSPanel?

    func show(store: PetStore) {
        if let panel { panel.orderFrontRegardless(); return }
        let width: CGFloat = 280
        let height: CGFloat = 300
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1200, height: 800)
        let savedX = UserDefaults.standard.object(forKey: "petWindowX") as? Double
        let savedY = UserDefaults.standard.object(forKey: "petWindowY") as? Double
        let frame = NSRect(x: savedX.map { CGFloat($0) } ?? (screen.maxX - width - 32),
                           y: savedY.map { CGFloat($0) } ?? (screen.minY + 28),
                           width: width, height: height)
        let panel = NSPanel(contentRect: frame,
                            styleMask: [.borderless, .nonactivatingPanel],
                            backing: .buffered, defer: false)
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.backgroundColor = .clear
        panel.isOpaque = false
        panel.hasShadow = false
        panel.hidesOnDeactivate = false
        panel.isMovableByWindowBackground = false
        panel.contentView = NSHostingView(rootView: PetOverlayView(store: store))
        panel.orderFrontRegardless()
        self.panel = panel
    }

    func move(dx: CGFloat, dy: CGFloat) {
        guard let panel else { return }
        var frame = panel.frame
        frame.origin.x += dx
        frame.origin.y -= dy
        panel.setFrame(frame, display: true)
        UserDefaults.standard.set(Double(frame.minX), forKey: "petWindowX")
        UserDefaults.standard.set(Double(frame.minY), forKey: "petWindowY")
    }

    func hide() { panel?.orderOut(nil) }
}

private struct PetOverlayView: View {
    @ObservedObject var store: PetStore
    @State private var previousDrag = CGSize.zero

    var body: some View {
        VStack(spacing: 0) {
            Spacer(minLength: 0)
            PetSceneView(behavior: store.behavior, modelURL: store.modelURL)
                .frame(width: 250, height: 235)
                .contentShape(Rectangle())
            HStack(spacing: 6) {
                Image(systemName: store.behavior.symbol)
                Text(store.behavior.title)
                if store.eventSource == "实时设备", store.lastEventAt != nil {
                    Text("· \(store.lastEventAt!, style: .relative)前")
                }
            }
            .font(.system(size: 12, weight: .semibold))
            .foregroundStyle(.primary)
            .padding(.horizontal, 11)
            .padding(.vertical, 6)
            .background(.regularMaterial, in: Capsule())
            .padding(.bottom, 8)
        }
        .frame(width: 280, height: 300)
        .background(Color.clear)
        .gesture(DragGesture(minimumDistance: 2)
            .onChanged { value in
                let dx = value.translation.width - previousDrag.width
                let dy = value.translation.height - previousDrag.height
                PetWindowController.shared.move(dx: dx, dy: dy)
                previousDrag = value.translation
            }
            .onEnded { _ in previousDrag = .zero })
        .contextMenu {
            Button("打开控制台") {
                NSApp.activate(ignoringOtherApps: true)
                NSApp.windows.first { $0.title == "DeskPet" }?.makeKeyAndOrderFront(nil)
            }
            Button("隐藏桌宠") { PetWindowController.shared.hide() }
        }
    }
}
