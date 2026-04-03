import os
import re
import json
import time
import zipfile
import subprocess
import requests
from typing import List, Dict

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "kimi-k2.5:cloud"  # The model you specified
ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
WAN2FLUX_DIR = os.path.join(os.path.dirname(__file__), "wan2flux_2")

def invoke_wgp(zip_path: str, stage_name: str):
    """Executes wgp.py locally to process the generated zip payload."""
    print(f"\n[>>>] Triggering GPU engine for: {stage_name}")
    print(f"      Running: python wgp.py --process {zip_path}")
    
    # We must properly format the absolute path for the zip payload so wan2flux can find it
    abs_zip_path = os.path.abspath(zip_path)
    
    try:
        # Run wgp.py exclusively from within its directory so its dependencies resolve
        result = subprocess.run(
            ["python", "wgp.py", "--process", abs_zip_path], 
            cwd=WAN2FLUX_DIR,
            check=False, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        if result.returncode == 0:
            print(f"[OK] Completed {stage_name} successfully!")
        else:
            print(f"[WARN] Command ran but returned non-zero code. Output might hold errors.")
        return True
    except FileNotFoundError:
        print(f"[FAIL] Could not find 'python' or 'wgp.py' inside {WAN2FLUX_DIR}.")
        return False

# We create directories if they don't exist
os.makedirs(ASSET_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_via_ollama(prompt: str) -> str:
    """Send prompt to Ollama API and return text."""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    print(f"[*] Calling Ollama ({MODEL_NAME})...")
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"[!] Ollama request failed: {e}")
        return ""

def step1_fetch_youtube_topic(user_topic: str) -> str:
    """Mock/Wrapper for Niche Discovery."""
    print(f"\n--- STEP 1: Fetching Niche Details for '{user_topic}' ---")
    # In a fully integrated version, this would call viral_optimizer.py
    # For now, we simulate finding the trending angle.
    niche_context = f"Trending angle for {user_topic}: High engagement, fast-paced action, vivid colors."
    return niche_context

def step2_write_script(topic: str, context: str, num_prompts: int) -> List[str]:
    """Uses Ollama to generate specified number of base prompts."""
    print(f"\n--- STEP 2: Writing Script for '{topic}' ({num_prompts} Prompts) ---")
    sys_prompt = f"""You are a professional video script writer. 
Topic: {topic}
Context: {context}
Requirement: Create EXACTLY {num_prompts} dynamic scene base prompts. Each prompt represents a 10-second video clip.
Keep the description highly visual, active, and detailed for AI generation.
Output format: Provide each base prompt on a new line. Do not include numbering or extra text."""
    
    script_text = generate_ollama_safe(sys_prompt)
    prompts = [p.strip() for p in script_text.split("\n") if p.strip()]
    
    # Fallback to ensure we have exactly num_prompts
    while len(prompts) < num_prompts:
        prompts.append(f"Extended scene for {topic} - continuing action...")
    prompts = prompts[:num_prompts]
    
    print(f"[*] Generated {len(prompts)} base scene prompts.")
    return prompts

def generate_ollama_safe(prompt: str):
    res = generate_via_ollama(prompt)
    if not res:
        return "Fallback generated prompt due to Ollama error."
    return res

def step3_extract_metadata(script: List[str]) -> Dict[str, List[str]]:
    """Extracts characters, props, environments from the script."""
    print("\n--- STEP 3: Extracting Characters, Props, Environments ---")
    
    # Compile the text for extraction
    full_script = "\\n".join(script)
    
    sys_prompt = f"""Analyze the following script and extract:
1. Unique Characters
2. Core Props
3. Environments

Return ONLY valid JSON format like:
{{
  "Characters": ["Name 1", "Name 2"],
  "Props": ["Prop 1"],
  "Environments": ["Environment 1"]
}}

Script:
{full_script}"""
    
    metadata_json = generate_ollama_safe(sys_prompt)
    try:
        # Simple extraction of JSON block
        start = metadata_json.find('{')
        end = metadata_json.rfind('}') + 1
        if start != -1 and end != 0:
            return json.loads(metadata_json[start:end])
    except Exception as e:
        print(f"[!] JSON parsing failed: {e}")
        
    return {"Characters": ["Protagonist"], "Props": [], "Environments": ["Main Setting"]}

def step4_create_asset_queue(metadata: Dict[str, List[str]]):
    """Zips the asset requests for Flux2."""
    print("\n--- STEP 4: Building Asset Generation Queue (Flux2) ---")
    queue_data = []
    
    # Assign ID
    uid = 1
    for char in metadata.get("Characters", []):
        queue_data.append({"id": uid, "prompt": f"Character sprite sheet for {char}, plain background, multiple poses", "type": "character"})
        uid += 1
    for env in metadata.get("Environments", []):
        queue_data.append({"id": uid, "prompt": f"Wide establishing shot of {env}, high detail, 8k", "type": "environment"})
        uid += 1

    queue_json_path = os.path.join(ASSET_DIR, "queue.json")
    with open(queue_json_path, 'w') as f:
        json.dump(queue_data, f, indent=4)
        
    zip_path = os.path.join(ASSET_DIR, "queue_assets.zip")
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(queue_json_path, arcname="queue.json")
    print(f"[*] Saved asset queue payload to {zip_path}")
    return zip_path

def step5_6_create_frame_queue(prompts: List[str], metadata: Dict[str, List[str]], frame_mode: str):
    """Creates Frame requests for Flux2."""
    print(f"\n--- STEP 5 & 6: Building Frame Queue (Mode {frame_mode}) ---")
    
    # Simulate the filenames that would be returned from Phase 2 (Asset Generation)
    reference_images = []
    uid = 1
    for char in metadata.get("Characters", []):
        reference_images.append(f"asset_{uid}.jpg")  # Simulating downloaded asset filename
        uid += 1
    for env in metadata.get("Environments", []):
        reference_images.append(f"asset_{uid}.jpg")
        uid += 1
        
    queue_data = []
    
    if frame_mode == '2':
        # Single Image Mode
        for i, p in enumerate(prompts):
            seq = i + 1
            queue_data.append({
                "id": f"{seq}_single",
                "prompt": p,
                "reference_images": reference_images
            })
    else:
        # First + Last Mode
        for i, p in enumerate(prompts):
            seq = i + 1
            # First frame
            queue_data.append({
                "id": f"{seq}_first",
                "prompt": f"Start of keyframe action, {p}",
                "reference_images": reference_images
            })
            # End frame
            queue_data.append({
                "id": f"{seq}_last",
                "prompt": f"End of keyframe action, {p}",
                "reference_images": reference_images
            })
        
    queue_json_path = os.path.join(ASSET_DIR, "queue_frames.json")
    with open(queue_json_path, 'w') as f:
        json.dump(queue_data, f, indent=4)
        
    zip_path = os.path.join(ASSET_DIR, "queue_frames.zip")
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(queue_json_path, arcname="queue.json")
    print(f"[*] Saved frame queue payload to {zip_path}")
    return zip_path

def step7_create_video_queue(prompts: List[str], frame_mode: str):
    """Creates LTX 2.3 queue referencing generated frames."""
    print("\n--- STEP 7: Building Video Generation Queue (LTX 2.3) ---")
    queue_data = []
    for i, p in enumerate(prompts):
        seq = i + 1
        
        if frame_mode == '2':
            # Sequence: 1->(1,none), 2->(2,3), 3->(3,4)...
            start_img = f"{seq}_single.jpg"
            if seq == 1:
                end_img = ""
            elif seq < len(prompts):
                end_img = f"{seq+1}_single.jpg"
            else:
                end_img = ""
                
            queue_data.append({
                "id": seq,
                "prompt": p,
                "first_frame": start_img,
                "last_frame": end_img,
            })
        else:
            # Use distinct first and last frames
            queue_data.append({
                "id": seq,
                "prompt": p,
                "first_frame": f"{seq}_first.jpg",
                "last_frame": f"{seq}_last.jpg",
            })
    
    queue_json_path = os.path.join(ASSET_DIR, "queue_ltx.json")
    with open(queue_json_path, 'w') as f:
        json.dump(queue_data, f, indent=4)
        
    zip_path = os.path.join(ASSET_DIR, "queue_ltx.zip")
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(queue_json_path, arcname="queue.json")
    print(f"[*] Saved video queue payload to {zip_path}")
    return zip_path

def step8_stitch_videos(segment_count: int):
    """Uses FFMPEG to concatenate the output mp4s."""
    print("\n--- STEP 8: Stitching Final Video ---")
    list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    
    with open(list_path, 'w') as f:
        for i in range(1, segment_count + 1):
            vid_path = os.path.join(OUTPUT_DIR, f"{i}_video.mp4")
            # In a real run, verify if file exists. We'll write it anyway.
            f.write(f"file '{vid_path}'\\n")
            
    final_output = os.path.join(OUTPUT_DIR, "final_stitched_video.mp4")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
        "-i", list_path, "-c", "copy", final_output
    ]
    
    print(f"[*] Running FFmpeg: {' '.join(cmd)}")
    try:
        # We don't block fully if files don't exist in dry-run
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[*] Final video successfully stitched: {final_output}")
    except Exception as e:
        print("[!] FFmpeg stitch encountered an issue (missing files likely if dry-run).")

