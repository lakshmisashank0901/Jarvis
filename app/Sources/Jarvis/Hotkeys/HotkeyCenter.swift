import Carbon
import Foundation

final class HotkeyCenter {
    private var ptt: EventHotKeyRef?
    private var cancel: EventHotKeyRef?
    var onPTTDown: (() -> Void)?
    var onPTTUp: (() -> Void)?
    var onCancel: (() -> Void)?

    @discardableResult
    func register() -> OSStatus {
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(GetApplicationEventTarget(), { _, event, user in
            guard let user else { return noErr }
            let center = Unmanaged<HotkeyCenter>.fromOpaque(user).takeUnretainedValue()
            var hotkeyID = EventHotKeyID()
            GetEventParameter(event, EventParamName(kEventParamDirectObject), EventParamType(typeEventHotKeyID), nil, MemoryLayout<EventHotKeyID>.size, nil, &hotkeyID)
            if hotkeyID.id == 1 { center.onPTTDown?() }
            if hotkeyID.id == 2 { center.onCancel?() }
            return noErr
        }, 1, &spec, Unmanaged.passUnretained(self).toOpaque(), nil)

        let pttID = EventHotKeyID(signature: OSType(0x4A525653), id: 1)
        // Not Space: macOS owns ⌥⌘Space (Finder search) and ⌘Space (Spotlight).
        let pttStatus = RegisterEventHotKey(UInt32(kVK_ANSI_J), UInt32(cmdKey | optionKey), pttID, GetApplicationEventTarget(), 0, &ptt)
        let cancelID = EventHotKeyID(signature: OSType(0x4A525653), id: 2)
        RegisterEventHotKey(UInt32(kVK_Escape), UInt32(cmdKey | optionKey), cancelID, GetApplicationEventTarget(), 0, &cancel)
        return pttStatus
    }
}
