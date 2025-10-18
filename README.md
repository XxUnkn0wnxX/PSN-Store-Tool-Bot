<h1 align="center">🎮 PSNToolBot</h1>
<p align="center">A Discord bot for PS3 avatar tools & PSN account lookups</p>

---

## 📌 What is PSNToolBot?

**PSNToolBot** is a handy Discord bot that allows you to:

- 🛒 Add **PlayStation avatars (PS3/PS4)** directly to your shopping cart
- 🔍 Retrieve **PlayStation Account IDs** using just a PSN username
- 💬 Trigger commands via slash menus or the legacy prefix (default `$`)

Built for convenience and PlayStation fans! 💙

---

## 🛠️ Requirements

Before running the bot, you'll need:

- ✅ A valid **NPSSO token** (for PSN API access)
- ✅ Your **Discord bot token**
- ✅ Your **Discord server id** (bot is locked to this server)

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

## ⚙️ Configure the Bot

### 1. `.config` (Discord settings)

Copy the template and fill in your Discord details:

```bash
cp .config.template .config
```

```
TOKEN=your_discord_bot_token
GUILD_ID=your_discord_server_id
PREFIX=$   # Optional; defaults to `$`
```

### 2. `.env` (PlayStation credentials)

Copy the template and add your PSN secrets:

```bash
cp .env.template .env
```

```
NPSSO=your_64_char_npsso_token
PDC=optional_pdccws_p_cookie
```

- `NPSSO` is required for PSN API calls.
- `PDC` is optional; if omitted, supply it as an override when commands ask for it.

---

## 🛡️ Discord Bot Configuration

In the [Discord Developer Portal](https://discord.com/developers/applications):

- Enable the **Message Content Intent** under *Privileged Gateway Intents*.
- Grab the **Server ID** of the guild where you want to test slash commands and set `GUILD_ID` in `.env`.
- Generate an OAuth2 URL with the following scopes:

  ```
  bot
  applications.commands
  ```

  Add extra permission bits (e.g. Administrator) if your server setup requires them.

---

## ▶️ Run the Bot

```bash
python3 bot.py
```

Your bot is now live and ready to add avatars or fetch PSN IDs! 🎉

### Optional CLI flags

- `python3 bot.py --force-sync` – Force a full slash-command resync even if commands already exist in Discord. Handy after you change command definitions and want them refreshed immediately.
- Supply your `pdccws_p` cookie at runtime or set it in `.env` as `PDC`. The slash commands will fall back to the `.env` value if you omit the cookie argument.
- Need to hit a different PlayStation account? Provide an `NPSSO` value in the slash command, otherwise the `.env` `NPSSO` is used.
- Legacy prefix commands mirror the slash commands but always use the credentials in `.env`. Set `PREFIX` in `.env` (default `$`) if you want to change it.

The bot auto-syncs commands in the guild defined by `GUILD_ID` on startup and refuses to run in other servers. Forced syncs and the built-in verifier ensure commands appear even if Discord is slow to propagate them.
**Important:** This project is intended for single-server/self-hosted setups. Invite the bot only to the server that matches `GUILD_ID`.

---

## 🕹️ Command Reference

### Slash commands (region-first)

| Command | Description |
| --- | --- |
| `/psn check <region> <product_id> [product_id ...]` | Fetch avatar previews. Optional NPSSO/PDC overrides accepted via command options. |
| `/psn add <region> <product_id>` | Add a single avatar to cart. Optional NPSSO/PDC overrides supported. |
| `/psn remove <region> <product_id>` | Remove a single avatar from cart. |
| `/psn account <username>` | Resolve a PSN username to the account ID. |
| `/ping`, `/tutorial`, `/credits`, `/help` | Utility commands for latency, onboarding, credits, and quick reference. |

> ℹ️ Slash commands accept overrides for NPSSO/PDC even if they are set in `.env`. If omitted, the bot falls back to the `.env` values.

### Prefix commands (default `$`)

| Command | Description |
| --- | --- |
| `$psn check <region> <product_id> [more ids…]` | Region-first syntax. Accepts multiple IDs separated by spaces or newlines. Shows an embed per ID. Alias: `$check_avatar`. |
| `$psn add <region> <product_id> [more ids…]` | Batch add avatars to cart. Alias: `$add_avatar`. |
| `$psn remove <region> <product_id> [more ids…]` | Batch remove avatars from cart. Alias: `$remove_avatar`. |
| `$psn account <username>` | Lookup a PSN account ID. Alias: `$account_id`. |
| `$ping`, `$tutorial`, `$credits`, `$help` | Prefix equivalents for utility commands. |

> ⚠️ Prefix commands always use the credentials defined in `.env`. Passing NPSSO or cookie overrides via prefix is blocked — use the slash command instead.

#### Batch entry examples

```
$psn check en-US
EP4293-CUSA15900_00-AV00000000000005
EP4067-NPEB01320_00-AVPOPULUSM000177
```

```
$psn add au EP4293-CUSA15900_00-AV00000000000005 EP4067-NPEB01320_00-AVPOPULUSM000177
```

Each ID is processed individually; the bot sends the familiar avatar preview embed for every success and a summary for any failures.

---

## 📝 TODO

- [ ] Store NPSSO/PDC values in an encrypted local database to support multiple users safely.
- [ ] Add a `--env` CLI flag so the bot can explicitly load credentials from `.env` when desired.

## 💬 Support & Feedback

Have issues or ideas?  
Open an [issue](https://github.com/yourusername/PSNToolBot/issues) or submit a pull request!

---

## 🧾 Credits

- 👨‍💻 **Bot Developer**: [𐌔𐌉𐌂𐌊.dll](https://github.com/sickfff)
- 🛠️ **Bot Maintainer**: [OpenAI](https://openai.com/codex/)
- 🧠 Inspired by tools and ideas shared within the **PS3 modding & dev community**
- 📘 Special thanks to contributors and open-source libraries that made this possible

---

<p align="center"><b>Built with 💻, ☕, and 🎮 by 𐌔𐌉𐌂𐌊.dll</b></p>
