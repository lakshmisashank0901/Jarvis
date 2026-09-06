import AppKit
import Foundation

struct SystemHost {
    func setVolume(level: Int) throws -> [String: Any] {
        let clamped = min(100, max(0, level))
        let script = "set volume output volume \(clamped)"
        _ = try NSAppleScript(source: script)?.executeAndReturnError(nil)
        return ["ok": true, "level": clamped]
    }

    func setMute(on: Bool) throws -> [String: Any] {
        let script = on ? "set volume with output muted" : "set volume without output muted"
        _ = try NSAppleScript(source: script)?.executeAndReturnError(nil)
        return ["ok": true, "on": on]
    }

    func lock() throws -> [String: Any] {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession")
        if FileManager.default.isExecutableFile(atPath: task.executableURL!.path) {
            task.arguments = ["-suspend"]
            try task.run()
        }
        return ["ok": true]
    }

    func sleep() throws -> [String: Any] {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/pmset")
        task.arguments = ["sleepnow"]
        try task.run()
        return ["ok": true]
    }
}
