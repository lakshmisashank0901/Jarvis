import Foundation

actor JarvisSocket {
    static let url = URL(string: "ws://127.0.0.1:8741/v1")!

    private var task: URLSessionWebSocketTask?
    var onHUD: (@Sendable (HUDState) -> Void)?
    var onRaw: (@Sendable (Data) -> Void)?

    func start() {
        let session = URLSession(configuration: .default)
        let ws = session.webSocketTask(with: Self.url)
        task = ws
        ws.resume()
        receive(ws)
    }

    func send(json: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: json),
              let text = String(data: data, encoding: .utf8) else { return }
        task?.send(.string(text)) { _ in }
    }

    private func receive(_ ws: URLSessionWebSocketTask) {
        ws.receive { [weak self] result in
            guard let self else { return }
            if case .success(let msg) = result {
                let data: Data
                switch msg {
                case .string(let s): data = Data(s.utf8)
                case .data(let d): data = d
                @unknown default: data = Data()
                }
                if let hud = try? JSONDecoder().decode(HUDState.self, from: data) {
                    self.onHUD?(hud)
                }
                self.onRaw?(data)
            }
            Task { await self.receive(ws) }
        }
    }
}
