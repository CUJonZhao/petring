import AppKit
import SceneKit
import SwiftUI

struct PetSceneView: NSViewRepresentable {
    let behavior: PetBehavior
    let modelURL: URL?

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeNSView(context: Context) -> SCNView {
        let view = SCNView()
        view.backgroundColor = .clear
        view.allowsCameraControl = false
        view.autoenablesDefaultLighting = false
        view.rendersContinuously = true
        context.coordinator.load(into: view, modelURL: modelURL)
        context.coordinator.animate(behavior)
        return view
    }

    func updateNSView(_ view: SCNView, context: Context) {
        if context.coordinator.loadedModelURL != modelURL {
            context.coordinator.load(into: view, modelURL: modelURL)
        }
        context.coordinator.animate(behavior)
    }

    final class Coordinator {
        var loadedModelURL: URL?
        private var lastBehavior: PetBehavior?
        private var actor = SCNNode()
        private var head: SCNNode?
        private var tail: SCNNode?
        private var tongue: SCNNode?
        private var waterBowl: SCNNode?
        private var waterRipple: SCNNode?
        private var legs: [SCNNode] = []
        private var legStandingPositions: [SCNVector3] = []
        private var openEyes: [SCNNode] = []
        private var closedEyes: [SCNNode] = []
        private var rigged = false
        private var rigKnees: [SCNNode] = []
        private var rigJaw: SCNNode?

        func load(into view: SCNView, modelURL: URL?) {
            loadedModelURL = modelURL
            lastBehavior = nil
            head = nil
            tail = nil
            tongue = nil
            waterBowl = nil
            waterRipple = nil
            legs = []
            legStandingPositions = []
            openEyes = []
            closedEyes = []
            rigged = false
            rigKnees = []
            rigJaw = nil
            let scene = SCNScene()
            scene.background.contents = NSColor.clear
            actor = SCNNode()
            actor.name = "pet"
            scene.rootNode.addChildNode(actor)
            if let modelURL, let model = try? SCNScene(url: modelURL, options: nil) {
                for child in model.rootNode.childNodes { actor.addChildNode(child.clone()) }
                actor.scale = SCNVector3(0.8, 0.8, 0.8)
            } else if let bundledURL = Bundle.main.url(forResource: "Delta", withExtension: "usdz"),
                      let model = try? SCNScene(url: bundledURL, options: nil) {
                let wrapper = SCNNode()
                wrapper.name = "delta_coordinate_conversion"
                wrapper.eulerAngles.x = -.pi / 2
                for child in model.rootNode.childNodes { wrapper.addChildNode(child.clone()) }
                actor.addChildNode(wrapper)
                actor.scale = SCNVector3(0.83, 0.83, 0.83)
                bindDeltaRig()
            } else {
                buildDemoDog(in: actor)
            }
            buildWaterBowl(in: scene.rootNode)
            let cameraNode = SCNNode()
            cameraNode.camera = SCNCamera()
            cameraNode.camera?.fieldOfView = 38
            cameraNode.position = SCNVector3(2.15, 1.65, 4.15)
            cameraNode.look(at: SCNVector3(0, 0.52, 0))
            scene.rootNode.addChildNode(cameraNode)
            let ambient = SCNNode()
            ambient.light = SCNLight()
            ambient.light?.type = .ambient
            ambient.light?.intensity = 400
            scene.rootNode.addChildNode(ambient)
            let key = SCNNode()
            key.light = SCNLight()
            key.light?.type = .omni
            key.light?.intensity = 620
            key.position = SCNVector3(-3, 5, 5)
            scene.rootNode.addChildNode(key)
            view.scene = scene
            view.pointOfView = cameraNode
        }

