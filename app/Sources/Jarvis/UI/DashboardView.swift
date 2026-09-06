import SwiftUI

struct LogLine: Identifiable, Equatable {
    let id = UUID()
    var role: String
    var text: String
}

@MainActor
final class DashboardModel: ObservableObject {
    @Published var command = ""
    @Published var confirmDangerous = false
    @Published var online = false
    @Published var busy = false
    @Published var lines: [LogLine] = []
    @Published var lastError: String?
    @Published var lastTool = ""
    @Published var clock = Date()

    private let brain = BrainClient()

    func refresh() async {
        online = await brain.health()
    }

    func fill(_ text: String) {
        command = text
    }

    func submit() async {
        let text = command.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !busy else { return }
        busy = true
        lastError = nil
        lines.append(LogLine(role: "you", text: text))
        command = ""
        do {
            let reply = try await brain.ask(text, confirmed: confirmDangerous)
            lastTool = reply.tool
            let tag = reply.tool.isEmpty ? "jarvis" : "jarvis · \(reply.tool)"
            lines.append(LogLine(role: tag, text: reply.text))
            online = true
        } catch {
            lastError = error.localizedDescription
            online = false
            lines.append(LogLine(role: "error", text: error.localizedDescription))
        }
        busy = false
    }
}

struct DashboardView: View {
    @StateObject private var model = DashboardModel()

    private let chips = [
        "Open Safari",
        "Quit Notes",
        "Go to https://example.com",
        "What's on my calendar tomorrow?",
    ]

