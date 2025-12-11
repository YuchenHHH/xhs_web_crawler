✅ 已加载环境变量: /Users/huangyuchen/Documents/workspace/web control/xhs_crawler_agent/.env

============================================================
🤖 小红书爬虫 Agent 启动
============================================================

📁 输出目录: /Users/huangyuchen/Documents/workspace/web control/xhs_crawler_agent/output/番茄炒蛋_20251211_153753
📋 初始配置:
   - 搜索关键词: 番茄炒蛋
   - 内容描述: 挑选其中 与菜肴相关的内容
   - 每轮点击数: 20
   - 执行轮次: 10
   - 图片浏览次数: 每个笔记按20次右键
   - Cookie 文件: 不存在


============================================================
📍 [Node 1/3] 初始化浏览器并访问首页
============================================================
🚀 [BrowserManager] 正在启动浏览器...
   - [Stealth] 已注入反爬虫 JS
   - [Cookie] 已加载 13 条 Cookie
✅ [BrowserManager] 浏览器启动成功
🌐 正在访问: https://www.xiaohongshu.com/explore

🧹 正在清理资源...
🛑 [BrowserManager] 正在关闭浏览器...
⚠️  [BrowserManager] 关闭时出现异常: BrowserContext.close: Target page, context or browser has been closed
Browser logs:

<launching> /Users/huangyuchen/Library/Caches/ms-playwright/chromium-1194/chrome-mac/Chromium.app/Contents/MacOS/Chromium --disable-field-trial-config --disable-background-networking --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-back-forward-cache --disable-breakpad --disable-client-side-phishing-detection --disable-component-extensions-with-background-pages --disable-component-update --no-default-browser-check --disable-default-apps --disable-dev-shm-usage --disable-extensions --disable-features=AcceptCHFrame,AvoidUnnecessaryBeforeUnloadCheckSync,DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,Translate,AutoDeElevate,RenderDocument --enable-features=CDPScreenshotNewSurface --allow-pre-commit-input --disable-hang-monitor --disable-ipc-flooding-protection --disable-popup-blocking --disable-prompt-on-repost --disable-renderer-backgrounding --force-color-profile=srgb --metrics-recording-only --no-first-run --password-store=basic --use-mock-keychain --no-service-autorun --export-tagged-pdf --disable-search-engine-choice-screen --unsafely-disable-devtools-self-xss-warnings --edge-skip-compat-layer-relaunch --enable-automation --enable-unsafe-swiftshader --no-sandbox --user-data-dir=/var/folders/vq/4g0n436j1vgdnw8wc8hflz000000gp/T/playwright_chromiumdev_profile-lGONDw --remote-debugging-pipe --no-startup-window
<launched> pid=9170
[pid=9170][err] [9170:16073786:1211/153753.682456:ERROR:net/cert/internal/trust_store_mac.cc:807] Error parsing certificate:
[pid=9170][err] ERROR: Failed parsing extensions
[pid=9170][err] 
[pid=9170][err] 2025-12-11 15:37:54.138 Chromium[9170:16073686] TSM AdjustCapsLockLEDForKeyTransitionHandling - _ISSetPhysicalKeyboardCapsLockLED Inhibit
[pid=9170][err] [9200:16074053:1211/153755.275708:ERROR:sandbox/mac/system_services.cc:31] SetApplicationIsDaemon: Error Domain=NSOSStatusErrorDomain Code=-50 "paramErr: error in user parameter list" (-50)
[pid=9170] <gracefully close start>

============================================================
✅ 程序执行完毕
============================================================

