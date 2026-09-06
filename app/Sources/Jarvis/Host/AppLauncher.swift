import AppKit

struct AppLauncher {
    func resolve(name: String?, bundleId: String?) -> String? {
        if let bundleId, !bundleId.isEmpty { return bundleId }
        guard let name, !name.isEmpty else { return nil }
        let cleaned = name.hasSuffix(".app") ? String(name.dropLast(4)) : name
        if cleaned.caseInsensitiveCompare("Safari") == .orderedSame { return "com.apple.Safari" }
        if let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: cleaned) {
            return Bundle(url: url)?.bundleIdentifier ?? cleaned
        }
        let appName = "\(cleaned).app"
        let dirs = [
            "/Applications",
            "/System/Applications",
            "/System/Applications/Utilities",
            NSHomeDirectory() + "/Applications",
        ]
        for dir in dirs {
            let url = URL(fileURLWithPath: dir).appendingPathComponent(appName)
            if let id = Bundle(url: url)?.bundleIdentifier { return id }
        }
        return NSWorkspace.shared.runningApplications.first {
            $0.localizedName?.caseInsensitiveCompare(cleaned) == .orderedSame
        }?.bundleIdentifier
    }

    func open(name: String?, bundleId: String?) throws -> [String: Any] {
        guard let id = resolve(name: name, bundleId: bundleId),
              let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: id) else {
            throw NSError(domain: "jarvis", code: 1, userInfo: [NSLocalizedDescriptionKey: "app not found"])
        }
        NSWorkspace.shared.openApplication(at: url, configuration: NSWorkspace.OpenConfiguration())
        return ["ok": true, "bundle_id": id]
    }

    func quit(name: String?, bundleId: String?) throws -> [String: Any] {
        guard let id = resolve(name: name, bundleId: bundleId) else {
            throw NSError(domain: "jarvis", code: 1, userInfo: [NSLocalizedDescriptionKey: "app not found"])
        }
        let apps = NSRunningApplication.runningApplications(withBundleIdentifier: id)
        guard !apps.isEmpty else {
            throw NSError(domain: "jarvis", code: 2, userInfo: [NSLocalizedDescriptionKey: "app not running"])
        }
        apps.forEach { $0.terminate() }
        return ["ok": true, "bundle_id": id, "name": name ?? id]
    }

    func focus(name: String?, bundleId: String?) throws -> [String: Any] {
        let id = resolve(name: name, bundleId: bundleId) ?? bundleId ?? ""
        NSRunningApplication.runningApplications(withBundleIdentifier: id).first?.activate()
        return ["ok": true, "bundle_id": id]
    }
}
