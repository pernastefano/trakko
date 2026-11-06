# User guide

TRAKKO lets you log things that happen on a calendar and see how often they happen. You create
**Tracks** (a topic, like "Workout" or "Menstrual Cycle"), give each Track its own **Event Types**
(like "Running" or "Cycle Start"), and log **Entries**: one occurrence of an Event Type on a day,
with an optional short note.

## Install the app on your phone

TRAKKO is a web app. Open its address in your phone's browser, then add it to the home screen so it
opens full-screen like any other app. The address must start with `https://` (ask whoever runs your
TRAKKO server if it does not).

**iPhone / iPad (Safari)**

1. Open the TRAKKO address in **Safari**.
2. Tap the **Share** button.
3. Choose **Add to Home Screen**, then **Add**.

**Android (Chrome)**

1. Open the TRAKKO address in **Chrome**.
2. Tap the **⋮** menu.
3. Choose **Install app** (or **Add to Home screen**), then confirm.

**Computer (Chrome, Edge)**: click the install icon in the address bar. You can also just use the
site in a tab; it is laid out as a centered column.

## Create your account

The first time you open TRAKKO you see the sign-in screen.

1. Tap **Create an account**.
2. Choose a **username** (3 to 32 letters, digits, dots, dashes or underscores) and a **password**
   (at least 8 characters), type the password twice, and tap **Create account**.
3. You are signed in on that device for 30 days, and you start with one Track, "My Track".

Several people can use the same TRAKKO server: each has their own account and sees only their own
Tracks, entries and statistics. To sign in on another device, use **Sign in** with the same
username and password. If **Create an account** is not offered, the person running the server has
closed registration: ask them for access.

There is no email address, so a forgotten password cannot be recovered. Keep your **Export JSON**
file (see below) so you can start again with a new account if you ever lose access.

## The screen

- **Top:** the current Track, with arrows and a position such as `2/5`. Swipe the bar left or right,
  or tap the arrows, to switch Track. The app starts on your default Track.
- **Middle:** the calendar (Home), your statistics, or your settings.
- **Bottom:** **Home**, **Statistics** and **Settings**.

The default look is dark graphite with amber highlights. You can change it in **Settings → Appearance** (see below).

## Create your Tracks and Event Types

1. Tap **Settings**.
2. Under **Tracks**, type a name in **New Track** and tap **Add**. You land on the new Track's page.
3. Tap **Add event type** and fill in:
   - **Name**, for example "Running".
   - **Color**: tap one of the colors. The second group, **Theme backgrounds**, has the background
     and surface colors of every theme (useful for a marker that blends with the app).
   - **Icon**: **None** (just the colored dot), **Emoji**, or **Letter or number** (one or two
     characters, such as `G` or `7`). For an emoji, tap **Choose an emoji** and pick one from the
     list; you do not type it. The list shows only emoji your device can display. The preview next
     to the name shows the result.
4. Tap **Save**.

Each Track has its own Event Types; a Track needs at least one before you can log anything in it.

### Change them later

