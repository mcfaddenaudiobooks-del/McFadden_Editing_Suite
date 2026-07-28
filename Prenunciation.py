# -*- coding: utf-8 -*-
"""
# ==============================================================================
#  (c) 2026 McFadden Audiobooks. 
#  McFadden Audiobooks Editing Suite: Prenunciation Checker (v1.0-beta)
#  Author: Jamie McFadden | Jamie@McfaddenAudiobooks.com
# ==============================================================================


**Prenunciation Checker (v1.0-beta):**

INPUTS:
        - Manuscript:  .txt of your chapter/ section you are preparing to record
        - Trap Word List: .csv of trap words. customizable list included
        
OUTPUTS:    
        - .html file with all trap words present in a given text including
         written and audio pronunciation guides and contextual notes
    
PURPOSE:
Scans a given manuscript for  any hard to pronounce, lesser know, or trap words 
as defined in trapwords.csv. trapwords.csv may be edited to be personalized.
Outputs an html complete with written and audio pronunciation guides and contextual notes

SECURITY & PRIVACY:
- RUNS 100% LOCALLY: No audio or manuscript data is ever sent to the cloud.
- Perfect for NDA-restricted projects or private narrations.

Created on Thu Mar  5 2026
Last Updated Wed Mar 18 2026

"""

import csv
import re
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import webbrowser
import subprocess, sys

def open_file(path):
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])

class ManuscriptPrepGUI:
    def __init__(self, root):
        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.title("McFadden Audiobooks: Prenunciation Checker")
        self.root.geometry("500x700")
        self.root.configure(bg="#2c2c2c")
        # Load and Display Logo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        #logo_path = os.path.join(script_dir, "logo.png")
        
        # --- LOGO SECTION ---
        self.logo_path = os.path.join(script_dir, "logo.png")
        if os.path.exists(self.logo_path):
            try:
                # Load the image
                full_img = tk.PhotoImage(file=self.logo_path, master=self.root)
                # Scale it down (3 means take every 3rd pixel, making it 1/3 size)
                # Adjust this number to make it bigger (2) or smaller (4)
                self.logo_img = full_img.subsample(3, 3) 
                
                #  Create label and keep a HARD reference
                self.logo_label = tk.Label(self.root, image=self.logo_img)
                self.logo_label.image = self.logo_img 
                self.logo_label.pack(pady=5)
                self.logo_label.configure(bg="#2c2c2c")
            except Exception as e:
                print(f"Could not load logo: {e}")
                

        # --- Default Paths ---
        # Defaults to 'trap_words.csv' in the same folder as this script
        self.default_csv = os.path.join(os.path.dirname(__file__), "trap_words.csv")
        self.manuscript_path = ""
        # --- UI Setup ---
        branding_frame = tk.Frame(self.root)
        branding_frame.pack(pady=(5, 0)) # Centered by default if you don't use anchor="w"
        tk.Label(root, text="McFadden Audiobooks Editing Suite", font=("Arial", 11, "bold"), fg="white", bg="#2c2c2c").pack(pady=1)
        tk.Label(root, text="For Independent Narrators", font=("Arial", 11, "italic"), fg="#b0b0b0", bg="#2c2c2c").pack(pady=1)
        tk.Label(root, text="Prenunciation Checker", font=("Arial", 18, "bold"), fg="white", bg="#2c2c2c").pack(pady=5)


        # Trap List Frame
        csv_frame = tk.LabelFrame(root, text="Pronunciation Reference", fg="white", bg="#2c2c2c")
        csv_frame.pack(fill="x", padx=10, pady=5)
        
        self.csv_label = tk.Label(csv_frame, text=f"CSV: {os.path.basename(self.default_csv)}", fg="#1e90ff", bg="#2c2c2c")
        self.csv_label.pack(side="left", padx=5, pady=5)
        
        tk.Button(csv_frame, text="Change CSV",fg="white",  bg="#497d86", command=self.select_csv).pack(side="right", padx=5, pady=5)

        # Manuscript Frame
        file_frame = tk.LabelFrame(root, text="Manuscript to Scan", fg="white", bg="#2c2c2c")
        file_frame.pack(fill="x", padx=10, pady=5)
        
        self.file_btn = tk.Button(file_frame, text="Select Manuscript (.txt)",fg="white",  bg="#497d86", command=self.select_manuscript)
        self.file_btn.pack(fill="x", padx=5, pady=5)
        
        self.file_label = tk.Label(file_frame, text="No file selected", fg="orange", bg="#2c2c2c")
        self.file_label.pack(pady=2)

        # Log Area
