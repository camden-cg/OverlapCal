# Hangout Finder

A single-page website. Create a group and share the link so everyone can easily upload their availability.

Site: `https://camden-cg.github.io/OverlapCal/`.

## Use

- Open the site and click **Create group link**. Each group gets its own
  link, like `.../#/g/k3x9...`. Send different links to different groups.
- Mouse: drag across the calendar, including across days, to add free time.
  A plain click adds one hour. Hover a block and click x to remove it.
- Phone: tap a start time, then tap an end time.
- Green areas and the **Best times** list show when the most people overlap.

## Privacy

Each group has a unique link that acts as its access key. Anyone with the link can view and edit that group's availability. Groups cannot access each other's data through the website.

Data submitted to the website is stored in a Firebase Realtime Database managed by the site owner. The site does not require accounts or collect email addresses. However, participant display names, group names, and availability are stored and are accessible to the site owner.

**Do not** share group links publicly or enter sensitive personal information.

If you prefer to host your own database, you can set one up using the instructions in private_hosting.md.
