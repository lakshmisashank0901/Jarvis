import SwiftUI

struct CoreOrb: View {
    var online: Bool
    var busy: Bool
    var onTap: () -> Void

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30.0)) { timeline in
            let t = timeline.date.timeIntervalSinceReferenceDate
            let pulse = busy ? 0.18 + 0.10 * sin(t * 8) : 0.10 + 0.04 * sin(t * 2.2)
            ZStack {
                ForEach(0..<3, id: \.self) { i in
                    Circle()
                        .stroke(
                            JarvisTheme.cyan.opacity(online ? 0.22 - Double(i) * 0.05 : 0.08),
                            lineWidth: 1
                        )
                        .frame(width: 88 + CGFloat(i) * 28, height: 88 + CGFloat(i) * 28)
                        .rotationEffect(.degrees(t * (i == 1 ? -18 : 12 + Double(i) * 6)))
                        .overlay {
                            Capsule()
                                .fill(JarvisTheme.cyan.opacity(online ? 0.45 : 0.15))
                                .frame(width: 10, height: 2)
                                .offset(y: -(44 + CGFloat(i) * 14))
                                .rotationEffect(.degrees(t * (i == 1 ? -18 : 12 + Double(i) * 6)))
                        }
                }
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [
                                (online ? JarvisTheme.cyan : JarvisTheme.gold).opacity(0.95),
                                JarvisTheme.void.opacity(0.2),
                            ],
                            center: .center,
                            startRadius: 2,
                            endRadius: 48
                        )
                    )
                    .frame(width: 72, height: 72)
                    .shadow(color: (online ? JarvisTheme.cyan : JarvisTheme.gold).opacity(0.55 + pulse), radius: 22)
                    .scaleEffect(1 + pulse * 0.35)
                VStack(spacing: 2) {
                    Text(busy ? "RUN" : (online ? "ON" : "OFF"))
                        .font(JarvisTheme.mono(11, weight: .bold))
                    Text(busy ? "EXEC" : "CORE")
                        .font(JarvisTheme.mono(8, weight: .medium))
                        .opacity(0.7)
                }
                .foregroundStyle(Color.black.opacity(0.85))
            }
            .frame(width: 160, height: 160)
            .contentShape(Circle())
            .onTapGesture(perform: onTap)
        }
    }
}
