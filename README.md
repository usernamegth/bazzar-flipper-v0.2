# Bazaar Flip Scanner (GitHub Pages edition)

Fully free, no server needed. A scheduled GitHub Actions workflow fetches the
Hypixel Skyblock Bazaar API, filters for items with high liquidity and a wide
instant-buy/instant-sell spread, and commits the result to `docs/data.json`.
GitHub Pages serves a static page (`docs/index.html`) that just reads that file.

Default filter:
- Estimated volume of **90,000+** over **5 days**, on both the buy side and sell side
- Spread of **20%+** between instant-buy and instant-sell price

(Same filter logic as before - see "How the 5-day volume figure works" below.)

## Setup (one-time)

1. **Push this folder to a GitHub repo** (see the earlier steps you already used, or:
   `git init && git add . && git commit -m "Initial commit" && git remote add origin <your-repo-url> && git push -u origin main`).

2. **Allow the workflow to commit back to the repo.**
   Go to your repo's **Settings → Actions → General → Workflow permissions**,
   select **"Read and write permissions"**, and save. (Without this, the
   workflow can fetch data but will fail to push `data.json` back.)

3. **Turn on GitHub Pages.**
   Go to **Settings → Pages**. Under "Build and deployment", set:
   - Source: **Deploy from a branch**
   - Branch: **main**, folder: **/docs**

   Save. GitHub will give you a URL like
   `https://your-username.github.io/your-repo-name/` within a minute or two.

4. **Run the workflow once manually** so you don't have to wait for the schedule.
   Go to the **Actions** tab → **Update Bazaar Data** (left sidebar) →
   **Run workflow** button → **Run workflow**. It takes a few seconds.

5. Visit your Pages URL. You should see live data. If it still says "No data
   yet", give it a minute - GitHub Pages caches through a CDN and can lag
   slightly behind a fresh commit.

After that, it runs itself: the workflow fires every 30 minutes on its own
schedule, no further action needed.

## How the "5-day volume" figure works

Hypixel's Bazaar API doesn't hand you a 5-day number directly - it gives you
`buyMovingWeek` / `sellMovingWeek`, the actual traded volume over the
trailing **7** days, live and server-maintained. This scales that down
(`x 5/7`) to estimate a 5-day figure. It's an estimate, not a true 5-day
rolling window, but it means the dashboard is useful from the very first run
instead of needing 5 real days of your own polling before it can show
anything.

## Changing the filter thresholds or schedule

Edit `.github/workflows/update-bazaar.yml`:

```yaml
on:
  schedule:
    - cron: "*/30 * * * *"   # change frequency here (cron syntax)

...

      - name: Fetch bazaar data and rebuild docs/data.json
        env:
          VOLUME_THRESHOLD: "90000"       # <- change thresholds here
          SPREAD_THRESHOLD_PCT: "20"
          WINDOW_DAYS: "5"
          POLL_INTERVAL_MINUTES: "30"     # keep this matching the cron above -
                                           # it's just used to label the countdown on the page
```

Commit the change and it takes effect on the next scheduled (or manual) run.
Hypixel's own bazaar data refreshes roughly once a minute, so there's no
benefit to a schedule tighter than that - and GitHub also throttles how
punctually scheduled workflows fire during high load, so very frequent
schedules (e.g. every 5 minutes) may run a bit late anyway.

## A few things worth knowing

- **Public repos get free Actions minutes**; a private repo has a monthly
  free allowance too (2,000 minutes/month as of writing) - either works fine
  for a job this light (well under a minute per run, every 30 minutes).
- **GitHub disables scheduled workflows automatically after 60 days with no
  repository activity.** If you go quiet on the repo for two months, just
  re-enable it from the Actions tab (or push any commit) to wake it back up.
- **This repo will grow one commit per successful run** (each one just
  updates `data.json`). That's normal and harmless, but if you'd rather not
  have a long history, you can periodically squash it, or switch the workflow
  to `git push --force` a single "data" branch instead - not necessary to
  start, just an option if the commit log bothers you.

## Project layout

```
.github/workflows/update-bazaar.yml   Scheduled job: fetch, filter, commit
scripts/poll_bazaar.py                 The fetch + filter logic (one-shot script)
docs/index.html                        The dashboard page (served by GitHub Pages)
docs/style.css
docs/app.js                            Reads docs/data.json and renders the table
docs/data.json                         Generated/overwritten by the workflow
requirements.txt                        Just `requests`, for the workflow's Python step
```

## Extending it

- **True 5-day volume**: have the workflow also append each run's raw
  `buyMovingWeek`/`sellMovingWeek` numbers to a small rolling log file, then
  compute an exact windowed volume from your own samples instead of the 7/5
  scaling estimate.
- **Discord bot**: `compute_filtered()` in `scripts/poll_bazaar.py` is
  already decoupled from the file-writing - straightforward to reuse it in a
  `discord.py` bot loop instead of (or alongside) the website.
- **Alerts**: diff each run's `items` against the previous commit's and flag
  items that just started (or stopped) qualifying.
