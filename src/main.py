#!/usr/bin/env python3
"""
CLAP Spatial Sonification — Desktop Application
------------------------------------------------
Cross-platform desktop app using pywebview.
Exposes a Python API bridge to the frontend HTML/JS.

Run:
    python main.py

Requires:
    pip install pywebview msclap laion-clap
"""

import os
import sys
import json
import threading
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

import webview


# ─── CLAP helpers ─────────────────────────────────────────────────────────────

def cosine_sim(a, b):
    import numpy as np
    a = a / (np.linalg.norm(a) + 1e-9)
    b = b / (np.linalg.norm(b) + 1e-9)
    return float(np.dot(a, b))


def cosine_to_spatial(sim: float) -> dict:
    sim = max(-1.0, min(1.0, float(sim)))
    return {
        "pan":                  round(sim, 4),
        "audio_pan":            round(sim - 0.15, 4),
        "text_pan":             round(sim + 0.15, 4),
        "distance_from_origin": round(1.0 - abs(sim), 4),
        "freq_multiplier":      round(0.5 + sim * 1.5, 4),
        "gain":                 round(0.3 + max(0.0, sim) * 0.5, 4),
    }


def collect_audio_files(audio_dir: str, extensions: list) -> list:
    root = Path(audio_dir)
    files = []
    for ext in extensions:
        files.extend(root.rglob(f"*{ext}"))
    return sorted(files)


def run_msclap(audio_files: list, tags: list, progress_cb) -> list:
    try:
        from msclap import CLAP
    except ImportError:
        return {"error": "msclap not installed. Run: pip install msclap"}

    progress_cb("msclap", "loading_model", 0, len(audio_files))
    clap = CLAP(version="2023", use_cuda=False)

    progress_cb("msclap", "embedding_tags", 0, len(audio_files))
    text_embs = clap.get_text_embeddings(tags)

    results = []
    for i, af in enumerate(audio_files):
        progress_cb("msclap", "processing", i, len(audio_files))
        try:
            audio_embs = clap.get_audio_embeddings([str(af)])
            audio_emb  = audio_embs[0]
            pairs = []
            for tag, text_emb in zip(tags, text_embs):
                sim = cosine_sim(audio_emb, text_emb)
                pairs.append({
                    "id":                f"msclap_{af.stem}_{tag.replace(' ','_')}",
                    "audio_label":       af.name,
                    "audio_path":        str(af),
                    "text_label":        tag,
                    "cosine_similarity": round(sim, 6),
                    "cosine_distance":   round(1.0 - sim, 6),
                    "spatial":           cosine_to_spatial(sim),
                })
            results.append({"file": af.name, "path": str(af), "pairs": pairs})
        except Exception as e:
            results.append({"file": af.name, "path": str(af), "error": str(e), "pairs": []})
    return results


def run_laion(audio_files: list, tags: list, progress_cb) -> list:
    try:
        import laion_clap
    except ImportError:
        return {"error": "laion-clap not installed. Run: pip install laion-clap"}

    progress_cb("laion", "loading_model", 0, len(audio_files))
    model = laion_clap.CLAP_Module(enable_fusion=False)
    model.load_ckpt()

    progress_cb("laion", "embedding_tags", 0, len(audio_files))
    padded    = [f" {t} " for t in tags]
    text_embs = model.get_text_embedding(padded, use_tensor=False)

    results = []
    for i, af in enumerate(audio_files):
        progress_cb("laion", "processing", i, len(audio_files))
        try:
            audio_embs = model.get_audio_embedding_from_filelist(
                [str(af)], use_tensor=False
            )
            audio_emb = audio_embs[0]
            pairs = []
            for tag, text_emb in zip(tags, text_embs):
                sim = cosine_sim(audio_emb, text_emb)
                pairs.append({
                    "id":                f"laion_{af.stem}_{tag.replace(' ','_')}",
                    "audio_label":       af.name,
                    "audio_path":        str(af),
                    "text_label":        tag,
                    "cosine_similarity": round(sim, 6),
                    "cosine_distance":   round(1.0 - sim, 6),
                    "spatial":           cosine_to_spatial(sim),
                })
            results.append({"file": af.name, "path": str(af), "pairs": pairs})
        except Exception as e:
            results.append({"file": af.name, "path": str(af), "error": str(e), "pairs": []})
    return results


# ─── API bridge (exposed to JS via window.pywebview.api) ──────────────────────

