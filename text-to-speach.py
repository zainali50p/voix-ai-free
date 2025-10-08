# tts_pro.py
import tkinter as tk
from tkinter import filedialog, messagebox
import asyncio
import edge_tts
import pygame
import os
import tempfile
import threading
import time

# -------------------- Ensure mixer initialized once --------------------
try:
    pygame.mixer.init()
except Exception:
    pass

TEMP_PREFIX = "tts_tmp_"

# -------------------- Extended VOICE_MAP (popular Azure neural voices) --------------------
VOICE_MAP = {
    "English (US)": {
        "Male": {
            "Guy": "en-US-GuyNeural",
            "Davis": "en-US-DavisNeural",
            "Tony": "en-US-TonyNeural",
            "Christopher": "en-US-ChristopherNeural",
        },
        "Female": {
            "Aria": "en-US-AriaNeural",
            "Jenny": "en-US-JennyNeural",
            "Amber": "en-US-AmberNeural",
            "Ashley": "en-US-AshleyNeural",
            "Michelle": "en-US-MichelleNeural",
        }
    },
    "English (UK)": {
        "Male": {
            "Ryan": "en-GB-RyanNeural",
            "Thomas": "en-GB-ThomasNeural",
            "Oliver": "en-GB-OliverNeural",
        },
        "Female": {
            "Sonia": "en-GB-SoniaNeural",
            "Libby": "en-GB-LibbyNeural",
        }
    },
    "Urdu (Pakistan)": {
        "Male": {"Asad": "ur-PK-AsadNeural"},
        "Female": {"Gul": "ur-PK-GulNeural"},
    },
    "Hindi (India)": {
        "Male": {"Madhur": "hi-IN-MadhurNeural", "Aarav": "hi-IN-AaravNeural"},
        "Female": {"Swara": "hi-IN-SwaraNeural", "Aarohi": "hi-IN-AarohiNeural"},
    },
    "Arabic (Egypt)": {
        "Male": {"Shakir": "ar-EG-ShakirNeural"},
        "Female": {"Salma": "ar-EG-SalmaNeural"},
    },
    "Spanish (Spain)": {
        "Male": {"Alvaro": "es-ES-AlvaroNeural"},
        "Female": {"Elvira": "es-ES-ElviraNeural"},
    },
    "French (France)": {
        "Male": {"Henri": "fr-FR-HenriNeural"},
        "Female": {"Denise": "fr-FR-DeniseNeural"},
    }
}

# -------------------- Emotions + Auto option --------------------
EMOTIONS = ["Default", "Auto Detect", "cheerful", "sad", "angry", "whispering", "chat", "newscast"]

# -------------------- Auto Emotion Detection helper --------------------
def detect_emotion(text):
    text_lower = (text or "").lower()
    if any(word in text_lower for word in ["happy", "great", "amazing", "wonderful", "joy", "excited", "love"]):
        return "cheerful"
    if any(word in text_lower for word in ["sad", "sorry", "pain", "loss", "cry", "alone", "depressed"]):
        return "sad"
    if any(word in text_lower for word in ["angry", "hate", "mad", "fight", "shout", "furious", "annoyed"]):
        return "angry"
    if any(word in text_lower for word in ["news", "breaking", "headline", "report", "update", "announce"]):
        return "newscast"
    return "Default"

# -------------------- Async TTS Function (safe style fallback) --------------------
async def tts_generate(text, voice, rate, style, file_path):
    kwargs = {"voice": voice}
    if rate:
        kwargs["rate"] = rate
    if style and style != "Default":
        kwargs["style"] = style
    try:
        communicate = edge_tts.Communicate(text, **kwargs)
        await communicate.save(file_path)
    except Exception:
        # fallback: try without style (Default)
        try:
            communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
            await communicate.save(file_path)
        except Exception as e:
            raise e

