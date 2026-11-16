import SwiftUI

struct Sample: Decodable { let hashrate: Double; let sampledUnix: Int }
struct Worker: Decodable, Identifiable {
    let workerId: String; let workerName: String?; let walletAddress: String
    let hashrate5m: Double; let hashrate24h: Double; let shares24h: Int; let lastShareUnix: Int; let history: [Sample]
    var id: String { workerId }
}
struct WorkFeed: Decodable { let available: Bool; let observedUnix: Int; let workers: [Worker] }
struct Credit: Decodable { let walletAddress: String; let earnedAllZats: Int64 }
struct CreditFeed: Decodable { let available: Bool; let observedUnix: Int; let wallets: [Credit] }
struct PriceFeed: Decodable { let available: Bool; let price: Double; let sampleTime: Double }

@MainActor final class MonitorStore: ObservableObject {
    @Published var wallet = UserDefaults.standard.string(forKey: "publicWallet") ?? ""
    @Published var workers: [Worker] = []; @Published var credit: Double?; @Published var price: Double?
    @Published var status = "Add your public ZEC wallet to monitor recorded work."
    @Published var loading = false; @Published var workAvailable = false
    private let allowed = ["/api/mining/public-work", "/api/mining/earned-credits", "/api/prices/zec?range=1m"]
    private func read<T: Decodable>(_ path: String, as: T.Type) async throws -> T {
        guard allowed.contains(path), let url = URL(string: "https://pointsixpool.com" + path) else { throw URLError(.badURL) }
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 12)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let config = URLSessionConfiguration.ephemeral; config.timeoutIntervalForRequest = 12; config.timeoutIntervalForResource = 15
        let (data, response) = try await URLSession(configuration: config).data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200,
              response.url?.scheme == "https", response.url?.host == "pointsixpool.com", data.count <= 4_194_304 else { throw URLError(.badServerResponse) }
        let decoder = JSONDecoder(); decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(T.self, from: data)
    }
    func refresh() async {
        guard !loading else { return }
        let address = wallet.trimmingCharacters(in: .whitespacesAndNewlines)
        guard address.range(of: "^t[13][1-9A-HJ-NP-Za-km-z]{33}$", options: .regularExpression) != nil else {
            workAvailable = false; workers = []; credit = nil; price = nil; status = "Enter your public ZEC t1/t3 receiving address."; return
        }
        loading = true; defer { loading = false }; UserDefaults.standard.set(address, forKey: "publicWallet")
        do {
            let feed: WorkFeed = try await read(allowed[0], as: WorkFeed.self)
            let age = Date().timeIntervalSince1970 - Double(feed.observedUnix)
            guard feed.available, age >= -5, age <= 90, feed.workers.count <= 500 else { throw URLError(.cannotParseResponse) }
            workAvailable = true; workers = feed.workers.filter { $0.walletAddress == address && $0.hashrate5m.isFinite && $0.hashrate5m >= 0 && $0.history.count <= 144 }
            status = "Updated " + Date(timeIntervalSince1970: Double(feed.observedUnix)).formatted(date: .omitted, time: .standard)
        } catch { workAvailable = false; workers = []; status = "Work feed awaiting update. Pull down to retry." }
        do {
            let feed: CreditFeed = try await read(allowed[1], as: CreditFeed.self)
            let age = Date().timeIntervalSince1970 - Double(feed.observedUnix)
            guard feed.available, age >= -5, age <= 90 else { throw URLError(.cannotParseResponse) }
            if let found = feed.wallets.first(where: { $0.walletAddress == address }), found.earnedAllZats >= 0, found.earnedAllZats <= 2_100_000_000_000_000 { credit = Double(found.earnedAllZats) / 100_000_000 } else { credit = nil }
        } catch { credit = nil }
        do {
            let quote: PriceFeed = try await read(allowed[2], as: PriceFeed.self)
            let age = Date().timeIntervalSince1970 - quote.sampleTime
            price = quote.available && quote.price.isFinite && quote.price > 0 && age >= -5 && age <= 900 ? quote.price : nil
        } catch { price = nil }
    }
}