        func animate(_ behavior: PetBehavior) {
            guard behavior != lastBehavior else { return }
            lastBehavior = behavior
            if rigged {
                animateDelta(behavior)
                return
            }
            actor.removeAllActions()
            head?.removeAllActions()
            tail?.removeAllActions()
            tongue?.removeAllActions()
            waterBowl?.removeAllActions()
            waterRipple?.removeAllActions()
            for leg in legs { leg.removeAllActions() }
            for eye in openEyes + closedEyes { eye.removeAllActions() }
            SCNTransaction.begin()
            SCNTransaction.animationDuration = behavior == .rest || behavior == .drink ? 0 : 0.3
            actor.position = SCNVector3(0, 0, 0)
            actor.eulerAngles = SCNVector3(0, 0, 0)
            head?.position = SCNVector3(0, 1.08, 0.69)
            head?.eulerAngles.x = 0
            tail?.eulerAngles = SCNVector3(-0.85, 0, 0)
            tongue?.position = SCNVector3(0, -0.13, 0.80)
            tongue?.opacity = 0
            waterBowl?.opacity = 0
            waterRipple?.opacity = 0
            waterRipple?.scale = SCNVector3(0.45, 0.45, 0.45)
            for (index, leg) in legs.enumerated() {
                leg.position = legStandingPositions[index]
                leg.eulerAngles.x = 0
            }
            for eye in openEyes { eye.opacity = 1 }
            for eye in closedEyes { eye.opacity = 0 }
            SCNTransaction.commit()

            let tailWag = SCNAction.sequence([.rotateBy(x: 0, y: 0.28, z: 0, duration: 0.24),
                                              .rotateBy(x: 0, y: -0.56, z: 0, duration: 0.48),
                                              .rotateBy(x: 0, y: 0.28, z: 0, duration: 0.24)])
            switch behavior {
            case .walk:
                actor.runAction(.repeatForever(.sequence([.moveBy(x: 0, y: 0.07, z: 0, duration: 0.22),
                                                           .moveBy(x: 0, y: -0.07, z: 0, duration: 0.22)])))
                for (index, leg) in legs.enumerated() {
                    let sign: CGFloat = index.isMultiple(of: 2) ? 1 : -1
                    leg.runAction(.repeatForever(.sequence([.rotateBy(x: 0.32 * sign, y: 0, z: 0, duration: 0.22),
                                                            .rotateBy(x: -0.64 * sign, y: 0, z: 0, duration: 0.44),
                                                            .rotateBy(x: 0.32 * sign, y: 0, z: 0, duration: 0.22)])))
                }
                tail?.runAction(.repeatForever(tailWag))
            case .drink:
                let approachDuration = 1.2
                let lowerDuration = 0.55
                waterBowl?.runAction(.fadeIn(duration: 0.28), forKey: "showBowl")
                actor.runAction(.group([
                    .move(to: SCNVector3(0.54, 0, 0.08), duration: approachDuration),
                    .rotateTo(x: 0, y: 0.28, z: 0, duration: approachDuration)
                ]), forKey: "approachBowl")
                for (index, leg) in legs.enumerated() {
                    let sign: CGFloat = index.isMultiple(of: 2) ? 1 : -1
                    let step = SCNAction.sequence([
                        .rotateBy(x: 0.29 * sign, y: 0, z: 0, duration: 0.15),
                        .rotateBy(x: -0.58 * sign, y: 0, z: 0, duration: 0.30),
                        .rotateBy(x: 0.29 * sign, y: 0, z: 0, duration: 0.15)
                    ])
                    leg.runAction(.sequence([.repeat(step, count: 2),
                                             .rotateTo(x: 0, y: 0, z: 0, duration: 0.12)]),
                                  forKey: "walkToBowl")
                }
                tail?.runAction(.repeat(tailWag, count: 1), forKey: "approachTail")
                let sip = SCNAction.repeatForever(.sequence([
                    .rotateTo(x: 0.43, y: 0, z: 0, duration: 0.18),
                    .rotateTo(x: 0.38, y: 0, z: 0, duration: 0.18)
                ]))
                head?.runAction(.sequence([
                    .wait(duration: approachDuration),
                    .group([
                        .move(to: SCNVector3(0, 0.70, 0.78), duration: lowerDuration),
                        .rotateTo(x: 0.40, y: 0, z: 0, duration: lowerDuration)
                    ]),
                    sip
                ]), forKey: "sipWater")
                let lick = SCNAction.repeatForever(.sequence([
                    .moveBy(x: 0, y: -0.07, z: 0, duration: 0.18),
                    .moveBy(x: 0, y: 0.07, z: 0, duration: 0.18)
                ]))
                tongue?.runAction(.sequence([
                    .wait(duration: approachDuration + lowerDuration),
                    .fadeIn(duration: 0.12),
                    lick
                ]), forKey: "lickWater")
                let ripple = SCNAction.repeatForever(.sequence([
                    .group([.fadeIn(duration: 0.10), .scale(to: 1, duration: 0.42)]),
                    .fadeOut(duration: 0.30),
                    .scale(to: 0.45, duration: 0)
                ]))
                waterRipple?.runAction(.sequence([
                    .wait(duration: approachDuration + lowerDuration), ripple
                ]), forKey: "waterRipples")
            case .bark:
                let target = head ?? actor
                target.runAction(.repeatForever(.sequence([.rotateTo(x: 0.18, y: 0, z: 0, duration: 0.13),
                                                            .rotateTo(x: 0, y: 0, z: 0, duration: 0.18),
                                                            .wait(duration: 0.35)])))
            case .rest:
                let turnDuration = 1.35
                let lieDuration = 0.65
                let turn = SCNAction.rotateBy(x: 0, y: 2 * .pi, z: 0, duration: turnDuration)
                turn.timingMode = .easeInEaseOut
                let lieDown = SCNAction.group([
                    .move(to: SCNVector3(0, -0.35, 0.1), duration: lieDuration),
                    .rotateTo(x: 0.08, y: 0.32, z: 0, duration: lieDuration)
                ])
                lieDown.timingMode = .easeInEaseOut
                let breathe = SCNAction.repeatForever(.sequence([
                    .moveBy(x: 0, y: 0.015, z: 0, duration: 1.4),
                    .moveBy(x: 0, y: -0.015, z: 0, duration: 1.4)
                ]))
                actor.runAction(.sequence([turn, lieDown, breathe]), forKey: "lieDown")
                head?.runAction(.sequence([
                    .wait(duration: turnDuration),
                    .group([
                        .move(to: SCNVector3(0, 0.72, 0.80), duration: lieDuration),
                        .rotateTo(x: 0.25, y: 0, z: 0, duration: lieDuration)
                    ])
                ]), forKey: "restHead")
                for (index, leg) in legs.enumerated() {
                    let start = legStandingPositions[index]
                    let target = SCNVector3(start.x, 0.46, start.z + (start.z > 0 ? 0.26 : -0.08))
                    leg.runAction(.sequence([
                        .wait(duration: turnDuration),
                        .group([
                            .move(to: target, duration: lieDuration),
                            .rotateTo(x: start.z > 0 ? -1.05 : 1.15, y: 0, z: 0,
                                      duration: lieDuration)
                        ])
                    ]), forKey: "foldLeg")
                }
                for eye in openEyes {
                    eye.runAction(.sequence([.wait(duration: turnDuration + 0.38),
                                              .fadeOut(duration: 0.22)]), forKey: "closeEye")
                }
                for eye in closedEyes {
                    eye.runAction(.sequence([.wait(duration: turnDuration + 0.38),
                                              .fadeIn(duration: 0.22)]), forKey: "showClosedEye")
                }
            case .idle:
                tail?.runAction(.repeatForever(tailWag))
            case .unknown: break
            }
        }

