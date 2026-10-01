import AppKit
import AVFoundation
import CoreVideo
import Foundation

struct Step: Decodable {
    let title: String
    let detail: String
    let tag: String
}

struct Clip: Decodable {
    let title: String
    let application: String
    let accent: String
    let steps: [Step]
    let audio: String
    let output: String
}

struct Manifest: Decodable { let clips: [Clip] }

let width = 1280
let height = 720
let fps: Int32 = 24

func color(_ hex: String, alpha: CGFloat = 1) -> NSColor {
    let raw = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
    let value = UInt64(raw, radix: 16) ?? 0x22B59A
    return NSColor(calibratedRed: CGFloat((value >> 16) & 255) / 255,
                   green: CGFloat((value >> 8) & 255) / 255,
                   blue: CGFloat(value & 255) / 255, alpha: alpha)
}

func rounded(_ rect: CGRect, radius: CGFloat, fill: NSColor, stroke: NSColor? = nil, width lineWidth: CGFloat = 1) {
    let path = NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius)
    fill.setFill(); path.fill()
    if let stroke { stroke.setStroke(); path.lineWidth = lineWidth; path.stroke() }
}

func label(_ value: String, _ rect: CGRect, size: CGFloat, weight: NSFont.Weight = .regular,
           tint: NSColor = color("#24323D"), alignment: NSTextAlignment = .left) {
    let paragraph = NSMutableParagraphStyle()
    paragraph.alignment = alignment
    paragraph.lineBreakMode = .byWordWrapping
    let attrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: size, weight: weight),
        .foregroundColor: tint,
        .paragraphStyle: paragraph,
    ]
    (value as NSString).draw(in: rect, withAttributes: attrs)
}

func circle(_ rect: CGRect, fill: NSColor, stroke: NSColor? = nil, lineWidth: CGFloat = 1) {
    let path = NSBezierPath(ovalIn: rect)
    fill.setFill(); path.fill()
    if let stroke { stroke.setStroke(); path.lineWidth = lineWidth; path.stroke() }
}

