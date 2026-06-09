# -*- coding: utf-8 -*-
"""
# ==============================================================================
#  (c) 2026 McFadden Audiobooks.
#  McFadden Audiobooks Editing Suite: Audio Marker Detector (v1.0)
#  Author: Jamie McFadden | Jamie@McfaddenAudiobooks.com
# ==============================================================================


**Audio Marker Detector (v1.0):**

PURPOSE:
Detects intentional spike transients (clicks, snaps, taps) in audio files to generate 
Audacity-compatible label tracks. Designed for narrators who use physical 
clickers to mark flubs during recording.

INPUTS:
        - Audio:  .mp3, .wav, .wv
        
OUTPUTS:    
    - .txt file with all Audio Markers complete with time stamp
        Compatible with Audacity Label Track (_Markers.txt) for easy editing.
    - .csv file with all Audio Markers complete with time stamp
        Compatible with Reaper region markers.

    

SECURITY & PRIVACY:
- RUNS 100% LOCALLY: No audio or manuscript data is ever sent to the cloud.
- Perfect for NDA-restricted projects or private narrations.

Created on Thu Mar  5 2026
Last Updated Mon Jun 8 2026 (updated to include reaper region marker output)
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import librosa
import numpy as np
import os
import threading
import json
import webbrowser

# --- DEFAULTS & CONFIG ---
DEFAULTS = {
    "sensitivity": 0.05,    # Lower = more sensitive
    "min_gap_ms": 500,      # Ignore secondary clicks within 500ms
    "label_text": "Edit",   # Text for the Audacity label
    "theme_bg": "#1e1e1e",
    "theme_fg": "#e0e0e0",
    "accent": "#007acc"
}

def load_settings():
    try:
        if os.path.exists("config_marker.json"):
            with open("config_marker.json", "r") as f:
                return {**DEFAULTS, **json.load(f)}
    except: pass
    return DEFAULTS

def save_settings(cfg):
    with open("config_marker.json", "w") as f:
        json.dump(cfg, f, indent=4)

class AudioMarkerDetectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("McFadden Audiobooks:Audio Marker Detector")
        self.root.geometry("550x650")
        self.root.configure(padx=20, pady=20)
        self.root.configure(bg="#2c2c2c")
        # 1. Load and Display Logo
        script_dir = os.path.dirname(os.path.abspath(__file__))

        
        # --- LOGO SECTION ---
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
        tk.Label(root, text="Audio Marker Detector", font=("Arial", 18, "bold"), fg="white", bg="#2c2c2c").pack(pady=5)        


        # Sensitivity Slider
        # 0.5 works well for me
        tk.Label(root, text="Sensitivity (Lower = Catches More)", bg="#2c2c2c", fg="white", font=("Arial", 10)).pack(pady=(10, 0))
        self.sens_slider = tk.Scale(root, from_=0.1, to_=1.0, resolution=0.05, 
                                    orient="horizontal", length=300, bg="#2c2c2c", fg="white", highlightthickness=0, troughcolor="#404040")
        self.sens_slider.set(0.5) 
        self.sens_slider.pack(pady=5)

        # Status
        self.status_label = tk.Label(root, text="Ready to scan...",bg="#2c2c2c", fg="white")
        self.status_label.pack(pady=20)
        
        # --- REAPER EXPORT CHECKBOX ---
        self.export_reaper_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            root, 
            text="Export Reaper Regions (.csv)", 
            variable=self.export_reaper_var,
            bg="#2c2c2c", 
            fg="white", 
            selectcolor="#404040", 
            activebackground="#2c2c2c", 
            activeforeground="white"
        ).pack(pady=(0, 15))
        
        # Action Button
        self.select_btn = tk.Button(root, text="Select Audio File (.mp3, .wav, .wv)", command=self.process_audio, 
                                   height=2, width=40, bg="#497d86", fg="white", font=("Helvetica", 10, "bold"))
        self.select_btn.pack()
        
        
        
        # Footer
        footer_frame = tk.Frame(root, bg="#2c2c2c")
        footer_frame.pack(side="bottom", pady=5)

        footer_text = tk.Label(
            footer_frame, 
            text="© 2026 McFadden Audiobooks All Rights Reserved | 100% Local Processing\n", 
            font=("Arial", 8), 
            fg="#888888", 
            bg="#2c2c2c"
        )
        footer_text.pack(side="top")

        # Clickable Hyperlink Label
        import webbrowser
        link_label = tk.Label(
            footer_frame, 
            text="www.McFaddenAudiobooks.com", 
            font=("Arial", 8, "underline"), 
            fg="#1e90ff",  # Nice visible blue against dark background
            bg="#2c2c2c", 
            cursor="hand2"  # Changes mouse cursor to a pointing hand
        )
        link_label.pack(side="top")
        
        # Bind the click event to open the website
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.McFaddenAudiobooks.com"))


    def process_audio(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.wv"), ("All files", "*.*")])
        if not file_path:
            return

        self.select_btn.config(state="disabled", text="Analyzing Audio...")
        self.status_label.config(text="Filtering High Frequencies...", fg="#1e90ff")
        
        thread = threading.Thread(target=self.run_logic, args=(file_path,))
        thread.start()



    def run_logic(self, file_path):
        try:
            # 1. Load Audio (22k is enough to see the audio marker peaks)
            y, sr = librosa.load(file_path, sr=22050)
            
            # 2. Spectral Flux Analysis
            # Look for 'suddenness' in the high frequencies (8kHz+)
            # Markers are instant; speech is a gradual 'ramp'
            onset_env = librosa.onset.onset_strength(y=y, sr=sr, 
                                                    feature=librosa.feature.melspectrogram,
                                                    fmin=8000) # Ignore speech core

            # 3. Apply Sensitivity
            # Use the slider to set how many standard deviations above the noise the 'hit' must be
            sens_val = self.sens_slider.get()
            # Inverting slider: 0.1 is very sensitive, 1.0 is very strict
            dynamic_threshold = np.mean(onset_env) + (np.std(onset_env) * (sens_val * 15))

            # 4. Find Peaks
            # wait=40 (~0.9s) ensures double-taps for a single mistake are treated as one event
            peaks = librosa.util.peak_pick(onset_env, 
                                          pre_max=5, post_max=5, 
                                          pre_avg=20, post_avg=20, 
                                          delta=dynamic_threshold, wait=40)
            
            times = librosa.frames_to_time(peaks, sr=sr)

            if len(times) == 0:
                self.reset_ui("No markers detected! Try lowering sensitivity.")
                return

            # 5. Export Label File
            output_file = os.path.splitext(file_path)[0] + "_Markers.txt"
            
            reaper_lines = ["#,Name,Start,End,Length,Color"]
            region_idx = 1
            
            with open(output_file, "w") as f:
                for s in times:
                    # Point label for Audacity
                    f.write(f"{s:.6f}\t{s:.6f}\tMarker\n")
                    
                    # Reaper CSV Format (Creates a 0.5s region for visibility)
                    reaper_lines.append(f"R{region_idx},\"Marker\",{s:.3f},{s + 0.5:.3f},0.500,")
                    region_idx += 1


            
            summary = (f"Found {len(times)} markers.\nLabels saved next to your audio file.")
            
            # 6. Export Reaper CSV if checked
            if self.export_reaper_var.get():
                reaper_path = os.path.splitext(file_path)[0] + "_Reaper_Markers.csv"
                with open(reaper_path, "w", encoding="utf-8") as rf:
                    rf.write("\n".join(reaper_lines))
                summary += f"\nReaper Export: {os.path.basename(reaper_path)}"
            
            self.reset_ui(f"Success! Found {len(times)} markers.")

                    
            def open_tip_jar():
    
                webbrowser.open_new("https://ko-fi.com/mcfaddenaudiobooks")
               
     
            # --- CUSTOM SUCCESS WINDOW ---
            success_win = tk.Toplevel(root) # 'root'  main app window variable
            success_win.title("Processing Complete")
            success_win.geometry("400x400")
            success_win.resizable(False, False)
            
            # 1. Header & Summary Icon
            tk.Label(success_win, text="✔ SUCCESS", font=("Arial", 14, "bold"), fg="#28a745").pack(pady=(20, 5))
            
            # 2. The Summary Text 
            summary_label = tk.Label(success_win, text=summary, justify="left", font=("Consolas", 10), padx=20)
            summary_label.pack(pady=10)
            
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
            tk.Button(success_win, text="Close", command=success_win.destroy, width=15).pack(pady=(5, 20))
            
            tk.Label(success_win, text="McFadden Audiobooks Editing Suite", font=("Arial", 9, "bold")).pack()
            tk.Label(success_win, text="For Independent Narrators", font=("Arial", 9, "italic")).pack()
    
            tk.Label(success_win, text="© 2026 McFadden Audiobooks. All Rights Reserved.", font=("Arial", 9)).pack()
            
            
            success_win.transient(root)
            success_win.grab_set()    
        
        except Exception as e:
            self.reset_ui("Error during processing.")
            messagebox.showerror("Error", str(e))

    def reset_ui(self, message):
        self.root.after(0, lambda: self._update_ui(message))

    def _update_ui(self, message):
        self.status_label.config(text=message)
        self.select_btn.config(state="normal", text="Select WAV File")

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioMarkerDetectorGUI(root)
    root.mainloop()