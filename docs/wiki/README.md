# Maya Pipeline Inspector — Wiki (source)

In-repository knowledge base for [GitHub Wiki](https://github.com/armasonix/maya-pipeline-inspector/wiki) or browsing under `docs/wiki/` on `main`.

## Start here

→ **[Home](Home.md)**

## Publish to GitHub Wiki

1. Wiki tab → create **Home** if the wiki is empty.
2. Clone the wiki repository (default branch is usually **`master`**):

```bash
git clone https://github.com/armasonix/maya-pipeline-inspector.wiki.git
cd maya-pipeline-inspector.wiki
```

3. Copy sources from the main repo (include `_Sidebar.md` and `_Footer.md`):

```bash
cp -r /d/Workspace/portfolio/maya-pipeline-inspector/docs/wiki/* .
rm -f README.md
git add .
git commit -m "Sync wiki from docs/wiki"
git push origin master
```

Use `git push origin master` (not `main`) unless the wiki default branch was renamed.

## GitHub Wiki link format

GitHub Wiki **ignores folder paths in links**. A file at `Panel/Validate-Tab.md` is published as page slug **`Validate-Tab`**, not `Panel/Validate-Tab`.

- Sidebar and cross-links in `docs/wiki/` use **flat slugs**: `[Validate tab](Validate-Tab)`.
- Duplicate basenames across folders break navigation — e.g. two `Overview.md` files collide. Use unique names (`Project-Overview.md`, `Panel-Overview.md`).
- Repo doc links (`../../MAYA_INSTALL.md`) still point at files on `main`; they are not wiki pages.

After editing here, re-sync the wiki clone and push. Remove obsolete pages (old `Overview.md` paths) if you renamed files.

## Layout files

| File | Role on GitHub Wiki |
| --- | --- |
| `Home.md` | Landing page |
| `_Sidebar.md` | Left navigation on every page |
| `_Footer.md` | Footer on every page |
