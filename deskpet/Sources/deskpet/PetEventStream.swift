import Foundation

final class PetEventStream {
    var onEvent: ((PetEvent) -> Void)?
    var onStatus: ((String) -> Void)?
    private var task: URLSessionWebSocketTask?
    private let decoder: JSONDecoder = {
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
        return decoder
    }()

    func connect(to url: URL) {
        task = URLSession.shared.webSocketTask(with: url)
        task?.resume()
        onStatus?("连接中，等待事件")
        receive()
    }

    func disconnect() {
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
    }

    private func receive() {
        task?.receive { [weak self] result in
            guard let self, self.task != nil else { return }
            switch result {
            case .success(let message):
                let data: Data
                switch message {
                case .string(let text): data = Data(text.utf8)
                case .data(let bytes): data = bytes
                @unknown default: self.receive(); return
                }
                if let event = try? self.decoder.decode(PetEvent.self, from: data) {
                    self.onEvent?(event)
                    self.onStatus?("已连接，接收事件中")
                } else {
                    self.onStatus?("事件格式错误，请检查网关 JSON")
                }
                self.receive()
            case .failure(let error):
                self.onStatus?("连接中断：\(error.localizedDescription)")
                self.task = nil
            }
        }
    }
}
