import AppKit

struct AppLauncher {
    func resolve(name: String?, bundleId: String?) -> String? {
        if let bundleId, !bundleId.isEmpty { return bundleId }
        guard let name, !name.isEmpty else { return nil }
        if name.caseInsensitiveCompare("Safari") == .orderedSame { return "com.apple.Safari" }
        if let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: name) {
            return Bundle(url: url)?.bundleIdentifier
        }
        let appName = name.hasSuffix(".app") ? name : "\(name).app"
        let url = URL(fileURLWithPath: "/Applications/\(appName)")
        return Bundle(url: url)?.bundleIdentifier
    }

    func open(name: String?, bundleId: String?) throws -> [String: Any] {
        guard let id = resolve(name: name, bundleId: bundleId),
              let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: id) else {
            throw NSError(domain: "jarvis", code: 1, userInfo: [NSLocalizedDescriptionKey: "app not found"])
        }
        NSWorkspace.shared.openApplication(at: url, configuration: NSWorkspace.OpenConfiguration())
        return ["ok": true, "bundle_id": id]
    }

    func quit(bundleId: String) throws -> [String: Any] {
        let apps = NSRunningApplication.runningApplications(withBundleIdentifier: bundleId)
        apps.forEach { $0.terminate() }
        return ["ok": true, "bundle_id": bundleId]
    }

    func focus(name: String?, bundleId: String?) throws -> [String: Any] {
        let id = resolve(name: name, bundleId: bundleId) ?? bundleId ?? ""
        NSRunningApplication.runningApplications(withBundleIdentifier: id).first?.activate()
        return ["ok": true, "bundle_id": id]
    }
}
