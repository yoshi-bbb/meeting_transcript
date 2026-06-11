from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    HAS_TRAY = True
except Exception:
    HAS_TRAY = False
    pystray = None  # type: ignore[assignment]

from meeting_mojiokoshi.audio import (
    AudioDevice,
    MeetingRecorder,
    list_audio_inputs,
    preferred_device_index,
    preferred_microphone_index,
)
from meeting_mojiokoshi.config import (
    AUTO_DEVICE,
    DISABLED_DEVICE,
    AppSettings,
    load_settings,
    save_settings,
)
from meeting_mojiokoshi.models import ALLOWED_MODEL_SIZES
from meeting_mojiokoshi.secure_fs import ensure_private_directory
from meeting_mojiokoshi.session import SessionPaths, create_session_paths
from meeting_mojiokoshi.transcriber import (
    TranscriptionResult,
    WhisperTranscriber,
    model_is_available,
    prepare_model,
)


APP_NAME = "Meeting Mojiokoshi"
DEFAULT_OUTPUT_DIR = Path.home() / "Documents" / "MeetingMojiokoshi"
MODEL_OPTIONS = tuple(
    model
    for model in ("tiny", "base", "small", "medium")
    if model in ALLOWED_MODEL_SIZES
)
NO_MICROPHONE = "使用しない"


class MeetingMojiokoshiApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("800x640")
        self.minsize(720, 580)

        self.settings = load_settings(DEFAULT_OUTPUT_DIR)
        self.devices: list[AudioDevice] = []
        self.recorder: MeetingRecorder | None = None
        self.session_paths: SessionPaths | None = None
        self.recording_started_at: float | None = None
        self.is_processing = False
        self.model_preparing = False
        self.close_after_finish = False
        self.recording_warning = ""
        self.ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.setting_widgets: list[tk.Widget] = []
        self.tray_icon: "pystray.Icon | None" = None
        self.tray_stopping = False

        model_size = self.settings.model_size if self.settings.model_size in MODEL_OPTIONS else "tiny"
        self.output_dir_var = tk.StringVar(value=self.settings.output_dir)
        self.meeting_device_var = tk.StringVar()
        self.microphone_device_var = tk.StringVar()
        self.model_var = tk.StringVar(value=model_size)
        self.language_var = tk.StringVar(value=self.settings.language)
        self.model_status_var = tk.StringVar(value="確認中")
        self.status_var = tk.StringVar(value="待機中")
        self.elapsed_var = tk.StringVar(value="00:00:00")

        self._configure_style()
        self._build_ui()
        self.model_var.trace_add("write", self._on_model_changed)
        self.refresh_devices()
        self._update_model_status()
        self.after(200, self._drain_ui_queue)
        self.after(1000, self._tick_elapsed)

        if HAS_TRAY:
            self._setup_tray()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TButton", padding=(12, 8))
        style.configure("Accent.TButton", padding=(14, 10), font=("", 10, "bold"))
        style.configure("Title.TLabel", font=("", 18, "bold"))
        style.configure("Status.TLabel", font=("", 11, "bold"))

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=20)
        container.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(4, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=1, sticky="e")

        settings = ttk.LabelFrame(container, text="設定", padding=14)
        settings.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="出力先").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        self.output_entry = ttk.Entry(settings, textvariable=self.output_dir_var)
        self.output_entry.grid(row=0, column=1, sticky="ew", pady=6)
        self.output_button = ttk.Button(settings, text="選択", command=self.choose_output_dir)
        self.output_button.grid(row=0, column=2, sticky="e", padx=(10, 0), pady=6)

        ttk.Label(settings, text="会議音声").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        self.meeting_device_combo = ttk.Combobox(
            settings,
            textvariable=self.meeting_device_var,
            state="readonly",
        )
        self.meeting_device_combo.grid(row=1, column=1, sticky="ew", pady=6)
        self.refresh_button = ttk.Button(settings, text="更新", command=self.refresh_devices)
        self.refresh_button.grid(row=1, column=2, sticky="e", padx=(10, 0), pady=6)

        ttk.Label(settings, text="マイク").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=6)
        self.microphone_device_combo = ttk.Combobox(
            settings,
            textvariable=self.microphone_device_var,
            state="readonly",
        )
        self.microphone_device_combo.grid(row=2, column=1, sticky="ew", pady=6)

        ttk.Label(settings, text="モデル").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=6)
        model_frame = ttk.Frame(settings)
        model_frame.grid(row=3, column=1, sticky="w", pady=6)
        self.model_buttons: list[ttk.Radiobutton] = []
        for column, model in enumerate(MODEL_OPTIONS):
            button = ttk.Radiobutton(model_frame, text=model, value=model, variable=self.model_var)
            button.grid(row=0, column=column, padx=(0, 14))
            self.model_buttons.append(button)
        self.prepare_model_button = ttk.Button(settings, text="モデル準備", command=self.prepare_selected_model)
        self.prepare_model_button.grid(row=3, column=2, sticky="e", padx=(10, 0), pady=6)

        ttk.Label(settings, text="モデル状態").grid(row=4, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Label(settings, textvariable=self.model_status_var).grid(row=4, column=1, sticky="w", pady=6)

        ttk.Label(settings, text="言語").grid(row=5, column=0, sticky="w", padx=(0, 10), pady=6)
        self.language_entry = ttk.Entry(settings, textvariable=self.language_var, width=10)
        self.language_entry.grid(row=5, column=1, sticky="w", pady=6)

        self.setting_widgets = [
            self.output_entry,
            self.output_button,
            self.meeting_device_combo,
            self.microphone_device_combo,
            self.refresh_button,
            self.prepare_model_button,
            self.language_entry,
            *self.model_buttons,
        ]

        controls = ttk.Frame(container)
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        self.start_button = ttk.Button(
            controls,
            text="録音開始",
            command=self.start_recording,
            style="Accent.TButton",
        )
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.stop_button = ttk.Button(
            controls,
            text="停止して文字起こし",
            command=self.stop_and_transcribe,
            state="disabled",
            style="Accent.TButton",
        )
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        elapsed_frame = ttk.Frame(container)
        elapsed_frame.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        elapsed_frame.columnconfigure(1, weight=1)
        ttk.Label(elapsed_frame, text="録音時間").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(elapsed_frame, textvariable=self.elapsed_var, font=("", 16, "bold")).grid(
            row=0, column=1, sticky="w"
        )

        log_frame = ttk.LabelFrame(container, text="ログ", padding=10)
        log_frame.grid(row=4, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=12, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def choose_output_dir(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.output_dir_var.get() or str(DEFAULT_OUTPUT_DIR))
        if chosen:
            self.output_dir_var.set(chosen)
            self._save_settings()

    def refresh_devices(self) -> None:
        requested_meeting = self._selected_meeting_device()
        requested_microphone = self._selected_microphone_device()
        meeting_name = requested_meeting.name if requested_meeting else self.settings.meeting_device_name
        microphone_name = (
            requested_microphone.name
            if requested_microphone
            else (
                DISABLED_DEVICE
                if self.microphone_device_var.get() == NO_MICROPHONE
                else self.settings.microphone_device_name
            )
        )

        try:
            self.devices = list_audio_inputs()
        except Exception as exc:  # noqa: BLE001 - show backend details to the user.
            self.devices = []
            self.meeting_device_combo["values"] = []
            self.microphone_device_combo["values"] = [NO_MICROPHONE]
            self.meeting_device_var.set("")
            self.microphone_device_var.set(NO_MICROPHONE)
            self._log(f"録音デバイスの取得に失敗しました: {exc}")
            return

        labels = [device.label for device in self.devices]
        self.meeting_device_combo["values"] = labels
        self.microphone_device_combo["values"] = [NO_MICROPHONE, *labels]

        meeting = self._device_named(meeting_name)
        if meeting is None:
            preferred_index = preferred_device_index(self.devices)
            meeting = self._device_at_index(preferred_index)
        self.meeting_device_var.set(meeting.label if meeting else "")

        if microphone_name == DISABLED_DEVICE:
            microphone = None
        else:
            microphone = self._device_named(microphone_name)
            if microphone is None:
                microphone = self._device_at_index(preferred_microphone_index(self.devices))
        self.microphone_device_var.set(microphone.label if microphone else NO_MICROPHONE)

        if not labels:
            self._log("録音デバイスが見つかりません。")

    def prepare_selected_model(self) -> None:
        if self.model_preparing or self.recorder:
            return
        model_size = self.model_var.get()
        self.model_preparing = True
        self.status_var.set("モデル準備中")
        self.model_status_var.set("ダウンロード中")
        self.start_button.configure(state="disabled")
        self._set_settings_enabled(False)
        self._log(f"モデル準備を開始しました: {model_size}")
        threading.Thread(
            target=self._prepare_model_worker,
            args=(model_size,),
            name="model-preparer",
            daemon=True,
        ).start()

    def _prepare_model_worker(self, model_size: str) -> None:
        try:
            model_path = prepare_model(
                model_size,
                progress=lambda message: self.ui_queue.put(("log", message)),
            )
            self.ui_queue.put(("model_ready", (model_size, model_path)))
        except Exception as exc:  # noqa: BLE001 - report download errors in the GUI.
            self.ui_queue.put(("model_failed", str(exc)))

    def start_recording(self) -> None:
        meeting_device = self._selected_meeting_device()
        if meeting_device is None:
            messagebox.showerror(APP_NAME, "会議音声の録音デバイスを選択してください。")
            return

        microphone_device = self._selected_microphone_device()
        if microphone_device and microphone_device.backend_id == meeting_device.backend_id:
            messagebox.showerror(APP_NAME, "会議音声とマイクには異なるデバイスを選択してください。")
            return

        output_dir_text = self.output_dir_var.get().strip()
        if not output_dir_text:
            messagebox.showerror(APP_NAME, "出力先を選択してください。")
            return
        output_dir = Path(output_dir_text).expanduser()
        try:
            ensure_private_directory(output_dir)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"出力先を作成できませんでした。\n{exc}")
            return

        self._save_settings()
        self.session_paths = create_session_paths(output_dir)
        selected_devices = [meeting_device]
        if microphone_device:
            selected_devices.append(microphone_device)

        self.recording_warning = ""
        self.recorder = MeetingRecorder(
            devices=selected_devices,
            output_path=self.session_paths.audio_path,
            on_error=lambda message: self.ui_queue.put(("recording_error", message)),
        )
        try:
            self.recorder.start()
        except Exception as exc:  # noqa: BLE001 - show startup errors in the GUI.
            messagebox.showerror(APP_NAME, f"録音を開始できませんでした。\n{exc}")
            self.recorder = None
            self.session_paths = None
            return

        self.recording_started_at = time.monotonic()
        self.status_var.set("録音中")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._set_settings_enabled(False)
        self._log(f"会議音声: {meeting_device.name}")
        if microphone_device:
            self._log(f"マイク: {microphone_device.name}")
        self._log(f"録音開始: {self.session_paths.audio_path.name}")

    def stop_and_transcribe(self) -> None:
        if not self.recorder or not self.session_paths or self.is_processing:
            return

        self.stop_button.configure(state="disabled")
        self.status_var.set("停止中")
        self.is_processing = True
        self._log("録音を停止しています。")
        model_size = self.model_var.get()
        language = self.language_var.get().strip() or None
        worker = threading.Thread(
            target=self._stop_and_transcribe_worker,
            args=(model_size, language),
            name="transcribe-worker",
            daemon=True,
        )
        worker.start()

    def _stop_and_transcribe_worker(self, model_size: str, language: str | None) -> None:
        recorder = self.recorder
        paths = self.session_paths
        if recorder is None or paths is None:
            self.ui_queue.put(("failed", "録音セッションが見つかりません。"))
            return
        try:
            recorder.stop()
            recorder.join()
            if recorder.frame_count <= 0:
                raise RuntimeError("録音された音声がありません。")

            for warning in dict.fromkeys(recorder.warnings):
                self.ui_queue.put(("log", f"録音警告: {warning}"))
            self.ui_queue.put(("status", "文字起こし中"))
            self.ui_queue.put(("log", f"音声を保存しました: {paths.audio_path}"))

            transcriber = WhisperTranscriber(model_size=model_size, language=language)
            result = transcriber.transcribe(
                paths.audio_path,
                paths.transcript_path,
                progress=lambda message: self.ui_queue.put(("log", message)),
            )
            self.ui_queue.put(("finished", result))
        except Exception as exc:  # noqa: BLE001 - surface backend errors to the GUI.
            message = str(exc)
            if paths.audio_path.exists():
                message += f"\n\n録音音声は保存されています:\n{paths.audio_path}"
            self.ui_queue.put(("failed", message))

    def on_close(self) -> None:
        self._save_settings()
        if self.recorder and self.recorder.is_recording:
            should_close = messagebox.askyesno(
                APP_NAME,
                "録音を停止し、文字起こししてから終了しますか？",
            )
            if not should_close:
                return
            self.close_after_finish = True
            self.stop_and_transcribe()
            return
        if self.is_processing:
            messagebox.showinfo(APP_NAME, "文字起こし中です。完了までお待ちください。")
            return
        if self.model_preparing:
            messagebox.showinfo(APP_NAME, "モデル準備中です。完了までお待ちください。")
            return
        if HAS_TRAY and self.tray_icon:
            self.withdraw()
            try:
                self.tray_icon.visible = True
            except Exception:
                pass
        else:
            self.destroy()

    def destroy(self) -> None:
        self._stop_tray_icon()
        super().destroy()

    def _selected_meeting_device(self) -> AudioDevice | None:
        return self._device_with_label(self.meeting_device_var.get())

    def _selected_microphone_device(self) -> AudioDevice | None:
        label = self.microphone_device_var.get()
        if not label or label == NO_MICROPHONE:
            return None
        return self._device_with_label(label)

    def _device_with_label(self, label: str) -> AudioDevice | None:
        for device in self.devices:
            if device.label == label:
                return device
        return None

    def _device_named(self, name: str) -> AudioDevice | None:
        if name in (AUTO_DEVICE, DISABLED_DEVICE):
            return None
        for device in self.devices:
            if device.name == name:
                return device
        return None

    def _device_at_index(self, index: int | None) -> AudioDevice | None:
        if index is None:
            return None
        for device in self.devices:
            if device.index == index:
                return device
        return None

    def _on_model_changed(self, *_args: object) -> None:
        self._update_model_status()

    def _update_model_status(self) -> None:
        model_size = self.model_var.get()
        ready = model_is_available(model_size)
        self.model_status_var.set("準備済み" if ready else "未準備")

    def _set_settings_enabled(self, enabled: bool) -> None:
        for widget in self.setting_widgets:
            if widget in (self.meeting_device_combo, self.microphone_device_combo):
                widget.configure(state="readonly" if enabled else "disabled")
            else:
                widget.configure(state="normal" if enabled else "disabled")

    def _current_settings(self) -> AppSettings:
        meeting = self._selected_meeting_device()
        microphone = self._selected_microphone_device()
        return AppSettings(
            output_dir=self.output_dir_var.get().strip() or str(DEFAULT_OUTPUT_DIR),
            meeting_device_name=meeting.name if meeting else AUTO_DEVICE,
            microphone_device_name=microphone.name if microphone else DISABLED_DEVICE,
            model_size=self.model_var.get(),
            language=self.language_var.get().strip(),
        )

    def _save_settings(self) -> None:
        try:
            self.settings = self._current_settings()
            save_settings(self.settings)
        except OSError as exc:
            self._log(f"設定を保存できませんでした: {exc}")

    def _drain_ui_queue(self) -> None:
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "log":
                    self._log(str(payload))
                elif kind == "status":
                    self.status_var.set(str(payload))
                elif kind == "recording_error":
                    self._handle_recording_error(str(payload))
                elif kind == "failed":
                    self._handle_failure(str(payload))
                elif kind == "finished":
                    self._handle_finished(payload)
                elif kind == "model_ready":
                    self._handle_model_ready(payload)
                elif kind == "model_failed":
                    self._handle_model_failed(str(payload))
        except queue.Empty:
            pass
        self.after(200, self._drain_ui_queue)

    def _handle_recording_error(self, message: str) -> None:
        self.recording_warning = message
        self._log(f"録音デバイスエラー: {message}")
        if self.recorder and not self.is_processing:
            self._log("残っている音声を保存して文字起こしへ進みます。")
            self.stop_and_transcribe()

    def _handle_finished(self, payload: object) -> None:
        result = payload if isinstance(payload, TranscriptionResult) else None
        self.status_var.set("完了")
        self.is_processing = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self._set_settings_enabled(True)
        self.recording_started_at = None
        self.recorder = None
        self.session_paths = None
        self.elapsed_var.set("00:00:00")
        self._update_model_status()
        self._log("完了しました。")
        if self.close_after_finish:
            self.destroy()
            return

        detail = "録音音声と文字起こしファイルを保存しました。"
        if result:
            detail += f"\n\n{result.audio_path}\n{result.transcript_path}"
        open_folder = messagebox.askyesno(APP_NAME, f"{detail}\n\n出力先を開きますか？")
        if open_folder and result:
            self._open_directory(result.audio_path.parent)

    def _handle_failure(self, message: str) -> None:
        self.status_var.set("エラー")
        self.is_processing = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self._set_settings_enabled(True)
        self.recording_started_at = None
        self.recorder = None
        self.session_paths = None
        self.elapsed_var.set("00:00:00")
        self._log(message)
        messagebox.showerror(APP_NAME, message)
        if self.close_after_finish:
            self.destroy()

    def _handle_model_ready(self, payload: object) -> None:
        model_size, model_path = payload if isinstance(payload, tuple) else (self.model_var.get(), "")
        self.model_preparing = False
        self.status_var.set("待機中")
        self.start_button.configure(state="normal")
        self._set_settings_enabled(True)
        self._update_model_status()
        self._log(f"モデル保存先: {model_path}")
        messagebox.showinfo(APP_NAME, f"{model_size} モデルの準備が完了しました。")

    def _handle_model_failed(self, message: str) -> None:
        self.model_preparing = False
        self.status_var.set("エラー")
        self.model_status_var.set("準備失敗")
        self.start_button.configure(state="normal")
        self._set_settings_enabled(True)
        self._log(f"モデル準備に失敗しました: {message}")
        messagebox.showerror(APP_NAME, f"モデル準備に失敗しました。\n{message}")

    def _tick_elapsed(self) -> None:
        if self.recording_started_at is not None:
            elapsed = int(time.monotonic() - self.recording_started_at)
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.elapsed_var.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        self.after(1000, self._tick_elapsed)

    def _create_tray_icon(self) -> "Image.Image":
        """Create a simple tray icon (64x64 blue circle with 'M')."""
        size = 64
        image = Image.new("RGB", (size, size), "white")
        draw = ImageDraw.Draw(image)
        # Blue circle
        margin = 6
        draw.ellipse([margin, margin, size - margin, size - margin], fill="#2E86AB")
        # White "M"
        try:
            # Try a nice font, fallback to default
            font = ImageFont.truetype("arial.ttf", 28)
        except Exception:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            except Exception:
                font = ImageFont.load_default()
        # Center the text
        text = "M"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - 2
        draw.text((x, y), text, fill="white", font=font)
        return image

    def _setup_tray(self) -> None:
        if not HAS_TRAY or self.tray_icon is not None:
            return
        try:
            icon_image = self._create_tray_icon()
            menu = pystray.Menu(
                pystray.MenuItem("ウィンドウを開く", self._show_window),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "録音開始",
                    self._tray_start_recording,
                    enabled=lambda item: self.recorder is None and not self.is_processing and not self.model_preparing,
                ),
                pystray.MenuItem(
                    "停止して文字起こし",
                    self._tray_stop_recording,
                    enabled=lambda item: self.recorder is not None and not self.is_processing,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("終了", self._quit_from_tray),
            )
            self.tray_icon = pystray.Icon(
                "meeting_mojiokoshi",
                icon_image,
                APP_NAME,
                menu=menu,
            )
            try:
                self.tray_icon.run_detached()
            except NotImplementedError:
                tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
                tray_thread.start()
        except Exception:
            # Tray setup failed (e.g. missing system libs on Linux), disable gracefully
            self.tray_icon = None

    def _show_window(self, icon: "pystray.Icon | None" = None, item: "pystray.MenuItem | None" = None) -> None:
        self._call_on_ui_thread(self._show_window_on_ui_thread)

    def _show_window_on_ui_thread(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()
        # Tray icon remains visible (recommended for quick access)

    def _tray_start_recording(self, icon: "pystray.Icon | None" = None, item: "pystray.MenuItem | None" = None) -> None:
        self._call_on_ui_thread(self.start_recording)

    def _tray_stop_recording(self, icon: "pystray.Icon | None" = None, item: "pystray.MenuItem | None" = None) -> None:
        self._call_on_ui_thread(self.stop_and_transcribe)

    def _quit_from_tray(self, icon: "pystray.Icon | None" = None, item: "pystray.MenuItem | None" = None) -> None:
        self._call_on_ui_thread(self._quit_from_tray_on_ui_thread)

    def _quit_from_tray_on_ui_thread(self) -> None:
        if self.recorder and self.recorder.is_recording:
            messagebox.showwarning(APP_NAME, "録音中です。先に停止してください。")
            return
        if self.is_processing:
            messagebox.showinfo(APP_NAME, "文字起こし中です。完了までお待ちください。")
            return
        if self.model_preparing:
            messagebox.showinfo(APP_NAME, "モデル準備中です。完了までお待ちください。")
            return
        self.destroy()

    def _stop_tray_icon(self) -> None:
        if not self.tray_icon or self.tray_stopping:
            return
        icon = self.tray_icon
        self.tray_icon = None
        self.tray_stopping = True
        try:
            icon.stop()
        except Exception:
            pass

    def _call_on_ui_thread(self, callback: Callable[[], None]) -> None:
        try:
            self.after(0, callback)
        except tk.TclError:
            pass

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    @staticmethod
    def _open_directory(path: Path) -> None:
        directory = str(path.resolve())
        try:
            if sys.platform == "win32":
                os.startfile(directory)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["/usr/bin/open", directory], close_fds=True)
            else:
                executable = shutil.which("xdg-open")
                if executable:
                    subprocess.Popen([executable, directory], close_fds=True)
        except OSError:
            pass


def main() -> None:
    app = MeetingMojiokoshiApp()
    app.mainloop()