        private func bindDeltaRig() {
            func named(_ name: String) -> SCNNode? {
                actor.childNode(withName: name, recursively: true)
            }
            head = named("delta_head")
            tail = named("delta_tail")
            tongue = named("delta_tongue")
            rigJaw = named("delta_jaw")
            let tags = ["fl", "fr", "hl", "hr"]
            legs = tags.compactMap { named("delta_leg_\($0)") }
            rigKnees = tags.compactMap { named("delta_knee_\($0)") }
            legStandingPositions = legs.map(\.position)
            openEyes = ["left", "right"].compactMap { named("delta_eye_\($0)") }
            closedEyes = ["left", "right"].compactMap { named("delta_closed_eye_\($0)") }
            for eye in closedEyes { eye.opacity = 0 }
            tongue?.opacity = 0
            rigged = head != nil && tail != nil && legs.count == 4 && rigKnees.count == 4
        }

        private func animateDelta(_ behavior: PetBehavior) {
            let all = [actor, head, tail, tongue, rigJaw, waterBowl, waterRipple]
                .compactMap { $0 } + legs + rigKnees + openEyes + closedEyes
            for node in all { node.removeAllActions() }
            SCNTransaction.begin()
            SCNTransaction.animationDuration = 0.22
            actor.position = SCNVector3Zero
            actor.eulerAngles = SCNVector3Zero
            head?.position = SCNVector3(0, -1.06, 1.42)
            head?.eulerAngles = SCNVector3Zero
            tail?.eulerAngles = SCNVector3Zero
            rigJaw?.eulerAngles = SCNVector3Zero
            tongue?.position = SCNVector3(0, -0.57, -0.28)
            tongue?.opacity = 0
            waterBowl?.opacity = 0
            waterRipple?.opacity = 0
            waterRipple?.scale = SCNVector3(0.45, 0.45, 0.45)
            for (index, leg) in legs.enumerated() {
                leg.position = legStandingPositions[index]
                leg.eulerAngles = SCNVector3Zero
            }
            for knee in rigKnees { knee.eulerAngles = SCNVector3Zero }
            for eye in openEyes { eye.opacity = 1 }
            for eye in closedEyes { eye.opacity = 0 }
            SCNTransaction.commit()

            let wag = SCNAction.repeatForever(.sequence([
                .rotateTo(x: 0, y: 0, z: 0.30, duration: 0.28),
                .rotateTo(x: 0, y: 0, z: -0.30, duration: 0.56),
                .rotateTo(x: 0, y: 0, z: 0, duration: 0.28)
            ]))
            switch behavior {
            case .idle:
                tail?.runAction(wag, forKey: "wag")
                actor.runAction(.repeatForever(.sequence([
                    .moveBy(x: 0, y: 0.010, z: 0, duration: 1.3),
                    .moveBy(x: 0, y: -0.010, z: 0, duration: 1.3)
                ])), forKey: "breathe")
            case .walk:
                startGait(cycles: nil)
                tail?.runAction(wag, forKey: "wag")
            case .rest:
                let turn = SCNAction.rotateBy(x: 0, y: 2 * .pi, z: 0, duration: 1.25)
                turn.timingMode = .easeInEaseOut
                let settle = SCNAction.group([
                    .move(to: SCNVector3(0, -0.50, 0.08), duration: 0.72),
                    .rotateTo(x: 0.10, y: 0.20, z: 0, duration: 0.72)
                ])
                settle.timingMode = .easeInEaseOut
                actor.runAction(.sequence([turn, settle, .repeatForever(.sequence([
                    .moveBy(x: 0, y: 0.012, z: 0, duration: 1.45),
                    .moveBy(x: 0, y: -0.012, z: 0, duration: 1.45)
                ]))]), forKey: "rest")
                for (index, leg) in legs.enumerated() {
                    let stance = legStandingPositions[index]
                    let target = SCNVector3(stance.x,
                                            stance.y + (index < 2 ? -0.20 : -0.08),
                                            stance.z)
                    leg.runAction(.sequence([.wait(duration: 1.25),
                        .group([.rotateTo(x: index < 2 ? -1.18 : 1.30, y: 0, z: 0,
                                          duration: 0.72),
                                .move(to: target, duration: 0.72)])]), forKey: "fold")
                }
                for (index, knee) in rigKnees.enumerated() {
                    knee.runAction(.sequence([.wait(duration: 1.25),
                        .rotateTo(x: index < 2 ? 0.40 : -1.48, y: 0, z: 0,
                                  duration: 0.72)]), forKey: "bend")
                }
                head?.runAction(.sequence([.wait(duration: 1.25),
                    .group([.move(to: SCNVector3(0, -1.10, 1.10), duration: 0.72),
                            .rotateTo(x: 0.14, y: 0, z: 0, duration: 0.72)])]),
                                forKey: "restHead")
                for eye in openEyes { eye.runAction(.sequence([
                    .wait(duration: 1.87), .fadeOut(duration: 0.25)])) }
                for eye in closedEyes { eye.runAction(.sequence([
                    .wait(duration: 1.87), .fadeIn(duration: 0.25)])) }
            case .drink:
                let approach = 1.3
                let lower = 0.65
                waterBowl?.runAction(.fadeIn(duration: 0.25), forKey: "showBowl")
                actor.runAction(.group([
                    .move(to: SCNVector3(0.45, 0, 0.03), duration: approach),
                    .rotateTo(x: 0, y: 0.20, z: 0, duration: approach)
                ]), forKey: "approach")
                startGait(cycles: 2)
                head?.runAction(.sequence([.wait(duration: approach),
                    .group([.move(to: SCNVector3(0, -1.06, 0.88), duration: lower),
                            .rotateTo(x: 0.58, y: 0, z: 0, duration: lower)]),
                    .repeatForever(.sequence([
                        .rotateTo(x: 0.61, y: 0, z: 0, duration: 0.18),
                        .rotateTo(x: 0.55, y: 0, z: 0, duration: 0.18)
                    ]))]), forKey: "lapHead")
                tongue?.runAction(.sequence([.wait(duration: approach + lower),
                    .fadeIn(duration: 0.10), .repeatForever(.sequence([
                        .moveBy(x: 0, y: -0.05, z: -0.045, duration: 0.17),
                        .moveBy(x: 0, y: 0.05, z: 0.045, duration: 0.17)
                    ]))]), forKey: "lapTongue")
                waterRipple?.runAction(.sequence([
                    .wait(duration: approach + lower),
                    .repeatForever(.sequence([
                        .group([.fadeIn(duration: 0.1), .scale(to: 1, duration: 0.4)]),
                        .fadeOut(duration: 0.28), .scale(to: 0.45, duration: 0)
                    ]))]), forKey: "ripple")
            case .bark:
                head?.runAction(.repeatForever(.sequence([
                    .rotateTo(x: -0.17, y: 0, z: 0, duration: 0.14),
                    .rotateTo(x: 0, y: 0, z: 0, duration: 0.20),
                    .wait(duration: 0.38)
                ])), forKey: "barkHead")
                rigJaw?.runAction(.repeatForever(.sequence([
                    .rotateTo(x: -0.36, y: 0, z: 0, duration: 0.12),
                    .rotateTo(x: 0, y: 0, z: 0, duration: 0.19),
                    .wait(duration: 0.41)
                ])), forKey: "barkJaw")
            case .unknown: break
            }
        }

