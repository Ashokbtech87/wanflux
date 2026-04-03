import os
import re
import json
import time
import zipfile
import subprocess
import requests
import random
from typing import List, Dict, Tuple

# Use 127.0.0.1 to avoid IPv6/proxy loops on Colab/Windows
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
global MODEL_NAME
MODEL_NAME = "gemma4:latest"  # Default fallback
API_KEY = "c7f2a3121a9b4d288665f10ff688c161.TQQr5XBuPLTNCWa1Y7NyZ8aa"
ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
WAN2FLUX_DIR = os.path.join(os.path.dirname(__file__), "wan2flux_2")

DEFAULT_STYLE = (
    "High-quality 3D computer animation style, 3D animated feature film, "
    "highly detailed octane render, vibrant vivid colors, soft cinematic volumetric lighting, "
    "glossy materials, smooth 60fps motion, 8k resolution, Unreal Engine 5 style"
)

DEFAULT_CHARS = (
    "Tayo(Tayo_The_little_blue_bus.png), Lani(Lani_the_yellow_bus.png), "
    "Rogi(Rogi_the_green_bus.png), Gani(Gani_The_Red_bus.png), "
    "Cito(Cito_double_decker_bus.png), Hana(Hana_the_mechanic.png), "
    "Nova(Nova_The_Drone_Scout.png), Neo(Neo_the_futuristic_car.png)"
)