struct HistoryGraph: View {
    let samples: [Sample]
    var body: some View {
        let points = samples.filter { $0.hashrate.isFinite && $0.hashrate >= 0 && Double($0.sampledUnix) <= Date().timeIntervalSince1970 - 600 }.sorted { $0.sampledUnix < $1.sampledUnix }
        if points.count < 2 { Text("Awaiting recorded history").font(.caption).foregroundStyle(.secondary) }
        else { GeometryReader { geometry in
            let first = points.first!.sampledUnix; let duration = max(1, points.last!.sampledUnix - first)
            let peak = max(1, points.map(\.hashrate).max() ?? 1)
            Path { path in
                for (index, sample) in points.enumerated() {
                    let point = CGPoint(x: Double(sample.sampledUnix-first)/Double(duration)*geometry.size.width, y: (1-sample.hashrate/peak)*geometry.size.height)
                    if index == 0 || sample.sampledUnix-points[index-1].sampledUnix > 600 { path.move(to: point) } else { path.addLine(to: point) }
                }
            }.stroke(.mint, style: StrokeStyle(lineWidth: 2, lineJoin: .round))
        }.frame(height: 96).accessibilityLabel("Recorded worker hashrate") }
    }
}
@main struct MonitorApp: App {
    @StateObject private var store = MonitorStore()
    @State private var selectedTab = 0
    @Environment(\.openURL) private var openURL
    @Environment(\.scenePhase) private var phase
    var body: some Scene { WindowGroup {
        TabView(selection: $selectedTab) {
            NavigationStack { List {
                Section("Public wallet") { TextField("ZEC t1/t3 address", text: $store.wallet).textInputAutocapitalization(.never).autocorrectionDisabled(); Button("Monitor") { Task { await store.refresh() } }.disabled(store.loading) }
                Section("Mining credits · all time") {
                    Text(store.credit.map { String(format: "%.8f ZEC", $0) } ?? "Awaiting verified credits").font(.title2.monospacedDigit())
                    if let credit = store.credit, let price = store.price { Text((credit*price).formatted(.currency(code: "USD"))).foregroundStyle(.mint) }
                    Text("Recorded wallet credits, not a withdrawable account balance. USD is a current valuation.").font(.caption).foregroundStyle(.secondary)
                }
                Section { LabeledContent("Workers", value: store.workAvailable ? String(store.workers.count) : "Awaiting update"); LabeledContent("Hashrate · 5m", value: store.workAvailable ? String(format: "%.2f Sol/s", store.workers.reduce(0) { $0+$1.hashrate5m }) : "Awaiting update"); Text(store.status).font(.caption) }
            }.navigationTitle("PointSixPool").refreshable { await store.refresh() } }.tabItem { Label("Income", systemImage: "chart.line.uptrend.xyaxis") }.tag(0)
            NavigationStack { List(store.workers) { worker in NavigationLink {
                List { Text(worker.workerName ?? ("Worker " + String(worker.workerId.prefix(8)))).font(.title2); LabeledContent("5 min", value: String(format: "%.2f Sol/s", worker.hashrate5m)); LabeledContent("24 hours", value: String(format: "%.2f Sol/s", worker.hashrate24h)); HistoryGraph(samples: worker.history); Text("Last accepted share: " + Date(timeIntervalSince1970: Double(worker.lastShareUnix)).formatted()) }
            } label: { HStack { Circle().fill(Date().timeIntervalSince1970-Double(worker.lastShareUnix)<600 ? .green : .red).frame(width: 8,height: 8); VStack(alignment: .leading) { Text(worker.workerName ?? ("Worker " + String(worker.workerId.prefix(8)))); Text(String(format: "%.2f Sol/s",worker.hashrate5m)).font(.caption.monospacedDigit()) } } } }.navigationTitle("Workers").refreshable { await store.refresh() } }.tabItem { Label("Workers",systemImage: "fanblades") }.tag(1)
            Color.clear.tabItem { Label("Account",systemImage: "person.crop.circle") }.tag(2)
        }.onChange(of: selectedTab) { value in if value == 2 { selectedTab = 0; openURL(URL(string: "https://pointsixpool.com/mobile/")!) } }.tint(.orange).preferredColorScheme(.dark).onReceive(Timer.publish(every: 30, on: .main, in: .common).autoconnect()) { _ in if phase == .active { Task { await store.refresh() } } }.task { await store.refresh() }.onChange(of: phase) { value in if value == .active { Task { await store.refresh() } } }
    } }
}