    var body: some View {
        ZStack {
            JarvisTheme.void.ignoresSafeArea()
            GridField()
            HStack(spacing: 0) {
                rail
                Rectangle().fill(JarvisTheme.cyan.opacity(0.18)).frame(width: 1)
                deck
            }
        }
        .preferredColorScheme(.dark)
        .background(VoidWindow())
        .frame(minWidth: 880, minHeight: 560)
        .task {
            await model.refresh()
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(2))
                model.clock = Date()
                await model.refresh()
            }
        }
    }

    private var rail: some View {
        VStack(spacing: 18) {
            Text("J.A.R.V.I.S")
                .font(JarvisTheme.mono(13, weight: .bold))
                .foregroundStyle(JarvisTheme.cyan)
                .tracking(3)
            CoreOrb(online: model.online, busy: model.busy) {
                Task { await model.refresh() }
            }
            statusLine
            VStack(spacing: 8) {
                toolTile("MEMORY", key: "memory", hint: "Remember ")
                toolTile("DESKTOP", key: "desktop", hint: "Open ")
                toolTile("BROWSER", key: "browser", hint: "Go to ")
                toolTile("CALENDAR", key: "calendar", hint: "What's on my calendar tomorrow?")
            }
            Spacer()
            Text("⌥⌘J  PTT")
                .font(JarvisTheme.mono(9))
                .foregroundStyle(JarvisTheme.steel.opacity(0.7))
        }
        .padding(20)
        .frame(width: 220)
        .background(JarvisTheme.panel.opacity(0.72))
    }

    private var statusLine: some View {
        VStack(spacing: 4) {
            Text(model.online ? "SYSTEMS ONLINE" : "BRAIN OFFLINE")
                .font(JarvisTheme.mono(9, weight: .semibold))
                .foregroundStyle(model.online ? JarvisTheme.ok : JarvisTheme.gold)
            Text(model.clock.formatted(date: .omitted, time: .standard))
                .font(JarvisTheme.mono(10))
                .foregroundStyle(JarvisTheme.steel)
        }
    }

    private func toolTile(_ title: String, key: String, hint: String) -> some View {
        let hot = model.lastTool == key
        return Button {
            model.fill(hint)
        } label: {
            HStack {
                Circle()
                    .fill(hot ? JarvisTheme.cyan : JarvisTheme.cyanDim)
                    .frame(width: 6, height: 6)
                Text(title)
                    .font(JarvisTheme.mono(10, weight: .semibold))
                    .foregroundStyle(hot ? JarvisTheme.cyan : JarvisTheme.steel)
                Spacer()
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 4)
                    .stroke(hot ? JarvisTheme.cyan.opacity(0.7) : JarvisTheme.cyan.opacity(0.18), lineWidth: 1)
                    .background(RoundedRectangle(cornerRadius: 4).fill(JarvisTheme.void.opacity(0.5)))
            )
        }
        .buttonStyle(.plain)
    }

    private var deck: some View {
        VStack(alignment: .leading, spacing: 14) {
            header
            log
            if model.lines.isEmpty {
                chipsRow
            }
            composer
        }
        .padding(22)
    }

    private var header: some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 4) {
                Text(model.busy ? "EXECUTING DIRECTIVE" : "AWAITING DIRECTIVE")
                    .font(JarvisTheme.mono(16, weight: .semibold))
                    .foregroundStyle(JarvisTheme.cyan)
                Text(model.online ? "Local brain · four tools · no cloud" : "Start ./ops/run-v1.sh then return")
                    .font(JarvisTheme.mono(11))
                    .foregroundStyle(JarvisTheme.steel)
            }
            Spacer()
            if model.busy {
                ProgressView()
                    .controlSize(.small)
                    .tint(JarvisTheme.cyan)
            }
        }
    }

    private var log: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    if model.lines.isEmpty {
                        Text("Type a command, tap a system, or use a chip below.")
                            .font(JarvisTheme.mono(12))
                            .foregroundStyle(JarvisTheme.steel.opacity(0.8))
                            .padding(.top, 24)
                    }
                    ForEach(model.lines) { line in
                        messageCard(line).id(line.id)
                    }
                }
                .padding(.trailing, 4)
            }
            .onChange(of: model.lines.count) { _, _ in
                if let last = model.lines.last {
                    withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func messageCard(_ line: LogLine) -> some View {
        let you = line.role == "you"
        let err = line.role == "error"
        let accent = err ? JarvisTheme.danger : (you ? JarvisTheme.gold : JarvisTheme.cyan)
        return HStack {
            if you { Spacer(minLength: 80) }
            VStack(alignment: .leading, spacing: 4) {
                Text(line.role.uppercased())
                    .font(JarvisTheme.mono(9, weight: .bold))
                    .foregroundStyle(accent.opacity(0.8))
                    .tracking(1.2)
                Text(line.text)
                    .font(.system(size: 15, weight: .medium))
                    .foregroundStyle(Color.white.opacity(0.92))
                    .textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(12)
            .frame(maxWidth: 560, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(JarvisTheme.panel.opacity(0.9))
                    .overlay(RoundedRectangle(cornerRadius: 6).stroke(accent.opacity(0.45), lineWidth: 1))
            )
            if !you { Spacer(minLength: 40) }
        }
        .transition(.opacity.combined(with: .move(edge: .bottom)))
    }

    private var chipsRow: some View {
        HStack(spacing: 8) {
            ForEach(chips, id: \.self) { chip in
                Button {
                    model.fill(chip)
                    Task { await model.submit() }
                } label: {
                    Text(chip)
                        .font(JarvisTheme.mono(10, weight: .medium))
                        .foregroundStyle(JarvisTheme.cyan)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(
                            Capsule().stroke(JarvisTheme.cyan.opacity(0.4), lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)
            }
        }
    }

    private var composer: some View {
        VStack(alignment: .leading, spacing: 10) {
            if let err = model.lastError {
                Text(err)
                    .font(JarvisTheme.mono(11))
                    .foregroundStyle(JarvisTheme.danger)
            }
            Button {
                model.confirmDangerous.toggle()
            } label: {
                HStack(spacing: 8) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(model.confirmDangerous ? JarvisTheme.gold : JarvisTheme.void)
                        .frame(width: 14, height: 14)
                        .overlay(RoundedRectangle(cornerRadius: 2).stroke(JarvisTheme.gold, lineWidth: 1))
                    Text(model.confirmDangerous ? "ARMED  ·  quit / lock / sleep / calendar write" : "SAFE  ·  tap to arm dangerous ops")
                        .font(JarvisTheme.mono(10, weight: .semibold))
                        .foregroundStyle(model.confirmDangerous ? JarvisTheme.gold : JarvisTheme.steel)
                }
            }
            .buttonStyle(.plain)
            HStack(spacing: 10) {
                Text("›")
                    .font(JarvisTheme.mono(20, weight: .bold))
                    .foregroundStyle(JarvisTheme.cyan)
                TextField("", text: $model.command, prompt: Text("Speak a command…").foregroundStyle(JarvisTheme.steel.opacity(0.55)))
                    .textFieldStyle(.plain)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(.white)
                    .onSubmit { Task { await model.submit() } }
                Button {
                    Task { await model.submit() }
                } label: {
                    Text(model.busy ? "…" : "EXECUTE")
                        .font(JarvisTheme.mono(11, weight: .bold))
                        .tracking(1)
                        .foregroundStyle(Color.black)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 8)
                        .background(JarvisTheme.cyan)
                        .clipShape(RoundedRectangle(cornerRadius: 3))
                }
                .buttonStyle(.plain)
                .keyboardShortcut(.return, modifiers: .command)
                .disabled(model.busy || model.command.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                .opacity(model.busy || model.command.isEmpty ? 0.45 : 1)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(JarvisTheme.void.opacity(0.85))
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(JarvisTheme.cyan.opacity(model.busy ? 0.9 : 0.35), lineWidth: 1)
                    )
                    .shadow(color: JarvisTheme.cyan.opacity(model.busy ? 0.35 : 0.08), radius: 12)
            )
        }
    }
}
