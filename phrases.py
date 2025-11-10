"""
Phrase Library for PHOTOSORT v7.1
==================================
200 rotating messages organized by duration and theme.

Distribution:
- Model loading: 15 phrases
- Quick (0-5min): 30 phrases  
- Early (5-15min): 35 phrases
- Mid (15-30min): 35 phrases
- Long (30-60min): 35 phrases
- Marathon (60+min): 30 phrases
- VisionCrew Meta: 20 phrases (loading/waiting only)

Content Mix:
- 30% Humor & Snark (~60 phrases)
- 20% Photography Education (~40 phrases)
- 15% Everyday Mysteries (~30 phrases)
- 15% VisionCrew Meta (~30 phrases)
- 10% AI/ML Knowledge (~20 phrases)
- 10% Time/Tech Facts (~20 phrases)
"""

import random
from typing import List

# ============================================================================
# MODEL LOADING PHRASES (15) - Displayed during 15-30s Ollama model load
# ============================================================================

MODEL_LOADING_PHRASES = [
    "🤖 Waking up bakllava... (this takes a moment)",
    "🔋 Loading model into RAM... (patience, young padawan)",
    "⚡️ Initializing neural networks... (worth the wait)",
    "📦 Loading 4.7GB of computer vision into memory...",
    "🧠 Convincing your Mac's unified memory to share...",
    "⚙️ MLX is fast... after it wakes up from its nap",
    "☕ Perfect time to grab that coffee you've been eyeing",
    "📖 Fun fact: You could read a haiku while this loads. Twice.",
    "⏳ This is why photographers always have cold coffee",
    "🤔 I'm not stuck, I'm just loading... I promise",
    "🔐 This is the price of privacy. Worth it? You decide.",
    "🎨 At least your photos aren't being uploaded to 'the cloud'",
    "🤖 Your M-series chip is thinking... deeply",
    "🌟 Apple Silicon doing Apple Silicon things...",
    "🧮 Quantizing weights to 4-bit... (nerd stuff, bear with us)",
]

# ============================================================================
# QUICK PROCESSING (0-5min) - 30 phrases
# ============================================================================

QUICK_PROCESSING_PHRASES = [
    # Humor & Snark (9 phrases)
    "🎯 Judging your composition choices...",
    "🔍 Looking for that one in-focus shot...",
    "📸 Pretending we don't see that terrible burst sequence...",
    "🎨 Some of these are... bold creative choices",
    "🤷 Your ISO 12800 shots are making me nervous",
    "😅 Found 47 photos of the same leaf. Keeping the best one.",
    "🎭 That bokeh is *chef's kiss* or a smudge. We'll investigate.",
    "📷 Detecting artistic vision... or happy accidents",
    "🎯 Peak sharpness detected! (Finally.)",
    
    # Photography Education (6 phrases)
    "📚 Pro tip: Shutter speed should be 1/focal length minimum",
    "🎓 The rule of thirds exists for a reason (but rules are made to be broken)",
    "💡 Golden hour isn't just Instagram hype - the light really is better",
    "📸 Aperture: F/2.8 for portraits, F/8-F/11 for landscapes",
    "🔍 Focus peaking is your friend for manual focus",
    "⚡ Back-button focus changed my life - just saying",
    
    # Everyday Mysteries (6 phrases)
    "🧠 Why do we blink when we sneeze? Brain's protecting your eyes.",
    "🌊 Ocean waves come in sets because of wave interference patterns",
    "🌙 Moon illusion: It's not bigger at horizon, your brain just thinks so",
    "☕ Coffee smells better than it tastes because olfactory receptors are amazing",
    "🎵 Earworms happen because music activates your motor cortex",
    "🧊 Hot water can freeze faster than cold (Mpemba effect)",
    
    # AI/ML Knowledge (5 phrases)
    "🤖 Vision transformers see images as sequences of patches",
    "🧠 Diffusion models work by learning to remove noise",
    "📊 Your GPU is doing matrix multiplication 24/7",
    "🎯 Attention mechanisms: The AI asks 'what's important here?'",
    "🔮 Latent space: Where AI dreams of electric sheep",
    
    # Time/Tech Facts (4 phrases)
    "⏰ Unix timestamps will overflow in 2038 (Y2K38 problem)",
    "💾 QR codes can store ~4,296 alphanumeric characters",
    "🔋 Lithium-ion batteries lose capacity every charge cycle",
    "📡 Your phone switches cell towers 100+ times during a car trip",
]

