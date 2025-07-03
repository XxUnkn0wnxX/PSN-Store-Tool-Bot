<h1 align="center">🎮 PSNToolBot</h1>
<p align="center">A Discord bot for PS3 avatar tools & PSN account lookups</p>

---

## 📌 What is PSNToolBot?

**PSNToolBot** is a handy Discord bot that allows you to:

- 🛒 Add **PlayStation 3 avatars** directly to your shopping cart
- 🔍 Retrieve **PlayStation Account IDs** using just a PSN username

Built for convenience and PlayStation fans! 💙

---

## 🛠️ Requirements

Before running the bot, you'll need:

- ✅ A valid **NPSSO token** (for PSN API access)
- ✅ Your **Discord bot token**

---

## 🔐 How to Get Your NPSSO Token

1. Log in to your PlayStation account at [playstation.com](https://www.playstation.com)
2. Open this URL:  
   👉 [`https://ca.account.sony.com/api/v1/ssocookie`](https://ca.account.sony.com/api/v1/ssocookie)
3. Find this line in the response:
   ```json
   {"npsso":"your-64-character-token"}
   ```
4. Copy the token and save it — you’ll need it in `.env`

---

## 🚀 Getting Started

Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/PSNToolBot.git
cd PSNToolBot
pip install -r requirements.txt
```

---

## ⚙️ Setup `.env`

Create a `.env` file in the root directory with:

```
DISCORD_TOKEN=your_discord_bot_token
NPSSO=your_64_char_npsso_token
```

---

## ▶️ Run the Bot

```bash
python bot.py
```

Your bot is now live and ready to add avatars or fetch PSN IDs! 🎉

---

## 💬 Support & Feedback

Have issues or ideas?  
Open an [issue](https://github.com/yourusername/PSNToolBot/issues) or submit a pull request!

---

## 🧾 Credits

- 👨‍💻 **Bot Developer**: [Gabriel Roriz Silva](https://github.com/groriz11)
- 🧠 Inspired by tools and ideas shared within the **PS3 modding & dev community**
- 📘 Special thanks to contributors and open-source libraries that made this possible

---

<p align="center"><b>Built with 💻, ☕, and 🎮 by Gabriel Roriz Silva</b></p>
