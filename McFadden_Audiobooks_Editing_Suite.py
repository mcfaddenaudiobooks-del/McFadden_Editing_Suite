# -*- coding: utf-8 -*-
"""
# ==============================================================================
#  (c) 2026 McFadden Audiobooks. 
#  McFadden Audiobooks Editing Suite (v1.0)
#       For Independent Narrators
#  Author: Jamie McFadden | Jamie@McfaddenAudiobooks.com
# ==============================================================================

    
PURPOSE: A unified suite of Python utilities designed to streamline audiobook production 
without ever sending your NDA-restricted audio to the cloud.

## 🛠️ The Toolbox: 

1. **Prenunciation Checker (v1.0):** Scans a given manuscript for  any hard to pronounce, 
lesser know, or trap words as defined in trapwords.csv. trapwords.csv may be edited 
to be personalized. Outputs an html complete with written and audio pronunciation guides 
and contextual notes

2. **Audio Marker Detector (v1.0):** Designed for narrators who use physical clickers to mark 
flubs during recording. Detects intentional spike transients (clicks, snaps, taps) 
in audio files to generate Audacity-compatible .txt label tracks. 

3. **Proof Listener (v1.0):** Automated tool designed to identify 
script deviations (flubs, omissions, and substitutions) in their recorded chapters. 
Outputs: Reaper Region file or Audacity-compatible .txt label tracks.

4. **Postnunciation Checker (v1.0):** Scans a given transcript from the Proof Listener 
for any hard to pronounce, lesser know, or trap words as defined in trapwords.csv. 
trapwords.csv may be edited to be personalized. 
Outputs Audacity Label Track (_labels.txt) for easy review.

5. **Synced Caption Writer (v1.0):** Creates captions from a given text, and matches the timeline 
from a given audiofile. Outputs SRT file for captioning word for word from the text.
Complete with punctuation, capitilization, spelling etc.

SECURITY & PRIVACY:
- RUNS 100% LOCALLY: No audio or manuscript data is ever sent to the cloud.
- Perfect for NDA-restricted projects or private narrations.

Created on Wed Mar 18 2026
Last Updated Mon Jun 8 2026 (Added Synced Caption Writer)

"""

import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys

class McFaddenLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("McFadden Audiobooks Editing Suite")
        self.root.geometry("500x600")
        self.root.configure(bg="#2c2c2c")  

        # Path handling for logo and scripts
        self.base_path = os.path.dirname(__file__)
        
        # 1. Logo Section
        try:
            logo_img = tk.PhotoImage(file=os.path.join(self.base_path, "logo.png"))
            # 2. Create the smaller version (3,3 means it takes every 3rd pixel)
            small_logo = logo_img.subsample(3, 3)
            logo_label = tk.Label(root, image=small_logo, bg="#2c2c2c")
            logo_label.image = small_logo 

            logo_label.pack(pady=10)


        except:
            tk.Label(root, text="McFADDEN AUDIOBOOKS", font=("Arial", 18, "bold"), 
                     fg="#FF813F", bg="#2c2c2c").pack(pady=20)


        
        tk.Label(root, text="McFadden Audiobooks Editing Suite", font=("Arial", 12, "bold"), 
                 fg="white", bg="#2c2c2c").pack(pady=2)
        
        tk.Label(root, text="For Independent Narrators", font=("Arial", 12, "italic"), 
                 fg="white", bg="#2c2c2c").pack(pady=2)
        
        tk.Label(root, text=" ", font=("Arial", 12, "italic"),
                 fg="white", bg="#2c2c2c").pack(pady=2)
                
        tk.Label(root, text="Select a Tool to Begin", font=("Arial", 12), 
                 fg="white", bg="#2c2c2c").pack(pady=5)

        # 2. Button Styling & Creation
        btn_options = {
            "font": ("Arial", 11, "bold"),
            "fg": "white",
            "bg": "#497d86",
            "activebackground": "#5c9ca5", 
            "width": 30,
            "pady": 2,
            "relief": "flat"
        }

        tools = [
            ("1. Prenunciation Checker", "Prenunciation.py"),
            ("2. Audio Marker Detector", "Marker_Detector.py"),
            ("3. Proof Listener", "Proof_Listener.py"),
            ("4. Postnunciation Checker", "Postnunciation.py"),
            ("5. Synced Caption Writer (.srt)", "Synced_Caption_Writer.py")
        ]

        for text, script in tools:
            btn = tk.Button(root, text=text, **btn_options, 
                            command=lambda s=script: self.launch_tool(s))
            btn.pack(pady=5)

        # 3. Footer
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


    def launch_tool(self, script_name):
        script_path = os.path.join(self.base_path, script_name)
        if os.path.exists(script_path):
            # Launch as a separate process so the menu stays open
            subprocess.Popen([sys.executable, script_path])
        else:
            messagebox.showerror("Error", f"Could not find {script_name} in this folder.")

if __name__ == "__main__":
    root = tk.Tk()
    app = McFaddenLauncher(root)
    root.mainloop()