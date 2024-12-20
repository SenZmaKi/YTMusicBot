# Setup the Bot

1. Head over to [Discord Developer Portal](https://discord.com/developers/applications).

- Create a new application.

  ![new application](https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/.github/images/setup-bot/1.png)
  
  ![create new application](https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/.github/images/setup-bot/2.png)

2. Switch to the `Bot` tab and click `Reset Token`.

   ![reset token](https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/.github/images/setup-bot/3.png)

   - Copy the token and create a `.env` file in the project root directory as follows:

     ```env
     DISCORD_TOKEN=<token-goes-here>
     ```

3. Switch to the `OAuth2` tab and scroll down to the `OAuth2 URL Generator` section.

   - Check the `application.commands` and `bot` scopes.

     ![oauth2 scopes](https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/.github/images/setup-bot/4.png)

4. Scroll down to the `Bot Permissions` section.

   - Check the `Send Messages`, `Send Messages in Threads`, `Connect`, and `Speak` permissions.

     ![bot permissions](https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/.github/images/setup-bot/5.png)

5. Scroll down to the `GENERATED URL` section.

   - Open the URL in a new tab.

     ![generated url](https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/.github/images/setup-bot/6.png)

6. Select your server and click `Continue`.

   ![select server](https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/.github/images/setup-bot/7.png)

7. Click `Authorize`.

   ![authorize](https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/.github/images/setup-bot/8.png)

8. Copy the Server ID.

   ![copy server id](https://raw.githubusercontent.com/SenZmaKi/YTMusicBot/master/.github/images/setup-bot/9.png)

   - Add the following to your `.env` file:

     ```env
     SERVER_IDS=<server-id>
     ```

9. At this point, your `.env` file should look something like this:

   ```env
   DISCORD_TOKEN=<token-goes-here>
   SERVER_IDS=<server-id>
   ```

10. To add other servers, repeat steps 5-8 for each server, but at step 8, append a comma followed by the new server ID to the `SERVER_IDS` variable:

    ```env
    SERVER_IDS=<server-id>,<server-id-2>
    ```