def main():
    print("=============================================")
    print("  AI Video Pipeline Orchestrator (Dry-Run)")
    print("=============================================")
    
    input_type = input("Do you want to provide a [1] Topic/Niche or [2] Full Story? (1/2) [default: 1]: ").strip()
    
    if input_type == '2':
        story_input = input("Enter the Full Story (or path to a .txt file): ").strip()
        if os.path.isfile(story_input):
            with open(story_input, 'r', encoding='utf-8') as f:
                context = f.read()
            topic = os.path.basename(story_input).replace('.txt', '')
        else:
            context = story_input
            topic = "User Provided Story"
    else:
        topic = input("Enter the Niche/Topic for the YouTube Channel: ").strip()
        if not topic:
            topic = "Epic Space Adventure"
        context = step1_fetch_youtube_topic(topic)
        
    num_prompts_str = input("Enter number of 10s prompts to generate [default: 25]: ").strip()
    num_prompts = int(num_prompts_str) if num_prompts_str.isdigit() else 25
        
    frame_mode = input("Select Image Mapping: [1] First+Last frames (Standard) or [2] Continuous Sequence (Img 2->3, 3->4) [default: 1]: ").strip()
    if frame_mode not in ['1', '2']:
        frame_mode = '1'

    # Phase 2
    prompts = step2_write_script(topic, context, num_prompts)
    
    # Phase 2 (Extraction)
    metadata = step3_extract_metadata(prompts)
    asset_zip = step4_create_asset_queue(metadata)
    
    invoke_wgp(asset_zip, "Asset Queue")
    
    # Phase 3
    frames_zip = step5_6_create_frame_queue(prompts, metadata, frame_mode)
    
    invoke_wgp(frames_zip, "Frames Queue (Flux2)")
    
    # Phase 4
    video_zip = step7_create_video_queue(prompts, frame_mode)
    
    invoke_wgp(video_zip, "Video Queue (LTX 2.3)")
    
    # Phase 5
    step8_stitch_videos(len(prompts))
    
    print("\n--- Pipeline Orchestration Complete ---")

if __name__ == "__main__":
    main()
