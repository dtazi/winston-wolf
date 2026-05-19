# Winston Wolf Outreach

Sends individual emails from a Microsoft 365 mailbox via Microsoft Graph, authenticated by OAuth using the device code flow. Designed for the Richbond mission; transferable to any M365 tenant by swapping the Azure AD app credentials in `.env`.

## Setup

From this `outreach/` directory:

    uv sync

That's the whole install.

## Commands

### Sign in (one-time, until revoked)

    uv run ww-outreach auth

You'll see a short URL and an 8-character code. Open the URL on any device, paste the code, sign in with your Richbond account, click Allow. The tool saves a refresh token to `~/.winston-wolf/outreach-token.json` with file permissions 0600 (owner read/write only).

### Send an email

    uv run ww-outreach send --to recipient@example.com --subject "Hello" --body-file message.txt

The body file is read as UTF-8 plain text. The mail goes from your Richbond address and appears in your Sent Items. Replies come back to your inbox normally.

### Revoke access

    uv run ww-outreach revoke

Deletes the local token file. The printed URL is where you also revoke the app from Microsoft's side — required by Richbond IT in case of doubt, compromise, or lost device.

## What this does NOT do yet

- Multiple recipients per call
- Campaigns or batch sending
- AI-generated email drafting
- Automatic reply detection (the `Mail.ReadBasic` permission is approved but not yet used)
- HTML email bodies
- Templates or variables

Each is added the moment an actual mission step needs it.

## Where things live

- `~/.winston-wolf/outreach-token.json` — refresh token, owner-readable only
- `outreach/.env` — Azure AD app identifiers (not secrets)

## Microsoft Graph permissions

Two delegated scopes granted by Richbond IT:

- `Mail.Send` — used by the `send` command
- `Mail.ReadBasic` — approved for future reply detection, not yet called
