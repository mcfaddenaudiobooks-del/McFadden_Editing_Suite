# McFadden Audiobooks Editing Suite: For Independent Narrators
/100% Local AI Tools for Narrators./
A unified suite of Python utilities designed to streamline audiobook production without ever sending your NDA-restricted audio to the cloud.
This project is licensed under the terms of the MIT License.

## 🛠️ The Toolbox: 

1. **Prenunciation Checker (v1.0):** Scans a given manuscript for  any hard to pronounce, lesser know, or trap words as defined in trapwords.csv. trapwords.csv may be edited to be personalized. Outputs an html complete with written and audio pronunciation guides and contextual notes

2. **Audio Marker Detector (v1.0):** Designed for narrators who use physical clickers to mark flubs during recording. Detects intentional spike transients (clicks, snaps, taps) in audio files to generate both Reaper compatible .csv and Audacity-compatible .txt label tracks.

3. **Proof Listener (v1.0):** Automated tool designed for professional narrators to identify script deviations (flubs, omissions, and substitutions) in their recorded chapters. Generates both Reaper compatible .csv and Audacity-compatible .txt label tracks.

4. **Postnunciation Checker (v1.0):** Scans a given transcript for any hard to pronounce, lesser know, or trap words as defined in trapwords.csv. trapwords.csv may be edited to be personalized. Outputs both Reaper compatible .csv and Audacity-compatible .txt label tracks.
for easy review.

5. **Synced Caption Writer (v1.0):** Creates captions from a given text, and matches the timeline 
from a given audiofile. Outputs SRT file for captioning word for word from the text.
Complete with punctuation, capitilization, spelling etc.

## 🛡️ Privacy & Security
- **100% Local Processing:** No audio or manuscript data ever leaves your machine.
- **NDA-Safe:** Designed for high-security projects requiring strict data sovereignty.

---

## 🚀 Quick Start Installation
1. **Install Python 3.9-3.12**
2. **Install Dependencies:**

# For Windows with NVIDIA GPU acceleration
Open your terminal or Command Prompt in this folder and run:
```bash
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   pip install -r requirements.txt```

# For Windows *without* NVIDIA GPU
Open your terminal or Command Prompt in this folder and run:
```bash
   pip install torch
   pip install -r requirements.txt```
   
# For mac/Linux/other
Open your terminal or Command Prompt in this folder and run:
```bash
   pip install -r requirements.txt```


*Note: On first launch, Proof Listener will automatically download the AI model (approx. 1.5GB). This will only happen once.*

## 📖 How to Use
1. **Run you Tool of choice**: Double-click on, or run: 
```bash 
   python Proof_Listener.py```
```bash 
   python Audio_Marker_Detector.py```

2. **Load Audio:** (If required) Select your `.wav` chapter.

3. **Load Script:** (If required) Select the corresponding `.txt` manuscript.

4. **Load Transcript:** (If required) Select the corresponding `.txt`  transcript.

5. **Load Trap Words:** (If required) Select your customizable  `trapwords.csv`  

6. **Adjust Settings:** (Optional) Adjust all settings in the GUI to optimize your experience.

7. **Run Tool:** Once finished, For the `Audio_Marker_Detector`, `Proof_Listener` and `Potsnuciation_Checker` both an Audacity-compatible `_labels.txt` file and a Reaper compatible .csv will be generated in your audio folder. For the `Prenunciation_Checker' a `.html' file will automatically load and be generated in your manuscript folder. For the Caption Writer, a .srt will be saved in your audio folder.

8. **Review:** Import the generated `_labels.txt` into Audacity (File > Import > Labels) to see exactly where your Audio markers/script deviations/trap words to review occurred.
For the `Prenunciation_Checker' review the list of trap words in the chapter. click on the link to the right of each word for an audio pronunciation example.


## 💻 Proof Listener, Postnunciation Checker, and Synced Caption Writer Hardware Support
- **Windows:** Supports NVIDIA GPU (CUDA) for high-speed analysis. (Recommended)
- **macOS:** Automatically optimized for Apple Silicon/Intel (runs on CPU/int8).
- **No GPU?** The app will automatically fallback to a safe CPU mode, but will be significantly slower.

> **AI Engine:** Powered by `faster-whisper` for industry-leading accuracy.

- **GPU Acceleration (Windows Only):** Point the GPU Engines setting in Advanced Settings to your NVIDIA library folder. To find your path, run: 
```bash 
python -c "import nvidia.cublas; import os; print(os.path.dirname(nvidia.cublas.__file__))"```
Copy file path and paste into the GPU engines input

- /Pro-Tip/: For the most stable performance, copy the `.dll` files from that bin folder directly into a folder named bin inside the McFadden Audiobooks directory and point the app there.


## ✉️ Contact & Support
**Created by Jamie McFadden.** (c) 2026 McFadden Audiobooks.  
Contact: [Jamie@McfaddenAudiobooks.com](mailto:Jamie@McfaddenAudiobooks.com)**