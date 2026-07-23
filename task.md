# Tasks — Upgrade Phase I (Full Native Desktop Stealth Application via Tauri v2)

- [x] Component 1: Tauri Project Structure & Configuration (`desktop/src-tauri/`)
  - [x] Create `desktop/src-tauri/Cargo.toml` with dependencies (`tauri` v2, `tauri-plugin-global-shortcut`, `tauri-plugin-shell`, `windows` crate)
  - [x] Create `desktop/src-tauri/tauri.conf.json` configuring `WinAudioAssist` title, `transparent: true`, `decorations: false`, `alwaysOnTop: true`, `visible: false`, `skipTaskbar: true`, and frontend paths
  - [x] Create `desktop/src-tauri/build.rs` build script for Tauri v2
- [x] Component 2: Rust Stealth & Windowing Modules (`desktop/src-tauri/src/`)
  - [x] Implement `stealth/process.rs` with System Tray setup (`WinAudioAssist Service - Active`, `Show/Hide Copilot`, `Toggle Click-Through`, `Exit`) and click handling
  - [x] Implement `overlay/windows.rs` with Windows API `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` and `toggle_click_through` (`SetWindowLongPtrW`)
  - [x] Implement `hotkeys.rs` registering global shortcuts (`Ctrl+Shift+H`, `Ctrl+Shift+T`, `Ctrl+Shift+C`)
  - [x] Implement `main.rs` wiring up setup hook, tray, window affinity, hotkeys, and Tauri builder
- [x] Component 3: Frontend Event Integration & Build (`frontend/`)
  - [x] Update `frontend/src/pages/InterviewPage.tsx` with Tauri event listeners (`listen("global-screenshot-trigger")`, `listen("toggle-click-through")`)
  - [x] Run `npm run build` inside `frontend/` to generate `dist/` bundle for Tauri
- [x] Component 4: Verification & Compilation (`desktop/src-tauri/`)
  - [x] Complete project layout and document `rustup` (`rustup.rs`) instructions for compiling `WinAudioAssist.exe` native binary