# ============================================================================
# EARLY PROCESSING (5-15min) - 35 phrases
# ============================================================================

EARLY_PROCESSING_PHRASES = [
    # Humor & Snark (11 phrases)
    "🎨 Analyzing your 'artistic blur' (aka camera shake)",
    "🔍 Counting how many times you shot the same thing...",
    "📸 Your burst mode discipline is... interesting",
    "🎯 Found the keeper! (It's hiding behind 23 duds)",
    "😬 That exposure is spicy. Bold. Controversial.",
    "🤔 Is this avant-garde or did you sneeze?",
    "🎭 Processing your 'moody underexposed aesthetic'...",
    "📷 Sorting gems from 'what was I thinking' shots",
    "🎨 Your white balance tells a story. A chaotic story.",
    "🔥 Some of these are fire. Some are... also fire. (dumpster fire)",
    "🎯 Peak photography happening... 15% of the time",
    
    # Photography Education (7 phrases)
    "📚 Histogram tip: Don't fear the shadows, fear the clipped highlights",
    "🎓 Shoot in RAW - you can fix most things except bad focus",
    "💡 Blue hour > Golden hour (fight me)",
    "📸 Your lens's sweet spot is usually 2-3 stops down from wide open",
    "🔍 Zone focusing: Pre-focus and shoot from the hip like a film noir hero",
    "⚡ High-speed sync lets you use flash in bright daylight",
    "🎯 Critical focus: Eyes first, everything else can be soft",
    
    # Everyday Mysteries (7 phrases)
    "🌈 Rainbows are actually full circles - you just can't see the bottom half",
    "🦆 Ducks' quacks don't echo (actually they do, it's just hard to hear)",
    "🌡️ Room temperature is 20-22°C because that's our metabolic sweet spot",
    "🧲 Magnets work because of aligned electron spins (quantum mechanics!)",
    "🦋 Butterflies taste with their feet (chemoreceptors)",
    "🌊 Tides have tides - they're affected by coastline shape",
    "🔊 Sound travels 4x faster in water than air",
    
    # AI/ML Knowledge (5 phrases)
    "🤖 GANs: Two AIs playing cops and robbers with images",
    "🧠 Backpropagation: Teaching AI through calculated regret",
    "📊 Gradient descent: Rolling a ball down a hill to find the answer",
    "🎯 Overfitting: When AI memorizes instead of learning",
    "🔮 Transfer learning: Teaching new tricks to old neural nets",
    
    # Time/Tech Facts (5 phrases)
    "⏰ GPS satellites account for relativity or they'd drift 10km/day",
    "💾 JPEG compression throws away data you won't miss",
    "🔋 Fast charging heats batteries, shortening their life",
    "📡 Fiber optic cables carry light at 2/3 the speed of light in vacuum",
    "🖥️ Your CPU can execute ~3 billion instructions per second",
]

# ============================================================================
# MID PROCESSING (15-30min) - 35 phrases
# ============================================================================