        private func startGait(cycles: Int?) {
            let stepDuration = 0.58
            for (index, leg) in legs.enumerated() {
                let phase = (index == 0 || index == 3) ? 0.0 : stepDuration / 2
                let step = SCNAction.sequence([
                    .rotateTo(x: -0.34, y: 0, z: 0, duration: stepDuration / 4),
                    .rotateTo(x: 0.34, y: 0, z: 0, duration: stepDuration / 2),
                    .rotateTo(x: 0, y: 0, z: 0, duration: stepDuration / 4)
                ])
                let motion = cycles.map { SCNAction.repeat(step, count: $0) }
                    ?? SCNAction.repeatForever(step)
                leg.runAction(.sequence([.wait(duration: phase), motion]), forKey: "gait")
            }
            for (index, knee) in rigKnees.enumerated() {
                let phase = (index == 0 || index == 3) ? 0.0 : stepDuration / 2
                let bend = SCNAction.sequence([
                    .rotateTo(x: index < 2 ? 0.38 : -0.38, y: 0, z: 0,
                              duration: stepDuration / 3),
                    .rotateTo(x: 0, y: 0, z: 0, duration: stepDuration * 2 / 3)
                ])
                let motion = cycles.map { SCNAction.repeat(bend, count: $0) }
                    ?? SCNAction.repeatForever(bend)
                knee.runAction(.sequence([.wait(duration: phase), motion]), forKey: "gaitKnee")
            }
            if cycles == nil {
                actor.runAction(.repeatForever(.sequence([
                    .moveBy(x: 0, y: 0.045, z: 0, duration: stepDuration / 2),
                    .moveBy(x: 0, y: -0.045, z: 0, duration: stepDuration / 2)
                ])), forKey: "gaitBob")
            }
        }

