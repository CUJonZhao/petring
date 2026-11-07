import AppKit
import SwiftUI
import UniformTypeIdentifiers

struct ControlView: View {
    @EnvironmentObject private var store: PetStore
    @State private var selectedAngle: PhotoAngle = .front

    private let columns = [GridItem(.adaptive(minimum: 110), spacing: 12)]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("DeskPet")
                            .font(.system(size: 32, weight: .bold, design: .rounded))
                        Text("让 Delta 的日常，在你的桌面陪伴你。")
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button("显示桌宠") { PetWindowController.shared.show(store: store) }
                }

                HStack(alignment: .top, spacing: 20) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("桌宠预览").font(.headline)
                        PetSceneView(behavior: store.behavior, modelURL: store.modelURL)
                            .frame(width: 250, height: 230)
                            .background(.quaternary.opacity(0.35), in: RoundedRectangle(cornerRadius: 16))
                        Label(store.behavior.title, systemImage: store.behavior.symbol)
                            .font(.subheadline.weight(.semibold))
                        Text(store.modelURL == nil ? "当前为 Delta 风格化 3D 模型" : "当前使用导入的 3D 模型")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    .frame(width: 260, alignment: .leading)

                    VStack(alignment: .leading, spacing: 14) {
                        Text("动作调试").font(.headline)
                        Text("先用模拟事件验证动画。接入设备后，动画将由实时事件驱动。")
                            .font(.subheadline).foregroundStyle(.secondary)
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                            ForEach(PetBehavior.allCases.filter { $0 != .unknown }) { state in
                                Button {
                                    store.simulate(state)
                                } label: {
                                    Label(state.title, systemImage: state.symbol)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                }
                                .buttonStyle(.bordered)
                            }
                            Button {
                                store.simulate(.unknown)
                            } label: {
                                Label("信号中断", systemImage: "wifi.slash")
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .buttonStyle(.bordered)
                        }
                        Divider()
                        Text("实时事件接口").font(.headline)
                        TextField("wss://你的服务地址/events", text: $store.streamURL)
                            .textFieldStyle(.roundedBorder)
                        HStack {
                            Button("连接") { store.connect() }
                                .buttonStyle(.borderedProminent)
                            Button("断开") { store.disconnect() }
                            Text(store.connectionStatus)
                                .font(.caption).foregroundStyle(.secondary)
                        }
                        Text("事件格式：{\"state\":\"walk\",\"confidence\":0.9}；支持 idle、rest、walk、drink、bark、unknown。设备消息超过 15 秒未更新时显示无法判断。")
                            .font(.caption).foregroundStyle(.secondary)
                            .textSelection(.enabled)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }

                Divider()

                VStack(alignment: .leading, spacing: 12) {
                    Text("Delta 的建模照片").font(.title3.weight(.semibold))
                    Text("按角度整理照片，作为后续生成写实 3D 模型的素材。照片只复制到这台 Mac 的应用数据目录。")
                        .font(.subheadline).foregroundStyle(.secondary)
                    Text("建模建议：自然光下平视拍摄，同一天的正面、左右侧面和背面全身照；尽量让狗狗站立、不要遮挡身体。")
                        .font(.caption).foregroundStyle(.secondary)
                    HStack {
                        Picker("拍摄角度", selection: $selectedAngle) {
                            ForEach(PhotoAngle.allCases) { angle in
                                Text(angle.title).tag(angle)
                            }
                        }
                        .frame(width: 185)
                        Button("添加照片") { pickPhotos() }
                            .buttonStyle(.borderedProminent)
                        Spacer()
                        Text("已导入 \(store.photos.count) 张")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    if store.photos.isEmpty {
                        ContentUnavailableView("还没有照片", systemImage: "photo.on.rectangle.angled",
                                               description: Text("建议先添加正面、左右侧面、背面和全身照片。"))
                            .frame(maxWidth: .infinity)
                    } else {
                        LazyVGrid(columns: columns, alignment: .leading, spacing: 12) {
                            ForEach(store.photos) { photo in
                                VStack(alignment: .leading, spacing: 6) {
                                    if let image = NSImage(contentsOf: store.photoURL(photo)) {
                                        Image(nsImage: image)
                                            .resizable().scaledToFill()
                                            .frame(width: 110, height: 100).clipped()
                                            .clipShape(RoundedRectangle(cornerRadius: 9))
                                    }
                                    HStack {
                                        Text(photo.angle.title).font(.caption.weight(.medium))
                                        Spacer()
                                        Button(role: .destructive) { store.removePhoto(photo) } label: {
                                            Image(systemName: "trash")
                                        }
                                        .buttonStyle(.plain)
                                    }
                                }
                                .frame(width: 110)
                            }
                        }
                    }
                }

                Divider()

                HStack(alignment: .top, spacing: 16) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("3D 模型").font(.title3.weight(.semibold))
                        Text("内置模型参考 Delta 的照片手工制作，包含独立的头、腿、尾和面部节点。它仍是风格化模型；可导入 USDZ 继续替换和精修。")
                            .font(.subheadline).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button("导入 USDZ") { pickModel() }
                    Button("使用内置 Delta 模型") { store.useDemoModel() }
                        .disabled(store.modelURL == nil)
                }
            }
            .padding(28)
        }
        .alert("DeskPet", isPresented: Binding(get: { store.errorMessage != nil },
                                               set: { if !$0 { store.errorMessage = nil } })) {
            Button("好") { store.errorMessage = nil }
        } message: {
            Text(store.errorMessage ?? "")
        }
    }

    private func pickPhotos() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.image]
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        if panel.runModal() == .OK { store.addPhotos(panel.urls, angle: selectedAngle) }
    }

    private func pickModel() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [UTType(filenameExtension: "usdz") ?? .data]
        panel.canChooseDirectories = false
        if panel.runModal() == .OK, let url = panel.url { store.importModel(url) }
    }
}