# -------------------- Playback + cleanup (background thread) --------------------
def play_and_cleanup(file_path):
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        try:
            if hasattr(pygame.mixer.music, "unload"):
                pygame.mixer.music.unload()
        except Exception:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                time.sleep(0.05)
                pygame.mixer.init()
            except Exception:
                pass
        time.sleep(0.05)
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

# -------------------- Speak & Save handlers --------------------
def speak_text():
    text = text_box.get("1.0", tk.END).strip()
    if not text:
        messagebox.showwarning("Warning", "Please enter some text!")
        return
    try:
        lang = lang_var.get()
        gender = gender_var.get()
        voice_name = voice_var.get()
        selected_voice = VOICE_MAP[lang][gender][voice_name]

        rate = f"+{speed_var.get()}%" if speed_var.get() >= 0 else f"{speed_var.get()}%"
        style = style_var.get()
        if style == "Auto Detect":
            style = detect_emotion(text)

        tmp = tempfile.NamedTemporaryFile(prefix=TEMP_PREFIX, suffix=".mp3", delete=False)
        tmp_path = tmp.name
        tmp.close()

        asyncio.run(tts_generate(text, selected_voice, rate, style, tmp_path))

        t = threading.Thread(target=play_and_cleanup, args=(tmp_path,), daemon=True)
        t.start()
    except Exception as e:
        messagebox.showerror("Error", str(e))

