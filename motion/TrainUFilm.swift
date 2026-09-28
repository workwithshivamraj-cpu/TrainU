import AppKit
import CoreText
import ImageIO

// TrainU product film. Render with: swift motion/TrainUFilm.swift
let W = 1280, H = 720, fps: Int32 = 20, duration = 12.0
let output = URL(fileURLWithPath: CommandLine.arguments.dropFirst().first ?? "motion/trainu-light.gif")
let preview = URL(fileURLWithPath: "motion/trainu-light-poster.png")

func color(_ hex: UInt32, _ a: CGFloat = 1) -> CGColor {
    CGColor(colorSpace: CGColorSpaceCreateDeviceRGB(), components: [CGFloat((hex >> 16) & 255)/255, CGFloat((hex >> 8) & 255)/255, CGFloat(hex & 255)/255, a])!
}
let ink = color(0x182B39), muted = color(0x617585), aqua = color(0x087F75)
func clamp(_ x: Double) -> Double { min(1, max(0, x)) }
func ease(_ x: Double) -> Double { let p = clamp(x); return 1 - pow(1-p, 3) }
func fade(_ t: Double, _ start: Double, _ end: Double, _ out: Double = 99) -> CGFloat {
    CGFloat(ease((t-start)/(end-start)) * (1-ease((t-out)/0.38)))
}
func rect(_ c: CGContext, _ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, _ r: CGFloat, _ fill: CGColor, _ stroke: CGColor? = nil) {
    let p = CGPath(roundedRect: CGRect(x:x,y:y,width:w,height:h), cornerWidth:r, cornerHeight:r, transform:nil)
    c.addPath(p); c.setFillColor(fill); c.fillPath()
    if let stroke { c.addPath(p); c.setStrokeColor(stroke); c.setLineWidth(1); c.strokePath() }
}
func line(_ c: CGContext, _ x1: CGFloat, _ y1: CGFloat, _ x2: CGFloat, _ y2: CGFloat, _ col: CGColor, _ width: CGFloat = 1) {
    c.setStrokeColor(col); c.setLineWidth(width); c.move(to: CGPoint(x:x1,y:y1)); c.addLine(to: CGPoint(x:x2,y:y2)); c.strokePath()
}
func txt(_ c: CGContext, _ s: String, _ x: CGFloat, _ y: CGFloat, _ size: CGFloat, _ col: CGColor, _ weight: NSFont.Weight = .regular, _ tracking: CGFloat = 0) {
    let font = NSFont.systemFont(ofSize:size, weight:weight)
    let attrs: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: NSColor(cgColor: col)!, .kern: tracking]
    let str = NSAttributedString(string:s, attributes:attrs)
    let ct = CTLineCreateWithAttributedString(str)
    c.saveGState(); c.translateBy(x:x,y:y+font.ascender); c.scaleBy(x:1,y:-1); c.textPosition = .zero
    CTLineDraw(ct,c); c.restoreGState()
}
func star(_ c: CGContext, _ x: CGFloat, _ y: CGFloat, _ size: CGFloat, _ alpha: CGFloat = 1) {
    let p = CGMutablePath()
    p.move(to: CGPoint(x:x,y:y-size)); p.addQuadCurve(to:CGPoint(x:x+size,y:y),control:CGPoint(x:x+size*0.1,y:y-size*0.1))
    p.addQuadCurve(to:CGPoint(x:x,y:y+size),control:CGPoint(x:x+size*0.1,y:y+size*0.1))
    p.addQuadCurve(to:CGPoint(x:x-size,y:y),control:CGPoint(x:x-size*0.1,y:y+size*0.1))
    p.addQuadCurve(to:CGPoint(x:x,y:y-size),control:CGPoint(x:x-size*0.1,y:y-size*0.1))
    c.addPath(p); c.setFillColor(color(0x087F75,alpha)); c.fillPath()
}
func background(_ c: CGContext, _ t: Double) {
    c.setFillColor(color(0xF7FAF8)); c.fill(CGRect(x:0,y:0,width:W,height:H))
    let center = CGPoint(x:950 + 50*sin(t*0.35), y:160 + 35*cos(t*0.3))
    let gradient = CGGradient(colorsSpace:CGColorSpaceCreateDeviceRGB(), colors:[color(0xBDECE0,0.62),color(0xE4F2EF,0.18),color(0xF7FAF8,0)] as CFArray, locations:[0,0.55,1])!
    c.drawRadialGradient(gradient,startCenter:center,startRadius:0,endCenter:center,endRadius:650,options:[])
    for x in stride(from:80,through:1200,by:80) { line(c,CGFloat(x),0,CGFloat(x),720,color(0x487F73,0.035)) }
    for y in stride(from:80,through:640,by:80) { line(c,0,CGFloat(y),1280,CGFloat(y),color(0x487F73,0.035)) }
    line(c,64,56,1216,56,color(0x487F73,0.15))
    line(c,64,662,1216,662,color(0x487F73,0.15))
    star(c,77,36,10)
    txt(c,"TrainU",99,22,23,ink,.bold,-0.5)
    txt(c,"KNOWLEDGE, IN MOTION",990,27,11,muted,.semibold,2)
    txt(c,t < 2.65 ? "01 / 03" : (t < 9.55 ? "02 / 03" : "03 / 03"),65,676,11,muted,.medium,1.5)
    txt(c,"ASK  ·  LEARN  ·  ACT",1040,676,11,muted,.medium,1.3)
}
func film(_ c: CGContext, _ t: Double) {
    background(c,t)
    let a = fade(t,0.18,0.75,2.65)
    if a > 0 {
        c.saveGState(); c.setAlpha(a)
        let dy = CGFloat((1-ease((t-0.18)/0.65))*30)
        txt(c,"YOUR TEAM KNOWS.",88,200+dy,17,aqua,.semibold,3)
        txt(c,"Now everyone",82,265+dy,89,ink,.semibold,-4)
        txt(c,"can find it.",82,367+dy,89,ink,.semibold,-4)
        rect(c,88,514+dy,425,1,0,color(0x087F75,0.75))
        txt(c,"Approved answers. Exact sources. Zero guesswork.",88,540+dy,21,muted,.regular,-0.2)
        c.restoreGState()
    }
    let b = fade(t,2.55,3.15,6.6)
    if b > 0 {
        c.saveGState(); c.setAlpha(b)
        let dy = CGFloat((1-ease((t-2.55)/0.66))*32)
        txt(c,"FROM QUESTION TO CLARITY",88,111+dy,16,aqua,.semibold,2.8)
        txt(c,"Ask what you need.",88,156+dy,54,ink,.semibold,-2)
        rect(c,84,258+dy,1112,322,26,color(0xFFFFFF,0.97),color(0xA6C7C0,0.38))
        rect(c,116,293+dy,1048,66,16,color(0xF1F7F5),color(0xBDD6D0,0.24))
        star(c,146,326+dy,12)
        let question = "How do I create a new client account?"
        let count = Int(Double(question.count)*ease((t-3.02)/0.86))
        txt(c,String(question.prefix(max(0,count))),173,311+dy,25,ink,.medium)
        if t < 4.1 && Int(t*3)%2 == 0 { rect(c,175+CGFloat(count)*12.2,315+dy,2,26,0,aqua) }
        let answer = fade(t,4.04,4.55)
        if answer > 0 {
            c.saveGState(); c.setAlpha(answer)
            rect(c,116,384+dy,1048,158,17,color(0xF6FBF9),color(0x087F75,0.28))
            star(c,151,419+dy,12)
            txt(c,"Create the account from the Clients workspace.",178,400+dy,23,ink,.semibold)
            txt(c,"Follow the approved onboarding steps, then submit for review.",178,438+dy,19,muted)
            rect(c,178,487+dy,220,33,17,color(0xDDF4EC),color(0x087F75,0.28))
            txt(c,"↗  Source video  ·  01:24",194,493+dy,14,aqua,.semibold)
            c.restoreGState()
        }
        c.restoreGState()
    }
    let d = fade(t,9.55,10.1)
    if d > 0 {
        c.saveGState(); c.setAlpha(d)
        let dy = CGFloat((1-ease((t-9.55)/0.6))*27)
        star(c,640,183+dy,27)
        txt(c,"Answers you",311,248+dy,77,ink,.semibold,-3)
        txt(c,"can verify.",376,337+dy,77,aqua,.semibold,-3)
        txt(c,"Every answer connects back to approved knowledge.",357,466+dy,21,muted)
        rect(c,535,528+dy,210,51,25,color(0x087F75))
        txt(c,"ASK TRAINU   ↗",569,543+dy,17,color(0xFFFFFF),.bold,1)
        c.restoreGState()
    }
    let source = fade(t,6.65,7.15,9.6)
    if source > 0 {
        c.saveGState(); c.setAlpha(source)
        txt(c,"ONE CLICK. EXACTLY THERE.",88,130,16,aqua,.semibold,2.6)
        txt(c,"Skip to the good part.",86,177,62,ink,.semibold,-2.5)
        rect(c,86,293,1108,299,28,color(0xFFFFFF),color(0xC8DDD6))
        rect(c,110,317,494,251,18,color(0xE2F2EB))
        txt(c,"CLIENT ONBOARDING",143,343,12,aqua,.bold,1.8)
        rect(c,144,386,424,130,12,color(0xFFFFFF))
        txt(c,"New client account",165,404,21,ink,.semibold)
        rect(c,165,442,200,12,5,color(0xD8E8E3))
        rect(c,165,466,280,12,5,color(0xE9F1EE))
        rect(c,165,490,82,15,7,aqua)
        line(c,144,542,569,542,color(0xB5D5C9),4)
        line(c,144,542,CGFloat(320+35*ease((t-7.3)/1.5)),542,aqua,4)
        rect(c,314,535,14,14,7,aqua)
        txt(c,"01:24",630,340,53,aqua,.semibold,-1.8)
        txt(c,"Right to the source.",630,411,32,ink,.semibold,-0.7)
        txt(c,"The approved clip behind your answer.",630,459,21,muted)
        rect(c,630,510,183,34,17,color(0xDDF4EC))
        txt(c,"✓  Approved knowledge",647,518,13,aqua,.semibold)
        c.restoreGState()
    }
    if t > 5.25 && t < 6.85 {
        let p = CGFloat(ease((t-5.25)/0.8))
        let x: CGFloat = 1060 - 760*p, y: CGFloat = 590 - 85*p
        c.saveGState(); c.setAlpha(fade(t,5.25,5.45,6.55))
        if t > 6.1 {
            let r = CGFloat(12 + 30*clamp((t-6.1)/0.5))
            c.setStrokeColor(color(0x087F75,CGFloat(1-clamp((t-6.1)/0.5))))
            c.setLineWidth(2); c.strokeEllipse(in:CGRect(x:x-r,y:y-r,width:2*r,height:2*r))
        }
        let pointer=CGMutablePath(); pointer.move(to:CGPoint(x:x,y:y)); pointer.addLine(to:CGPoint(x:x+4,y:y+26)); pointer.addLine(to:CGPoint(x:x+11,y:y+18)); pointer.addLine(to:CGPoint(x:x+23,y:y+17)); pointer.closeSubpath()
        c.addPath(pointer); c.setFillColor(ink); c.setStrokeColor(color(0xFFFFFF)); c.setLineWidth(2); c.drawPath(using:.fillStroke)
        c.restoreGState()
    }
    let progress = CGFloat(t/duration)
    rect(c,64,658,1152*progress,3,0,aqua)
}