class CLAPBridge:
    def __init__(self):
        self._window = None   # set after window creation

    def set_window(self, win):
        self._window = win

    def _emit(self, event: str, payload: dict):
        """Push an event to the frontend via JS evaluation."""
        # Double-encode: json.dumps(json.dumps(...)) produces a JS string literal
        # that JSON.parse() can safely deserialise — no manual escaping needed.
        encoded = json.dumps(json.dumps(payload))
        self._window.evaluate_js(
            f"window.__clapEvent('{event}', JSON.parse({encoded}))"
        )

    # ── called from JS ────────────────────────────────────────────────────────

    def pick_directory(self):
        """Open native folder picker, return selected path."""
        result = self._window.create_file_dialog(
            webview.FOLDER_DIALOG,
            allow_multiple=False
        )
        if result and len(result) > 0:
            return {"path": result[0]}
        return {"path": None}

    def pick_output_file(self):
        """Open native save dialog for JSON output."""
        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename="clap_results.json",
            file_types=("JSON files (*.json)",)
        )
        if result:
            path = result if isinstance(result, str) else result[0]
            return {"path": path}
        return {"path": None}

    def scan_directory(self, audio_dir: str, extensions: list = None):
        """Return list of audio files found in directory."""
        if not extensions:
            extensions = [".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff"]
        try:
            files = collect_audio_files(audio_dir, extensions)
            return {
                "files": [{"name": f.name, "path": str(f), "size": f.stat().st_size}
                           for f in files],
                "count": len(files)
            }
        except Exception as e:
            return {"error": str(e), "files": [], "count": 0}

    def run_analysis(self, audio_dir: str, tags: list, models: list,
                     extensions: list = None, output_path: str = None):
        """
        Run CLAP analysis in a background thread.
        Progress + completion are pushed as JS events.
        """
        if not extensions:
            extensions = [".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff"]

        def _worker():
            try:
                audio_files = collect_audio_files(audio_dir, extensions)
                if not audio_files:
                    self._emit("clap_error", {"message": f"No audio files found in {audio_dir}"})
                    return

                total_files = len(audio_files)
                self._emit("clap_start", {
                    "total_files": total_files,
                    "tags": tags,
                    "models": models
                })

                def progress(model, stage, current, total):
                    self._emit("clap_progress", {
                        "model": model, "stage": stage,
                        "current": current, "total": total,
                        "pct": round(current / max(total, 1) * 100)
                    })

                output = {
                    "metadata": {
                        "created":     datetime.utcnow().isoformat() + "Z",
                        "audio_dir":   str(Path(audio_dir).resolve()),
                        "tags":        tags,
                        "audio_files": [f.name for f in audio_files],
                        "models":      models,
                    },
                    "msclap": [],
                    "laion":  [],
                }

                if "msclap" in models:
                    output["msclap"] = run_msclap(audio_files, tags, progress)
                    self._emit("clap_model_done", {"model": "msclap"})

                if "laion" in models:
                    output["laion"] = run_laion(audio_files, tags, progress)
                    self._emit("clap_model_done", {"model": "laion"})

                # auto-save if output path given
                if output_path:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "w") as f:
                        json.dump(output, f, indent=2)

                self._emit("clap_done", {
                    "result": output,
                    "saved_to": output_path or None
                })

            except Exception as e:
                import traceback
                self._emit("clap_error", {
                    "message": str(e),
                    "traceback": traceback.format_exc()
                })

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return {"status": "started"}

    def save_json(self, data: dict, output_path: str):
        """Save result JSON to disk."""
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            return {"ok": True, "path": output_path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def load_json(self, path: str):
        """Load a previously saved results JSON."""
        try:
            with open(path) as f:
                return {"ok": True, "data": json.load(f)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def load_json_dialog(self):
        """Open native file picker for JSON, return parsed contents."""
        result = self._window.create_file_dialog(
            webview.OPEN,
            allow_multiple=False,
            file_types=("JSON files (*.json)",)
        )
        if result and len(result) > 0:
            return self.load_json(result[0])
        return {"ok": False, "error": "cancelled"}

    def get_platform(self):
        import platform
        return {"os": platform.system(), "version": platform.version()}


# ─── entry point ──────────────────────────────────────────────────────────────

def main():
    bridge = CLAPBridge()

    html_path = Path(__file__).parent / "assets" / "index.html"
    # pywebview v6 needs a bare absolute path string (not a file:// URI —
    # is_local_url() returns False for file:// and the server 404s)
    url = str(html_path.resolve())

    window = webview.create_window(
        title="CLAP Spatial Sonification",
        url=url,
        js_api=bridge,
        width=1400,
        height=920,
        min_size=(900, 650),
        background_color="#0e0f11",
    )

    bridge.set_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