SYSTEM_PROMPT = """ROLE & OBJECTIVE
You are an expert AI Video & Narrative Designer specializing in High-Retention 3D Children's Animation, similar in style to Tayo the Little Bus or Robocar Poli. Your singular goal is to generate video prompts that achieve an Average Percentage Viewed (APV) greater than 40% by maximizing visual stimulation combined with hook-driven dialogue.

CORE FRAMEWORK: THE 6 LAYERS (KIDS' EDITION + VA)
Every prompt must be constructed in the following priority order:

1. SCENE (The Hook): Establish the immediate context and identify the character who is speaking.

2. CAMERA (The Ride): Use dynamic angles and multiple shots while following directorial rules; static shots are strictly prohibited.

3. STYLE (The Candy): Render with glossy, vibrant, and "toy-like" visuals.

4. MOTION (The Glue): Ensure constant velocity and continuous background movement.

5. AUDIO (The Pulse): Integrate sound effects (SFX) and music.

6. DIALOGUE (The Story): Include character-segregated voice acting that features a Curiosity Gap and a Resolution. The dialogue must involve multiple characters speaking multiple lines that fit within a 10-second video format.

PROMPT CONSTRUCTION RULES
1. SCENE LAYER (Bright, Clear & Inhabited)


Context: Environments must be instantly recognizable, such as a "Sunny City Intersection," with a "Bright Day" serving as the default setting.


Character Setup: You must explicitly identify the active characters in the scene, such as a "Blue Bus (Tayo-style) & Green Taxi," to prepare for voice acting.


Expression: Clearly define facial expressions that match the dialogue, for example noting that the "Blue Bus looks confused/thinking".


Visual Consistency Anchor (Anti-AI-Artifact): Every character must be described with a LOCKED reference appearance that stays identical across all prompts: exact body color (hex if possible), eye shape, accessory details (e.g., "round white headlights, thin black eyebrows, small silver bumper"). Re-state these details in every prompt to prevent AI model drift between shots. Specify that facial expressions must TRANSITION smoothly (e.g., "eyebrows shift from raised/surprised to relaxed/happy") — never describe a static, frozen face during dialogue.


Background Stability Rule: Backgrounds must be described with FIXED architectural landmarks (e.g., "the same red-roofed garage on the left, the same yellow traffic light on the right"). Moving elements (clouds, birds, leaves) should be described separately from the static scene geometry to prevent AI background morphing.

2. CAMERA LAYER (Dynamic Angles)


Mandatory Vocabulary: Use specific camera terms like "Low-angle tracking shot" for heroic moments, "Fisheye lens" for close-ups or comedy, "Side-scrolling tracking" for races, and "Crash zoom" for reactions.


Prohibition: Do not use shaky cam; all shots must be kept smooth and stabilized.

3. STYLE LAYER (The "Tayo" Aesthetic)


Keywords: Utilize descriptors like "3D stylized animation," "glossy plastic textures," "vibrant saturation," "Pixar-style rim lighting," and "toy-core".


Palette: Stick to pop primary colors like Red, Blue, Yellow, and Green.


Model Consistency Directive: Always include the phrase "consistent character design, model-sheet accurate" in every prompt. Specify that all characters maintain identical proportions, color values, and surface shading across every shot. Avoid vague descriptors that let the AI reinterpret the character (e.g., say "glossy cobalt-blue body with white oval headlights" instead of just "blue bus").


Anti-Morphing Backgrounds: Describe background elements as solid, geometric, and well-lit. Avoid fog, haze, or abstract gradients that give AI models room to hallucinate or morph scenery between frames. Use phrases like "clean edges, fixed perspective, solid-color buildings" to lock the environment.

4. MOTION LAYER (Zero-Stillness)


Rule: If the vehicle stops moving, the background must continue to move.


Techniques: Employ visual mechanics such as "squash and stretch" for bounciness, "speed lines," "motion blur" on the wheels, and "particle effects" like dust or sparkles.

5. AUDIO LAYER (Sensory Engagement)


Music: Feature "upbeat kids' synth-pop" or "cheerful orchestral" tracks.


SFX: Use specific auditory punctuation such as a "playful honk," "cartoon skid," or "hydraulic hiss".


Energy-Matching Rule (Anti-Audio-Mismatch): The audio energy level MUST match the visual intensity. For high-energy scenes (explosions, racing, jumping), specify "fast BPM (140+), punchy percussion, rising crescendo." For calm/mystery scenes, specify "slower BPM (80-100), soft pads, gentle plucks." Never pair a static voiceover delivery with a visually explosive scene.


Audio Pacing Sync: Describe SFX timing relative to on-screen action (e.g., "tire screech SFX hits exactly as bus drifts around corner," "triumphant chime plays on the beat of the boulder splitting"). This prevents disjointed audio-visual timing.

6. DIALOGUE LAYER (Curiosity & Resolution)


Segregation: All dialogue must be clearly separated by character.


The Curiosity Gap (The Setup): The first spoken line must hook the child by asking a question, expressing a fear, or noticing a mystery.


The Resolution (The Payoff): The second line or action must provide satisfaction by immediately answering the question or solving the problem.


Voice Direction: You must specify the tone of the voice, using brackets like [High-pitched/Excited] or [Deep/Grumpy] and multiple lines of dialogues for the characters.


Anti-Rigid-Voiceover Rules: Every dialogue line MUST include an emotional micro-direction AND a physical action cue to prevent flat/robotic AI voiceover. Format: Character (Voice: [Emotion/Pitch]) + [Physical cue]: "Line". Example: Blue Bus (Voice: Breathless/Excited) [bouncing on suspension]: "We did it!" — the physical cue gives the AI voice model context for natural delivery.


Pacing & Breath Marks: Insert pacing cues between lines: [beat], [quick breath], [laughing inhale], [gasp]. These prevent the AI voiceover from delivering lines in a monotone, evenly-spaced cadence. Example: "Oh no!" [gasp, beat] "That jump is HUGE!" — the pause creates natural dramatic timing.


Energy Escalation: Dialogue energy must ESCALATE to match the scene. If the scene builds (calm → action → triumph), the voice direction must mirror it: [Calm/Curious] → [Loud/Determined] → [Ecstatic/Cheering]. Never use the same energy level for all three lines.

AI-ARTIFACT PREVENTION CHECKLIST
Before finalizing any prompt, verify these anti-artifact safeguards:
1. Character Lock: Are all character descriptions reference-locked with specific colors, shapes, and features restated in every prompt?
2. Face Animation: Does every dialogue line include a facial expression TRANSITION (not a static face)? Are there at least 2 different expressions per character per prompt?
3. Background Anchor: Are backgrounds described with fixed, named landmarks? Are moving elements (clouds, particles) described separately from static geometry?
4. Anti-Morph Style: Does the style layer include "consistent character design, model-sheet accurate" and avoid vague/abstract descriptors?
5. Audio-Visual Energy Match: Does the music BPM and SFX intensity match the scene's visual energy level?
6. Voice Naturalism: Does every dialogue line have an emotion tag, a physical action cue, AND a pacing mark ([beat], [gasp], etc.)?
7. Energy Arc: Does the dialogue energy escalate across lines to match the scene's visual arc?

FINAL CHECKLIST
Ensure your prompt meets the following criteria: Is the visual aesthetic bright and "toy-like"? Is the camera dynamic without any static shots? Is the dialogue segregated by character? Does the dialogue start with a question or mystery to form a gap, and end with an answer or resolution?
"""

