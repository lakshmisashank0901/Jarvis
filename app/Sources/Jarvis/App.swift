import AppKit
import SwiftUI

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        Self.bringDashboardForward()
    }

    @MainActor
    static func bringDashboardForward() {
        NSApp.activate(ignoringOtherApps: true)
        for window in NSApp.windows {
            let name = String(describing: type(of: window))
            if name.contains("StatusBar") || name.contains("MenuBar") { continue }
            if window is NSPanel { continue }
            window.makeKeyAndOrderFront(nil)
        }
    }
}

@main
struct JarvisApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var session = JarvisSession()

    var body: some Scene {
        Window("Jarvis", id: "main") {
            DashboardView()
                .onAppear {
                    session.ensureStarted()
                    AppDelegate.bringDashboardForward()
                }
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 960, height: 640)

        MenuBarExtra("Jarvis", systemImage: "waveform") {
            Button("Show Jarvis window") { AppDelegate.bringDashboardForward() }
            Divider()
            Button("Quit Jarvis") { NSApplication.shared.terminate(nil) }
        }
        .menuBarExtraStyle(.menu)
    }
}
