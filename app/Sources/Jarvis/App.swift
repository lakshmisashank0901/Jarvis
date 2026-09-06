import SwiftUI

@main
struct JarvisApp: App {
    @State private var session = JarvisSession()

    var body: some Scene {
        MenuBarExtra("Jarvis", systemImage: "waveform") {
            Button("Audit…") { session.openAudit() }
            Divider()
            Button("Quit Jarvis") { NSApplication.shared.terminate(nil) }
        }
        .menuBarExtraStyle(.menu)
    }

    init() {
        session.start()
    }
}

import AppKit
