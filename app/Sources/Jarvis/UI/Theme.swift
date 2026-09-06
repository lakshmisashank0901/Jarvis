import AppKit
import SwiftUI

enum JarvisTheme {
    static let void = Color(red: 0.02, green: 0.04, blue: 0.055)
    static let panel = Color(red: 0.035, green: 0.07, blue: 0.09)
    static let cyan = Color(red: 0.24, green: 0.91, blue: 1.0)
    static let cyanDim = Color(red: 0.12, green: 0.42, blue: 0.48)
    static let gold = Color(red: 0.91, green: 0.72, blue: 0.29)
    static let steel = Color(red: 0.55, green: 0.64, blue: 0.71)
    static let ok = Color(red: 0.24, green: 1.0, blue: 0.60)
    static let danger = Color(red: 1.0, green: 0.30, blue: 0.32)

    static func mono(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }
}

struct VoidWindow: NSViewRepresentable {
    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async {
            guard let window = view.window else { return }
            window.backgroundColor = NSColor(calibratedRed: 0.02, green: 0.04, blue: 0.055, alpha: 1)
            window.titlebarAppearsTransparent = true
            window.titleVisibility = .hidden
            window.isMovableByWindowBackground = true
            window.titlebarSeparatorStyle = .none
        }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {}
}

struct GridField: View {
    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 24.0)) { timeline in
            let t = timeline.date.timeIntervalSinceReferenceDate
            Canvas { ctx, size in
                let step: CGFloat = 28
                var path = Path()
                var x: CGFloat = 0
                while x <= size.width {
                    path.move(to: CGPoint(x: x, y: 0))
                    path.addLine(to: CGPoint(x: x, y: size.height))
                    x += step
                }
                var y: CGFloat = CGFloat(t.truncatingRemainder(dividingBy: 4)) * 7
                while y <= size.height {
                    path.move(to: CGPoint(x: 0, y: y))
                    path.addLine(to: CGPoint(x: size.width, y: y))
                    y += step
                }
                ctx.stroke(path, with: .color(JarvisTheme.cyan.opacity(0.06)), lineWidth: 0.6)
            }
        }
        .allowsHitTesting(false)
    }
}
