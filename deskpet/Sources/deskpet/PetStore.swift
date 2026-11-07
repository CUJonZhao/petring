import AppKit
import Foundation

enum PetBehavior: String, Codable, CaseIterable, Identifiable {
    case idle, rest, walk, drink, bark, unknown

    var id: String { rawValue }

    var title: String {
        switch self {
        case .idle: "待机"
        case .rest: "安静休息"
        case .walk: "正在活动"
        case .drink: "可能在喝水"
        case .bark: "检测到叫声"
        case .unknown: "暂时无法判断"
        }
    }

    var symbol: String {
        switch self {
        case .idle: "pawprint.fill"
        case .rest: "moon.zzz.fill"
        case .walk: "figure.walk"
        case .drink: "drop.fill"
        case .bark: "waveform"
        case .unknown: "wifi.slash"
        }
    }
}

enum PhotoAngle: String, Codable, CaseIterable, Identifiable {
    case front, fullBodyFront, left, right, back, standing, resting, detail

    var id: String { rawValue }
    var title: String {
        switch self {
        case .front: "正面"
        case .fullBodyFront: "正面全身"
        case .left: "左侧"
        case .right: "右侧"
        case .back: "背面"
        case .standing: "站立"
        case .resting: "趴卧"
        case .detail: "花纹细节"
        }
    }
}

struct PetPhoto: Codable, Identifiable {
    let id: UUID
    let angle: PhotoAngle
    let filename: String
    let addedAt: Date
}

struct PetEvent: Decodable {
    let state: PetBehavior
    let confidence: Double?
    let timestamp: Date?
}

private struct SavedSettings: Codable {
    var photos: [PetPhoto] = []
    var modelFilename: String? = nil
    var streamURL: String = ""
}

@MainActor
final class PetStore: ObservableObject {
    @Published private(set) var photos: [PetPhoto] = []
    @Published private(set) var modelURL: URL?
    @Published private(set) var behavior: PetBehavior = .idle
    @Published private(set) var lastEventAt: Date?
    @Published private(set) var eventSource = "演示模式"
    @Published private(set) var connectionStatus = "未连接"
    @Published var streamURL = ""
    @Published var errorMessage: String?

    let dataDirectory: URL
    private let settingsURL: URL
    private var stream: PetEventStream?
    private var stalenessTimer: Timer?

    init() {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        dataDirectory = base.appendingPathComponent("DeskPet", isDirectory: true)
        settingsURL = dataDirectory.appendingPathComponent("settings.json")
        try? FileManager.default.createDirectory(at: dataDirectory, withIntermediateDirectories: true)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
            let text = try decoder.singleValueContainer().decode(String.self)
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = formatter.date(from: text) { return date }
            formatter.formatOptions = [.withInternetDateTime]
            if let date = formatter.date(from: text) { return date }
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath,
                                                    debugDescription: "Invalid ISO 8601 date"))
        }
        if let data = try? Data(contentsOf: settingsURL),
           let saved = try? decoder.decode(SavedSettings.self, from: data) {
            photos = saved.photos
            streamURL = saved.streamURL
            if let filename = saved.modelFilename {
                let url = dataDirectory.appendingPathComponent(filename)
                if FileManager.default.fileExists(atPath: url.path) { modelURL = url }
            }
        }
        stalenessTimer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in self?.checkStaleness() }
        }
    }

    func photoURL(_ photo: PetPhoto) -> URL {
        dataDirectory.appendingPathComponent(photo.filename)
    }

    func addPhotos(_ urls: [URL], angle: PhotoAngle) {
        for url in urls {
            let accessed = url.startAccessingSecurityScopedResource()
            defer { if accessed { url.stopAccessingSecurityScopedResource() } }
            do {
                guard NSImage(contentsOf: url) != nil else { throw DeskPetError.invalidImage }
                let ext = url.pathExtension.isEmpty ? "jpg" : url.pathExtension.lowercased()
                let filename = "photo-\(UUID().uuidString).\(ext)"
                try FileManager.default.copyItem(at: url, to: dataDirectory.appendingPathComponent(filename))
                photos.append(PetPhoto(id: UUID(), angle: angle, filename: filename, addedAt: Date()))
            } catch {
                errorMessage = "无法导入 \(url.lastPathComponent)：\(error.localizedDescription)"
            }
        }
        save()
    }

    func removePhoto(_ photo: PetPhoto) {
        try? FileManager.default.removeItem(at: photoURL(photo))
        photos.removeAll { $0.id == photo.id }
        save()
    }

    func importModel(_ url: URL) {
        let accessed = url.startAccessingSecurityScopedResource()
        defer { if accessed { url.stopAccessingSecurityScopedResource() } }
        do {
            let destination = dataDirectory.appendingPathComponent("pet-model.usdz")
            if FileManager.default.fileExists(atPath: destination.path) {
                try FileManager.default.removeItem(at: destination)
            }
            try FileManager.default.copyItem(at: url, to: destination)
            modelURL = destination
            save()
        } catch {
            errorMessage = "无法导入模型：\(error.localizedDescription)"
        }
    }

    func useDemoModel() {
        modelURL = nil
        save()
    }

    func simulate(_ state: PetBehavior) {
        accept(state: state, source: "演示模式", at: Date())
    }

    func connect() {
        guard let url = URL(string: streamURL), ["wss", "ws"].contains(url.scheme?.lowercased() ?? "") else {
            errorMessage = "请输入 ws:// 或 wss:// 开头的事件地址。"
            return
        }
        disconnect()
        save()
        connectionStatus = "连接中"
        let client = PetEventStream()
        client.onEvent = { [weak self] event in
            Task { @MainActor [weak self] in
                guard let self else { return }
                if let confidence = event.confidence, confidence < 0.6 { return }
                self.accept(state: event.state, source: "实时设备", at: Date())
            }
        }
        client.onStatus = { [weak self] status in
            Task { @MainActor [weak self] in self?.connectionStatus = status }
        }
        stream = client
        client.connect(to: url)
    }

    func disconnect() {
        stream?.disconnect()
        stream = nil
        connectionStatus = "未连接"
        if eventSource == "实时设备" { behavior = .unknown }
    }

    private func accept(state: PetBehavior, source: String, at date: Date) {
        behavior = state
        eventSource = source
        lastEventAt = date
    }

    private func checkStaleness() {
        guard eventSource == "实时设备", let lastEventAt else { return }
        if Date().timeIntervalSince(lastEventAt) > 15 { behavior = .unknown }
    }

    private func save() {
        let saved = SavedSettings(photos: photos,
                                  modelFilename: modelURL?.lastPathComponent,
                                  streamURL: streamURL)
        do {
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            try encoder.encode(saved).write(to: settingsURL, options: .atomic)
        }
        catch { errorMessage = "保存设置失败：\(error.localizedDescription)" }
    }
}

private enum DeskPetError: LocalizedError {
    case invalidImage
    var errorDescription: String? { "文件不是可读取的图片" }
}