func drawFrame(_ clip: Clip, time: Double, duration: Double, context cg: CGContext) {
    let ns = NSGraphicsContext(cgContext: cg, flipped: true)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = ns

    color("#F6F8F5").setFill(); NSRect(x: 0, y: 0, width: width, height: height).fill()
    circle(CGRect(x: 1010, y: -190, width: 430, height: 430), fill: color(clip.accent, alpha: 0.07))
    circle(CGRect(x: -180, y: 565, width: 330, height: 330), fill: color("#F4B860", alpha: 0.10))

    // Compact TU mark and the guide label.
    rounded(CGRect(x: 54, y: 38, width: 44, height: 44), radius: 14, fill: color(clip.accent))
    label("TU", CGRect(x: 54, y: 47, width: 44, height: 27), size: 17, weight: .bold,
          tint: .white, alignment: .center)
    label("TRAINU  /  FIELD GUIDE", CGRect(x: 112, y: 42, width: 330, height: 20), size: 12,
          weight: .bold, tint: color("#73818A"))
    label(clip.application.uppercased(), CGRect(x: 900, y: 44, width: 325, height: 20), size: 12,
          weight: .semibold, tint: color(clip.accent), alignment: .right)

    let index = min(max(Int(time / max(duration, 0.1) * Double(clip.steps.count)), 0), clip.steps.count - 1)
    let step = clip.steps[index]
    let local = (time / max(duration, 0.1) * Double(clip.steps.count)).truncatingRemainder(dividingBy: 1)
    let ease = 1 - pow(1 - min(max(local / 0.22, 0), 1), 3)
    let slide = (1 - ease) * 42

    label(clip.title, CGRect(x: 58, y: 105, width: 1120, height: 64), size: 37, weight: .bold,
          tint: color("#17252E"))
    label("A clear, repeatable workflow", CGRect(x: 60, y: 163, width: 650, height: 24), size: 15,
          tint: color("#71808A"))

    // Simulated product window with the current action highlighted.
    rounded(CGRect(x: 58, y: 222, width: 690, height: 370), radius: 23, fill: .white,
            stroke: color("#E4EAE7"))
    rounded(CGRect(x: 58, y: 222, width: 690, height: 62), radius: 23, fill: color("#FBFCFB"))
    color("#FBFCFB").setFill(); NSRect(x: 58, y: 261, width: 690, height: 24).fill()
    circle(CGRect(x: 82, y: 245, width: 9, height: 9), fill: color("#ED9B87"))
    circle(CGRect(x: 98, y: 245, width: 9, height: 9), fill: color("#EFCB74"))
    circle(CGRect(x: 114, y: 245, width: 9, height: 9), fill: color("#75C9A6"))
    label(clip.application, CGRect(x: 154, y: 239, width: 360, height: 24), size: 14,
          weight: .semibold, tint: color("#4F606A"))
    label("WORKSPACE  /  TRAINING", CGRect(x: 88, y: 308, width: 260, height: 18), size: 10,
          weight: .bold, tint: color("#9AA6A8"))
    label(step.title, CGRect(x: 88, y: 339, width: 600, height: 35), size: 23, weight: .semibold)

    let rows = clip.steps.prefix(4).map(\.title)
    for row in 0..<4 {
        let y = 390 + CGFloat(row) * 43
        let isCurrent = row == index % 4
        let isDone = row < index % 4
        rounded(CGRect(x: 82, y: y, width: 640, height: 34), radius: 10,
                fill: isCurrent ? color(clip.accent, alpha: 0.10) : color("#F8FAF8"),
                stroke: isCurrent ? color(clip.accent, alpha: 0.38) : nil)
        circle(CGRect(x: 96, y: y + 9, width: 16, height: 16),
               fill: isDone ? color(clip.accent) : .white,
               stroke: isCurrent ? color(clip.accent) : color("#D9E1DC"))
        if isDone {
            label("✓", CGRect(x: 96, y: y + 7, width: 16, height: 16), size: 11,
                  weight: .bold, tint: .white, alignment: .center)
        }
        label(rows[row], CGRect(x: 124, y: y + 8, width: 440, height: 20), size: 13,
              weight: isCurrent ? .semibold : .regular,
              tint: isCurrent ? color("#24323D") : color("#71808A"))
        if isCurrent {
            rounded(CGRect(x: 625, y: y + 12, width: 68, height: 10), radius: 5,
                    fill: color(clip.accent, alpha: 0.18))
            rounded(CGRect(x: 625, y: y + 12, width: 68 * ease, height: 10), radius: 5,
                    fill: color(clip.accent))
        }
    }

    // Floating step card with gentle Motion-style entrance.
    let cardX = CGFloat(790) + slide
    rounded(CGRect(x: cardX, y: 232, width: 420, height: 337), radius: 25, fill: .white,
            stroke: color("#E4EAE7"))
    rounded(CGRect(x: cardX + 26, y: 258, width: 100, height: 29), radius: 14,
            fill: color(clip.accent, alpha: 0.11))
    label(String(format: "STEP %02d", index + 1), CGRect(x: cardX + 26, y: 266, width: 100, height: 16),
          size: 10, weight: .bold, tint: color(clip.accent), alignment: .center)
    label(step.tag, CGRect(x: cardX + 26, y: 308, width: 366, height: 22), size: 12,
          weight: .semibold, tint: color("#859198"))
    label(step.title, CGRect(x: cardX + 26, y: 339, width: 366, height: 66), size: 27,
          weight: .bold, tint: color("#17252E"))
    label(step.detail, CGRect(x: cardX + 26, y: 411, width: 364, height: 80), size: 16,
          tint: color("#61717A"))
    rounded(CGRect(x: cardX + 26, y: 518, width: 366, height: 8), radius: 4,
            fill: color("#EEF2EF"))
    rounded(CGRect(x: cardX + 26, y: 518, width: 366 * CGFloat(min(max(time / duration, 0), 1)), height: 8),
            radius: 4, fill: color(clip.accent))

    // Subtle animated orb and timeline underscore give the still UI a motion feel.
    let orbX = 1110 + sin(time * 1.4) * 13
    circle(CGRect(x: orbX, y: 610 + cos(time * 1.1) * 5, width: 13, height: 13),
           fill: color(clip.accent, alpha: 0.68))
    label("TRAINU  ·  LEARN IT. DO IT. OWN IT.", CGRect(x: 58, y: 631, width: 500, height: 17),
          size: 10, weight: .semibold, tint: color("#9AA6A8"))
    label("\(index + 1) / \(clip.steps.count)", CGRect(x: 1110, y: 631, width: 95, height: 17),
          size: 11, weight: .semibold, tint: color("#7B888D"), alignment: .right)
    rounded(CGRect(x: 58, y: 675, width: 1164, height: 5), radius: 3, fill: color("#E8EEEA"))
    rounded(CGRect(x: 58, y: 675, width: 1164 * CGFloat(min(max(time / duration, 0), 1)), height: 5),
            radius: 3, fill: color(clip.accent))
    NSGraphicsContext.restoreGraphicsState()
}

