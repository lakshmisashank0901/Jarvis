import AppKit

struct FileHost {
    func open(path: String) throws -> [String: Any] {
        let url = URL(fileURLWithPath: (path as NSString).expandingTildeInPath)
        NSWorkspace.shared.open(url)
        return ["ok": true, "path": url.path]
    }

    func reveal(path: String) throws -> [String: Any] {
        let url = URL(fileURLWithPath: (path as NSString).expandingTildeInPath)
        NSWorkspace.shared.activateFileViewerSelecting([url])
        return ["ok": true, "path": url.path]
    }
}
