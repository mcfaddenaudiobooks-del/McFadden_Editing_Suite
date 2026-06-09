
# -*- coding: utf-8 -*-
"""
# ==============================================================================
#  (c) 2026 McFadden Audiobooks. 
#  McFadden Audiobooks Editing Suite: Proof Listener (v1.0)
#  Author: Jamie McFadden | Jamie@McfaddenAudiobooks.com
# ==============================================================================


**Proof Listener (v1.0):** 

HARDWARE RECOMMENDATIONS:
- AI ENGINE: Powered by 'faster-whisper' (OpenAI Whisper implementation).
- GPU: Highly recommended to use an NVIDIA RTX card (or equivalent with CUDA support).
- PERFORMANCE: Running on CPU is possible but will be significantly slower.

PURPOSE: 
Automated proof listening tool. Transcribes recorded audio 
and compares against a manuscript to identify additions and flubs, 
and then reverse compares the manuscript against the transcription for omissions,
finally comparing additions and ommisions to label substitutions.

INPUTS:
    Required:
        - Audio: .mp3 or .wav
        - Script: .txt (UTF-8 )
    Optional:
        - Dialect/Era Prompt: Prompt transcriber to bias towards a specfic dialect
        - Force Transcription Vocab: Forces Transcriber to replace specific 
          transcribed words with defined script words.
            Format: 'spoken_word=script_word' mapping (e.g., 'mod=maude')
            New line for each entry
        - Vocab .txt file: Can have a saved vocab .txt file to load in
            Format: 'spoken_word=script_word' mapping (e.g., 'mod=maude')
            New line for each entry
        - Generate Reaper output: additionally generates Reaper region marker .csv file

OUTPUTS:
        - .txt file with all additions, flubs, ommisions and substitutions with time stamp
            Compatible with Audacity Label Track (_Proofing.txt) for easy editing.
        - .csv file with all additions, flubs, ommisions and substitutions Compatible
            with Reaper region markers.

DEPENDENCIES: faster-whisper, tkinter, difflib

PIP INSTALLS:
    Several pip installs are required to run this code.
    A requirements.txt file is included for easy setup.
    Run the install: Open your terminal (or Anaconda Prompt) and type:
        pip install -r requirements.txt
        
SECURITY & PRIVACY:
- RUNS 100% LOCALLY: No audio or manuscript data is ever sent to the cloud.
- Perfect for NDA-restricted projects or private narrations.

Created on Mon Mar 2 2026
Last Updated Mon Jun 8 2026 (updated to include reaper region marker output)
"""

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import difflib
import re
import threading
import time
import webbrowser
from faster_whisper import WhisperModel