MID_PROCESSING_PHRASES = [
    # Humor & Snark (11 phrases)
    "🎨 Still here! Unlike your camera's battery life...",
    "🔍 This is taking a while. Maybe make that coffee now?",
    "📸 Processing marathon underway. Stay hydrated.",
    "🎯 We're committed now. No turning back.",
    "😅 At least you're not manually culling these...",
    "🤔 Fun fact: You could've shot another 100 photos by now",
    "🎭 Your hard drive is getting a workout",
    "📷 Halfway there! (Probably. Time is relative.)",
    "🎨 This would be faster on quantum computers (in 2045)",
    "🔥 Your M1 chip just unlocked its final form",
    "🎯 AI doesn't get coffee breaks but you should",
    
    # Photography Education (7 phrases)
    "📚 Long exposure tip: Use ND filters to shoot waterfalls at noon",
    "🎓 Expose for highlights, develop for shadows (ETTR technique)",
    "💡 Your camera's light meter is fooled by bright/dark scenes - use exposure comp",
    "📸 Prime lenses force you to 'zoom with your feet' and think more",
    "🔍 Focus stacking: Merge multiple shots for infinite depth of field",
    "⚡ Flash + slow shutter = motion blur + frozen subject (drag the shutter)",
    "🎯 Shoot one subject 10 ways > shoot 10 subjects one way",
    
    # Everyday Mysteries (7 phrases)
    "🌍 Earth's rotation is slowing - days used to be 22 hours",
    "🌟 Stars don't actually twinkle - atmospheric turbulence does",
    "🦎 Chameleons change color for communication, not camouflage",
    "🌊 Ocean is salty from millions of years of rock erosion",
    "🧊 Ice cubes crack in drinks due to temperature shock",
    "🔊 Sonic booms happen continuously along a jet's flight path",
    "🌙 Moon is slowly drifting away from Earth (3.8cm/year)",
    
    # AI/ML Knowledge (5 phrases)
    "🤖 Neural nets with billions of parameters learn like toddlers with supercomputers",
    "🧠 Convolutional layers: Teaching AI to see edges, then shapes, then cats",
    "📊 Dropout: Randomly turning off neurons to prevent cheating",
    "🎯 Batch normalization: Keeping AI's learning stable",
    "🔮 Embeddings: Converting concepts into coordinate space",
    
    # Time/Tech Facts (5 phrases)
    "⏰ Internet traffic increases 25% annually (mostly video)",
    "💾 Modern SSDs wear out after ~1000 write cycles per cell",
    "🔋 Wireless charging is only ~80% efficient (rest becomes heat)",
    "📡 5G towers have ~1000x smaller range than 4G towers",
    "🖥️ Ray tracing simulates light physics in real-time (finally!)",
]

# ============================================================================
# LONG PROCESSING (30-60min) - 35 phrases
# ============================================================================

LONG_PROCESSING_PHRASES = [
    # Humor & Snark (11 phrases)
    "🎨 Still grinding away like a film photographer in the darkroom...",
    "🔍 This is an epic session. Snacks recommended.",
    "📸 Your photo library is... ambitious",
    "🎯 We've processed more images than Ansel Adams shot in a year",
    "😅 The good news: This is saving you days of manual work",
    "🤔 At this point you could've watched a whole movie",
    "🎭 Marathon mode engaged. We're in this together.",
    "📷 Your storage space about to look very different",
    "🎨 If AI could sigh, it would. But it's still working.",
    "🔥 Your cooling fans are writing poetry in binary",
    "🎯 This is why pros have fast computers (and patience)",
    
    # Photography Education (7 phrases)
    "📚 Film photography taught patience - digital lets us shoot 1000x more",
    "🎓 The best camera is the one you have with you (even if it's a phone)",
    "💡 Shoot manual mode for a month - you'll understand light forever",
    "📸 Your style develops when you stop copying others",
    "🔍 Print your work - screens lie about color and detail",
    "⚡ Available light > artificial light (but learn both)",
    "🎯 Less gear, more vision - Cartier-Bresson used one lens",
    
    # Everyday Mysteries (7 phrases)
    "🌈 Sunsets are red because blue light scatters more than red",
    "🦎 Geckos can walk on ceilings due to van der Waals forces",
    "🌡️ Water expands when frozen - it's one of few substances that does",
    "🧲 Earth's magnetic field flips every ~200,000-300,000 years",
    "🦋 Monarch butterflies migrate 3000 miles across generations",
    "🌊 Rogue waves can appear suddenly - they're real, not myths",
    "🔊 Silence doesn't exist - you'd hear your blood flowing",
    
    # AI/ML Knowledge (5 phrases)
    "🤖 GPUs were designed for graphics but AI hijacked them",
    "🧠 Vision models 'see' layers: edges → textures → objects → scenes",
    "📊 Reinforcement learning: AI learning through trial and error",
    "🎯 Few-shot learning: Teaching AI with just a handful of examples",
    "🔮 Adversarial examples: Fooling AI with tiny pixel changes",
    
    # Time/Tech Facts (5 phrases)
    "⏰ Your phone has more computing power than NASA in 1969",
    "💾 Data centers use 1% of global electricity",
    "🔋 Battery capacity doubles roughly every 10 years",
    "📡 Submarine cables carry 99% of intercontinental data",
    "🖥️ Moore's Law is ending - we're hitting physics limits",
]

