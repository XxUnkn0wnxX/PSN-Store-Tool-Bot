<h1 align="center">🎮 PSNToolBot</h1>
<p align="center">A Discord bot for PS3/PS4 avatar tools & PSN account lookups</p>

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

- ✅ A valid **pdccws_p cookie** (PDC) from [playstation.com](https://www.playstation.com)
- ✅ Your **Discord bot token**
- ✅ The **Discord server ID(s)** you want the bot to run in (list all allowed servers)

## 🚀 Getting Started

Clone the repository and install dependencies:

```bash
git clone https://github.com/XxUnkn0wnxX/PSNToolBot.git
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
GUILD_ID=primary_server_id[,another_server_id,...]
PREFIX=$   # Optional; defaults to `$`
```

### 2. `.env` (PlayStation credentials)

Copy the template and add your PSN secrets:

```bash
cp .env.template .env
```

```
PDC=your_pdccws_p_cookie
```

- `PDC` is the `pdccws_p` cookie you can grab from your browser after logging into [playstation.com](https://www.playstation.com). Start the bot with `--env` to let it fall back to this value; otherwise pass the cookie with each command.
- *(Optional)* If you still need NPSSO for account lookups, see the legacy section at the end of this README.

---

## 🛡️ Discord Bot Configuration

In the [Discord Developer Portal](https://discord.com/developers/applications):

- Enable the **Message Content Intent** under *Privileged Gateway Intents*.
- Grab the **Server ID(s)** of every guild where the bot should run and set `GUILD_ID` in `.env` (comma-separated for multiples).
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
- `python3 bot.py --env [path]` – Load credentials from `.env` (or the file at `path`) so the bot can fall back to `PDC`/`NPSSO` without requiring per-command overrides.
- Cart commands generate NPSSO tokens automatically; no manual NPSSO input is required for add/remove flows.
- Legacy prefix commands mirror the slash commands but always use the credentials in `.env`. Set `PREFIX` in `.env` (default `$`) if you want to change it.

The bot auto-syncs commands in every guild listed in `GUILD_ID` on startup and refuses to run in other servers. Forced syncs and the built-in verifier ensure commands appear even if Discord is slow to propagate them across all configured guilds.
**Important:** This project is intended for self-hosted setups. Only list guild IDs that you control in `GUILD_ID`.

---

## 🕹️ Command Reference

### Slash commands (region-first)

| Command | Description |
| --- | --- |
| `/psn check <region> <product_id> [up to 3 more IDs]` | Fetch up to four avatar previews without needing NPSSO/PDC overrides. |
| `/psn add <region> <product_id> [up to 3 more IDs]` | Add up to four avatars to cart. Provide PDC unless the bot runs with `--env`. |
| `/psn remove <region> <product_id> [up to 3 more IDs]` | Remove up to four avatars from cart. Provide PDC unless the bot runs with `--env`. |
| `/psn account <username>` | Resolve a PSN username to the account ID (requires NPSSO in `.env`). |
| `/ping`, `/tutorial`, `/credits`, `/help` | Utility commands for latency, onboarding, credits, and quick reference. |

> ℹ️ The add/remove slash commands accept optional PDC overrides and auto-generate NPSSO tokens. `/psn account` will only work when an NPSSO is configured in `.env`.

### Prefix commands (default `$`)

| Command | Description |
| --- | --- |
| `$psn check <region> <product_id> [more ids…]` | Region-first syntax. Accepts multiple IDs separated by spaces or newlines. |
| `$psn add <region> <product_id> [more ids…] --pdc YOUR_COOKIE` | Batch add avatars to cart. Required when the bot wasn't started with `--env`. |
| `$psn remove <region> <product_id> [more ids…] --pdc YOUR_COOKIE` | Batch remove avatars from cart. Required when the bot wasn't started with `--env`. |
| `$psn account <username>` | Lookup a PSN account ID (requires NPSSO in `.env`). |
| `$ping`, `$tutorial`, `$credits`, `$help` | Prefix equivalents for utilities. |

> ⚠️ Prefix commands delete your invoking message. Add `--pdc YOUR_COOKIE` at the end unless the bot is running with `--env`.

#### Batch entry examples

```
$psn check en-AU
EP4293-CUSA15900_00-AV00000000000005
EP4067-NPEB01320_00-AVPOPULUSM000177
```

```
$psn add au EP4293-CUSA15900_00-AV00000000000005 EP4067-NPEB01320_00-AVPOPULUSM000177 --pdc MY_PDCCWS_COOKIE
```

Each ID is processed individually; the bot sends the familiar avatar preview embed for every success and a summary for any failures.

---

## 📝 TODO

- [ ] Store PDC values in an encrypted local database to support multiple users safely.
- [ ] Add a `--env` CLI flag so the bot can explicitly load credentials from `.env` when desired.
- [ ] Build a per-user cart UI with buttons to review/remove queued items.
- [ ] Add buttons to avatar preview embeds so users can add items to cart directly.


---

## 📚 Legacy NPSSO Reference

NPSSO tokens are no longer required for cart operations, but you can still generate one if you want `/psn account` or other advanced PSN features.

1. Log in to your PlayStation account at [playstation.com](https://www.playstation.com)
2. Open this URL:  
   👉 [`https://ca.account.sony.com/api/v1/ssocookie`](https://ca.account.sony.com/api/v1/ssocookie)
3. Look for the line containing:
   ```json
   {"npsso":"your-64-character-token"}
   ```
4. Copy the token and add it to your `.env` file as `NPSSO=...`

---

## 💬 Support & Feedback

Have issues or ideas?  
Open an [issue](https://github.com/XxUnkn0wnxX/PSN-Store-Tool-Bot/issues) or submit a pull request!

---

## 🧾 Credits

- 👨‍💻 **Bot Developer**: [𐌔𐌉𐌂𐌊.dll](https://github.com/sickfff)
- 🛠️ **Bot Maintainer**: [OpenAI](https://openai.com/codex/)
- 🧠 Inspired by tools and ideas shared within the **PS3 modding & dev community**
- 📘 Special thanks to contributors and open-source libraries that made this possible

---

<p align="center"><b>Built with 💻, ☕, and 🎮 by 𐌔𐌉𐌂𐌊.dll</b></p>
