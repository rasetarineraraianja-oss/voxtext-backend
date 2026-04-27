# -*- coding: utf-8 -*-
"""
transcriber_debug.py - Version debug pour identifier le blocage.
Remplacez temporairement votre transcriber.py par ce fichier pour diagnostiquer.
"""

import os
import subprocess
import traceback

# Parametres modele
MODEL_SIZE = "small"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"
CPU_THREADS = 2

_model = None


def _report_progress(progress_callback, value: float, status: str = ""):
    """Envoie une progression normalisee [0, 1] a l'UI."""
    if progress_callback is None:
        return

    value = max(0.0, min(1.0, float(value)))
    progress_callback(value, status)


def _get_model():
    global _model
    if _model is None:
        print(f"[DEBUG] Chargement modele Whisper ({MODEL_SIZE})...", flush=True)
        from faster_whisper import WhisperModel

        _model = WhisperModel(
            MODEL_SIZE,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
            cpu_threads=CPU_THREADS,
        )
        print("[DEBUG] Modele charge OK", flush=True)
    return _model


def convert_to_wav(input_path: str) -> str:
    """Convertit un fichier audio en WAV 16kHz mono via ffmpeg."""
    out_path = os.path.splitext(input_path)[0] + "_16k_mono.wav"

    if os.path.exists(out_path):
        print(f"[DEBUG] WAV deja existant : {out_path}", flush=True)
        return out_path

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        out_path,
    ]
    print(f"[DEBUG] Conversion ffmpeg : {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg a echoue :\n{result.stderr.decode('utf-8', errors='replace')}"
        )

    size = os.path.getsize(out_path)
    print(f"[DEBUG] convert_to_wav OK - {out_path} ({size} octets)", flush=True)
    return out_path


def transcribe(path: str, language: str = None, hint: str = "", progress_callback=None) -> str:
    """
    Transcrit un fichier audio. Retourne le texte avec horodatages.
    """
    print(
        f"[DEBUG] transcribe() appele -> path={path!r}  lang={language!r}  hint={hint!r}",
        flush=True,
    )
    _report_progress(progress_callback, 0.02, "Preparation du fichier...")

    try:
        wav_path = convert_to_wav(path)
        print(f"[DEBUG] WAV pret : {wav_path} ({os.path.getsize(wav_path)} octets)", flush=True)
        _report_progress(progress_callback, 0.12, "Audio converti, chargement du modele...")
    except Exception as exc:
        print(f"[DEBUG] ERREUR convert_to_wav : {exc}", flush=True)
        traceback.print_exc()
        raise

    try:
        model = _get_model()
        print("[DEBUG] Modele recupere OK", flush=True)
        _report_progress(progress_callback, 0.22, "Modele pret, self.tr('in_progress')")
    except Exception as exc:
        print(f"[DEBUG] ERREUR chargement modele : {exc}", flush=True)
        traceback.print_exc()
        raise

    kwargs = {
        "beam_size": 8,
        "best_of": 3,
        "temperature": 0.0,
        "vad_filter": False,
        "initial_prompt": "Paroles de chanson",
    }
    if hint:
        kwargs["initial_prompt"] = hint
    if language:
        kwargs["language"] = language

    print(f"[DEBUG] Lancement model.transcribe() avec kwargs={kwargs}", flush=True)
    _report_progress(progress_callback, 0.28, "Analyse de l'audio...")

    try:
        segments_gen, info = model.transcribe(wav_path, **kwargs)

        print(f"[DEBUG] model.transcribe() retourne - langue detectee : {info.language}", flush=True)
        print("[DEBUG] Iteration des segments...", flush=True)

        lines = []
        total_duration = float(
            getattr(info, "duration_after_vad", 0.0)
            or getattr(info, "duration", 0.0)
            or 0.0
        )

        for i, seg in enumerate(segments_gen):
            line = seg.text.strip()
            lines.append(line)
            print(f"[DEBUG] segment {i:03d} : {line}", flush=True)

            if total_duration > 0:
                segment_end = float(getattr(seg, "end", 0.0) or 0.0)
                transcription_ratio = min(segment_end / total_duration, 1.0)
                ui_progress = 0.28 + (transcription_ratio * 0.70)
                _report_progress(
                    progress_callback,
                    ui_progress,
                    f"Transcription... {int(transcription_ratio * 100)}%",
                )

        print(f"[DEBUG] Transcription terminee - {len(lines)} segments", flush=True)
        _report_progress(progress_callback, 1.0, "Transcription terminee")
        return "\n".join(lines)

    except Exception as exc:
        print(f"[DEBUG] ERREUR pendant transcription : {type(exc).__name__} : {exc}", flush=True)
        traceback.print_exc()
        raise
