import AppKit
import Foundation

@MainActor
final class JarvisSession {
    private let socket = JarvisSocket()
    private let hud = HUDPanel()
    private let hotkeys = HotkeyCenter()
    private let audit = AuditWindow()
    private let host = HostSocket()
    private var lines: [String] = []

    func start() {
        try? host.start()
        hotkeys.onPTTDown = { [weak self] in
            Task { await self?.socket.send(json: ["t": "hotkey", "name": "ptt_down"]) }
        }
        hotkeys.onCancel = { [weak self] in
            Task { await self?.socket.send(json: ["t": "hotkey", "name": "cancel"]) }
        }
        hotkeys.register()
        Task {
            await socket.onHUD = { [weak self] state in
                Task { @MainActor in
                    self?.hud.apply(state)
                    if let text = state.confirm?.text, let id = state.confirm?.id {
                        self?.hud.showConfirm(id: id, text: text) { ok in
                            Task { await self?.socket.send(json: ["t": "confirm", "id": id, "ok": ok]) }
                        }
                    }
                }
            }
            await socket.start()
        }
    }

    func openAudit() {
        audit.show(lines: lines.isEmpty ? ["(empty audit)"] : lines)
    }
}
