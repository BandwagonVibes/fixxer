#!/usr/bin/env python3
"""
Enhanced Burst Stacking for PhotoSort v9.0

NEW FEATURES:
1. All burst folders organized into a parent "_Bursts" directory
2. AI-powered folder naming (e.g., "_Bursts/golden-retriever-playing/" instead of "burst-001")

INTEGRATION INSTRUCTIONS:
Replace the burst folder creation section (lines 1483-1514) with the code below.
"""

# ============================================================================
# REPLACE THIS SECTION IN photosort.py (lines 1483-1514)
# ============================================================================

def get_ai_burst_folder_name(image_path: Path, model_name: str) -> Optional[str]:
    """
    Generate AI-powered folder name for a burst group.
    Uses the first (or best) image from the burst.
    Returns a clean folder name or None on failure.
    """
    try:
        base64_image = encode_image(image_path)
        if not base64_image:
            return None
        
        # Simple prompt: just get a short description
        prompt = """Describe this image in 2-4 words for a folder name.
        
Return ONLY a JSON object:
{
  "folder_name": "<short-descriptive-name>"
}

Examples:
- "golden-retriever-playing"
- "sunset-over-ocean"
- "city-street-night"
"""
        
        payload = {
            "model": model_name,
            "messages": [{
                "role": "user",
                "content": prompt,
                "images": [base64_image]
            }],
            "stream": False,
            "format": "json"
        }
        
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)  # Short timeout
        response.raise_for_status()
        
        result = response.json()
        json_string = result['message']['content'].strip()
        data = json.loads(json_string)
        
        folder_name = data.get("folder_name")
        if folder_name:
            # Clean it up for filesystem use
            clean_name = clean_filename(folder_name)  # Reuse existing function
            return clean_name
        
        return None
        
    except Exception:
        return None  # Silent fail - use fallback naming


# ============================================================================
# NEW VERSION OF BURST FOLDER CREATION
# Replace lines 1483-1514 in photosort.py with this:
# ============================================================================

    # === v9.0 ENHANCED: Parent directory + AI naming ===
    
    # Check if parent folder is enabled
    use_parent_folder = APP_CONFIG.get('burst_parent_folder', True)
    
    if use_parent_folder:
        bursts_parent = directory / "_Bursts"
        print(f"\n Organizing burst groups into: {bursts_parent.name}/")
        if not dry_run:
            bursts_parent.mkdir(exist_ok=True)
    else:
        bursts_parent = directory
    
    print(f"\n Stacking {len(all_burst_groups)} burst groups...")
    
    # Get model for AI naming (use default from config)
    ai_model = APP_CONFIG.get('default_model', DEFAULT_MODEL_NAME)
    
    for i, group in enumerate(all_burst_groups):
        # === NEW: Try AI naming first ===
        ai_folder_name = None
        winner_data = best_picks.get(i)
        
        # Use the best pick for AI naming (or first image as fallback)
        sample_image = winner_data[0] if winner_data else group[0]
        
        print(f"\n Burst {i+1}/{len(all_burst_groups)}: Generating name...")
        ai_folder_name = get_ai_burst_folder_name(sample_image, ai_model)
        
        if ai_folder_name:
            # Success! Use AI name
            folder_name = ai_folder_name
            print(f"   ✓ AI named: {folder_name}")
        else:
            # Fallback to numbered naming
            folder_name = f"burst-{i+1:03d}"
            print(f"   ⚠️  AI naming failed, using: {folder_name}")
        
        # Create folder path (either in parent or root)
        folder_path = bursts_parent / folder_name
        
        # Handle name collisions
        if folder_path.exists():
            counter = 2
            original_name = folder_name
            while folder_path.exists():
                folder_name = f"{original_name}-{counter}"
                folder_path = bursts_parent / folder_name
                counter += 1
        
        print(f"   📁 {folder_path.relative_to(directory)}/ ({len(group)} files)")
        
        if not dry_run:
            folder_path.mkdir(parents=True, exist_ok=True)
        
        # Move files into the burst folder
        for file_path in group:
            if winner_data and file_path == winner_data[0]:
                new_name = f"{BEST_PICK_PREFIX}{file_path.name}"
            else:
                new_name = file_path.name
            
            new_file_path = folder_path / new_name
            
            if not dry_run:
                try:
                    shutil.move(str(file_path), str(new_file_path))
                    print(f"      Moved {file_path.name} → {new_name}")
                except Exception as e:
                    print(f"      FAILED to move {file_path.name}: {e}")
            else:
                if winner_data and file_path == winner_data[0]:
                    print(f"     [PREVIEW] Would move and RENAME {file_path.name} to {new_name}")
                else:
                    print(f"     [PREVIEW] Would move {file_path.name}")
    
    print("\n Burst stacking complete!")
    if use_parent_folder:
        print(f" All burst groups organized in: {bursts_parent}")

# ============================================================================
# IMPORTANT: Also update auto_workflow to look in the new location!
# Replace line 2130 in photosort.py:
# ============================================================================

# OLD (line 2130):
#     for burst_folder in directory.glob("burst-*/"):

# NEW (supports both parent and root locations):
    # Look for burst folders (check parent directory first, then root)
    burst_parent = directory / "_Bursts"
    if burst_parent.exists() and burst_parent.is_dir():
        burst_folders = list(burst_parent.iterdir())
        burst_folders = [f for f in burst_folders if f.is_dir()]
    else:
        burst_folders = list(directory.glob("burst-*/"))
    
    for burst_folder in burst_folders:
        # (rest of the loop stays the same)
