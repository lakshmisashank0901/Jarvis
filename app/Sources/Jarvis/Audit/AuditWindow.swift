import AppKit
import SwiftUI

@MainActor
final class AuditWindow {
    private var window: NSWindow?

    func show(lines: [String]) {
        let view = List(lines, id: \.self) { Text($0).font(.system(.body, design: .monospaced)) }
        let hosting = NSHostingController(rootView: view)
        let win = NSWindow(contentViewController: hosting)
        win.title = "Jarvis audit"
        win.setContentSize(NSSize(width: 520, height: 360))
        win.makeKeyAndOrderFront(nil)
        window = win
    }
}