try? FileManager.default.removeItem(at:output)
let frameCount = Int(duration*Double(fps))
let gif = CGImageDestinationCreateWithURL(output as CFURL,"com.compuserve.gif" as CFString,frameCount,nil)!
CGImageDestinationSetProperties(gif,[kCGImagePropertyGIFDictionary:[kCGImagePropertyGIFLoopCount:0]] as CFDictionary)
for frame in 0..<Int(duration*Double(fps)) {
    let c = CGContext(data:nil,width:W,height:H,bitsPerComponent:8,bytesPerRow:0,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedFirst.rawValue)!
    c.translateBy(x:0,y:CGFloat(H)); c.scaleBy(x:1,y:-1)
    film(c,Double(frame)/Double(fps))
    guard let image = c.makeImage() else { fatalError("Image") }
    CGImageDestinationAddImage(gif,image,[kCGImagePropertyGIFDictionary:[kCGImagePropertyGIFDelayTime:1/Double(fps)]] as CFDictionary)
    if frame == 162, let dest = CGImageDestinationCreateWithURL(preview as CFURL,"public.png" as CFString,1,nil) {
        CGImageDestinationAddImage(dest,image,nil); CGImageDestinationFinalize(dest)
    }
    if frame % 40 == 0 { print("Rendered \(frame)/\(frameCount)") }
}
guard CGImageDestinationFinalize(gif) else { fatalError("GIF export failed") }
print("Wrote \(output.path)")
