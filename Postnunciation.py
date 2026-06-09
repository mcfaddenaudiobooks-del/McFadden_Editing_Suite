# -*- coding: utf-8 -*-
"""
# ==============================================================================
#  (c) 2026 McFadden Audiobooks. 
#  McFadden Audiobooks Editing Suite: Postnunciation Checker (v1.0)
#  Author: Jamie McFadden | Jamie@McfaddenAudiobooks.com
# ==============================================================================


**Postnunciation Checker (v1.0):** 

INPUTS:
        - Transcript from the Proof Listener Tool: .txt of your transcribed chapter
        - Trap Word List: .csv of trap words. customizable list included
        
OUTPUTS:    
        - .txt file with all trap words labeled with time stamp
            Compatible with Audacity Label Track (_labels.txt) for easy review.
        - .csv file with all trap words labeled with time stamp 
            Compatible with Reaper region markers.
    
PURPOSE:
Scans a given transcript for any hard to pronounce, lesser know, or trap words 
as defined in trapwords.csv. trapwords.csv may be edited to be personalized.
Outputs Audacity Label Track (_labels.txt) for easy review.

SECURITY & PRIVACY:
- RUNS 100% LOCALLY: No audio or manuscript data is ever sent to the cloud.
- Perfect for NDA-restricted projects or private narrations.

Created on Mon Mar 16 2026
Last Updated Mon Jun 8 2026 (updated to include reaper region marker output)


"""
import re
import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import webbrowser
import re

