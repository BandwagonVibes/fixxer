# 🔰 The "Zero-to-Hero" Guide

**Never opened a terminal in your life? You're in the right place.**

If you're used to clicking icons and dragging folders, the terminal (that black screen with text) can look intimidating. But it's actually just a conversation. You type a request, and the computer does exactly what you ask.

This guide will teach you the basics and get FIXXER installed in under 5 minutes.

---

## 1. Open The Terminal

* **🍎 Mac:** Press `Command + Space`, type **Terminal**, and hit Enter.
* **⊞ Windows:** Press the Windows Key, type **PowerShell**, and hit Enter.
* **🐧 Linux:** You probably already know this, but usually `Ctrl + Alt + T`.

---

## 2. Anatomy of the Screen

When it opens, you'll see a line of text followed by a blinking cursor. It usually looks like `name@computer ~ %`.

Here's a breakdown of what you're looking at:

```text
  jane@macbook: ~ $ █
  └─1─┘ └─2──┘  3 4 5
```

1. **Who you are:** Your username (e.g., jane).
2. **Where you are:** The computer's name.
3. **The Folder:** The tilde (`~`) is shorthand for your Home folder.
4. **The Prompt:** The `$` or `%` symbol means "I'm listening."
5. **The Cursor:** This is where you type.

---

## 3. How to Speak "Computer"

Terminal commands are just sentences. They usually follow a simple **Verb → Adverb → Noun** structure.

Let's look at the command you'll use to install dependencies:

```text
  pip   install   -r   requirements.txt
  └1┘   └──2──┘   └3┘  └──────4───────┘
```

1. **The Tool (The Chef):** `pip` is the name of the program we want to use.
2. **The Action (The Verb):** `install` tells the program what to do.
3. **The Option (The Adverb):** `-r` stands for "recursive" or "read from." It modifies the action.
4. **The Target (The Noun):** `requirements.txt` is the file we want to act on.

**Rule of Thumb:**

- Spaces matter. Think of them as the spaces between words in a sentence.
- Capitalization matters. `Desktop` is different from `desktop`.

---

## 4. Let's Install FIXXER

Now that you know the language, let's execute the installation. You'll type (or copy-paste) these lines one by one, pressing **Enter** after each line.

### Option A: Easy Install with Homebrew (Mac Only - Recommended)

If you're on a Mac, this is the simplest way. Homebrew is like an "app store" for terminal programs.

**First, install Homebrew if you don't have it:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Then install FIXXER:**
```bash
# Add the FIXXER tap (this tells Homebrew where to find FIXXER)
brew tap bandwagonvibes/fixxer

# Install FIXXER (this downloads and installs everything automatically)
brew install fixxer
```

That's it! Skip to Step 5 to launch it.

---

### Option B: Install From Source (All Platforms)

If you're on Windows/Linux or prefer to install from source:

**Step 1: Download the Code**

This uses `git` to download the FIXXER folder from the internet to your computer.

```bash
git clone https://github.com/BandwagonVibes/fixxer.git
```

**Step 2: Enter the Folder**

This command `cd` (Change Directory) moves you inside the folder you just downloaded.

```bash
cd fixxer
```

**Step 3: Create a Safe Space (Virtual Environment)**

This creates a "virtual environment." Think of this like a **sandbox**. Anything we install here stays inside this folder and won't mess up your other computer settings.

```bash
python3 -m venv venv
```

Now **activate** the sandbox:

**On Mac/Linux:**
```bash
source venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
venv\Scripts\activate
```

You'll know it worked when your terminal line starts with `(venv)`.

**Step 4: The Final Install**

This installs FIXXER and all the fancy AI brains (CLIP, BRISQUE) into your sandbox.

```bash
pip install -e .
```

**Note:** On first launch, FIXXER will auto-download the CLIP vision model (~300MB). This happens only once.

---

## 5. Launch It!

If the previous steps finished without red text, you're done. Congratulations, you're now a terminal user! 🎉

To launch the app, just type:

```bash
fixxer
```

(You can use your mouse to click buttons inside the app, or use your keyboard!)

---

## 🆘 Troubleshooting

### "Command not found: brew" (Mac users doing Homebrew install)
- Install Homebrew first: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- Visit [brew.sh](https://brew.sh) for more info

### "Command not found: git" (Source install only)
- **Mac:** Install with `xcode-select --install`
- **Windows:** Download from [git-scm.com](https://git-scm.com)
- **Linux:** `sudo apt install git`

### "Command not found: python3" (Source install only)
- **Mac:** Install with `brew install python@3.11` (install Homebrew first: [brew.sh](https://brew.sh))
- **Windows:** Download from [python.org](https://python.org)
- **Linux:** `sudo apt install python3 python3-venv`

### Red Text During Install
- Read the error message carefully
- Common fix: Close terminal, reopen, try again
- Google the exact error message (seriously, this is what pros do!)

---

## 💡 Pro Tips

### Copying Text from Terminal
- **Mac:** `Command + C` (just like normal)
- **Windows PowerShell:** Highlight text, right-click
- **Linux:** `Ctrl + Shift + C`

### Pasting Text into Terminal
- **Mac:** `Command + V`
- **Windows PowerShell:** Right-click
- **Linux:** `Ctrl + Shift + V`

### Clearing the Screen
Type `clear` and hit Enter. Everything disappears, but nothing is deleted.

### Stopping a Running Program
Press `Ctrl + C`. This tells the program "Stop what you're doing."

---

**Built with precision. Secured with cryptography. Powered by AI.**

✞ **FIXXER PRO** - "CHAOS PATCHED // LOGIC INJECTED"