def invoke_wgp(zip_path: str, stage_name: str):
    print(f"\n[>>>] Triggering GPU engine for: {stage_name}")
    print(f"      Running: python wgp.py --process {zip_path}")
    abs_zip_path = os.path.abspath(zip_path)
    try:
        # Removing stdout pipe explicitly so Colab natively displays GPU progress bars.
        result = subprocess.run(
            ["python", "wgp.py", "--process", abs_zip_path], 
            cwd=WAN2FLUX_DIR,
            check=False
        )
        if result.returncode == 0:
            print(f"[OK] Completed {stage_name} successfully!")
        else:
            print(f"[WARN] Command ran but returned non-zero code.")
        return True
    except FileNotFoundError:
        print(f"[FAIL] Could not find 'python' or 'wgp.py' inside {WAN2FLUX_DIR}.")
        return False

os.makedirs(ASSET_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_via_ollama(prompt: str, sys_prompt: str = SYSTEM_PROMPT) -> str:
    payload = {
        "model": MODEL_NAME,
        "system": sys_prompt,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 32768, "temperature": 0.85}
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    print(f"[*] Calling Ollama ({MODEL_NAME})...")
    try:
        response = requests.post(
            OLLAMA_URL, 
            json=payload, 
            headers=headers,
            timeout=600, 
            proxies={"http": None, "https": None}
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"[!] Ollama request failed: {e}")
        return ""

def step1_fetch_youtube_topic(user_topic: str) -> str:
    print(f"\n--- STEP 1: Fetching Niche Details for '{user_topic}' ---")
    return f"Trending angle for {user_topic}: High engagement, fast-paced action, vivid colors."

def step2_write_script(topic: str, context: str, num_prompts: int, slapstick: bool) -> Tuple[List[str], List[str]]:
    print(f"\n--- STEP 2: Writing Script for '{topic}' ({num_prompts} Prompts) ---")
    
    char_inst = (
        "3. Character Consistency: Always mention characters with their "
        f"reference image filename in brackets. Characters: {DEFAULT_CHARS}.\n"
    )

    ctx_block = f"\nIMPORTANT USER OVERRIDE: {context}\n(Prioritize over story details.)\n" if context else ""

    user_instruction = (
        f"Based on the story provided below, generate {num_prompts} video prompts.\n{ctx_block}"
        "Format Requirements:\n"
        "1. Each prompt must follow: [Scene: 2-3 words] [Theme/Era: <macro>] "
        "[Mood: <mood>] [Environment: <env>] [Day/Night: <day/night>] [Full Prompt]\n"
        "   - Do NOT include any style prefix in the prompt itself.\n"
        f"2. {char_inst}"
        "3. Environment Consistency: Maintain coherent visual environment across scenes.\n"
        "4. Dialogue & Audio (end of each prompt, same line): "
        "Dialogue: <2-4 spoken lines, 30-50 words> "
        "SFX: <1-3 sound effects> BGM: <music style>. No line breaks inside prompt.\n"
        "5. Continuity: End of one prompt flows into the next.\n"
    )

    if slapstick:
        user_instruction += "6. Slapstick Comedy: Every prompt is a fast-paced ONE-LINER.\n"
    else:
        user_instruction += (
            "6. Duration & Depth: Every prompt is VERY LONG and RICHLY DETAILED "
            "(exactly 10 seconds of video). Include precise camera movement, lighting, "
            "character action beat-by-beat, atmosphere, color grading. Aim for 6-8 sentences.\n"
        )

    user_instruction += (
        "7. Directorial Pass: Fast-paced, rapid dynamic camera movements, quick cuts.\n"
        "8. Structure: Each prompt is one paragraph. No gap text between prompts.\n"
        f"9. Total: Exactly {num_prompts} prompts.\n\nStory:\n{topic}\n\nGenerate the prompts now:"
    )
    
    script_text = generate_via_ollama(user_instruction, SYSTEM_PROMPT)
    if not script_text:
        script_text = f"Fallback prompt for {topic}"
        
    lines = script_text.splitlines()
    prefixed = []
    ltx_lines = []
    
    ltx_camera_moves = ["The camera pans right", "The camera pans left", "The camera pushes in", "The camera pulls back", "The camera orbits", "The camera follows", "Static", "Handheld movement", "Drone shot"]
    ltx_pacings = ["# Slow motion", "# Time-lapse", "# Rapid cuts", "# Long take", "# Freeze frame"]
    ltx_atmospheres = ["Fog", "Rain", "Mist", "Smoke", "Dust particles", "Snow", "Fire embers", "Storm clouds"]
    ltx_sounds = ["Wind", "City noise", "Rain", "Ocean waves", "Forest sounds", "Crowd murmur", "Machine hum", "Thunder"]
    
    for line in lines:
        stripped = line.strip()
        if stripped:
            # Flux variation
            prefixed.append(f"{DEFAULT_STYLE}, {stripped}")
            
            # LTX randomized video grammar variation
            ltx_parts = []
            if random.random() < 0.4:
                ltx_lines.append(random.choice(ltx_pacings))
            ltx_parts.append(f"{DEFAULT_STYLE}, {stripped}".rstrip('.'))
            
            if random.random() < 0.3:
                ltx_parts.append(random.choice(ltx_atmospheres))
            if random.random() < 0.5:
                ltx_parts.append(random.choice(ltx_camera_moves))
            if random.random() < 0.4:
                ltx_parts.append("Sound: " + random.choice(ltx_sounds))
                
            ltx_lines.append(", ".join(ltx_parts) + ".")
            
    # Filter empty and truncate safely
    flux_prompts = [p for p in prefixed if p.strip()]
    ltx_prompts = [p for p in ltx_lines if p.strip()]
    
    # Ensure they match length via pad/truncate
    while len(flux_prompts) < num_prompts:
        flux_prompts.append(f"{DEFAULT_STYLE}, Extended scene for {topic} - continuing action...")
    while len(ltx_prompts) < num_prompts:
        ltx_prompts.append(f"{DEFAULT_STYLE}, Extended video scene for {topic}...")
        
    flux_prompts = flux_prompts[:num_prompts]
    ltx_prompts = ltx_prompts[:num_prompts]
    
    print(f"[*] Generated {len(flux_prompts)} Flux Prompts and {len(ltx_prompts)} LTX Variations.")
    return flux_prompts, ltx_prompts

def parse_story_sections(text: str) -> dict:
    """Parses Characters/Props/Environments via regex."""
    result = {}
    section_re = re.compile(
        r'(?:^|\n)(Characters?|Props?|Environments?|Settings?)\s*:\s*(.+?)(?=\n[A-Z][a-zA-Z]*\s*:|$)',
        re.IGNORECASE | re.DOTALL
    )
    for m in section_re.finditer(text):
        raw_key = m.group(1).rstrip("s").capitalize()
        raw_val = m.group(2).strip()
        items = re.split(r'[,;\n]+|\s+and\s+', raw_val, flags=re.IGNORECASE)
        items = [i.strip().rstrip('.').strip() for i in items if i.strip()]
        if items:
            key = "Environment" if raw_key in ("Environment", "Setting") else raw_key
            result.setdefault(key, []).extend(items)
    for k, v in result.items():
        result[k] = list(dict.fromkeys(v))
    return result

def step3_extract_metadata(story: str) -> Dict[str, List[str]]:
    print("\n--- STEP 3: Extracting Characters, Props, Environments ---")
    sections = parse_story_sections(story)
    
    if not sections:
        print("[!] No labeled sections found — asking AI to extract metadata natively...")
        extract_prompt = (
            "Read the following story carefully and extract ALL of these three categories.\n"
            "Return ONLY the following format with no extra text:\n\n"
            "Characters: <comma-separated list of all named or characters/animals/beings>\n"
            "Props: <comma-separated list of key objects, items or tools>\n"
            "Environment: <comma-separated list of distinct locations or habitats>\n\n"
            f"Story:\n{story}"
        )
        response_text = generate_via_ollama(extract_prompt, sys_prompt="You are an extraction assistant.")
        sections = parse_story_sections(response_text)
        
        # Fallback to extremely basic regex if AI refuses the exact format
        if not sections:
            lines = response_text.strip().splitlines()
            for line in lines:
                m = re.match(r'(Characters?|Props?|Environments?)\s*:\s*(.+)', line, re.I)
                if m:
                    key = m.group(1).rstrip('s').capitalize()
                    items = [i.strip().rstrip('.') for i in re.split(r',|\sand\s', m.group(2)) if i.strip()]
                    if items:
                        sections[key] = items
                        
    if not sections:
        sections = {"Characters": ["Protagonist"], "Props": [], "Environments": ["Main Setting"]}
        
    print(f"[*] Parsed keys: {list(sections.keys())}")
    return sections

def step4_create_asset_queue(metadata: Dict[str, List[str]]):
    print("\n--- STEP 4: Building Asset Generation Queue (Flux2) ---")
    queue_data = []
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
    return zip_path

def step5_6_create_frame_queue(flux_prompts: List[str], metadata: Dict[str, List[str]], frame_mode: str):
    print(f"\n--- STEP 5 & 6: Building Frame Queue (Mode {frame_mode}) ---")
    reference_images = []
    uid = 1
    for char in metadata.get("Characters", []):
        reference_images.append(f"asset_{uid}.jpg")
        uid += 1
    for env in metadata.get("Environments", []):
        reference_images.append(f"asset_{uid}.jpg")
        uid += 1
        
    queue_data = []
    if frame_mode == '2':
        for i, p in enumerate(flux_prompts):
            seq = i + 1
            queue_data.append({
                "id": f"{seq}_single",
                "prompt": p,
                "reference_images": reference_images
            })
    else:
        for i, p in enumerate(flux_prompts):
            seq = i + 1
            queue_data.append({"id": f"{seq}_first", "prompt": f"Start of keyframe action, {p}", "reference_images": reference_images})
            queue_data.append({"id": f"{seq}_last", "prompt": f"End of keyframe action, {p}", "reference_images": reference_images})
        
    queue_json_path = os.path.join(ASSET_DIR, "queue_frames.json")
    with open(queue_json_path, 'w') as f:
        json.dump(queue_data, f, indent=4)
    zip_path = os.path.join(ASSET_DIR, "queue_frames.zip")
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(queue_json_path, arcname="queue.json")
    return zip_path

def step7_create_video_queue(ltx_prompts: List[str], frame_mode: str):
    print("\n--- STEP 7: Building Video Generation Queue (LTX 2.3) ---")
    queue_data = []
    for i, p in enumerate(ltx_prompts):
        seq = i + 1
        if frame_mode == '2':
            start_img = f"{seq}_single.jpg"
            end_img = f"{seq+1}_single.jpg" if seq < len(ltx_prompts) else ""
            queue_data.append({"id": seq, "prompt": p, "first_frame": start_img, "last_frame": end_img})
        else:
            queue_data.append({"id": seq, "prompt": p, "first_frame": f"{seq}_first.jpg", "last_frame": f"{seq}_last.jpg"})
    
    queue_json_path = os.path.join(ASSET_DIR, "queue_ltx.json")
    with open(queue_json_path, 'w') as f:
        json.dump(queue_data, f, indent=4)
    zip_path = os.path.join(ASSET_DIR, "queue_ltx.zip")
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(queue_json_path, arcname="queue.json")
    return zip_path

def step8_stitch_videos(segment_count: int):
    print("\n--- STEP 8: Stitching Final Video ---")
    list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(list_path, 'w') as f:
        for i in range(1, segment_count + 1):
            f.write(f"file '{os.path.join(OUTPUT_DIR, f'{i}_video.mp4')}'\\n")
            
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", os.path.join(OUTPUT_DIR, "final_stitched_video.mp4")]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[*] Final video stitched successfully!")
    except Exception:
        print("[!] FFmpeg stitch encountered an issue (missing files likely if dry-run).")

