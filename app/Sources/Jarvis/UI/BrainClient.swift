import Foundation

struct BrainReply: Sendable {
    var text: String
    var tool: String
}

enum BrainClientError: LocalizedError {
    case offline
    case badResponse

    var errorDescription: String? {
        switch self {
        case .offline: "Brain is not running. Start ./ops/run-v1.sh"
        case .badResponse: "Brain returned a bad reply"
        }
    }
}

struct BrainClient: Sendable {
    private static let session: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.waitsForConnectivity = false
        config.timeoutIntervalForRequest = 8
        config.timeoutIntervalForResource = 12
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        return URLSession(configuration: config)
    }()

    private let healthURL = URL(string: "http://127.0.0.1:8742/v1/health")!
    private let chatURL = URL(string: "http://127.0.0.1:8742/v1/chat/completions")!

    func health() async -> Bool {
        var req = URLRequest(url: healthURL)
        req.timeoutInterval = 2
        do {
            let (_, res) = try await Self.session.data(for: req)
            return (res as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func ask(_ text: String, confirmed: Bool) async throws -> BrainReply {
        var req = URLRequest(url: chatURL)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 12
        let body: [String: Any] = [
            "stream": false,
            "confirmed": confirmed,
            "messages": [["role": "user", "content": text]],
        ]
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, res) = try await Self.session.data(for: req)
        guard (res as? HTTPURLResponse)?.statusCode == 200 else { throw BrainClientError.offline }
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw BrainClientError.badResponse
        }
        let choices = json["choices"] as? [[String: Any]]
        let message = choices?.first?["message"] as? [String: Any]
        let textOut = message?["content"] as? String ?? ""
        let jarvis = json["jarvis"] as? [String: Any]
        let call = jarvis?["call"] as? [String: Any]
        let tool = call?["name"] as? String ?? ""
        return BrainReply(text: textOut, tool: tool)
    }
}
