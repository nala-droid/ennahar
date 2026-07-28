name: Daily Ennahar News

on:
  schedule:
    - cron: "0 8 * * *"   # 08:00 UTC = 09:00 Algiers time (Algeria has no DST)
  workflow_dispatch:        # adds a "Run workflow" button on GitHub for manual testing

jobs:
  post-news:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install -r requirements.txt

      - run: python fetch_and_post.py
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
