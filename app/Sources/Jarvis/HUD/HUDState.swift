import Foundation

enum HUDPhase: String, Codable, Sendable {
    case idle, listening, thinking, speaking, confirm
}

struct HUDConfirm: Codable, Sendable, Equatable {
    var id: String
    var text: String
    var deadline_ms: Int
}

struct HUDState: Codable, Sendable, Equatable {
    var t: String
    var state: HUDPhase
    var partial: String?
    var confirm: HUDConfirm?

    init(from decoder: Decoder) throws {
        let box = try decoder.container(keyedBy: CodingKeys.self)
        t = try box.decodeIfPresent(String.self, forKey: .t) ?? "hud"
        let raw = try box.decode(String.self, forKey: .state)
        state = HUDPhase(rawValue: raw) ?? .idle
        partial = try box.decodeIfPresent(String.self, forKey: .partial)
        confirm = try box.decodeIfPresent(HUDConfirm.self, forKey: .confirm)
    }
}