# --- Log Area Section ---
        log_header_frame = tk.Frame(root)
        log_header_frame.pack(fill="x", padx=10)
        log_header_frame.configure(bg="#2c2c2c")
        
        
        tk.Label(log_header_frame, text="Found in Manuscript:", fg="white", bg="#2c2c2c").pack(side="left")
        
        # This adds the manual clear button
        tk.Button(log_header_frame, text="Clear Log",fg="white",  bg="#497d86", command=self.clear_log, 
                  font=("Arial", 8)).pack(side="right")

        self.log_area = scrolledtext.ScrolledText(root, height=6,  bg="#f0f0f0")
        self.log_area.pack(fill="both", padx=10, pady=5, expand=True)
        # Action Button
        self.run_btn = tk.Button(root, text="Generate Prep Report (HTML)", command=self.process, bg="#497d86", fg="white", font=("Arial", 10, "bold"))
        self.run_btn.pack(pady=10, fill="x", padx=10)
        #  Footer
        footer_frame = tk.Frame(root, bg="#2c2c2c")
        footer_frame.pack(side="bottom", pady=10)

        footer_text = tk.Label(
            footer_frame, 
            text="© 2026 McFadden Audiobooks | 100% Local Processing\n", 
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

    def select_manuscript(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path:
            self.manuscript_path = path
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
        """The main logic for scanning and generating the report."""
        self.log_area.config(state='normal')
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state='disabled')

        trap_dict = {}
        # 1. Load CSV (using latin-1 for Regency characters)
        try:
            with open(self.default_csv, mode='r', encoding='latin-1') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    word = row.get('Word', '').strip()
                    if word:
                        trap_dict[word.lower()] = {
                            'original': word,
                            'pronunciation': row.get('Regency Pronunciation', '').strip(),
                            'link': row.get('Cambridge Dictionary Link', '').strip(),
                            'note': row.get('Note', '').strip()
                        }
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV: {e}")
            return

        # 2. Read Manuscript
        try:
            with open(self.manuscript_path, mode='r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read manuscript: {e}")
            return

        # 3. Scan for matches
        found_traps = {}
        for trap_word_lower, data in trap_dict.items():
            pattern = rf'\b{re.escape(trap_word_lower)}\b'
            matches = re.findall(pattern, content, flags=re.IGNORECASE)
            if matches:
                count = len(matches)
                found_traps[trap_word_lower] = data
                found_traps[trap_word_lower]['count'] = count
                self.log(f"Found '{data['original']}' ({count}x)")

        # 4. Generate HTML Report
        if found_traps:
            output_path = self.manuscript_path.replace('.txt', '_Prep_Report.html')
            # This finds the directory where your .py script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "logo.png")
            try:
                with open(output_path, mode='w', encoding='utf-8') as f:
                    f.write("<html><body style='font-family:sans-serif; padding:20px;'>")
                    # Use the absolute path so the HTML can find the logo on your machine
                    f.write(f"<img src='file:///{logo_path}' alt='Logo' style='height:80px; margin-bottom:10px;'>")
                    f.write(f"<h1>Prep Report: {os.path.basename(self.manuscript_path)}</h1>")
                    f.write("<table border='1' cellpadding='10' style='border-collapse:collapse; width:100%;'>")
                    f.write("<tr style='background:#f4f4f4;'><th>Word</th><th>Count</th><th>Pronunciation</th><th>Notes</th><th>Resource</th></tr>")
                    
                    for w in sorted(found_traps.keys()):
                        d = found_traps[w]
                        link_html = f"<a href='{d['link']}' target='_blank'>Cambridge Audio Guide 🔊</a>" if d['link'] else ""
                        f.write(f"<tr>")
                        f.write(f"<td><b>{d['original']}</b></td>")
                        f.write(f"<td>{d['count']}</td>")
                        f.write(f"<td>{d['pronunciation']}</td>")
                        f.write(f"<td>{d['note']}</td>")
                        f.write(f"<td>{link_html}</td>")
                        f.write(f"</tr>")
                    
                    f.write("</table></body></html>")
                    
                summary=(f"Report created with {len(found_traps)} unique traps.\nSaved as: {os.path.basename(output_path)}")

                #messagebox.showinfo("Success", f"Report created!\nSaved to: {os.path.basename(output_path)}")
                open_file(output_path)
                
                def open_tip_jar():
        
                    webbrowser.open_new("https://ko-fi.com/mcfaddenaudiobooks")
                   
         
                # --- CUSTOM SUCCESS WINDOW ---
                success_win = tk.Toplevel(self.root) # 'root'  main app window variable
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
                

                success_win.transient(self.root)
                success_win.grab_set()        
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save report: {e}")
        else:
            messagebox.showinfo("Scan Complete", "No trap words found.")
    def on_closing(self):
        self.root.quit()     # This stops the kernel from staying "busy"
        self.root.destroy()  # This closes the actual window

if __name__ == "__main__":
    root = tk.Tk()
    app = ManuscriptPrepGUI(root)
    root.mainloop()