        private func buildDemoDog(in root: SCNNode) {
            func part(_ geometry: SCNGeometry, color: NSColor, at position: SCNVector3,
                      scale: SCNVector3 = SCNVector3(1, 1, 1)) -> SCNNode {
                geometry.firstMaterial?.diffuse.contents = color
                geometry.firstMaterial?.lightingModel = .physicallyBased
                let node = SCNNode(geometry: geometry)
                node.position = position
                node.scale = scale
                root.addChildNode(node)
                return node
            }
            let white = NSColor(calibratedRed: 0.91, green: 0.93, blue: 0.92, alpha: 1)
            let silver = NSColor(calibratedRed: 0.57, green: 0.61, blue: 0.64, alpha: 1)
            let charcoal = NSColor(calibratedRed: 0.18, green: 0.21, blue: 0.24, alpha: 1)
            let dark = NSColor(calibratedRed: 0.09, green: 0.11, blue: 0.13, alpha: 1)
            _ = part(SCNSphere(radius: 0.7), color: silver,
                     at: SCNVector3(0, 0.8, 0), scale: SCNVector3(0.73, 0.63, 1.12))
            _ = part(SCNSphere(radius: 0.58), color: charcoal,
                     at: SCNVector3(0.08, 1.15, -0.21), scale: SCNVector3(0.76, 0.36, 1.07))
            _ = part(SCNSphere(radius: 0.50), color: white,
                     at: SCNVector3(0, 0.78, 0.56), scale: SCNVector3(0.94, 1.13, 0.65))
            for x: Float in [-0.39, 0.39] {
                _ = part(SCNSphere(radius: 0.20), color: white,
                         at: SCNVector3(x, 0.99, 0.55), scale: SCNVector3(0.65, 1.26, 0.78))
            }
            let headPivot = SCNNode()
            headPivot.position = SCNVector3(0, 1.08, 0.69)
            root.addChildNode(headPivot)
            head = headPivot
            func headPart(_ geometry: SCNGeometry, color: NSColor, at position: SCNVector3,
                          scale: SCNVector3 = SCNVector3(1, 1, 1)) {
                geometry.firstMaterial?.diffuse.contents = color
                let node = SCNNode(geometry: geometry)
                node.position = position
                node.scale = scale
                headPivot.addChildNode(node)
            }
            headPart(SCNSphere(radius: 0.43), color: silver, at: SCNVector3(0, 0.18, 0),
                     scale: SCNVector3(0.96, 0.92, 1.1))
            headPart(SCNSphere(radius: 0.27), color: charcoal,
                     at: SCNVector3(-0.22, 0.27, 0.23), scale: SCNVector3(0.78, 1.0, 0.42))
            headPart(SCNSphere(radius: 0.28), color: white,
                     at: SCNVector3(0, 0.12, 0.26), scale: SCNVector3(0.48, 1.23, 0.67))
            headPart(SCNSphere(radius: 0.27), color: white, at: SCNVector3(0, 0.02, 0.43),
                     scale: SCNVector3(0.97, 0.68, 1.45))
            headPart(SCNSphere(radius: 0.105), color: dark, at: SCNVector3(0, 0.08, 0.79))
            let tongueNode = SCNNode(geometry: SCNCapsule(capRadius: 0.047, height: 0.24))
            tongueNode.geometry?.firstMaterial?.diffuse.contents = NSColor(
                calibratedRed: 0.88, green: 0.28, blue: 0.39, alpha: 1)
            tongueNode.position = SCNVector3(0, -0.13, 0.80)
            tongueNode.opacity = 0
            headPivot.addChildNode(tongueNode)
            tongue = tongueNode
            for x: Float in [-0.19, 0.19] {
                let eyeColor = x < 0
                    ? NSColor(calibratedRed: 0.50, green: 0.70, blue: 0.78, alpha: 1)
                    : dark
                let eye = SCNNode(geometry: SCNSphere(radius: 0.062))
                eye.geometry?.firstMaterial?.diffuse.contents = eyeColor
                eye.position = SCNVector3(x, 0.29, 0.37)
                headPivot.addChildNode(eye)
                openEyes.append(eye)
                let closedEye = SCNNode(geometry: SCNCapsule(capRadius: 0.014, height: 0.14))
                closedEye.geometry?.firstMaterial?.diffuse.contents = dark
                closedEye.position = SCNVector3(x, 0.29, 0.43)
                closedEye.eulerAngles.z = .pi / 2
                closedEye.opacity = 0
                headPivot.addChildNode(closedEye)
                closedEyes.append(closedEye)
                let ear = SCNNode(geometry: SCNCone(topRadius: 0.015, bottomRadius: 0.19, height: 0.46))
                ear.geometry?.firstMaterial?.diffuse.contents = charcoal
                ear.position = SCNVector3(x * 1.65, 0.53, -0.05)
                ear.eulerAngles.z = x < 0 ? 0.2 : -0.2
                headPivot.addChildNode(ear)
            }
            for x: Float in [-0.34, 0.34] {
                for z: Float in [-0.52, 0.54] {
                    let leg = part(SCNCapsule(capRadius: 0.14, height: 0.62), color: white,
                                   at: SCNVector3(x, 0.39, z))
                    legs.append(leg)
                    legStandingPositions.append(leg.position)
                }
            }
            let tailNode = part(SCNCapsule(capRadius: 0.14, height: 0.62), color: silver,
                                at: SCNVector3(0, 1.04, -0.92))
            tailNode.eulerAngles.x = -0.85
            tail = tailNode
        }

