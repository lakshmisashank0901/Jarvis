import EventKit
import Foundation

final class CalendarStore {
    private let store = EKEventStore()

    func list(from: String?, to: String?) throws -> [String: Any] {
        try request()
        let start = Self.parse(from) ?? Date()
        let end = Self.parse(to) ?? start.addingTimeInterval(86_400)
        let pred = store.predicateForEvents(withStart: start, end: end, calendars: nil)
        let events = store.events(matching: pred).map { ev in
            [
                "id": ev.eventIdentifier ?? "",
                "title": ev.title ?? "",
                "start": ISO8601DateFormatter().string(from: ev.startDate),
                "end": ISO8601DateFormatter().string(from: ev.endDate),
            ]
        }
        return ["ok": true, "events": events]
    }

    func create(title: String, start: String?, end: String?) throws -> [String: Any] {
        try request()
        let ev = EKEvent(eventStore: store)
        ev.title = title
        ev.startDate = Self.parse(start) ?? Date()
        ev.endDate = Self.parse(end) ?? ev.startDate.addingTimeInterval(1800)
        ev.calendar = store.defaultCalendarForNewEvents
        try store.save(ev, span: .thisEvent)
        return ["ok": true, "id": ev.eventIdentifier ?? ""]
    }

    func update(id: String, title: String?, start: String?, end: String?) throws -> [String: Any] {
        try request()
        guard let ev = store.event(withIdentifier: id) else {
            return ["ok": false, "error": "not found"]
        }
        if let title { ev.title = title }
        if let start { ev.startDate = Self.parse(start) }
        if let end { ev.endDate = Self.parse(end) }
        try store.save(ev, span: .thisEvent)
        return ["ok": true]
    }

    private func request() throws {
        let sem = DispatchSemaphore(value: 0)
        var err: Error?
        store.requestFullAccessToEvents { _, e in
            err = e
            sem.signal()
        }
        sem.wait()
        if let err { throw err }
    }

    private static func parse(_ raw: String?) -> Date? {
        guard let raw else { return nil }
        return ISO8601DateFormatter().date(from: raw)
    }
}
