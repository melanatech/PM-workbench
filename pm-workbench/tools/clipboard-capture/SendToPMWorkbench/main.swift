import AppKit
import Foundation

/// Real Cocoa NSServices provider — required for right-click / Services menu.
final class ServiceProvider: NSObject {
    let liveRoot: String
    let capturePy: String
    private(set) var handled = false

    init(liveRoot: String, capturePy: String) {
        self.liveRoot = liveRoot
        self.capturePy = capturePy
        super.init()
    }

    /// Info.plist NSMessage `processText` → processText:userData:error:
    @objc func processText(
        _ pboard: NSPasteboard,
        userData: String,
        error: NSErrorPointer
    ) {
        handled = true
        let text =
            pboard.string(forType: .string)
            ?? pboard.string(forType: NSPasteboard.PasteboardType("public.utf8-plain-text"))
            ?? ""
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            Self.alert("Select some text first, then choose Services → Send to PM Workbench.")
            quitSoon()
            return
        }
        runCapture(stdin: trimmed)
        quitSoon()
    }

    func runCaptureFromClipboard() {
        let clip = NSPasteboard.general.string(forType: .string)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !clip.isEmpty else {
            Self.alert("Clipboard is empty — select text and use Services, or copy first.")
            quitSoon()
            return
        }
        runCapture(stdin: clip)
        quitSoon()
    }

    private func runCapture(stdin: String) {
        guard FileManager.default.isReadableFile(atPath: capturePy) else {
            Self.alert("Missing scripts/capture_clipboard.py under \(liveRoot)")
            return
        }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = [capturePy, "--root", liveRoot, "--gui", "--stdin"]
        let inPipe = Pipe()
        let errPipe = Pipe()
        process.standardInput = inPipe
        process.standardOutput = Pipe()
        process.standardError = errPipe
        do {
            try process.run()
            inPipe.fileHandleForWriting.write(Data(stdin.utf8))
            try? inPipe.fileHandleForWriting.close()
            process.waitUntilExit()
            if process.terminationStatus != 0 {
                let err = String(data: errPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8)?
                    .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                Self.alert(err.isEmpty ? "Capture failed (exit \(process.terminationStatus))." : err)
            }
        } catch {
            Self.alert("Could not run capture: \(error.localizedDescription)")
        }
    }

    private func quitSoon() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) {
            NSApp.terminate(nil)
        }
    }

    static func alert(_ message: String) {
        let escaped = message
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
            .replacingOccurrences(of: "\n", with: " ")
        let script = "display alert \"PM Workbench\" message \"\(escaped)\""
        var err: NSDictionary?
        NSAppleScript(source: script)?.executeAndReturnError(&err)
    }
}

@main
enum AppMain {
    static func main() {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let marker = (home as NSString).appendingPathComponent(".pm-workbench/live-root")
        var liveRoot = ProcessInfo.processInfo.environment["PM_LIVE_ROOT"]
            ?? (home as NSString).appendingPathComponent("pm-live")
        if let raw = try? String(contentsOfFile: marker, encoding: .utf8) {
            for line in raw.split(separator: "\n").map(String.init) {
                let t = line.trimmingCharacters(in: .whitespacesAndNewlines)
                if !t.isEmpty && !t.hasPrefix("#") {
                    liveRoot = t
                    break
                }
            }
        }
        var capturePy = (liveRoot as NSString).appendingPathComponent("scripts/capture_clipboard.py")
        if !FileManager.default.isReadableFile(atPath: capturePy),
           let bundled = Bundle.main.path(forResource: "capture_clipboard", ofType: "py") {
            capturePy = bundled
        }

        let provider = ServiceProvider(liveRoot: liveRoot, capturePy: capturePy)
        let app = NSApplication.shared
        app.setActivationPolicy(.accessory)
        app.servicesProvider = provider
        NSUpdateDynamicServices()

        // If Services invoked us, processText: arrives on the run loop shortly.
        // If opened from Spotlight/Dock instead, fall back to clipboard after a beat.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
            if !provider.handled {
                provider.runCaptureFromClipboard()
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 180) {
            NSApp.terminate(nil)
        }
        app.run()
    }
}