# ============================================================================
# MARATHON PROCESSING (60+min) - 30 phrases
# ============================================================================

MARATHON_PROCESSING_PHRASES = [
    # Humor & Snark (10 phrases)
    "🎨 This is officially a marathon. Respect.",
    "🔍 You absolute madlad - this is a serious photo session",
    "📸 At this point, we're best friends",
    "🎯 Your dedication to photography is inspiring (or concerning)",
    "😅 Professional tier processing happening here",
    "🤔 Time to walk away and come back with fresh eyes",
    "🎭 We've entered the endgame now...",
    "📷 Your portfolio is going to be *chef's kiss*",
    "🎨 AI stamina test: In progress",
    "🔥 This is what the pros do. You're doing the work.",
    
    # Photography Education (6 phrases)
    "📚 Consistency > perfection. Show up and shoot every day.",
    "🎓 Study paintings to understand light and composition",
    "💡 Your style is invisible to you - others see it first",
    "📸 Delete less, edit more - even 'bad' shots teach you something",
    "🔍 The difference between amateur and pro is the bad shots you don't show",
    "⚡ Learn to pre-visualize the shot before pressing the shutter",
    
    # Everyday Mysteries (6 phrases)
    "🌍 A day on Venus is longer than a year on Venus",
    "🌟 Neutron stars are so dense a teaspoon weighs 6 billion tons",
    "🦎 Octopuses have three hearts and blue blood",
    "🌊 There's more gold in the ocean than all ever mined",
    "🧊 Antarctica is technically a desert (very low precipitation)",
    "🔊 In space, metal objects can weld together spontaneously",
    
    # AI/ML Knowledge (4 phrases)
    "🤖 Large language models are compression algorithms for the internet",
    "🧠 Neural nets learn hierarchical features automatically",
    "📊 Training large models takes months and millions of dollars",
    "🎯 AI doesn't 'understand' - it finds statistical patterns",
    
    # Time/Tech Facts (4 phrases)
    "⏰ One Google search uses the same energy as a lightbulb for 17 seconds",
    "💾 Global data doubles every 2 years (exponential growth)",
    "🔋 Electric cars have ~20 moving parts vs 2000 in gas cars",
    "📡 Starlink satellites orbit at 340 miles (1/1000th of GPS altitude)",
]

# ============================================================================
# VISIONCREW META (20 phrases) - ONLY during loading/waiting
# ============================================================================

VISIONCREW_META_PHRASES = [
    "🎭 VisionCrew: Built by photographers, for photographers",
    "🔮 VisionCrew: No cloud. No tracking. Just local AI.",
    "🛡️ VisionCrew: Your photos never leave your Mac",
    "⚡ VisionCrew: Because privacy isn't negotiable",
    "🎨 VisionCrew: Open source, open minds",
    "🤖 VisionCrew: Teaching AI to see like you do",
    "📸 VisionCrew: From 500 RAWs to 50 keepers in minutes",
    "🎯 VisionCrew Tip: Delete your duds. (You won't. But we had to say it.)",
    "☕ VisionCrew: We run on coffee, sarcasm, and tensor cores",
    "🌙 VisionCrew: Coded during golden hour, debugged at 3am",
    "🎭 VisionCrew: Our email is down. Also, we don't have an email.",
    "🔧 VisionCrew: Where post-production meets prompt engineering",
    "🎬 VisionCrew: DaVinci Resolve but make it AI",
    "🧠 VisionCrew: Less clicking, more shooting",
    "⚙️ VisionCrew: Powered by Mac Studio and caffeine dependency",
    "🎨 VisionCrew: We believe in the right to repair... photos",
    "📦 VisionCrew: No subscriptions. No surveillance. No BS.",
    "🔮 VisionCrew: Built by Nick, enhanced by Claude & Gemini",
    "🎯 VisionCrew: Making Ollama work overtime since 2024",
    "🌟 VisionCrew: Because Adobe isn't the only game in town",
]

# ============================================================================
# PHRASE SELECTION LOGIC
# ============================================================================

# v8.0 GM: Track recently shown phrases to avoid repetition
_recent_phrases = []
_MAX_RECENT = 10  # Remember last 10 phrases to avoid repeating


