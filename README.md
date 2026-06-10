# ⚠️ Beta Warning: A Note from the Author

This suite was built by me, for me, to solve the specific bottlenecks in my own audiobook production workflow. It is currently in beta.

Customized for My Workflow: The AI logic, pronunciation defaults, and processing settings are currently optimized for my voice and my specific project needs. It has not been widely tested on other machines, with other voices, or with different recording styles.

Your Input is Key: If it works for you, that’s great! If it doesn't, please open an [Issue] on GitHub and let me know. Your feedback is exactly what I need to make this better for everyone.

# McFadden Audiobooks Editing Suite: For Independent Narrators (v1.0-beta)
/100% Local AI Tools for Narrators./
A unified suite of Python utilities designed to streamline audiobook production without ever sending your NDA-restricted audio to the cloud.
This project is licensed under the terms of the MIT License.

## 🛠️ The Toolbox: 

1. **Prenunciation Checker (v1.0-beta):** Scans a given manuscript for  any hard to pronounce, lesser know, or trap words as defined in trapwords.csv. trapwords.csv may be edited to be personalized. Outputs an html complete with written and audio pronunciation guides and contextual notes

2. **Marker Detector (v1.0-beta):** Designed for narrators who use physical clickers to mark flubs during recording. Detects intentional spike transients (clicks, snaps, taps) in audio files to generate both Reaper compatible .csv and Audacity-compatible .txt label tracks.

3. **Proof Listener (v1.0-beta):** Automated tool designed for professional narrators to identify script deviations (flubs, omissions, and substitutions) in their recorded chapters. Generates both Reaper compatible .csv and Audacity-compatible .txt label tracks.

4. **Postnunciation Checker (v1.0-beta):** Scans a given transcript for any hard to pronounce, lesser know, or trap words as defined in trapwords.csv. trapwords.csv may be edited to be personalized. Outputs both Reaper compatible .csv and Audacity-compatible .txt label tracks.
for easy review.

5. **Synced Caption Writer (v1.0-beta):** Creates captions from a given text, and matches the timeline 
from a given audiofile. Outputs SRT file for captioning word for word from the text.
Complete with punctuation, capitalization, spelling etc.

## 🛡️ Privacy & Security
- **100% Local Processing:** No audio or manuscript data ever leaves your machine.
- **NDA-Safe:** Designed for high-security projects requiring strict data sovereignty.

---

## 🚀 Quick Start Installation
1. **Install Python 3.9-3.13**
2. **Install Dependencies:**

# For Windows with NVIDIA GPU acceleration. Estimated processing time will be a 1:10 of your audiofile length (example: 50 min chapter will process in 5 min)

Open your terminal or Command Prompt in this folder and run:
```bash
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   pip install -r requirements.txt```

# For Windows *without* NVIDIA GPU. Note: Without GPU, the Proof Listener and Caption writer will be *much* slower. Estimated processing time will be a 1:1 for your audiofile length.
Open your terminal or Command Prompt in this folder and run:
```bash
   pip install torch
   pip install -r requirements.txt```
   
# For mac/Linux/other. Note: Without GPU, the Proof Listener and Caption writer will be *much* slower. Estimated processing time will be a 1:1 for your audiofile length.

Open your terminal or Command Prompt in this folder and run:
```bash
   pip install -r requirements.txt```


*Note: On first launch, Proof Listener will automatically download the AI model (approx. 1.5GB). This will only happen once.*

## 📖 How to Use
1. **Open the Tool Suite**: Double-click on, or run: 
```bash 
   python McFadden_Audiobooks_Editing_Suite.py```

2. **Run your Tool of choice**: click on the button for which tool you wish to run. Please note, Postnunciation Checker requires the Proof Listener to be run first.

3. **Load Audio:** (If required) Select your `.wav` chapter.

4. **Load Script:** (If required) Select the corresponding `.txt` manuscript.

5. **Load Transcript:** (If required) Select the corresponding `.txt`  transcript.

6. **Load Trap Words:** (If required) Select your customizable  `trapwords.csv`  

7. **Adjust Settings:** (Optional) Adjust all settings in the GUI to optimize your experience.

8. **Run Tool:** Once finished, For the `Marker_Detector`, `Proof_Listener` and `Postnunciation_Checker` both an Audacity-compatible `_labels.txt` file and a Reaper compatible .csv will be generated in your audio folder. For the `Prenunciation_Checker` a `.html` file will automatically load and be generated in your manuscript folder. For the Caption Writer, a .srt will be saved in your audio folder.

9. **Review:** Import the Reaper .csv into reaper's markers and review. Audacity: import generated `_labels.txt` into Audacity (File > Import > Labels) to see exactly where your Audio markers/script deviations/trap words to review occurred.
For the `Prenunciation_Checker` review the list of trap words in the chapter. click on the link to the right of each word for an audio pronunciation example.


## 💻 Proof Listener, Postnunciation Checker, and Synced Caption Writer Hardware Support
- **Windows:** Supports NVIDIA GPU (CUDA) for high-speed analysis. (Recommended)
- **macOS:** Automatically optimized for Apple Silicon/Intel (runs on CPU/int8).
- **No GPU?** The app will automatically fallback to a safe CPU mode, but will be significantly slower.

> **AI Engine:** Powered by `faster-whisper` for industry-leading accuracy.

- **GPU Acceleration (Windows Only):** Point the GPU Engines setting in Advanced Settings to your NVIDIA library folder. To find your path, run: 
```bash 
python -c "import nvidia.cublas; import os; print(os.path.dirname(nvidia.cublas.__file__))"```
Copy file path and paste into the GPU engines input

- /Pro-Tip/: For the most stable performance, copy the `.dll` files from that bin folder directly into a folder named bin inside the McFadden Audiobooks Editing Suite directory and manually enter the path name on the advanced tab. If you are not comfortable moving files, the tool will still work fine without this step—it just helps with stability on some systems


## ✉️ Contact & Support
**Created by Jamie McFadden.** (c) 2026 McFadden Audiobooks.  
Contact: [Jamie@McfaddenAudiobooks.com](mailto:Jamie@McfaddenAudiobooks.com)**