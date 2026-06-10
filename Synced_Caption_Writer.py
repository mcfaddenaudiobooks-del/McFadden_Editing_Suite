# -*- coding: utf-8 -*-
"""
# ==============================================================================
#  (c) 2026 McFadden Audiobooks. 
#  McFadden Audiobooks Editing Suite: Synced Caption Writer (v1.0-beta)
#  Author: Jamie McFadden | Jamie@McfaddenAudiobooks.com
# ==============================================================================

    
**Synced Caption Writer (v1.0-beta):** 

INPUTS:
        - Audio:  .mp3, .wav, .wv
        - Text:  .txt
        
OUTPUTS:    
        - Caption file:  .srt

PURPOSE: Creates captions from a given text, and matches the timeline from a given audiofile. 
Outputs SRT file for captioning word for word from the text. Complete with punctuation, capitalization, spelling etc.

SECURITY & PRIVACY:
  - RUNS 100% LOCALLY: No audio or manuscript data is ever sent to the cloud.
  - Perfect for NDA-restricted projects or private narrations.

Created on Sun Jun 7 2026
Last Updated Mon Jun 8 2026
"""

import os
import re
import json
import time
import threading
import difflib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser      
from faster_whisper import WhisperModel

# FORCE OPENMP TO COOPERATE BEFORE LOADING OTHER LIBRARIES
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# --- CONFIGURATION DEFAULTS ---
DEFAULTS = {
    "model_path": "", # Empty = auto-download "large-v3" or Users set this in Advanced Tab
    "lib_cublas": "", # Empty = auto-detect from pip install or Users set this in Advanced Tab
    "lib_cudnn": "",  # Empty = auto-detect from pip install or Users set this in Advanced Tab
    "no_speech_thresh": 0.6,
    "word_prob_min": 0.1,
    "sync_window": 3,
    "recovery_lookahead": 10,
    "base_cutoff": 0.5,
    "short_word_cutoff": 0.55,
    "mid_word_cutoff": 0.45,
    "flub_prob_thresh": 0.8,
    "unique_word_len": 6,
    "search_radius_large": 25,
    "search_radius_small": 5,
    "strict_cutoff_tiny": 0.95,
    "strict_cutoff_mid": 0.85,
    "strict_cutoff_long": 0.70,
    "anchor_len": 5,
    "max_jump_anchor": 25,
    "max_jump_small": 5,
    "backtrack_limit": 30,
    "sub_window_range": 4,
    
    # --- WORD COUNT BOUNDARY DEFAULTS ---
    "min_words_per_caption": 1,
    "max_words_per_caption": 12
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_caption_writer.json")

def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                merged = {**DEFAULTS, **saved}
                # Validate path fields — reset if they no longer exist
                for key in ('model_path', 'lib_cublas', 'lib_cudnn'):
                    val = merged.get(key, '').strip()
                    if val and not os.path.exists(val):
                        merged[key] = ''
                return merged
        except:
            return DEFAULTS
    return DEFAULTS

def save_settings(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)


def setup_environment(cfg):
    """Sets up CUDA library paths, auto-detecting if not manually specified."""
    
    paths_to_add = []
    
    # --- Auto-detect cuBLAS ---
    cublas_path = cfg.get('lib_cublas', '').strip()
    if not cublas_path:
        try:
            import nvidia.cublas
            cublas_path = os.path.join(os.path.dirname(nvidia.cublas.__file__), 'bin')
        except ImportError:
            cublas_path = None
    
    if cublas_path and os.path.exists(cublas_path):
        paths_to_add.append(cublas_path)
    
    # --- Auto-detect cuDNN ---
    cudnn_path = cfg.get('lib_cudnn', '').strip()
    if not cudnn_path:
        try:
            import nvidia.cudnn
            cudnn_path = os.path.join(os.path.dirname(nvidia.cudnn.__file__), 'bin')
        except ImportError:
            cudnn_path = None
    
    if cudnn_path and os.path.exists(cudnn_path):
        paths_to_add.append(cudnn_path)
    
    # --- Add all valid paths to environment ---
    for p in paths_to_add:
        os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(p)
            except OSError:
                pass
    
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def clean_word_token(w, v_map=None):
    w = w.lower().replace('’', "'").replace('‘', "'").replace("'", "")
    w = re.sub(r'[^\w\s]', '', w)
    if v_map and w in v_map:
        w = v_map[w]
    return w

def format_srt_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    if milliseconds == 1000:
        secs += 1
        milliseconds = 0
        if secs == 60:
            minutes += 1
            secs = 0
            if minutes == 60:
                hours += 1
                minutes = 0
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def ensure_model(model_name, model_path, status_label):
    """Shows a download warning only if the model won't be found."""
    
    # If the user has pointed to a specific folder, trust that it exists
    if model_path and os.path.exists(model_path):
        return

    # Otherwise check the default Hugging Face cache
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
    model_is_cached = False
    if os.path.exists(cache_dir):
        search = f"faster-whisper-{model_name}".lower()
        model_is_cached = any(search in f.lower() for f in os.listdir(cache_dir))

    if not model_is_cached:
        status_label.config(
            text="Status: Downloading AI model (~1.5 GB) — first run only, please wait...",
            fg="orange"
        )
        status_label.update_idletasks()

def run_captioning(audio_path, script_path, status_label, cfg, root ):
    setup_environment(cfg)
    try:
        start_time_proc = time.time()
        status_label.config(text="Status: Loading AI Model...", fg="orange")

        model_path = cfg.get('model_path', '').strip() or "large-v3"
        ensure_model(model_path, cfg.get('model_path', '').strip(), status_label)
        try:
            model = WhisperModel(model_path, device="cuda", compute_type="int8_float16")
        except Exception:
            model = WhisperModel(model_path, device="cpu", compute_type="int8")
        
        status_label.config(text="Status: Transcribing Audio...", fg="#1e90ff")
        
        segments, info = model.transcribe(
            audio_path, word_timestamps=True, beam_size=5, 
            condition_on_previous_text=False, 
            no_speech_threshold=cfg['no_speech_thresh']
        )
        
        whisper_words = []
        for segment in segments:
            if segment.no_speech_prob > cfg['no_speech_thresh']: continue
            for word in segment.words:
                if word.probability > cfg['word_prob_min']:
                    w_stripped = word.word.strip().lower().replace('’', "'").replace('‘', "'")
                    w_stripped = re.sub(r'[—\-\_\.\…\*\,\?\!\(\)]+', ' ', w_stripped)
                    w_stripped = w_stripped.replace("'", "")
                    w_stripped = re.sub(r'[^\w\s]', '', w_stripped).strip()
                    
                    if w_stripped:
                        whisper_words.append({
                            "word": w_stripped,
                            "start": word.start,
                            "end": word.end
                        })

        status_label.config(text="Status: Aligning Script text...", fg="#1e90ff")
        with open(script_path, 'r', encoding='utf-8') as f:
            full_script = f.read()

        matches = list(re.finditer(r'[^\s—\-\_\.\…\*\,\?\!\(\)]+', full_script))
        
        script_idx = 0
        time_map = {}
        end_time_map = {}
        
        window = cfg["sync_window"]
        recovery_lookahead = cfg["recovery_lookahead"]
        cutoff_val = cfg["base_cutoff"]

        for w_data in whisper_words:
            n_word = w_data['word']
            match_found = False
            
            if script_idx < len(matches):
                target_raw = matches[script_idx].group()
                target_word = clean_word_token(target_raw)
                
                current_cutoff = cfg["short_word_cutoff"] if len(target_word) <= 3 else (cfg["mid_word_cutoff"] if len(target_word) <= 5 else cutoff_val)
                if difflib.get_close_matches(n_word, [target_word], cutoff=current_cutoff):
                    time_map[script_idx] = w_data['start']
                    end_time_map[script_idx] = w_data['end']
                    script_idx += 1
                    match_found = True

            if not match_found:
                search_start = 0 if script_idx == 0 else max(0, script_idx - 1)
                current_search_limit = 500 if script_idx == 0 else window + 2
                for i in range(current_search_limit):
                    target_idx = search_start + i
                    if target_idx < len(matches):
                        target_raw = matches[target_idx].group()
                        target_word = clean_word_token(target_raw)
                        
                        temp_cutoff = cfg["short_word_cutoff"] if len(target_word) <= 3 else (cfg["mid_word_cutoff"] if len(target_word) <= 5 else cutoff_val)
                        if difflib.get_close_matches(n_word, [target_word], cutoff=temp_cutoff):
                            time_map[target_idx] = w_data['start']
                            end_time_map[target_idx] = w_data['end']
                            script_idx = target_idx + 1
                            match_found = True
                            break
            
            if not match_found:
                for i in range(recovery_lookahead):
                    target_idx = script_idx + i
                    if target_idx < len(matches):
                        target_raw = matches[target_idx].group()
                        candidate = clean_word_token(target_raw)
                        if len(candidate) >= 4 and difflib.get_close_matches(n_word, [candidate], cutoff=cfg["flub_prob_thresh"]):
                            time_map[target_idx] = w_data['start']
                            end_time_map[target_idx] = w_data['end']
                            script_idx = target_idx + 1
                            match_found = True
                            break

        status_label.config(text="Status: Building Subtitle Blocks...", fg="#1e90ff")
        
        captions = []
        current_block_indices = []
        block_start_time = None
        block_end_time = None
        
        # Pull slider rules directly from updated config
        max_words_per_block = cfg.get("max_words_per_caption", 12)
        min_words_per_block = cfg.get("min_words_per_caption", 1)

        for idx in range(len(matches)):
            token_start = time_map.get(idx)
            token_end = end_time_map.get(idx)
            
            if token_start is not None:
                if block_start_time is None:
                    block_start_time = token_start
                block_end_time = token_end
                
            current_block_indices.append(idx)
            
            if idx + 1 < len(matches):
                trailing = full_script[matches[idx].end() : matches[idx + 1].start()]
            else:
                trailing = full_script[matches[idx].end() : ]
                
            is_paragraph_break = '\n\n' in trailing or ('\n' in trailing and len(trailing.strip()) == 0)
            is_hard_punct = any(p in trailing for p in ['.', '!', '?', ':', '”', '…'])
            is_soft_punct = any(p in trailing for p in [',', ';', '—'])
            
            words_accumulated = len(current_block_indices)
            
            should_break = False
            if idx == len(matches) - 1:
                should_break = True
            elif is_paragraph_break:
                should_break = True
            elif is_hard_punct and words_accumulated >= max(min_words_per_block, 12): 
                should_break = True
            elif is_soft_punct and words_accumulated >= max(min_words_per_block, 16): 
                should_break = True
            elif words_accumulated >= max_words_per_block:
                should_break = True
                
            if should_break:
                start_w_idx = current_block_indices[0]
                end_w_idx = current_block_indices[-1]
                
                if end_w_idx + 1 < len(matches):
                    block_text = full_script[matches[start_w_idx].start() : matches[end_w_idx + 1].start()]
                else:
                    block_text = full_script[matches[start_w_idx].start() : ]
                
                block_text = block_text.strip().replace('\n', ' ')
                
                if block_start_time is None:
                    prev_end = 0.0
                    for k in range(start_w_idx - 1, -1, -1):
                        if k in end_time_map:
                            prev_end = end_time_map[k]
                            break
                    block_start_time = prev_end
                    
                if block_end_time is None or block_end_time <= block_start_time:
                    next_start = block_start_time + 2.5
                    for k in range(end_w_idx + 1, len(matches)):
                        if k in time_map:
                            next_start = time_map[k]
                            break
                    block_end_time = min(next_start, block_start_time + 2.5)
                
                # --- DYNAMIC MINIMUM DURATION ENGINE ---
                word_count = len(block_text.split())
                word_based_min = (word_count * 0.3) + 0.2
                absolute_floor = 1.5
                
                calculated_minimum = max(word_based_min, absolute_floor)
                actual_duration = block_end_time - block_start_time
                
                if actual_duration < calculated_minimum:
                    next_spoken_start = None
                    for k in range(end_w_idx + 1, len(matches)):
                        if k in time_map:
                            next_spoken_start = time_map[k]
                            break
                    
                    proposed_end = block_start_time + calculated_minimum
                    if next_spoken_start is not None:
                        block_end_time = min(proposed_end, next_spoken_start - 0.05)
                    else:
                        block_end_time = proposed_end
                    
                if block_text:
                    captions.append({
                        "text": block_text,
                        "start": block_start_time,
                        "end": block_end_time
                    })
                
                current_block_indices = []
                block_start_time = None
                block_end_time = None

        output_path = audio_path.rsplit('.', 1)[0] + "_captions.srt"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, cap in enumerate(captions, start=1):
                start_str = format_srt_time(cap['start'])
                end_str = format_srt_time(cap['end'])
                f.write(f"{i}\n")
                f.write(f"{start_str} --> {end_str}\n")
                f.write(f"{cap['text']}\n\n")
                #log_func(f"[{start_str} -> {end_str}] {cap['text']}")

        duration = time.time() - start_time_proc
        
        def open_tip_jar():
    
            webbrowser.open_new("https://ko-fi.com/mcfaddenaudiobooks")
           
 
        # --- CUSTOM SUCCESS WINDOW ---
        success_win = tk.Toplevel(root) # 'root'  main app window variable
        success_win.title("Processing Complete")
        success_win.geometry("400x350")
        success_win.resizable(False, False)
        
        # 1. Header & Summary Icon
        tk.Label(success_win, text="✔ SUCCESS", font=("Arial", 14, "bold"), fg="#28a745").pack(pady=(10, 5))
        
        # 2. The Summary Text 
        summary_label = tk.Label(success_win, text=(f"Subtitles compiled successfully in {duration:.1f}s!\nSaved: {os.path.basename(output_path)}"), justify="left", font=("Consolas", 10), padx=20)
        summary_label.pack(pady=5)
        
        # 3. The Tip Jar Section 
        tk.Frame(success_win, height=1, bg="lightgray").pack(fill="x", padx=40, pady=10)
        tk.Label(success_win, text="Did this tool save you time today?", font=("Arial", 9, "italic")).pack()
        
        tip_button = tk.Button(success_win, 
                               text="Buy the Dev a Coffee", 
                               command=open_tip_jar,
                               bg="#FF813F", # Friendly orange
                               fg="white", 
                               font=("Arial", 10, "bold"), 
                               relief="flat", 
                               padx=10, pady=5)
        tip_button.pack(pady=10)
        
        # 4. Close Button
        tk.Button(success_win, text="Close", command=success_win.destroy, width=15).pack(pady=(5, 10))
        
        tk.Label(success_win, text="McFadden Audiobooks Editing Suite", font=("Arial", 9, "bold")).pack()
        tk.Label(success_win, text="For Independent Narrators", font=("Arial", 9, "italic")).pack()

        tk.Label(success_win, text="© 2026 McFadden Audiobooks. All Rights Reserved.", font=("Arial", 9)).pack()
        

        success_win.transient(root)
        success_win.grab_set()    
        
        
        
        status_label.config(text="Status: Complete!",fg="white", bg="#2c2c2c")
       # messagebox.showinfo("Success", f"Subtitles compiled successfully in {duration:.1f}s!\nSaved: {os.path.basename(output_path)}")
        
    except Exception as e:
        status_label.config(text="Status: Execution Error", fg="red")
        messagebox.showerror("System Error", str(e))


class GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("McFadden Audiobooks: Synced Caption Writer")
        self.root.geometry("600x900+100+20")
        self.root.configure(bg="#2c2c2c")
        
        self.cfg = load_settings()
        
        # --- TOP BRANDING HEADER ---
        try:
            logo_img = tk.PhotoImage(file=os.path.join(os.path.dirname(__file__), "logo.png"))
            small_logo = logo_img.subsample(3, 3)
            logo_label = tk.Label(root, image=small_logo, bg="#2c2c2c")
            logo_label.image = small_logo 
            logo_label.pack(pady=10)
        except:
            tk.Label(root, text="McFADDEN AUDIOBOOKS", font=("Arial", 18, "bold"), fg="#FF813F", bg="#2c2c2c").pack(pady=15)
        
        tk.Label(root, text="McFadden Audiobooks Editing Suite", font=("Arial", 11, "bold"), fg="white", bg="#2c2c2c").pack(pady=1)
        tk.Label(root, text="For Independent Narrators", font=("Arial", 11, "italic"), fg="#b0b0b0", bg="#2c2c2c").pack(pady=1)
        tk.Label(root, text="Synced Caption Writer", font=("Arial", 18, "bold"), fg="white", bg="#2c2c2c").pack(pady=5)

        # --- NOTEBOOK FOR TABS (Dark Styled) ---
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#2c2c2c', borderwidth=0)
        style.configure('TNotebook.Tab', background='#404040', foreground='white', padding=[15, 5])
        style.map('TNotebook.Tab', background=[('selected', '#497d86')], foreground=[('selected', 'white')])
        style.configure('TFrame', background='#2c2c2c')

        self.nb = ttk.Notebook(root)
        self.tab_main = ttk.Frame(self.nb)
        self.tab_adv = ttk.Frame(self.nb)
        self.nb.add(self.tab_main, text=" Main Captioning ")
        self.nb.add(self.tab_adv, text=" Advanced Settings ")
        self.nb.pack(expand=1, fill="both", padx=10, pady=5)
        
        self.setup_main_tab()
        self.setup_adv_tab()
        
        # --- FOOTER SECTION ---
        footer_frame = tk.Frame(root, bg="#2c2c2c")
        footer_frame.pack(side="bottom", pady=10, fill="x")

        tk.Label(
            footer_frame, 
            text="© 2026 McFadden Audiobooks All Rights Reserved | 100% Local Processing", 
            font=("Arial", 8), fg="#888888", bg="#2c2c2c"
        ).pack(side="top")

        link_label = tk.Label(
            footer_frame, 
            text="www.McFaddenAudiobooks.com", 
            font=("Arial", 8, "underline"), fg="#1e90ff", bg="#2c2c2c", cursor="hand2"
        )
        link_label.pack(side="top", pady=2)
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.McFaddenAudiobooks.com"))       

    def setup_main_tab(self):
        f = self.tab_main
        
        # File Selection Block
        file_frame = tk.LabelFrame(f, text=" Audio Track and Manuscript Selection ", fg="white", bg="#2c2c2c", padx=10, pady=10)
        file_frame.pack(fill="x", padx=10, pady=10)
        file_frame.columnconfigure(0, weight=1)
        
        tk.Label(file_frame, text="Audio Track Master File (.mp3/.wav/.wv):", bg="#2c2c2c", fg="white").grid(row=0, column=0, sticky="w", pady=2)
        self.audio_entry = tk.Entry(file_frame, bg="#404040", fg="white", insertbackground="white", bd=1)
        self.audio_entry.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=2)
        tk.Button(file_frame, text="Browse...", bg="#497d86", fg="white", activebackground="#5c9ca5", command=self.browse_audio).grid(row=1, column=1, pady=2)
        
        tk.Label(file_frame, text="Manuscript Editorial Text File (.txt):", bg="#2c2c2c", fg="white").grid(row=2, column=0, sticky="w", pady=(8, 2))
        self.script_entry = tk.Entry(file_frame, bg="#404040", fg="white", insertbackground="white", bd=1)
        self.script_entry.grid(row=3, column=0, sticky="ew", padx=(0, 5), pady=2)
        tk.Button(file_frame, text="Browse...", bg="#497d86", fg="white", activebackground="#5c9ca5", command=self.browse_script).grid(row=3, column=1, pady=2)
        
        # Word Limit Sliders Block
        word_limit_frame = tk.LabelFrame(f, text=" Caption Word Limits ", fg="white", bg="#2c2c2c", padx=10, pady=10)
        word_limit_frame.pack(fill="x", padx=10, pady=5)
        word_limit_frame.columnconfigure(1, weight=1)
        
        tk.Label(word_limit_frame, text="Minimum Words:", bg="#2c2c2c", fg="white").grid(row=0, column=0, sticky="w", pady=5)
        self.min_word_scale = tk.Scale(word_limit_frame, from_=1, to=10, orient=tk.HORIZONTAL, bg="#2c2c2c", fg="white", highlightthickness=0, troughcolor="#404040")
        self.min_word_scale.set(self.cfg.get("min_words_per_caption", 1))
        self.min_word_scale.grid(row=0, column=1, sticky="ew", padx=10)
        
        tk.Label(word_limit_frame, text="Maximum Words:", bg="#2c2c2c", fg="white").grid(row=1, column=0, sticky="w", pady=5)
        self.max_word_scale = tk.Scale(word_limit_frame, from_=1, to=30, orient=tk.HORIZONTAL, bg="#2c2c2c", fg="white", highlightthickness=0, troughcolor="#404040")
        self.max_word_scale.set(self.cfg.get("max_words_per_caption", 12))
        self.max_word_scale.grid(row=1, column=1, sticky="ew", padx=10)
        
        self.min_word_scale.config(command=self.validate_word_limits)
        self.max_word_scale.config(command=self.validate_word_limits)
        

        # # Controls / Status Bottom Row
        footer_btn_frame = tk.Frame(f, bg="#2c2c2c")
        footer_btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.status_label = tk.Label(footer_btn_frame, text="Status: Ready", bg="#2c2c2c", font=("Arial", 10, "bold"), fg="#497d86")
        self.status_label.pack(side="left")
        
        tk.Button(footer_btn_frame, text="Generate Captions", command=self.start, width=22, bg="#497d86", fg="white", font=("Arial", 11, "bold"), activebackground="#5c9ca5").pack(side="right")

    def setup_adv_tab(self):
        f = self.tab_adv
        canvas = tk.Canvas(f, bg="#2c2c2c", highlightthickness=0)
        scroll = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        
        # Style canvas structure window
        self.scroll_frame = tk.Frame(canvas, bg="#2c2c2c")
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        
        self.adv_entries = {}
        settings_map = [
            ("model_path", "AI Model Path", "Folder containing Whisper large_v3", True),
            ("lib_cublas", "cuBLAS Path", "Directory for nvidia cublas DLLs", True),
            ("lib_cudnn", "cuDNN Path", "Directory for nvidia cudnn DLLs", True),
            ("no_speech_thresh", "Silence Thresh", "AI skips segments if silence prob high", False),
            ("short_word_cutoff", "Short Word Threshold", "Fuzzy match for words <= 3 chars", False),
            ("mid_word_cutoff", "Med Word Thresh", "Fuzzy match for words <= 5 chars", False),
            ("flub_prob_thresh", "Extra Word Thresh", "Min AI confidence to report an extra word", False),
            ("word_prob_min", "Min AI Conf", "Min confidence to recognize a word", False),            
            ("search_radius_small", "Common Radius", "Search distance for common words", False),
            ("strict_cutoff_mid", "Med Omit Thresh", "Omission strictness for mid words", False),
            ("strict_cutoff_long", "Long Omit Thresh", "Omission strictness for long words", False),
            ("anchor_len", "Anchor Word Length", "Word length required to move pointer", False),
            ("max_jump_anchor", "Anchor Jump", "Allowed jump distance for anchor words", False),
            ("max_jump_small", "Small Jump", "Allowed jump distance for small words", False),
            ("backtrack_limit", "Backtracking", "How far back to look for timestamp anchor", False),            
            ("sync_window", "Sync Window", "Lookahead range for basic alignment", False),
            ("recovery_lookahead", "Recovery Jump", "Max jump to find a strong anchor", False),
            ("base_cutoff", "Match Sensitivity", "Fuzzy matching (lower = more loose)", False),
            ("unique_word_len", "Anchor Length", "Min length to trust as anchor word", False),
            ("search_radius_large", "Large Search", "Scan range for anchor words", False),
            ("strict_cutoff_tiny", "Tiny Word Strict", "Match strictness for tiny words", False),
            ("sub_window_range", "Sub Radius", "Distance to pair omission with flub", False)
        ]

        for key, name, hint, is_dir in settings_map:
            row = tk.Frame(self.scroll_frame, bg="#2c2c2c")
            row.pack(fill="x", padx=10, pady=4)
            
            tk.Label(row, text=name, width=18, anchor="w", bg="#2c2c2c", fg="white").pack(side="left")
            ent = tk.Entry(row, width=25, bg="#404040", fg="white", insertbackground="white", bd=1)
            ent.insert(0, str(self.cfg.get(key, "")))
            ent.pack(side="left", padx=5)
            self.adv_entries[key] = ent
            
            if is_dir:
                tk.Button(row, text="...", bg="#497d86", fg="white", command=lambda e=ent: self.browse_dir(e)).pack(side="left", padx=2)
            tk.Label(row, text=f"({hint})", fg="#a0a0a0", bg="#2c2c2c", font=("Arial", 8)).pack(side="left", padx=5)

        adv_btn_frame = tk.Frame(f, bg="#2c2c2c")
        adv_btn_frame.pack(fill="x", side="bottom", padx=20, pady=15)
        tk.Button(adv_btn_frame, text="Save & Apply Settings", bg="#2e7d32", fg="white", font=('Arial', 10, 'bold'), command=self.save_adv).pack(side="left", expand=True, fill="x", padx=(0, 5))
        tk.Button(adv_btn_frame, text="Restore Defaults", bg="#d32f2f", fg="white", font=('Arial', 10, 'bold'), command=self.reset_adv).pack(side="right", expand=True, fill="x", padx=(5, 0))

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def validate_word_limits(self, *args):
        min_val = self.min_word_scale.get()
        max_val = self.max_word_scale.get()
        if min_val > max_val:
            self.max_word_scale.set(min_val)

    def browse_audio(self):
        filename = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.wv"), ("All Files", "*.*")])
        if filename:
            self.audio_entry.delete(0, tk.END)
            self.audio_entry.insert(0, filename)
            
    def browse_script(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if filename:
            self.script_entry.delete(0, tk.END)
            self.script_entry.insert(0, filename)

    def browse_dir(self, entry_widget):
        d = filedialog.askdirectory()
        if d: 
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, d)

    def save_adv(self):
        new_cfg = self.cfg.copy()
        for k, entry in self.adv_entries.items():
            val = entry.get().strip()
            if any(x in k for x in ["path", "lib"]): 
                new_cfg[k] = val
            else:
                try: new_cfg[k] = float(val) if "." in val else int(val)
                except: new_cfg[k] = val
        save_settings(new_cfg)
        self.cfg = load_settings()
        messagebox.showinfo("Saved", "Advanced configuration parameters written back successfully to file.")

    def reset_adv(self):
        for k, v in DEFAULTS.items():
            if k in self.adv_entries: 
                self.adv_entries[k].delete(0, tk.END)
                self.adv_entries[k].insert(0, str(v))
            

    def start(self):
        self.cfg["min_words_per_caption"] = self.min_word_scale.get()
        self.cfg["max_words_per_caption"] = self.max_word_scale.get()
        save_settings(self.cfg)
        
        if not self.audio_entry.get() or not self.script_entry.get():
            messagebox.showwarning("Error", "Please provide all valid audio and text file paths.")
            #messagebox.showinfo("Selection Error", "Please provide a valid audio file path.",fg="red")
            return
        audio_path = self.audio_entry.get().strip()
        
        script_path = self.script_entry.get().strip()
        
        

            
        self.status_label.config(text="Status: Initializing...", fg="orange")
        
        threading.Thread(
            target=run_captioning,
            args=(audio_path, script_path, self.status_label, self.cfg, self.root),
            daemon=True
        ).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = GUI(root)
    root.mainloop()