- **Rename a Track**: open it in Settings, edit the name, tap **Save**.
- **Default Track**: open it and tap **Make default**. The app starts on the default Track.
- **Reorder**: use the up and down arrows next to a Track or an Event Type.
- **Edit an Event Type**: tap it in the Track's page. You can change the name, color and icon.
- **Delete**: **Delete Track** (on the Track's page) or **Delete** (in the Event Type dialog). The app
  tells you how many Event Types and entries will disappear and asks you to confirm. This cannot be
  undone. The only remaining Track cannot be deleted.

## Log what happened

1. On **Home**, tap a day.
2. Tap the Event Type, optionally write a **Note** (up to 280 characters), and tap **Save**.

The day now shows a colored marker with the Event Type's icon. You can log several entries on the
same day, even of the same Event Type.

### Edit or delete an entry

Tap the day, then tap the entry in the list at the top of the sheet. Change the Event Type or the
note and tap **Save**, or tap **Delete** to remove it. **Cancel** goes back to adding a new entry.

## The calendar

Switch between **Day**, **Week** and **Month** with the control at the top (Month is the default).

- **Swipe** left or right (or tap the arrows next to the title) to move to the next or previous
  month, week or day.
- **Today** jumps back to the current date. Today is highlighted.
- Weeks start on **Monday**.
- Month view is a grid of bordered days. It shows up to three markers per day; more are shown as
  `+2`, `+3`, and so on. Open the day to see everything.
- Only the entries of the current Track are shown. Days of the neighboring months are dimmed but can
  be tapped too.

## Statistics

Tap **Statistics**. Choose **Month**, **Year** or **All**; the arrows move to the previous or next
month or year. Everything is for the current Track.

- **Event types**: for each one, the number of entries in the period, when the last entry was,
  the **current streak** (days in a row up to today or yesterday), the **longest streak**, and the
  **average interval** between entries (useful, for example, to see the length of a cycle).
  Streaks, "last entry" and the interval always consider the whole history, not just the period.
- **Entries per week / month**: a bar chart.
- **Activity**: a heatmap with a square per day; a stronger color means more entries that day. For a year or
  all time it scrolls sideways and starts at the most recent weeks.

## Back up and move your data

In **Settings → Data**:

- **Export JSON** downloads a file (`trakko-export-<date>.json`) with all your Tracks, Event Types
  and entries. Keep it somewhere safe.
- **Import JSON** reads such a file. **It replaces everything currently in the app**, so the app asks
  you to confirm first. A file that cannot be read, or that is not a valid TRAKKO export, is
  rejected and nothing changes.

### Default calendar view

Under **Settings → Tracks**, **Default calendar view** (Day, Week or Month) sets the view the app
opens with. It is saved in your account, so every device you sign in on starts the same way. You can
still switch view at any time from the calendar; that does not change your default.

### Appearance

**Settings → Appearance** lets you pick a theme. **Automatic** (the full-width card at the top) is the
default look, or a light one when your phone is set to light mode; below it are **Graphite**, **Midnight**, **Forest** and **Ember** (dark), and
**Paper** and **Sand** (light). The change is immediate and is saved in your account, so every
device you sign in on shows the same theme. (If the app cannot reach the server it says so and
applies the theme on that device only.)

### Account

**Settings → Account** shows who is signed in.

- **Change password**: enter your current password, then the new one twice (at least 8
  characters, different from the old one) and tap **Change password**. You stay signed in on this
  device; **your other devices are signed out** and need the new password. If you forgot your
  current password it cannot be changed here (there is no email recovery).
- **Sign out**: do it when you share a device.

### Version and credits

The last section of Settings has two links: the **Project** (TRAKKO, on GitHub:
https://github.com/pernastefano/trakko/) and its **Author** (Stefano Perna:
https://github.com/pernastefano/). Below them, a small line shows the version of the app that is
running (for example `TRAKKO v0.1.2`): useful when you report a problem.

## Working offline

The app opens without a connection and shows the last data it loaded, with a banner saying you are
offline. Changes cannot be saved offline: try again when you are back online.

## Troubleshooting

| Problem | What to do |
|---------|------------|
| "Add to Home Screen" is missing on iPhone | Use Safari (not another browser's in-app view). |
| The calendar shows no markers | Check the Track in the top bar; markers belong to the current Track. |
| I cannot log anything | The Track has no Event Types yet; add one in Settings. |
| "Authentication required" or the sign-in screen appears | Your session ended; sign in again. |
| "Invalid username or password" | Check both; usernames ignore capital letters, passwords do not. |
| "The current password is not correct" | Typed wrong when changing your password; try again. |
| I changed my password and my phone was signed out | Expected: sign in again on your other devices with the new password. |
| "That username is already taken" | Choose another username. |
| "Registration is closed" | The server does not accept new accounts; ask whoever runs it. |
| An update does not appear | Close and reopen the app (or reload the page); a new version is fetched in the background and used the next time it opens. |