# --- CONFIGURATION DEFAULTS ---
# These act as the "Recommended" settings and the fallback if fields are empty
DEFAULTS = {
    "model_path": "", # Users set this in Advanced Tab
    "lib_cublas": "", # Users set this in Advanced Tab
    "lib_cudnn": "",  # Users set this in Advanced Tab
    "no_speech_thresh": 0.6,    # Threshold to ignore non-speech segments
    "word_prob_min": 0.1,       # Min AI confidence to accept a word
    "sync_window": 3,           # Normal lookahead range for synchronization
    "recovery_lookahead": 10,   # How far to jump to find a high-quality anchor
    "base_cutoff": 0.5,         # General fuzzy match sensitivity
    "short_word_cutoff": 0.55,  # Fuzzy match for words <= 3 chars
    "mid_word_cutoff": 0.45,    # Fuzzy match for words <= 5 chars
    "flub_prob_thresh": 0.8,    # Min AI confidence to report an extra word
    "unique_word_len": 6,       # Length to treat word as a 'Unique Anchor'
    "search_radius_large": 25,  # Search distance for unique words
    "search_radius_small": 5,   # Search distance for common words
    "strict_cutoff_tiny": 0.95, # Omission strictness for tiny words
    "strict_cutoff_mid": 0.85,  # Omission strictness for mid words
    "strict_cutoff_long": 0.70, # Omission strictness for long words
    "anchor_len": 5,            # Word length required to move the 'GPS' pointer
    "max_jump_anchor": 25,      # Allowed jump distance for anchor words
    "max_jump_small": 5,        # Allowed jump distance for small words
    "backtrack_limit": 30,      # How far back to look for a timestamp anchor
    "sub_window_range": 4       # Radius to match a flub to an omission
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                return {**DEFAULTS, **saved}
        except: return DEFAULTS
    return DEFAULTS

def save_settings(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def setup_environment(cfg):
    # Use entered path, or fallback to default if empty
    paths = [
        cfg.get('lib_cublas') or DEFAULTS['lib_cublas'],
        cfg.get('lib_cudnn') or DEFAULTS['lib_cudnn']
    ]
    for p in paths:
        if os.path.exists(p):
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]
            if hasattr(os, 'add_dll_directory'):
                try: os.add_dll_directory(p)
                except: pass
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

def clean_text(text, v_map=None):
    """Aggressively normalizes text for dialect, dashes, and word-mushing."""
    if not text: return []
    # 1. Convert to lowercase
    text = text.lower()
    
    # 2. Handle curly apostrophes FIRST (convert them to straight ones)
    text = text.replace('’', "'").replace('‘', "'")
    
    # 3. TARGET DASHES: Replace all types of dashes with a space
    text = re.sub(r'[—\-\_\.\…\*\,\?\!\(\)]+', ' ', text)
    
    # 4. Strip suffixes globally (turns 'maudes' to 'maude', 'asked' to 'ask')
    #text = re.sub(r'(ed|s)\b', '', text)
    
    # 5. DIALECT/APOSTROPHE FIX: 
    # Remove apostrophes entirely so "'ead" becomes "ead" and "blow me 'ead" matches "blow me ead"
    text = text.replace("'", "")
    
    # 6. Removes all remaining punctuation (keep letters and spaces)
    text = re.sub(r'[^\w\s]', '', text)
    
    # 7. Final contraction cleanup
    text = text.replace("its", "its").replace("dont", "dont") 
    
    words= text.split()

# Apply Box 4 mapping (the character name fixes)
    if v_map:
        words = [v_map.get(w, w) for w in words]
    return words

def get_synchronized_data(full_script, whisper_words, v_map):
    # A. Clean the Script (The Gold Standard)
    script_words = clean_text(full_script, v_map=v_map)

    # B. Generate the Clean Transcript List directly from our "Perfect Array"
    # This ensures the index of 'whisper_clean_list' matches 'whisper_words' exactly
    whisper_clean_list = [w['word'] for w in whisper_words]
    
    # C. Add 'clean_word' key for Phase 1 compatibility
    for w_data in whisper_words:
         w_data['clean_word'] = w_data['word']

    return script_words, whisper_clean_list, whisper_words

def run_proofing(audio_path, script_path, custom_vocab, context_era, status_label, cfg, log_func):
    
        #  Use GUI/Default Lib Paths
    setup_environment(cfg)
    #global audio_debug_array
    #global script_debug_array
    try:
        start_time_proc = time.time()
        script_start_time = time.time()
        status_label.config(text="Status: Loading files...please wait...", fg="orange")
        
        
        model_path = cfg.get('model_path') or DEFAULTS['model_path']
        print("Loading files...please wait...")
        #  CREATE THE MAP IMMEDIATELY
        v_map = {}
        for line in custom_vocab.split('\n'):
            if '=' in line:
                k, v = line.split('=', 1)
                v_map[k.strip().lower()] = v.strip().lower()
        
        
        model = WhisperModel(model_path, device="cuda", compute_type="int8_float16")
        
        prompt = f"{context_era}. Vocabulary: {custom_vocab}"
        status_label.config(text="Status: Transcribing...", fg="#1e90ff")
        
        segments, info = model.transcribe(audio_path, word_timestamps=True, beam_size=5, initial_prompt=prompt, condition_on_previous_text=False, no_speech_threshold=cfg['no_speech_thresh'])
        audio_duration = info.duration

        #  BUILD THE PERFECT ARRAY
        whisper_words = []
        for segment in segments:
            if segment.no_speech_prob > cfg['no_speech_thresh']: continue
        # THE LIVE FEED: Print the timestamp and the text to the console
            # This shows: [00:12] word
            
            timestamp_log = time.strftime('%M:%S', time.gmtime(segment.start))
            log_entry = f"[{timestamp_log}] {segment.text}"
            print(log_entry)       # Still prints to Spyder for backup
            log_func(log_entry)    # This sends it to your new GUI box
            #print(f"[{timestamp_log}] {segment.text}")
            for word in segment.words:
                if word.probability > cfg['word_prob_min']:
                    # Clean the word AND apply the map (Mod -> maude, him. -> him)
                    # We use [0] because clean_text returns a list of words
                    cleaned_list = clean_text(word.word.strip(), v_map=v_map)
                    safe_word = cleaned_list[0] if cleaned_list else ""
                    
                    whisper_words.append({
                        "word": safe_word, # This is your clean reference
                        "start": word.start, 
                        "end": word.end, 
                        "probability": word.probability
                    })

        # --- ELASTIC SYNC LOGIC (PHASE 1: ADDITIONS/FLUBS) ---
        with open(script_path, 'r', encoding='utf-8') as f:
            full_script = f.read()
          # Pass v_map (the dictionary) instead of custom_vocab (the string)
            script_words, whisper_clean_list, whisper_words = get_synchronized_data(
                full_script, whisper_words, v_map
            )
        
        # --- NEW: STUTTER SCRUBBER (HIGHEST PROBABILITY) ---
        # We process the raw 'whisper_words' to remove AI temporal loops
        cleaned_whisper_words = []
        i = 0
        while i < len(whisper_words):
            current_word = whisper_words[i]
            same_time_group = [current_word]
            next_j = i + 1
            # Group words that share the exact same start timestamp
            while next_j < len(whisper_words) and whisper_words[next_j]['start'] == current_word['start']:
                same_time_group.append(whisper_words[next_j])
                next_j += 1
            
            # Keep only the word the AI was most confident in
            winner = max(same_time_group, key=lambda x: x['probability'])
            cleaned_whisper_words.append(winner)
            i = next_j

# --- CALCS ---
        total_words = len(script_words)
        wpm = (total_words / (audio_duration / 60)) if audio_duration > 0 else 0
        
# Update the main list so the rest of the script uses the scrubbed data
        whisper_words = cleaned_whisper_words 
        # ---------------------------------------------------

        output_path = audio_path.rsplit('.', 1)[0] + "_Proof_Listen.txt"
        additions_count = 0
        script_idx = 0
        
        time_map = {} 
        flub_data_list = [] # Store raw flub info for substitution matching
        
        window = cfg["sync_window"]  
        recovery_lookahead = cfg["recovery_lookahead"]  
        cutoff_val = cfg["base_cutoff"]   

        for w_idx, w_data in enumerate(whisper_words):
            n_word = w_data.get('clean_word', '')
            if not n_word: continue

            match_found = False
            
            # --- STEP 1: INCREMENTAL STEP-FORWARD (The "Miss Miss" Fix) ---
            # Look only at the VERY NEXT script word first to prevent skipping duplicates.
            if script_idx < len(script_words):
                target_word = script_words[script_idx]
                
                # Apply your specific lowered thresholds
                if len(target_word) <= 3: current_cutoff = cfg["short_word_cutoff"]
                elif len(target_word) <= 5: current_cutoff = cfg["mid_word_cutoff"]
                else: current_cutoff = cutoff_val
                
                if difflib.get_close_matches(n_word, [target_word], cutoff=current_cutoff):
                    time_map[script_idx] = w_data['start']
                    script_idx += 1  # Polite step: exactly one word forward
                    match_found = True

            # --- STEP 2: WINDOW SEARCH (Emergency Backup) ---
            # If the next word wasn't a match, then scan the small local window.
            if not match_found:
                search_start = 0 if script_idx == 0 else max(0, script_idx - 1)
                current_search_limit = 500 if script_idx == 0 else window + 2
                
                for i in range(current_search_limit):
                    target_idx = search_start + i
                    if target_idx < len(script_words):
                        target_word = script_words[target_idx]
                        
                        # Use the same lowered thresholds for consistency
                        if len(target_word) <= 3: temp_cutoff = cfg["short_word_cutoff"]
                        elif len(target_word) <= 5: temp_cutoff = cfg["mid_word_cutoff"]
                        else: temp_cutoff = cutoff_val
                        
                        if difflib.get_close_matches(n_word, [target_word], cutoff=temp_cutoff):
                            time_map[target_idx] = w_data['start']
                            script_idx = target_idx + 1 # Teleport sync to this anchor
                            match_found = True
                            break
            
            # --- STEP 3: LONG DISTANCE RECOVERY ---
            # If still not found, check further ahead for a high-quality anchor.
            if not match_found:
                for i in range(recovery_lookahead):
                    target_idx = script_idx + i
                    if target_idx < len(script_words):
                        candidate = script_words[target_idx]
                        if len(candidate) >= 4 and difflib.get_close_matches(n_word, [candidate], cutoff=cfg["flub_prob_thresh"]):
                            time_map[target_idx] = w_data['start']
                            script_idx = target_idx + 1
                            match_found = True
                            break

            # If no match anywhere, log as a Flub/Addition
            if not match_found and w_data['probability'] > cfg["flub_prob_thresh"]:
                flub_data_list.append({
                    'start': w_data['start'],
                    'end': w_data['end'],
                    'word': w_data['word'],
                    'clean_word': n_word,
                    'w_idx': w_idx,
                    'is_sub': False
                })
                additions_count += 1

# --- PHASE 2: REVERSE CHECK (OMISSIONS & SUBSTITUTIONS) ---
        status_label.config(text="Status: Omissions Checking...", fg="purple")
        
        
        omission_count = 0
        sub_count = 0
        transcript_ptr = 0
        
        # Temporary list to hold raw omission data before bundling
        raw_omissions = []
        
        for s_idx, s_word in enumerate(script_words):
            if len(s_word) <= 2: continue
        #  Check if Phase 1 already matched this script word
            # If s_idx is in time_map, it means it was found and is NOT an omission.
            if s_idx in time_map:
                found_in_audio = True
                # Sync the transcript pointer to this known good location
                for i, w_check in enumerate(whisper_words):
                    if w_check['start'] == time_map[s_idx]:
                        transcript_ptr = i + 1
                        break
                continue
            
            found_in_audio = False
            is_unique = len(s_word) > cfg["unique_word_len"]
            search_radius = cfg["search_radius_large"] if is_unique else cfg["search_radius_small"]
            
            
            search_start = max(0, transcript_ptr - search_radius)
            search_end = min(len(whisper_clean_list), transcript_ptr + search_radius)

                
                # Search with specific cutoff based on word length
# --- TIGHTENED INDEX-BASED MATCHING ---
            # Increase strictness based on word length to prevent "Desperation Matches"
            if len(s_word) <= 3:
                target_cutoff = cfg["strict_cutoff_tiny"]  # Must be an almost exact match for tiny words
            elif len(s_word) <= 5:
                target_cutoff = cfg["strict_cutoff_mid"]
            else:
                target_cutoff = cfg["strict_cutoff_long"]  # More grace for long unique words
            
            for i in range(search_start, search_end):
                # Check Box 4 mapping BEFORE checking difflib
                audio_word_clean = whisper_clean_list[i]
                # High-Confidence Match
                # NEW: Prioritize an EXACT match to fix "him/him" double-reporting
                if s_word == audio_word_clean:
                    transcript_ptr = i + 1
                    found_in_audio = True
                    break
                
                if  difflib.get_close_matches(s_word, [audio_word_clean], cutoff=target_cutoff):
                    
                    # STABILITY CHECK: Don't let the pointer jump more than 15 words 
                    # unless it's a perfect match on a long word.
                    jump_distance = abs(i - transcript_ptr)
                    # If it's a tiny word, don't let it pull the whole script forward
                    # Define how much we trust this word to move our 'GPS' (pointer)
                    is_anchor = len(s_word) >= cfg["anchor_len"]
                    max_allowed_jump = cfg["max_jump_anchor"] if is_anchor else cfg["max_jump_small"] 
    
                    if jump_distance <= max_allowed_jump:
                        transcript_ptr = i + 1
                        found_in_audio = True
                        break # Match accepted, move to next script word
                    else:
                        # If it's a short word far away, ignore the match to prevent the cascade
                        # We don't 'break' here, we keep looking for a closer match
                        continue

            if not found_in_audio:
                # Look backward in the script to find the last known GOOD timestamp.
                # This keeps the 'est_time' accurate even if the pointer is lagging.
                est_time = 0.0
                for check_idx in range(s_idx, max(-1, s_idx - cfg["backtrack_limit"]), -1):
                    if check_idx in time_map:
                        est_time = time_map[check_idx]
                        break
                
                # Fallback if we have no confirmed anchors nearby
                if est_time == 0.0:
                    safe_ptr = min(transcript_ptr, len(whisper_words) - 1)
                    est_time = whisper_words[safe_ptr]['start']    

                
                # Check for Substitution
                matched_flub = None
                for flub in flub_data_list:
                    f_idx = flub.get('w_idx')
                    #if abs(flub['w_idx'] - transcript_ptr) <= 3:
                    if f_idx is not None and (transcript_ptr - cfg["sub_window_range"] <= f_idx <= transcript_ptr + cfg["sub_window_range"]):
                        matched_flub = flub
                        break
                 
                if matched_flub:

                # We compare the cleaned script word to the cleaned flub word.
                # If the map turned 'mod' into 'maude', this now matches perfectly.
                # We use .get() as a safety fallback.
                    f_word_clean = matched_flub.get('clean_word', matched_flub['word'])
            
                    if s_word == f_word_clean:
                        found_in_audio = True # It's a match! Not an error.
                        transcript_ptr = matched_flub['w_idx'] + 1 # DIRECT SYNC via Index
                        continue

                    else:
                        raw_omissions.append({"time": est_time, "text": s_word, "sub_with": matched_flub['word'],"s_idx": s_idx})
                        matched_flub['is_sub'] = True
                        sub_count += 1
                        transcript_ptr = matched_flub['w_idx'] + 1 # DIRECT SYNC via Index

                else:
                    # --- THE FIX: SHORT WORD SKEPTICISM ---
                    is_short_word = len(s_word) <= 5
                    
                    # If it's a short word (who, him), try one more search with a lower cutoff 
                    # to see if the AI heard *anything* similar nearby.
                    if is_short_word:
                        retry_matches = difflib.get_close_matches(s_word, whisper_clean_list[search_start:search_end], cutoff=cfg["mid_word_cutoff"])
                        if retry_matches:
                            found_in_audio = True
                            continue # Skip adding to omissions

                    # Still not found? Then it's a real omission.
                    raw_omissions.append({"time": est_time, "text": s_word, "sub_with":matched_flub['word'] if matched_flub else None, "s_idx": s_idx })
                    omission_count += 1

        # --- BUNDLING LOGIC ---
# --- PHASE 3: INDEX-BASED BUNDLING ---
        final_phase2_lines = []
        if raw_omissions:
            current_bundle = raw_omissions[0]
            words_in_bundle = [current_bundle['text']]
            last_idx = current_bundle['s_idx']
            for next_om in raw_omissions[1:]:
                # Check if this word is the immediate next word in the script index
                is_neighbor = (next_om['s_idx'] == current_bundle['s_idx'] + len(words_in_bundle))
                
                # Check if it's part of the same substitution
                same_sub = (next_om['sub_with'] == current_bundle['sub_with'] and next_om['sub_with'] is not None)
        
                if is_neighbor or same_sub:
                    words_in_bundle.append(next_om['text'])
                    last_idx = next_om['s_idx']
                else:
                    # Save the previous bundle using its timestamp for Audacity
                    phrase = " ".join(words_in_bundle)
                    t = current_bundle['time']
                    
                    if current_bundle['sub_with']:
                        final_phase2_lines.append(f"{t:.3f}\t{t:.3f}\tSUB: '{phrase}' -> '{current_bundle['sub_with']}'\n")
                    else:
# FIXED: idx_range now correctly uses the last_idx of the BUNDLE
                        idx_range = f"[{current_bundle['s_idx']}]" if len(words_in_bundle) == 1 else f"[{current_bundle['s_idx']}-{last_idx}]"
                        final_phase2_lines.append(f"{t:.3f}\t{t:.3f}\tOMISSION {idx_range}: Missing '{phrase}'\n")
                    
                    # Start new bundle
                    current_bundle = next_om
                    words_in_bundle = [next_om['text']]
                    last_idx = next_om['s_idx']
            
            # Handle the final bundle
            phrase = " ".join(words_in_bundle)
            t = current_bundle['time']
            if current_bundle['sub_with']:
                final_phase2_lines.append(f"{t:.3f}\t{t:.3f}\tSUB: '{phrase}' -> '{current_bundle['sub_with']}'\n")
            else:
                idx_range = f"[{current_bundle['s_idx']}]" if len(words_in_bundle) == 1 else f"[{current_bundle['s_idx']}-{last_idx}]"
                final_phase2_lines.append(f"{t:.3f}\t{t:.3f}\tOMISSION {idx_range}: Missing '{phrase}'\n")
            
           # --- BUILD THE AUDIO-FIRST MASTER ARRAY ---
        audio_master_list = []
        for idx, w_data in enumerate(whisper_words):
            # Find if this audio word was mapped to a script index in Phase 1
            matched_script_word = None
            for s_idx, timestamp in time_map.items():
                if timestamp == w_data['start']:
                    matched_script_word = script_words[s_idx]
                    break
            
            audio_master_list.append({
                "index": idx,
                "audio_word": w_data['word'],
                "start": w_data['start'],
                "end": w_data['end'],
                "probability": w_data['probability'],
                "mapped_script_word": matched_script_word  # None if it's a FLUB/EXTRA
            })
            # --- BUILD THE SCRIPT-FIRST MASTER ARRAY ---
        script_master_list = []
        for s_idx, s_word in enumerate(script_words):
            is_omission = True
            found_time = None
            
            if s_idx in time_map:
                is_omission = False
                found_time = time_map[s_idx]
            
            script_master_list.append({
                "script_index": s_idx,
                "script_word": s_word,
                "found_in_audio": not is_omission,
                "timestamp": found_time if found_time else "ESTIMATED_OMISSION"
            })
            
            # Exporting for manual troubleshooting
        debug_file = audio_path.rsplit('.', 1)[0] + "_Transcript.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write("=== AUDIO-FIRST VIEW (Is it an Extra Word?) ===\n")
            for item in audio_master_list:
                match_status = f"MATCHED: {item['mapped_script_word']}" if item['mapped_script_word'] else "!!! EXTRA/FLUB !!!"
                f.write(f"[{item['start']:>7.2f}s] AI: {item['audio_word']:<15} | {match_status} (Prob: {item['probability']:.2f})\n")
            
            f.write("\n\n=== SCRIPT-FIRST VIEW (Is it an Omission?) ===\n")
            for item in script_master_list:
                status = "FOUND" if item['found_in_audio'] else "MISSING"
                f.write(f"Idx: {item['script_index']:<5} | Word: {item['script_word']:<15} | Status: {status}\n")
        

# --- FINAL WRITE ---
        reaper_lines = ["#,Name,Start,End,Length,Color"]
        region_idx = 1
        
        with open(output_path, 'w', encoding='utf-8') as label_file:
            label_file.write("--- PHASE 1: EXTRA WORDS / FLUBS ---\n")
            for flub in flub_data_list:
                if not flub['is_sub']:
                    label_text = f"FLUB/EXTRA: {flub['word']}"
                    label_file.write(f"{flub['start']:.3f}\t{flub['end']:.3f}\t{label_text}\n")
                    # Add to Reaper list
                    reaper_lines.append(f"R{region_idx},\"{label_text}\",{flub['start']:.3f},{flub['end']:.3f},{flub['end']-flub['start']:.3f},")
                    region_idx += 1
                else:
                    additions_count -= 1 

            label_file.write("\n--- PHASE 2: OMISSIONS & SUBSTITUTIONS ---\n")
            for line in final_phase2_lines:
                label_file.write(line)
                # Parse the line to add to Reaper if it's a valid label line
                # Assuming your final_phase2_lines are tab-separated "Start\tEnd\tText"
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    start, end, text = parts[0], parts[1], parts[2]
                    reaper_lines.append(f"R{region_idx},\"{text}\",{start},{end},{float(end)-float(start):.3f},")
                    region_idx += 1

        # Save the Reaper file
        reaper_path = os.path.splitext(output_path)[0] + "_Reaper.csv"
        with open(reaper_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(reaper_lines))
        duration = time.time() - start_time_proc
        avg_conf = (sum(w['probability'] for w in whisper_words) / len(whisper_words)) * 100 if whisper_words else 0
        efficiency = (audio_duration / duration)
        print("\n" + "="*40 + "\nCHAPTER ANALYSIS SUMMARY\n" + "="*40)
        print(f"Processing Time:    {duration:.2f} seconds")
        print(f"Avg. Confidence:    {avg_conf:.2f}%")
        print(f"Additions/Flubs:    {additions_count}")
        print(f"Substitutions:      {sub_count}")
        print(f"Possible Omissions: {omission_count}")
        print(f"Label File:         {output_path}\n" + "="*40)

        status_label.config(text="Status: Complete!", fg="green")
        

        
        summary = (
            #f"\n\nAnalysis Complete!\n"
            f"\n\n--- CHAPTER ANALYSIS SUMMARY ---\n"
            f"\nAdditions: {additions_count}\n"
            f"Substitutions: {sub_count}\n"
            f"Omissions: {omission_count}\n"
            f"\n--- Performance Stats ---\n"
            f"Average WPM: {wpm:.1f}\n"
            f"Processing Time: {duration/60:.2f} min\n"
            f"Efficiency: {efficiency:.1f}x (Audio vs Script speed)\n\n"
            f"Output File: {os.path.basename(output_path)}"
            f"\nReaper File: {os.path.basename(reaper_path)}"
        )
        log_func(summary)
        
        def open_tip_jar():
    
            webbrowser.open_new("https://ko-fi.com/mcfaddenaudiobooks")
           
 
        # --- CUSTOM SUCCESS WINDOW ---
        success_win = tk.Toplevel(root) # 'root'  main app window variable
        success_win.title("Processing Complete")
        success_win.geometry("400x500")
        success_win.resizable(False, False)
        
        # 1. Header & Summary Icon
        tk.Label(success_win, text="✔ SUCCESS", font=("Arial", 14, "bold"), fg="#28a745").pack(pady=(10, 5))
        
        # 2. The Summary Text 
        summary_label = tk.Label(success_win, text=summary, justify="left", font=("Consolas", 10), padx=20)
        summary_label.pack(pady=5)
        
        # 3. The Tip Jar Section 
        tk.Frame(success_win, height=1, bg="lightgray").pack(fill="x", padx=40, pady=10)
        tk.Label(success_win, text="Did this tool save you time today?", font=("Arial", 9, "italic")).pack()
        
        tip_button = tk.Button(success_win, 
                               text="Buy the Dev a Coffee", 
                               command=open_tip_jar,
                               bg="#FF813F", #  orange
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
        

    
    except Exception as e:
        status_label.config(text="Status: Error (check spyder console)", fg="red")
        messagebox.showerror("System Error", str(e))
class GUI:
    def __init__(self, root):
        self.root = root; self.root.title("McFadden Audiobooks: Proof Listener"); 
        self.root.geometry("600x875")
        self.root.configure(bg="#2c2c2c")
        self.current_cfg = load_settings()
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
                
# 3. Create label and keep a HARD reference
                self.logo_label = tk.Label(self.root, image=self.logo_img,bg="#2c2c2c")
                self.logo_label.image = self.logo_img 
                self.logo_label.pack(pady=5)
            except Exception as e:
                print(f"Could not load logo: {e}")
    
        tk.Label(root, text="McFadden Audiobooks Editing Suite", font=("Arial", 11, "bold"), fg="white", bg="#2c2c2c").pack(pady=1)
        tk.Label(root, text="For Independent Narrators", font=("Arial", 11, "italic"), fg="#b0b0b0", bg="#2c2c2c").pack(pady=1)
        tk.Label(root, text="Proof Listener", font=("Arial", 18, "bold"), fg="white", bg="#2c2c2c").pack(pady=5)
        self.current_cfg = load_settings()
        
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#2c2c2c', borderwidth=0)
        style.configure('TNotebook.Tab', background='#404040', foreground='white')
        style.map('TNotebook.Tab', background=[('selected', '#497d86')], foreground=[('selected', 'white')])
        style.configure('TFrame', background='#2c2c2c')

        self.nb = ttk.Notebook(root)
        self.tab_main = ttk.Frame(self.nb)
        self.tab_adv = ttk.Frame(self.nb)
        self.nb.add(self.tab_main, text=" Main Analysis ")
        self.nb.add(self.tab_adv, text=" Advanced Settings ")
        self.nb.pack(expand=1, fill="both")
        
        self.setup_main_tab()
        self.setup_adv_tab()

        # --- FOOTER SECTION ---
        footer_frame = tk.Frame(root, bg="#2c2c2c")
        footer_frame.pack(side="bottom", pady=5, fill="x")

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


    def gui_log(self, message):
        """Thread-safe way to write to the live_log widget."""
        self.live_log.config(state='normal')
        self.live_log.insert(tk.END, message + "\n")
        self.live_log.see(tk.END) # Auto-scroll to the bottom
        self.live_log.config(state='disabled')

    def save_log_to_file(self):
        """Saves the current content of the live log to a text file."""
        # Get content (1.0 is start, end-1c removes the extra newline tk adds)
        log_content = self.live_log.get("1.0", "end-1c")
        
        if not log_content.strip():
            messagebox.showwarning("Empty Log", "There is nothing in the log to save!")
            return

        # Open the Save As dialog
        f = filedialog.asksaveasfile(
            mode='w', 
            defaultextension=".txt",
            initialfile="Raw_Transcript_Notes.txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if f:
            f.write(log_content)
            f.close()
            messagebox.showinfo("Success", "Log saved successfully.")

    def clear_live_log(self):
        """Wipes the live transcription log."""
        self.live_log.config(state='normal')
        self.live_log.delete('1.0', tk.END)
        self.live_log.config(state='disabled')

    def setup_main_tab(self):
        f = self.tab_main
        f.configure(style='TFrame')

        
# --- STEP 1: AUDIO ---
        # Label on its own line
        tk.Label(f, text="Step 1: Load Audio File (.mp3 or .wav)",fg="white", bg="#2c2c2c").pack(anchor="w", padx=10, pady=(10, 0))

        # Frame for Entry + Button
        s1_frame = tk.Frame(f, bg="#2c2c2c")
        s1_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        self.audio_entry = tk.Entry(s1_frame, width=50)
        self.audio_entry.pack(side="left", padx=(10, 5), expand=True, fill="x")
        
        tk.Button(s1_frame, text="Browse Audio",bg="#497d86", fg="white", font=("Arial", 8), 
                  command=lambda: self.browse_file(self.audio_entry)).pack(side="right")


# --- STEP 2: SCRIPT ---
        # Label stays on its own line
        tk.Label(f, text="Step 2: Load Script File (.txt)",fg="white", bg="#2c2c2c").pack(anchor="w", padx=10, pady=(10, 0))

        # Frame for Entry + Button on the line below
        s2_frame = tk.Frame(f, bg="#2c2c2c")
        s2_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        # Entry box packed to the left, expanding to fill space
        self.script_entry = tk.Entry(s2_frame, width=50)
        self.script_entry.pack(side="left", padx=(10, 5), expand=True, fill="x")
        
        # Browse button packed to the right
        tk.Button(s2_frame, text="Browse Script",bg="#497d86", fg="white", font=("Arial", 8), 
                  command=lambda: self.browse_script(self.script_entry)).pack(side="right")     


# --- STEP 3: DIALECT ---
        # Label stays on its own line to match Step 1 & 2
        tk.Label(f, text="Step 3: Dialect / Era Prompt (e.g. Victorian)",fg="white", bg="#2c2c2c").pack(anchor="w", padx=10, pady=(10, 0))

        # Frame to wrap the entry so it aligns with the frames above
        s3_frame = tk.Frame(f, bg="#2c2c2c")
        s3_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        # Setting side="left" and expand=True ensures the box matches the width of the others
        self.dialect_entry = tk.Entry(s3_frame, width=50)
        self.dialect_entry.insert(0, "General")
        self.dialect_entry.pack(side="left",padx=(10, 5), expand=True, fill="x")
        
        # We add a small invisible spacer or just padding to account for the missing button space
        tk.Label(s3_frame, text="", bg="#2c2c2c", width=12).pack(side="right")

# --- STEP 4: VOCAB ---
        # Label stays on its own line to match Step 1, 2, & 3
        tk.Label(f, text="Step 4: Force Transcription Vocab (Format: wrong=correct)",fg="white", bg="#2c2c2c").pack(anchor="w", padx=10, pady=(10, 0))

        # Frame to hold both the ScrolledText and the Import Button
        s4_frame = tk.Frame(f, bg="#2c2c2c")
        s4_frame.pack(fill="x", padx=10, pady=(10, 5))

        # The Vocabulary Box
        # height=2 keeps it compact, but the button will center against it
        self.vocab_box = scrolledtext.ScrolledText(s4_frame, height=1, width=45)
        self.vocab_box.pack(side="left", padx=(10, 5), expand=True, fill="both")

        # The Import Button
        # Packing this 'right' inside the same frame centers it vertically by default
        tk.Button(s4_frame, text="Import List (.txt)",bg="#497d86", fg="white", font=("Arial", 8), 
                  command=self.import_vocab).pack(side="right")

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
        ).pack(anchor="w", padx=10, pady=(5, 0))


        log_header_frame = tk.Frame(f, bg="#2c2c2c")
        log_header_frame.pack(fill="x", padx=10)
        tk.Label(log_header_frame, text="Live Transcription Log (Uncorrected Raw Transcription):",fg="white", bg="#2c2c2c").pack(side="left")
        
        tk.Button(log_header_frame, text="Clear Log", command=self.clear_live_log, 
                  font=("Arial", 8),fg="white", bg="#497d86").pack(side="right", padx=2)
        tk.Button(log_header_frame, text="Save Log", command=self.save_log_to_file, 
                  font=("Arial", 8),fg="white", bg="#00273d").pack(side="right", padx=2)
        
        self.live_log = scrolledtext.ScrolledText(f, height=8, width=65, state='disabled', bg="#f0f0f0")
        self.live_log.pack(padx=10, pady=2)

        # # Controls / Status Bottom Row
        footer_btn_frame = tk.Frame(f, bg="#2c2c2c")
        footer_btn_frame.pack(fill="x", padx=10, pady=5)
        
        self.status_label = tk.Label(footer_btn_frame, text="Status: Ready", bg="#2c2c2c", font=("Arial", 10, "bold"), fg="#497d86")
        self.status_label.pack(side="left")
        
        tk.Button(footer_btn_frame, text="Run Proof Listener", command=self.start, width=22, bg="#497d86", fg="white", font=("Arial", 11, "bold"),  activebackground="#5c9ca5").pack(side="right")


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
            ent.insert(0, str(self.current_cfg.get(key, "")))
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
        
    def browse_file(self, entry_widget):
        f = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.wv"), ("All Files", "*.*")]); 
        if f: entry_widget.delete(0, tk.END); entry_widget.insert(0, f)
        
    def browse_script(self, entry_widget):
        f = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]); 
        if f: entry_widget.delete(0, tk.END); entry_widget.insert(0, f)

    def browse_dir(self, entry_widget):
        d = filedialog.askdirectory(); 
        if d: entry_widget.delete(0, tk.END); entry_widget.insert(0, d)
    
    def import_vocab(self):
        f = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if f:
            with open(f, 'r', encoding='utf-8') as vf: self.vocab_box.insert(tk.END, "\n" + vf.read())

    def save_adv(self):
        new_cfg = {}
        for k, entry in self.adv_entries.items():
            val = entry.get().strip()
            # If the setting is a path, keep it a string. Otherwise, try converting to float.
            if any(x in k for x in ["path", "lib"]):
                new_cfg[k] = val
            else:
                try:
                    new_cfg[k] = float(val) if "." in val else int(val)
                except:
                    new_cfg[k] = val
        save_settings(new_cfg)
        self.current_cfg = load_settings()
        messagebox.showinfo("Saved", "Settings updated and saved to config.json")

    def reset_adv(self):
        for k, v in DEFAULTS.items():
            if k in self.adv_entries: self.adv_entries[k].delete(0, tk.END); self.adv_entries[k].insert(0, str(v))

    def start(self):
        cfg = load_settings() 
        threading.Thread(target=run_proofing, args=(self.audio_entry.get(), self.script_entry.get(), self.vocab_box.get("1.0", tk.END).strip(), self.dialect_entry.get(), self.status_label, cfg, self.gui_log), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk(); app =GUI(root); root.mainloop()
