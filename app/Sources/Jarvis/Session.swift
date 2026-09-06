import AppKit
import Combine
import Foundation

@MainActor
final class JarvisSession: ObservableObject {
    private let socket = JarvisSocket()
    private let hud = HUDPanel()
    private let hotkeys = HotkeyCenter()
    private let audit = AuditWindow()
    private let host = HostSocket()
    private var lines: [String] = []

    init() {
        start()
    }

    func start() {
        try? host.start()
        hotkeys.onPTTDown = { [weak self] in
            self?.socket.send(json: ["t": "hotkey", "name": "ptt_down"])
        }
        hotkeys.onCancel = { [weak self] in
            self?.socket.send(json: ["t": "hotkey", "name": "cancel"])
        }
        hotkeys.register()
        socket.onHUD = { [weak self] state in
            Task { @MainActor in
                self?.hud.apply(state)
                if let confirm = state.confirm {
                    self?.hud.showConfirm(id: confirm.id, text: confirm.text) { ok in
                        self?.socket.send(json: ["t": "confirm", "id": confirm.id, "ok": ok])
                    }
                }
            }
        }
        socket.start()
    }

    func openAudit() {
        audit.show(lines: lines.isEmpty ? ["(empty audit)"] : lines)
    }
}
