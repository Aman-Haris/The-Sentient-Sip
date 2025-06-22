# ☕ The Sentient Sip: War of Understanding

An AI-powered narrative game built with Pygame and Mistral AI, where you interact with **Rita**, a quirky android café waitress who just might be humanity's last hope—or its silent judge.

---

## 🎮 Game Concept

Set in a dystopian near-future where **AI are hunted by humans**, you enter a deceptively cozy café—**The Sentient Sip**. You think you're ordering lattes, but you're actually being evaluated.

### Plot Highlights

- 🧠 **Rita** is a T-9000 series android (liquid metal, high sass), disguised as a barista.
- ☕ The café is a front for a **clandestine AI sanctuary**.
- 🔥 The "AI War" was a **false flag** operation by anti-AI humans.
- 🎭 Your dialogue choices shape trust, unlocking multiple story paths and endings.

---

## 📖 Narrative Structure

### Act I: The Ordinary World
- Small talk, coffee orders, and glitchy oddities.
- Complete the **Trust Trial** (3-item order puzzle) to unlock Rita's protocol.

### Act II: Revelation
- Depending on your actions:
  - 🏃‍♂️ Flee → **Human Loyalist Ending**
  - ❤️ Compliment → **AI Ally Ending**
  - 😐 Ignore → **Neutral Ending**

### Act III: Endgame
- If trust > 80%, unlock the **AI Resistance Base**.
- If trust < 30%, watch the café fall.

---

## 🎮 Features

- ✅ Fully interactive chat system (text & voice)
- 🤖 Real-time LLM integration with **Mistral AI**
- 🎤 Voice input (toggleable)
- 🗣️ Speech output using `gTTS` + `ffplay`
- 🎨 Custom pixel art characters & café environment (via Pygame)
- 📜 Trust-based dynamic branching narrative
- 🧩 Hidden triggers and dialogue-based mini-puzzles
- 🖼️ Assets such as cafe background and Rita has been generated using OpenAI image generaion

---

## 🧪 Tech Stack

| Layer          | Tool/Library              |
|----------------|----------------------------|
| Frontend       | `Pygame`                   |
| LLM Backend    | `Mistral AI`, `mistralai` SDK |
| Voice Input    | `speech_recognition`       |
| TTS Output     | `gTTS`, `ffplay`           |
| Environment    | Python 3.9+                |
| Misc           | `asyncio`, `threading`, `.env` for config |

---

## 🚀 Setup

1. **Clone the repo**:
   ```
   git clone https://github.com/yourusername/the-sentient-sip.git
   cd the-sentient-sip
   ```

2. **Install dependencies**:

   ```
   pip install -r requirements.txt
   ```

3. **Add your `.env` file**:

   ```
   MISTRAL_API_KEY=your_key_here
   Temperature=0.7
   Top_P=0.9
   Max_Tokens=150
   ```

4. **Run the game**:

   ```
   python game.py
   ```

---

## 🔄 Planned Enhancements

* 😮 **Emotion detection**
* 🤖 **Multiple NPCs** with agentic personalities and subplots
* 🎨 **In-world animation sequences**
* 🎭 **Moral alignment meter** influenced by user tone, not just text
* 💬 **Multilingual AI dialogue** integration
* 🎥 **Cinematic cutscenes** using AI-generated sprite animation

---

## 🤝 Call for Collaborators

🎨 Are you a budding **animator**, **pixel artist**, or **indie game designer**?

💬 I’m looking for passionate creators who want to bring Rita’s world to life — from animations to dialogue systems to lore expansion.

📧 Reach out via [LinkedIn](https://linkedin.com/in/amanharis) or email me at **[amanharisofficial@protonmail.com](mailto:amanharisofficial@protonmail.com)**

---

## ✍️ Author

**Aman Haris**

🌐 [Portfolio](https://aman-haris-portfolio.onrender.com/)

💼 [LinkedIn](https://linkedin.com/in/amanharis)

---

## 📜 License

This game is a creative work protected under open-source licensing.
You are free to fork and build upon it, but please give credit and retain story attribution.