class PronunciationCheckerGUI:
    def __init__(self, root):
        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.title("McFadden Audiobooks: Postnunciation Checker")
        self.root.geometry("500x800")
        self.root.configure(bg="#2c2c2c")
        # Load and Display Logo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # --- LOGO SECTION ---
        self.logo_path = os.path.join(script_dir, "logo.png")
        if os.path.exists(self.logo_path):
            try:
                # Load the image
                full_img = tk.PhotoImage(file=self.logo_path, master=self.root)
                # Scale it down (3 means take every 3rd pixel, making it 1/3 size)
                # Adjust this number to make it bigger (2) or smaller (4)
                self.logo_img = full_img.subsample(3, 3) 
                
                # Create label and keep a HARD reference
                self.logo_label = tk.Label(self.root, image=self.logo_img)
                self.logo_label.image = self.logo_img 
                self.logo_label.pack(pady=5)
                self.logo_label.configure(bg="#2c2c2c")
            except Exception as e:
                print(f"Could not load logo: {e}")

        # --- Default Paths ---
        # Defaults to 'trap_words.csv' in the same folder as this script
        self.default_csv = os.path.join(os.path.dirname(__file__), "trap_words.csv")
        self.transcript = ""

        # --- UI Setup ---
        branding_frame = tk.Frame(self.root)
        branding_frame.pack(pady=(5, 0)) # Centered by default if you don't use anchor="w"
        tk.Label(root, text="McFadden Audiobooks Editing Suite", font=("Arial", 11, "bold"), fg="white", bg="#2c2c2c").pack(pady=1)
        tk.Label(root, text="For Independent Narrators", font=("Arial", 11, "italic"), fg="#b0b0b0", bg="#2c2c2c").pack(pady=1)
        tk.Label(root, text="Postnuciation Checker", font=("Arial", 18, "bold"), fg="white", bg="#2c2c2c").pack(pady=5)


        tk.Label(root, text="Requires Proofreader to be Run First", font=("Arial",12 , "bold"), fg="orange",bg="#2c2c2c").pack(pady=5)
        # Trap List Section
        csv_frame = tk.LabelFrame(root, text="Reference Data", fg="white", bg="#2c2c2c")
        csv_frame.pack(fill="x", padx=10, pady=5)
        
        self.csv_label = tk.Label(csv_frame, text=f"CSV: {os.path.basename(self.default_csv)}", fg="#1e90ff", bg="#2c2c2c")
        self.csv_label.pack(side="left", padx=5, pady=5)
        
        tk.Button(csv_frame, text="Change CSV",fg="white",  bg="#497d86", command=self.select_csv).pack(side="right", padx=5, pady=5)

        # Transcript File Section
        file_frame = tk.LabelFrame(root, text="Input File", fg="white", bg="#2c2c2c")
        file_frame.pack(fill="x", padx=10, pady=5)
        
        self.file_btn = tk.Button(file_frame, text="Select Transcript.txt",fg="white",  bg="#497d86", command=self.select_transcript)
        self.file_btn.pack(fill="x", padx=5, pady=5)
        
        self.file_label = tk.Label(file_frame, text="No file selected", fg="gray")
        self.file_label.pack(pady=2)

        # Progress / Log Section
        tk.Label(root, text="Found Matches:", fg="white", bg="#2c2c2c").pack(anchor="w", padx=10)
        # --- Log Area Section ---
        log_header_frame = tk.Frame(root)
        log_header_frame.pack(fill="x", padx=10)
        log_header_frame.configure(bg="#2c2c2c")
        
        tk.Label(log_header_frame, text="Found in Recording:",fg="white", bg="#2c2c2c").pack(side="left")
        
        # This adds the manual clear button
        tk.Button(log_header_frame, text="Clear Log",fg="white",  bg="#497d86", command=self.clear_log, 
                  font=("Arial", 8)
                  ).pack(side="right")

        self.log_area = scrolledtext.ScrolledText(root, height=6, state='disabled', bg="#f0f0f0")
        self.log_area.pack(fill="both", padx=10, pady=5, expand=True)
        
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
        ).pack(anchor="w", padx=10, pady=(0, 5))
        
        # Run Button
        self.run_btn = tk.Button(root, text="Generate Pronunciation Labels", command=self.process, bg="#497d86", fg="white", font=("Arial", 10, "bold"))
        self.run_btn.pack(pady=10, fill="x", padx=10)
        
        # 3. Footer
        footer_frame = tk.Frame(root, bg="#2c2c2c")
        footer_frame.pack(side="bottom", pady=10)

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
    def select_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            self.default_csv = path
            self.csv_label.config(text=f"CSV: {os.path.basename(path)}")

    def select_transcript(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*_transcript.txt"), ("All files", "*.*")])
        if path:
            self.transcript = path
            self.file_label.config(text=os.path.basename(path), fg="black")
            self.run_btn.config(state="normal")

    def log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
    def clear_log(self):
        """Manually wipes the log area."""
        self.log_area.config(state='normal')
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state='disabled')
    def process(self):

        self.log_area.config(state='normal')
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state='disabled')
        
        trap_map = {}
        # 1. Load Trap Words (using latin-1 for Regency accents)
        try:
            with open(self.default_csv, mode='r', encoding='latin-1') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('Word'):
                        word = row['Word'].strip().lower()
                        # Use Pronunciation, fallback to Note
                        pron = row.get('Regency Pronunciation', '').strip() or row.get('Note', '').strip()
                        trap_map[word] = pron
        
        
        except Exception as e:
            messagebox.showerror("CSV Error", f"Could not read CSV:\n{e}")
            return

        # 2. Parse Transcript File
        pattern = re.compile(r"\[\s*([\d\.]+)s\] AI:\s+([a-zA-Z']+)")
        labels = []
        reaper_lines = ["#,Name,Start,End,Length,Color"]
        region_idx = 1
        
        try:
            with open(self.transcript, 'r', encoding='utf-8') as f:
                for line in f:
                    match = pattern.search(line)
                    if match:
                        timestamp = float(match.group(1))
                        raw_word = match.group(2)
                        clean_word = raw_word.lower()
                        
                        if clean_word in trap_map:
                            pron = trap_map[clean_word]
                            label_text = f"PRO: {raw_word} ({pron})"
                            # Audacity Format
                            labels.append(f"{timestamp:.6f}\t{timestamp + 0.5:.6f}\t{label_text}")
                            
                            # Reaper CSV Format (Length is hardcoded to 0.5s to match Audacity)
                            reaper_lines.append(f"R{region_idx},\"{label_text}\",{timestamp:.3f},{timestamp + 0.5:.3f},0.500,")
                            region_idx += 1
                            
                            self.log(f"[{timestamp}s] Found: {raw_word} -> {pron}")
            

        except Exception as e:
            messagebox.showerror("File Error", f"Could not read transcript file:\n{e}")
            return

       
        # 3. Save
        if labels:
            input_path = self.transcript 

            
            # 1. Try a case-insensitive "Swap" first
            # This handles: Chapter1_transcript.txt -> Chapter1_Post_Pronunciation.txt
            new_name = re.sub(r'(?i)_transcript\.txt', '_Post_Pronunciation.txt', input_path)

            # 2. Check if the swap actually happened
            if new_name != input_path:
                output_path = new_name
            else:
                # 3. If the user named it "blue.txt", we don't want to overwrite it!
                # This peels off ".txt" and adds the suffix safely.
                # Result: blue_Post_Pronunciation.txt
                file_root, ext = os.path.splitext(input_path)
                output_path = f"{file_root}_Post_Pronunciation.txt"

            # 4. Perform the actual save
            with open(output_path, "w", encoding="utf-8") as out:
                out.write("\n".join(labels))
            
            summary = (f"Created {len(labels)} labels!\nSaved as: {os.path.basename(output_path)}")
            # 5. Perform Reaper CSV Save if checked
            if self.export_reaper_var.get():
                reaper_name = re.sub(r'(?i)_transcript\.txt', '_Reaper_Pronunciation.csv', input_path)
                if reaper_name != input_path:
                    reaper_path = reaper_name
                else:
                    reaper_path = f"{file_root}_Reaper_Pronunciation.csv"
                    
                with open(reaper_path, "w", encoding="utf-8") as out_csv:
                    out_csv.write("\n".join(reaper_lines))
                    
                summary += f"\nReaper Export: {os.path.basename(reaper_path)}"
            os.startfile(output_path)
        

            
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
                                   bg="#FF813F", # orange
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
                
        
        else:
            messagebox.showinfo("Finished", "No trap words found in this file.")
    def on_closing(self):
        self.root.quit()     # This stops the kernel from staying "busy"
        self.root.destroy()  # This closes the actual window

if __name__ == "__main__":
    root = tk.Tk()
    app = PronunciationCheckerGUI(root)
    root.mainloop()