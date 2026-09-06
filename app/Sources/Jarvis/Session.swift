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

    private var started = false

    func ensureStarted() {
        guard !started else { return }
        started = true
        start()
    }

    func start() {
        try? host.start()
        hotkeys.onPTTDown = { [weak self] in
            self?.pingPTT()
        }
        hotkeys.onCancel = { [weak self] in
            self?.socket.send(json: ["t": "hotkey", "name": "cancel"])
        }
        DispatchQueue.main.async { [weak self] in
            _ = self?.hotkeys.register()
        }
        socket.onHUD = { [weak self] state in
            Task { @MainActor in
                guard let confirm = state.confirm else { return }
                self?.hud.showConfirm(id: confirm.id, text: confirm.text) { ok in
                    self?.socket.send(json: ["t": "confirm", "id": confirm.id, "ok": ok])
                }
            }
        }
        socket.start()
    }

    func pingPTT() {
        AppDelegate.bringDashboardForward()
        socket.send(json: ["t": "hotkey", "name": "ptt_down"])
    }

    func openAudit() {
        audit.show(lines: lines.isEmpty ? ["(empty audit)"] : lines)
    }
}
