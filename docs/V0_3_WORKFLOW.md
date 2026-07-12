# v0.3 Git workflow (same rhythm as v0.1 / v0.2)

**Baseline:** `main` @ `v0.3.0`. v0.3 cycle complete (Milestones 15–21, Issues #071–#090).

## Rules

1. **One GitHub issue → one implementation → one commit → one push.**
2. **Never** land code for a later issue in an earlier commit.
3. **`dev`** is the integration branch during the cycle.
4. **`main`** gets a PR only when a **milestone** is complete (e.g. M15 = #071 + #072).
5. Commit message format:

   ```
   #071 - Add Python MPx plugin stub and dual install path

   Closes #91
   ```

   Use plan id `#071` in the subject; `Closes #91` is the GitHub issue number.

## Issue map

| Plan | GitHub | Milestone |
|------|--------|-----------|
| #071 | #91 | M15 Plugin |
| #072 | #92 | M15 Plugin |
| #073 | #93 | M16 Fingerprint |
| #074 | #94 | M16 Fingerprint |
| #075 | #95 | M16 Fingerprint |
| #076 | #96 | M16 Fingerprint |
| #077 | #97 | M17 Gates |
| #078 | #98 | M17 Gates |
| #079 | #99 | M17 Gates |
| #080 | #101 | M18 Apply |
| #081 | #104 | M18 Apply |
| #082 | #107 | M18 Apply |
| #083 | #100 | M18 Apply |
| #084 | #103 | M19 Resolution |
| #085 | #106 | M19 Resolution |
| #086 | #109 | M19 Resolution |
| #087 | #102 | M20 Polish |
| #088 | #105 | M20 Polish |
| #089 | #108 | M20 Polish |
| #090 | #110 | M21 Release |

Details: [V0_3_DEVELOPMENT_PLAN.md](V0_3_DEVELOPMENT_PLAN.md).

## Per-issue loop (repeat for #071 … #090)

```bash
cd /d/Workspace/portfolio/maya-pipeline-inspector
git checkout dev
git pull origin dev

# Implement ONLY the current issue, then:
python -m pytest <tests for this issue> -q

git add <files touched by this issue only>
git diff --cached --stat

git commit -m "#071 - <title from GitHub>" -m "Closes #91"
git push origin dev
```

No `git add -p` between issues — each issue should touch only its own scope.

## Milestone merge to main

After the last issue in a milestone (e.g. #072 for M15):

```bash
gh pr create --base main --head dev \
  --title "Milestone 15: Maya Plugin Entry" \
  --body "Closes #91, Closes #92"
```