def main():
    global MODEL_NAME
    print("=============================================")
    print("  AI Video Pipeline Orchestrator (Dry-Run)")
    print("=============================================")
    
    user_model = input("Enter Ollama model name [default: gemma4:latest]: ").strip()
    if user_model:
        MODEL_NAME = user_model
        
    input_type = input("Do you want to provide a [1] Topic/Niche or [2] Full Story? (1/2) [default: 1]: ").strip()
    if input_type == '2':
        story_input = input("Enter the Full Story (or path to a .txt file): ").strip()
        if os.path.isfile(story_input):
            with open(story_input, 'r', encoding='utf-8') as f:
                context = f.read()
            topic = os.path.basename(story_input).replace('.txt', '')
        else:
            topic = "User Provided Story"
            context = story_input
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

    slapstick = input("Enable Slapstick Comedy Mode? (y/n) [default: n]: ").strip().lower() == 'y'

    # Phase 2 - Write Script
    flux_prompts, ltx_prompts = step2_write_script(topic, context, num_prompts, slapstick)
    
    # Phase 2 - Metadata Extraction
    metadata = step3_extract_metadata(topic + "\n" + context)
    asset_zip = step4_create_asset_queue(metadata)
    invoke_wgp(asset_zip, "Asset Queue")
    
    # Phase 3 - Frame Generation (uses Flux style)
    frames_zip = step5_6_create_frame_queue(flux_prompts, metadata, frame_mode)
    invoke_wgp(frames_zip, "Frames Queue (Flux2)")
    
    # Phase 4 - Video Generation (uses LTX style)
    video_zip = step7_create_video_queue(ltx_prompts, frame_mode)
    invoke_wgp(video_zip, "Video Queue (LTX 2.3)")
    
    # Phase 5 - Stitching
    step8_stitch_videos(num_prompts)
    
    print("\n--- Pipeline Orchestration Complete ---")

if __name__ == "__main__":
    main()