func renderVideo(_ clip: Clip) throws -> Double {
    let audioURL = URL(fileURLWithPath: clip.audio)
    let audioAsset = AVURLAsset(url: audioURL)
    let audioDuration = CMTimeGetSeconds(audioAsset.duration)
    guard audioDuration.isFinite, audioDuration > 1 else { throw NSError(domain: "TrainU", code: 1) }
    let silentURL = URL(fileURLWithPath: clip.output + ".silent.mp4")
    try? FileManager.default.removeItem(at: silentURL)
    try? FileManager.default.removeItem(atPath: clip.output)
    let writer = try AVAssetWriter(outputURL: silentURL, fileType: .mp4)
    let videoInput = AVAssetWriterInput(mediaType: .video, outputSettings: [
        AVVideoCodecKey: AVVideoCodecType.h264,
        AVVideoWidthKey: width,
        AVVideoHeightKey: height,
        AVVideoCompressionPropertiesKey: [
            AVVideoAverageBitRateKey: 2_000_000,
            AVVideoMaxKeyFrameIntervalKey: fps * 2,
        ],
    ])
    videoInput.expectsMediaDataInRealTime = false
    let attrs: [String: Any] = [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
        kCVPixelBufferWidthKey as String: width,
        kCVPixelBufferHeightKey as String: height,
        kCVPixelBufferCGImageCompatibilityKey as String: true,
        kCVPixelBufferCGBitmapContextCompatibilityKey as String: true,
    ]
    let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: videoInput,
                                                        sourcePixelBufferAttributes: attrs)
    guard writer.canAdd(videoInput) else { throw writer.error ?? NSError(domain: "TrainU", code: 2) }
    writer.add(videoInput)
    writer.startWriting()
    writer.startSession(atSourceTime: .zero)
    let frames = Int(ceil(audioDuration * Double(fps)))
    for frame in 0..<frames {
        while !videoInput.isReadyForMoreMediaData { Thread.sleep(forTimeInterval: 0.003) }
        var optionalBuffer: CVPixelBuffer?
        let status = CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, adaptor.pixelBufferPool!, &optionalBuffer)
        guard status == kCVReturnSuccess, let buffer = optionalBuffer else { throw NSError(domain: "TrainU", code: 3) }
        CVPixelBufferLockBaseAddress(buffer, [])
        let ctx = CGContext(data: CVPixelBufferGetBaseAddress(buffer), width: width, height: height,
                            bitsPerComponent: 8, bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
                            space: CGColorSpaceCreateDeviceRGB(),
                            bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue |
                                CGBitmapInfo.byteOrder32Little.rawValue)!
        drawFrame(clip, time: Double(frame) / Double(fps), duration: audioDuration, context: ctx)
        CVPixelBufferUnlockBaseAddress(buffer, [])
        let pts = CMTime(value: CMTimeValue(frame), timescale: fps)
        guard adaptor.append(buffer, withPresentationTime: pts) else { throw writer.error ?? NSError(domain: "TrainU", code: 4) }
    }
    videoInput.markAsFinished()
    let videoDone = DispatchSemaphore(value: 0)
    writer.finishWriting { videoDone.signal() }
    videoDone.wait()
    guard writer.status == .completed else { throw writer.error ?? NSError(domain: "TrainU", code: 5) }

    // Mux the generated voice track into the rendered motion graphics.
    let composition = AVMutableComposition()
    let silentAsset = AVURLAsset(url: silentURL)
    guard let videoSource = silentAsset.tracks(withMediaType: .video).first,
          let videoTrack = composition.addMutableTrack(withMediaType: .video,
                                                       preferredTrackID: kCMPersistentTrackID_Invalid),
          let audioSource = audioAsset.tracks(withMediaType: .audio).first,
          let audioTrack = composition.addMutableTrack(withMediaType: .audio,
                                                       preferredTrackID: kCMPersistentTrackID_Invalid) else {
        throw NSError(domain: "TrainU", code: 6)
    }
    // CoreVideo's bitmap row order is opposite QuickTime display coordinates on macOS.
    // Reflect the composition track so the saved movie displays upright in browsers.
    videoTrack.preferredTransform = CGAffineTransform(scaleX: 1, y: -1)
        .translatedBy(x: 0, y: -CGFloat(height))
    let muxDuration = min(CMTimeGetSeconds(audioAsset.duration), CMTimeGetSeconds(silentAsset.duration))
    let end = CMTime(seconds: muxDuration, preferredTimescale: 600)
    try videoTrack.insertTimeRange(CMTimeRange(start: .zero, duration: end), of: videoSource, at: .zero)
    try audioTrack.insertTimeRange(CMTimeRange(start: .zero, duration: end), of: audioSource, at: .zero)
    guard let exporter = AVAssetExportSession(asset: composition, presetName: AVAssetExportPresetHighestQuality) else {
        throw NSError(domain: "TrainU", code: 7)
    }
    exporter.outputURL = URL(fileURLWithPath: clip.output)
    exporter.outputFileType = .mp4
    let exportDone = DispatchSemaphore(value: 0)
    exporter.exportAsynchronously { exportDone.signal() }
    exportDone.wait()
    try? FileManager.default.removeItem(at: silentURL)
    guard exporter.status == .completed else { throw exporter.error ?? NSError(domain: "TrainU", code: 8) }
    return audioDuration
}

do {
    let manifestURL = URL(fileURLWithPath: CommandLine.arguments[1])
    let manifest = try JSONDecoder().decode(Manifest.self, from: Data(contentsOf: manifestURL))
    var results: [[String: Any]] = []
    for clip in manifest.clips {
        let duration = try renderVideo(clip)
        print("Rendered \(URL(fileURLWithPath: clip.output).lastPathComponent) — \(Int(duration.rounded()))s")
        results.append(["output": clip.output, "duration_seconds": duration])
    }
    let resultURL = manifestURL.deletingLastPathComponent().appendingPathComponent("render-results.json")
    let data = try JSONSerialization.data(withJSONObject: results, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: resultURL, options: .atomic)
} catch {
    fputs("Motion video render failed: \(error)\n", stderr)
    exit(1)
}
