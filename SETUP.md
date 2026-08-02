# Setting this up

GitHub profile READMEs work through one rule: a public repo with the exact
same name as your username. For you that's a repo called `Aryanlohri`.

## 1. Create the repo
- New repo → name it exactly `Aryanlohri` → Public → no README (you already have one here).

## 2. Push these files
```bash
cd Aryanlohri
git init
git remote add origin https://github.com/Aryanlohri/Aryanlohri.git
git add .
git commit -m "profile: initial version"
git branch -M main
git push -u origin main
```

## 3. Enable the live heatmap
The workflow uses `secrets.GH_TOKEN` because the default `GITHUB_TOKEN` in
Actions can't read your contribution calendar via GraphQL — it needs a
personal token with `read:user` scope.

- GitHub → Settings → Developer settings → Personal access tokens →
  Fine-grained tokens → generate one scoped to `read:user`, no repo access needed.
- In the `Aryanlohri/Aryanlohri` repo: Settings → Secrets and variables →
  Actions → New repository secret → name it `GH_TOKEN`, paste the token.
- Run the workflow once manually (Actions tab → "Update contribution
  heatmap" → Run workflow) to generate the real heatmap instead of the
  zero-contribution placeholder that ships in this repo.

It'll then refresh itself daily at 03:00 UTC and on every push to `main`.

## 4. Optional next passes
- `info-card.svg` is static — if you want it to also pull live LeetCode
  solved-count or repo stats the way your `aryanlohri.xyz` "Currently"
  section does, the same GraphQL/REST pattern in
  `scripts/generate_heatmap.py` extends to that.
- Add LinkedIn/X/Instagram badges to the README badge row if you want
  them here too — left out since I didn't have those handles on file.
