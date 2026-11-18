Follow the steps below if you want to keep all data 100% private within your group.

## Deploy on GitHub Pages

1. Put `index.html` in a GitHub repo.
2. Repo **Settings > Pages**, set the source to your main branch, root folder.
3. Your site is at `https://<user>.github.io/<repo>/`.
Site: `https://<user>.github.io/<repo>/`.

## Turn on syncing (one-time)

GitHub Pages can't store data, so availability lives in your own free Firebase
Realtime Database. Nothing is stored on GitHub (or anywhere else).

1. Go to console.firebase.google.com and sign in with a Google account.
2. Click **Create a project** (or **Add project**), name it, turn off Google
   Analytics if asked, and click **Create**.
3. In the left menu, open **Build > Realtime Database** and click **Create Database**.
4. Pick any location, choose **Start in locked mode**, and click **Enable**.
5. Open the **Rules** tab, replace everything with the rules below, and click **Publish**:
   ```json
   {
     "rules": {
       "groups": {
         "$gid": {
           ".read": true,
           ".write": true,
           ".validate": "$gid.length >= 10 && $gid.length <= 30"
         }
       }
     }
   }
   ```
   There is no rule on `groups` itself, so nobody can list or browse groups.
   You can only read or write a group if you know its link.
6. Open the **Data** tab and copy the URL at the top. It looks like
   `https://your-project-default-rtdb.firebaseio.com` (some regions end in
   `.firebasedatabase.app`).
7. In `index.html`, paste it in place of the default database (keep the ''):
   ```js
   const DB = "https://your-project-default-rtdb.firebaseio.com";
   ```
8. Commit the change to GitHub and wait a minute for Pages to update.

To test, create a group on your site and open its link in a second browser or
on your phone. Blocks you add should appear in both within a few seconds.

Until `DB` is set, the site runs in demo mode (data stays in your browser).
