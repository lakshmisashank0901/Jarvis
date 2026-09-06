import AppKit
import SwiftUI

@MainActor
final class HUDPanel {
    private let panel: NSPanel
    private let root = HUDViewModel()

    init() {
        let view = HUDView(model: root)
        let hosting = NSHostingView(rootView: view)
        hosting.frame = NSRect(x: 0, y: 0, width: 360, height: 88)
        panel = NSPanel(
            contentRect: hosting.frame,
            styleMask: [.nonactivatingPanel, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        panel.level = .statusBar
        panel.isFloatingPanel = true
        panel.hidesOnDeactivate = false
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isMovableByWindowBackground = true
        panel.titleVisibility = .hidden
        panel.titlebarAppearsTransparent = true
        panel.backgroundColor = NSColor.black.withAlphaComponent(0.72)
        panel.contentView = hosting
        panel.orderFrontRegardless()
    }

    func apply(_ state: HUDState) {
        root.state = state
        panel.orderFrontRegardless()
    }

    func showConfirm(id: String, text: String, deadlineMs: Int = 3000, onResult: @escaping (Bool) -> Void) {
        root.confirmText = text
        root.onConfirm = onResult
        DispatchQueue.main.asyncAfter(deadline: .now() + Double(deadlineMs) / 1000.0) { [weak self] in
            guard let self, self.root.confirmText == text else { return }
            onResult(false)
            self.root.confirmText = nil
        }
        panel.orderFrontRegardless()
    }
}

@MainActor
final class HUDViewModel: ObservableObject {
    @Published var state: HUDState?
    @Published var confirmText: String?
    var onConfirm: ((Bool) -> Void)?
}

struct HUDView: View {
    @ObservedObject var model: HUDViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text((model.state?.state.rawValue ?? "idle").uppercased())
                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                .foregroundStyle(.white.opacity(0.7))
            Text(model.confirmText ?? model.state?.partial ?? "Jarvis")
                .font(.system(size: 16, weight: .medium))
                .foregroundStyle(.white)
                .lineLimit(2)
            if model.confirmText != nil {
                HStack {
                    Button("Cancel") { model.onConfirm?(false); model.confirmText = nil }
                    Button("OK") { model.onConfirm?(true); model.confirmText = nil }
                }
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
    }
}
