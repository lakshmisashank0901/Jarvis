import Foundation
import Network

final class HostSocket: @unchecked Sendable {
    static let path = "/tmp/jarvis-host.sock"

    private let launcher = AppLauncher()
    private let files = FileHost()
    private let system = SystemHost()
    private let calendar = CalendarStore()
    private var listener: NWListener?

    func start() throws {
        try? FileManager.default.removeItem(atPath: Self.path)
        let params = NWParameters()
        params.defaultProtocolStack.transportProtocol = NWProtocolTCP.Options()
        let listener = try NWListener(using: .tcp, on: NWEndpoint.Port(integerLiteral: 0))
        // Prefer unix domain via FileHandle accept loop — Network.framework unix varies by OS.
        self.listener = listener
        UnixJSONServer(path: Self.path) { [weak self] req in
            self?.handle(req) ?? ["ok": false, "error": "dead"]
        }.start()
    }

    func handle(_ req: [String: Any]) -> [String: Any] {
        let op = req["op"] as? String ?? ""
        do {
            switch op {
            case "app.open":
                return try launcher.open(name: req["name"] as? String, bundleId: req["bundle_id"] as? String)
            case "app.quit":
                return try launcher.quit(bundleId: req["bundle_id"] as? String ?? "")
            case "app.focus":
                return try launcher.focus(name: req["name"] as? String, bundleId: req["bundle_id"] as? String)
            case "files.open":
                return try files.open(path: req["path"] as? String ?? "")
            case "files.reveal":
                return try files.reveal(path: req["path"] as? String ?? "")
            case "system.volume":
                return try system.setVolume(level: req["level"] as? Int ?? 0)
            case "system.mute":
                return try system.setMute(on: req["on"] as? Bool ?? true)
            case "system.lock":
                return try system.lock()
            case "system.sleep":
                return try system.sleep()
            case "calendar.list":
                return try calendar.list(from: req["from"] as? String, to: req["to"] as? String)
            case "calendar.create":
                return try calendar.create(title: req["title"] as? String ?? "", start: req["start"] as? String, end: req["end"] as? String)
            case "calendar.update":
                return try calendar.update(id: req["id"] as? String ?? "", title: req["title"] as? String, start: req["start"] as? String, end: req["end"] as? String)
            default:
                return ["ok": false, "error": "unknown op"]
            }
        } catch {
            return ["ok": false, "error": error.localizedDescription]
        }
    }
}

final class UnixJSONServer: @unchecked Sendable {
    private let path: String
    private let handler: ([String: Any]) -> [String: Any]
    private var source: DispatchSourceRead?

    init(path: String, handler: @escaping ([String: Any]) -> [String: Any]) {
        self.path = path
        self.handler = handler
    }

    func start() {
        unlink(path)
        let fd = socket(AF_UNIX, SOCK_STREAM, 0)
        guard fd >= 0 else { return }
        var addr = sockaddr_un()
        addr.sun_family = sa_family_t(AF_UNIX)
        let maxLen = MemoryLayout.size(ofValue: addr.sun_path) - 1
        withUnsafeMutablePointer(to: &addr.sun_path.0) { ptr in
            path.withCString { cstr in
                strncpy(ptr, cstr, maxLen)
            }
        }
        let addrLen = socklen_t(MemoryLayout<sockaddr_un>.size)
        _ = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { bind(fd, $0, addrLen) }
        }
        listen(fd, 4)
        let src = DispatchSource.makeReadSource(fileDescriptor: fd, queue: .global())
        src.setEventHandler { [handler] in
            let client = accept(fd, nil, nil)
            guard client >= 0 else { return }
            var buf = [UInt8](repeating: 0, count: 16_384)
            let n = read(client, &buf, buf.count)
            guard n > 0, let line = String(bytes: buf[0..<n], encoding: .utf8) else {
                close(client)
                return
            }
            let raw = line.split(separator: "\n", maxSplits: 1).first.map(String.init) ?? line
            let req = (try? JSONSerialization.jsonObject(with: Data(raw.utf8))) as? [String: Any] ?? [:]
            let resp = handler(req)
            if let data = try? JSONSerialization.data(withJSONObject: resp) {
                var out = data
                out.append(0x0A)
                _ = out.withUnsafeBytes { write(client, $0.baseAddress, out.count) }
            }
            close(client)
        }
        src.resume()
        source = src
    }
}