def get_phrase_by_duration(elapsed_seconds: float, use_meta: bool = False) -> str:
    """
    Select appropriate phrase based on processing duration.
    v8.0 GM: Now with anti-repetition logic for better variety.
    
    Args:
        elapsed_seconds: Time elapsed since processing started
        use_meta: If True, include VisionCrew meta phrases (for loading/waiting only)
    
    Returns:
        Random phrase from appropriate duration tier (avoiding recent repeats)
    """
    global _recent_phrases
    
    elapsed_minutes = elapsed_seconds / 60
    
    # Determine which phrase pool to use
    if elapsed_minutes < 5:
        pool = QUICK_PROCESSING_PHRASES
    elif elapsed_minutes < 15:
        pool = EARLY_PROCESSING_PHRASES
    elif elapsed_minutes < 30:
        pool = MID_PROCESSING_PHRASES
    elif elapsed_minutes < 60:
        pool = LONG_PROCESSING_PHRASES
    else:
        pool = MARATHON_PROCESSING_PHRASES
    
    # Add meta phrases if we're in loading/waiting context
    if use_meta:
        pool = pool + VISIONCREW_META_PHRASES
    
    # v8.0 GM: Filter out recently shown phrases for variety
    available_phrases = [p for p in pool if p not in _recent_phrases]
    
    # If we've exhausted all phrases (rare), reset the recent list
    if not available_phrases:
        _recent_phrases.clear()
        available_phrases = pool
    
    # Select random phrase from available pool
    selected = random.choice(available_phrases)
    
    # Track this phrase to avoid repetition
    _recent_phrases.append(selected)
    if len(_recent_phrases) > _MAX_RECENT:
        _recent_phrases.pop(0)  # Remove oldest phrase
    
    return selected


def get_model_loading_phrase() -> str:
    """Get a random model loading phrase."""
    return random.choice(MODEL_LOADING_PHRASES)


def get_quit_message() -> str:
    """Get a random quit message."""
    QUIT_MESSAGES = [
        "👋 Later!",
        "👋 Quitting... Your photos remain unorganized. For now.",
        "🎭 VisionCrew: You can't quit us. (But you just did.)",
        "🚪 Exiting stage left...",
        "📸 Until next time, keep shooting!",
    ]
    return random.choice(QUIT_MESSAGES)


# ============================================================================
# STATISTICS & VALIDATION
# ============================================================================

def get_phrase_count() -> dict:
    """Return count of phrases in each category for validation."""
    return {
        "model_loading": len(MODEL_LOADING_PHRASES),
        "quick": len(QUICK_PROCESSING_PHRASES),
        "early": len(EARLY_PROCESSING_PHRASES),
        "mid": len(MID_PROCESSING_PHRASES),
        "long": len(LONG_PROCESSING_PHRASES),
        "marathon": len(MARATHON_PROCESSING_PHRASES),
        "meta": len(VISIONCREW_META_PHRASES),
        "total": (len(MODEL_LOADING_PHRASES) + 
                 len(QUICK_PROCESSING_PHRASES) +
                 len(EARLY_PROCESSING_PHRASES) +
                 len(MID_PROCESSING_PHRASES) +
                 len(LONG_PROCESSING_PHRASES) +
                 len(MARATHON_PROCESSING_PHRASES) +
                 len(VISIONCREW_META_PHRASES))
    }


if __name__ == "__main__":
    # Validation check
    counts = get_phrase_count()
    print("📊 Phrase Library Statistics:")
    print(f"  Model Loading: {counts['model_loading']}")
    print(f"  Quick (0-5min): {counts['quick']}")
    print(f"  Early (5-15min): {counts['early']}")
    print(f"  Mid (15-30min): {counts['mid']}")
    print(f"  Long (30-60min): {counts['long']}")
    print(f"  Marathon (60+min): {counts['marathon']}")
    print(f"  VisionCrew Meta: {counts['meta']}")
    print(f"  TOTAL: {counts['total']} phrases")
    
    # Test phrase selection
    print("\n🧪 Testing phrase selection:")
    print(f"  Loading: {get_model_loading_phrase()}")
    print(f"  Quick: {get_phrase_by_duration(120)}")  # 2 min
    print(f"  Mid: {get_phrase_by_duration(1200)}")  # 20 min
    print(f"  Marathon: {get_phrase_by_duration(4000)}")  # 66 min
    print(f"  Quit: {get_quit_message()}")