def save_audio():
    text = text_box.get("1.0", tk.END).strip()
    if not text:
        messagebox.showwarning("Warning", "Please enter some text!")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".mp3",
                                             filetypes=[("Audio Files", "*.mp3")])
    if not file_path:
        return
    try:
        lang = lang_var.get()
        gender = gender_var.get()
        voice_name = voice_var.get()
        selected_voice = VOICE_MAP[lang][gender][voice_name]

        rate = f"+{speed_var.get()}%" if speed_var.get() >= 0 else f"{speed_var.get()}%"
        style = style_var.get()
        if style == "Auto Detect":
            style = detect_emotion(text)

        asyncio.run(tts_generate(text, selected_voice, rate, style, file_path))
        messagebox.showinfo("Saved", f"Audio saved as {file_path}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# -------------------- UI helpers: update voice options --------------------
def update_voice_options(*args):
    lang = lang_var.get()
    gender = gender_var.get()
    if lang not in VOICE_MAP or gender not in VOICE_MAP[lang]:
        voices = ["-"]
    else:
        voices = list(VOICE_MAP[lang][gender].keys())
    menu = voice_menu["menu"]
    menu.delete(0, "end")
    for v in voices:
        menu.add_command(label=v, command=lambda val=v: voice_var.set(val))
    if voices:
        voice_var.set(voices[0])

# -------------------- Build GUI --------------------
root = tk.Tk()
root.title("Text To Speech")
root.geometry("920x640")
root.resizable(True, True)
root.configure(bg="#0f1724")

# ✅ Set App Icon
try:
    root.iconbitmap("texttospeach.ico")
except Exception as e:
    print("⚠ Icon not found, skipping...", e)

# Title bar
title = tk.Label(root, text="🎙️ Text To Speech Pro Free", font=("Segoe UI", 18, "bold"),
                 fg="#E6F0FF", bg="#0f1724")
title.pack(pady=(12, 4))

subtitle = tk.Label(root, text="Natural voices · Multi-language · Emotions · Export MP3",
                    font=("Segoe UI", 10), fg="#B8C6E6", bg="#0f1724")
subtitle.pack(pady=(0, 12))

# Main frame
main_frame = tk.Frame(root, bg="#111827", padx=12, pady=12)
main_frame.pack(fill="both", expand=True, padx=12, pady=8)

# Text area
text_box = tk.Text(main_frame, wrap="word", font=("Segoe UI", 12), height=14, bg="#0b1220", fg="#E6EEF8",
                   insertbackground="#E6EEF8", relief="flat", padx=8, pady=8)
text_box.insert("1.0", "Type or paste text here...")
text_box.pack(fill="both", padx=6, pady=(6, 12))

# Controls
controls_frame = tk.Frame(main_frame, bg="#0f1724")
controls_frame.pack(fill="x", pady=(4, 8))

label_cfg = {"bg": "#0f1724", "fg": "#DDE9FF", "font": ("Segoe UI", 10, "bold")}

# Language
tk.Label(controls_frame, text="Language:", **label_cfg).grid(row=0, column=0, padx=6, pady=6, sticky="w")
lang_var = tk.StringVar(value="English (US)")
lang_menu = tk.OptionMenu(controls_frame, lang_var, *VOICE_MAP.keys())
lang_menu.config(width=18)
lang_menu.grid(row=0, column=1, padx=6, pady=6, sticky="w")

# Gender
tk.Label(controls_frame, text="Gender:", **label_cfg).grid(row=0, column=2, padx=6, pady=6, sticky="w")
gender_var = tk.StringVar(value="Male")
gender_menu = tk.OptionMenu(controls_frame, gender_var, "Male", "Female")
gender_menu.config(width=10)
gender_menu.grid(row=0, column=3, padx=6, pady=6, sticky="w")

# Voice
tk.Label(controls_frame, text="Voice:", **label_cfg).grid(row=0, column=4, padx=6, pady=6, sticky="w")
voice_var = tk.StringVar(value="")
voice_menu = tk.OptionMenu(controls_frame, voice_var, "")
voice_menu.config(width=18)
voice_menu.grid(row=0, column=5, padx=6, pady=6, sticky="w")

# Speed slider
tk.Label(controls_frame, text="Speed:", **label_cfg).grid(row=1, column=0, padx=6, pady=6, sticky="w")
speed_var = tk.IntVar(value=0)
speed_slider = tk.Scale(controls_frame, variable=speed_var, from_=-50, to=50, orient="horizontal", length=240,
                        bg="#0f1724", fg="#DDE9FF", troughcolor="#1f2937")
speed_slider.grid(row=1, column=1, columnspan=2, padx=6, pady=6, sticky="w")

# Emotion / Style
tk.Label(controls_frame, text="Emotion:", **label_cfg).grid(row=1, column=3, padx=6, pady=6, sticky="w")
style_var = tk.StringVar(value="Default")
style_menu = tk.OptionMenu(controls_frame, style_var, *EMOTIONS)
style_menu.config(width=14)
style_menu.grid(row=1, column=4, columnspan=2, padx=6, pady=6, sticky="w")

# Buttons
btn_frame = tk.Frame(main_frame, bg="#0f1724")
btn_frame.pack(pady=(6, 12))

btn_style = {"font": ("Segoe UI", 11, "bold"), "width": 16, "bd": 0, "relief": "flat"}

speak_btn = tk.Button(btn_frame, text="▶ Speak (Play)", command=speak_text,
                      bg="#10B981", fg="white", **btn_style)
speak_btn.grid(row=0, column=0, padx=10, pady=6)

save_btn = tk.Button(btn_frame, text="💾 Save Audio", command=save_audio,
                     bg="#3B82F6", fg="white", **btn_style)
save_btn.grid(row=0, column=1, padx=10, pady=6)

clear_btn = tk.Button(btn_frame, text="🧹 Clear Text", command=lambda: text_box.delete("1.0", tk.END),
                      bg="#F97316", fg="white", **btn_style)
clear_btn.grid(row=0, column=2, padx=10, pady=6)

# Footer
footer = tk.Label(root, text="Tip: Use 'Auto Detect' in Emotion to automatically pick style from text. "
                             "If a style is not supported by a voice, the app will safely fallback.",
                  font=("Segoe UI", 9), bg="#0f1724", fg="#9fb0d8")
footer.pack(pady=(4, 10))

# Update voices on change
lang_var.trace("w", update_voice_options)
gender_var.trace("w", update_voice_options)
update_voice_options()

# Run app
root.mainloop()