        private func buildWaterBowl(in root: SCNNode) {
            let bowl = SCNNode()
            bowl.position = SCNVector3(0.85, 0, 1.45)
            bowl.opacity = 0
            root.addChildNode(bowl)
            waterBowl = bowl

            let base = SCNNode(geometry: SCNCylinder(radius: 0.29, height: 0.15))
            base.geometry?.firstMaterial?.diffuse.contents = NSColor(
                calibratedRed: 0.22, green: 0.49, blue: 0.72, alpha: 1)
            base.position.y = 0.08
            bowl.addChildNode(base)

            let water = SCNNode(geometry: SCNCylinder(radius: 0.235, height: 0.012))
            water.geometry?.firstMaterial?.diffuse.contents = NSColor(
                calibratedRed: 0.57, green: 0.84, blue: 0.95, alpha: 1)
            water.geometry?.firstMaterial?.specular.contents = NSColor.white
            water.position.y = 0.158
            bowl.addChildNode(water)

            let rim = SCNNode(geometry: SCNTorus(ringRadius: 0.27, pipeRadius: 0.045))
            rim.geometry?.firstMaterial?.diffuse.contents = NSColor(
                calibratedRed: 0.30, green: 0.63, blue: 0.84, alpha: 1)
            rim.position.y = 0.17
            bowl.addChildNode(rim)

            let ripple = SCNNode(geometry: SCNTorus(ringRadius: 0.10, pipeRadius: 0.009))
            ripple.geometry?.firstMaterial?.diffuse.contents = NSColor.white
            ripple.position.y = 0.178
            ripple.opacity = 0
            ripple.scale = SCNVector3(0.45, 0.45, 0.45)
            bowl.addChildNode(ripple)
            waterRipple = ripple
        }
    }
}
