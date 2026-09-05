# YouTube cookies on Dokploy

YTMusicBot can provide a Netscape-format cookie file to yt-dlp. This can help
when YouTube requires authentication or responds with a "confirm you're not a
bot" error.

Cookies are account credentials. Never commit the cookie file, paste it into
logs, or send it to another person.

> [!WARNING]
> Use a dedicated Chrome profile and preferably a separate, non-primary Google
> account for the bot. The exported file can grant access to the signed-in
> session, and automated access may cause YouTube to invalidate the session or
> take action against the account. Do not export cookies from a profile that
> contains your personal email, banking, work, or other sensitive sessions.

## 1. Export cookies locally

Sign in to YouTube in your browser. From PowerShell in the project directory,
export the browser cookies with yt-dlp:

```powershell
uv run yt-dlp --cookies-from-browser chrome --cookies "app\secrets\youtube-cookies.txt"
```

### Select a browser profile

The option format is `BROWSER:PROFILE`. For example, to export from Chrome's
`Profile 1`:

```powershell
uv run yt-dlp --cookies-from-browser "chrome:Profile 1" --cookies "app\secrets\youtube-cookies.txt"
```

For Chrome's default profile, use:

```powershell
uv run yt-dlp --cookies-from-browser "chrome:Default" --cookies "app\secrets\youtube-cookies.txt"
```

To find the correct profile name:

1. Open the intended Chrome profile.
2. Navigate to `chrome://version`.
3. Find **Profile Path**. Its final directory is the profile name, commonly
   `Default`, `Profile 1`, or `Profile 2`.

You can also pass the complete profile directory:

```powershell
uv run yt-dlp --cookies-from-browser "chrome:C:\Users\YOUR_NAME\AppData\Local\Google\Chrome\User Data\Profile 1" --cookies "app\secrets\youtube-cookies.txt"
```

Keep the entire browser specification in quotes when the profile name or path
contains spaces. Selecting a profile does not bypass the Windows DPAPI error;
use the extension-based fallback below if Chrome still refuses decryption.

Replace `chrome` with `edge` or `firefox` if necessary. Chromium-based browsers
may need to be completely closed before yt-dlp can access their cookie database.

On newer Windows/Chrome installations, the command may fail with `Failed to
decrypt with DPAPI`. In that case, use the **Get cookies.txt LOCALLY** browser
extension recommended by the yt-dlp documentation:

1. Open a private/incognito window and sign in to YouTube.
2. Export only the `youtube.com` cookies in Netscape format.
3. Save the export as `app/secrets/youtube-cookies.txt`.
4. Close the private/incognito window and do not reopen that session.

Be careful with similarly named extensions. The old **Get cookies.txt**
extension—not **Get cookies.txt LOCALLY**—was reported as malware and removed
from the Chrome Web Store.

This command may export cookies for sites other than YouTube. A safer option is
to use a dedicated browser profile containing only the YouTube session. See the
[yt-dlp cookie documentation](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
and [YouTube extractor guidance](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)
for current browser-specific recommendations.

The exported file must use Netscape cookie format. Its first line should be one
of the following:

```text
# Netscape HTTP Cookie File
```

```text
# HTTP Cookie File
```

## 2. Create the Dokploy file mount

Open the YTMusicBot application in Dokploy, then:

1. Open **Advanced**.
2. Find **Mounts** and add a **File Mount**.
3. Paste the complete contents of `app/secrets/youtube-cookies.txt` into
   **Content**.
4. Set the file path/name to `youtube-cookies.txt`.
5. Set **Mount Path** to `/app/secrets/youtube-cookies.txt`.
6. Save the mount.

File mounts are intended for individual configuration files and persist across
deployments. See the [Dokploy mount documentation](https://docs.dokploy.com/docs/core/applications/advanced#volumesmounts).

Dokploy may expose the mounted file as root-owned or read-only to the non-root
application user. At startup, YTMusicBot copies it to a private writable file in
the container's temporary directory because yt-dlp updates its cookie jar while
running. The original mounted file remains unchanged.

## 3. Configure the environment

In the application's **Environment** section, add:

```env
YTDLP_COOKIE_FILE=/app/secrets/youtube-cookies.txt
```

Do not also configure `YTDLP_COOKIES_FROM_BROWSER`. The production container
does not have access to the browser profile on your computer.

Save the environment and redeploy the application.

## 4. Verify the mount

Use Dokploy's application terminal or run-command feature to check that the
non-root application user can read the file:

```sh
test -r /app/secrets/youtube-cookies.txt && echo "Cookie file is readable"
```

Do not use `cat`, `head`, or another command that would print cookie contents
into the terminal or deployment logs.

After verification, play a song and inspect the application logs for yt-dlp
errors.

## Updating expired cookies

YouTube may rotate or invalidate cookies. If authentication errors return:

1. Export a fresh `app/secrets/youtube-cookies.txt` locally.
2. Replace the content of the existing Dokploy File Mount.
3. Save and redeploy the application.
4. Delete the local exported file when it is no longer needed.

## Why not store the contents in an environment variable?

`YTDLP_COOKIE_FILE` is expected to contain a file path, not cookie contents.
Netscape cookie files are multiline and tab-delimited, so copying them into an
environment variable can corrupt their formatting. Environment values can also
be exposed through container inspection or diagnostics. A File Mount supplies
the exact file yt-dlp expects without requiring a startup script to reconstruct
it.
