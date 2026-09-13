# Local and remote GitHub workflow

## Resolve and read

Use installed tool help to confirm supported flags. Keep the GitHub host explicit for Enterprise repositories. Prefer argument arrays in subprocess calls; branch names and titles are data, not shell code. Validate ref names and quote shell arguments safely. Use body files or structured API fields for multiline PR descriptions.

For a local path, inspect `git status --porcelain=v1`, `git remote -v`, `git worktree list --porcelain`, local refs and upstreams, and stash inventory. Confirm the intended remote before fetching. Fetch without resetting local refs; `git fetch --prune` removes stale remote-tracking refs, not local branches, and should follow the user's cleanup scope. Avoid automatically stashing dirty changes.

For either input, resolve GitHub's `defaultBranchRef` and repository identity with `gh repo view --repo HOST/OWNER/REPO --json nameWithOwner,defaultBranchRef,url`. Query branches and PRs with pagination. For example, `gh api --hostname HOST --paginate 'repos/OWNER/REPO/branches?per_page=100'` and the pulls endpoint with `state=all&per_page=100`; inspect merged status separately from closed status. URL-encode branch names in REST paths. List limits must not silently truncate the cleanup inventory.

Inspect rulesets and target branch protection, including required reviews/checks, conversation resolution, merge queue, permitted strategies, and deletion restrictions. A permission error is unknown policy, not proof of no rules. If tests or merge ancestry need local objects, clone into an isolated task directory and fetch the exact relevant refs. Honor local guidance in the checkout. Do not invoke arbitrary code while merely inventorying refs.

## PR and merge sequence

1. Match existing PRs using both head repository/ref and intended base; fork branch names alone are ambiguous. For new PRs, use `gh pr create --repo HOST/OWNER/REPO --base BASE --head HEAD --title TITLE --body-file FILE`. Review the complete preview first; do not publish unrelated local-only work.
2. Read the current PR head OID, base, draft state, reviews, mergeability and check rollup. Obtain required policy separately; missing checks or an empty review decision are not automatically sufficient. Observe required checks on the actual head or merge-queue candidate as appropriate.
3. Revalidate dependencies and test scope when a preceding merge changes the target. Resolve conflicts only within authorized scope and rerun affected checks. Never choose ours/theirs wholesale to silence a conflict.
4. Select a permitted method. Where supported, use `gh pr merge PR --repo HOST/OWNER/REPO --match-head-commit REVIEWED_SHA` with the chosen merge/squash/rebase flag. For a required merge queue, follow its supported invocation and observe the queue; do not pass `--admin`. Do not use `--delete-branch` here: deletion gets an independent proof and head check.
5. Read back the terminal PR state and merge result. Preserve pending queue/auto-merge actions in the ledger; do not report them as completed. Fetch the resulting target. If required post-merge checks fail, stop dependent merges and report remediation; keep useful source refs while investigating.

## Integration and deletion proof

For a normal merge, `git merge-base --is-ancestor SOURCE_SHA TARGET_SHA` proves source ancestry. A nonzero result may mean not integrated, missing objects, or an error; distinguish these cases. An exact branch equal to its retained target has no unique commits but may still be operationally protected.

Squash/rebase often fails ancestry despite successful integration. Require all of:
- GitHub PR is MERGED into the intended base, with the same source repository and exact recorded head SHA.
- The branch still points to that head and has no later work.
- The returned merge/result commit is reachable from the refreshed retained target. If the API cannot supply a usable result, obtain equivalent durable evidence before deletion; do not guess.
- No retained policy, open dependent PR, or worktree needs the ref.

Patch equivalence, `git cherry`, and `git branch --merged` are useful investigation aids but are not a complete deletion decision for squash/rebase or reverted/reworked changes. Reachability does not prove the feature is still enabled after later reverts; do not claim that it does.

Prefer a remote compare-and-delete operation. With Git transport, pass an explicit expected-ref lease and deletion refspec as separate arguments, conceptually:

    git push --force-with-lease=refs/heads/BRANCH:EXPECTED_SHA REMOTE :refs/heads/BRANCH

This permits deletion only when the server ref matches the expected SHA; it is not permission to overwrite branch history. Confirm Git/server support and valid exact ref names before use. If a lease fails, refresh and reassess the new commits. Do not fall back to unconditional deletion. An API without atomic expected-SHA deletion cannot rule out concurrent branch updates; use the leased Git transport or leave the branch pending until an explicitly authorized coordination mechanism resolves the race.

Read back the remote ref after deletion. If already absent, record that state without inventing who deleted it. For local cleanup, verify the branch tip separately: it may differ from its remote. `git branch -d` is preferred, but its success alone is not integration evidence because it can consider an upstream branch. Use your recorded retained-target proof first. For squash/rebase, `-D` is acceptable only for the exact locally verified integrated tip within authorized merged-branch cleanup and never for a branch checked out in any worktree.

Record deleted full ref, former SHA, repository, PR/merge proof, and readback. Preserve unmerged data through an explicitly agreed retention plan rather than creating hidden backups and treating that as permission to discard work.

## Official references

Consult these when local tool behavior or repository policy differs:
- [Git push reference](https://git-scm.com/docs/git-push): deletion refspecs and explicit expected-value leases.
- [GitHub CLI merge reference](https://cli.github.com/manual/gh_pr_merge): head matching, merge methods, and queue behavior.
- [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches): reviews, status checks, and retained-branch restrictions.
