# Releasing Kagenti

This guide describes how maintainers create tags, pre-releases, and stable (GA)
releases across the Kagenti organization.

> **Policy:** For branching strategy, support windows, and governance decisions,
> see [docs/release-sop.md](release-sop.md).
>
> **AI-assisted releases:** Use the `/release` skill to walk through the release
> process interactively. See [Using the Release Skill](#using-the-release-skill)
> at the end of this guide for examples.

## Versioning Scheme

Kagenti follows [Semantic Versioning 2.0](https://semver.org/) with three
pre-release stages:

```
vX.Y.0-alpha.N   →   vX.Y.0-rc.N   →   vX.Y.0   →   vX.Y.Z (patches)
```

| Tag pattern | Stage | GitHub Release type |
|-------------|-------|---------------------|
| `vX.Y.0-alpha.N` | **Alpha** — active development, may break | Pre-release |
| `vX.Y.0-rc.N` | **Release Candidate** — feature-complete, stabilization only | Pre-release |
| `vX.Y.0` | **General Availability (GA)** — stable, production-ready | Latest |
| `vX.Y.Z` | **Patch** — critical fixes against a GA release | Latest |

GoReleaser's `prerelease: auto` setting automatically marks tags containing
`-alpha` or `-rc` as pre-releases on GitHub. No manual intervention is needed.

## Release Governance

Any Kagenti maintainer (member of the
[kagenti-maintainers](mailto:kagenti-maintainers@googlegroups.com) team) can
cut a release. For GA releases, at least one other maintainer must sign off
before tagging.

## Version Compatibility

Each `kagenti/kagenti` release tag represents a tested set of component versions
across the organization. The Helm chart (`charts/kagenti/Chart.yaml`) pins the
exact sub-chart versions, and `charts/kagenti/values.yaml` pins the container
image tags.

GA release notes should include a compatibility table:

```markdown
## Component Versions

| Component | Version |
|-----------|---------|
| kagenti (platform) | v0.6.0 |
| kagenti-extensions (webhook) | v0.5.0 |
| kagenti-operator | v0.3.0 |
| agent-examples | v0.2.0 |
```

Users who install via Helm charts do not need to manage
version compatibility manually — checking out a Kagenti release tag gives a
consistent, tested set of components.

## Repositories and Artifacts

The Kagenti platform spans multiple repositories. Each produces different
artifacts when a tag is pushed:

| Repository | Artifacts on tag push | CI workflow(s) |
|------------|----------------------|----------------|
| [kagenti/kagenti](https://github.com/kagenti/kagenti) | Container images (ui-v2, backend, oauth-secrets), Helm charts (kagenti, kagenti-deps) | `build.yaml` |
| [kagenti/kagenti-extensions](https://github.com/kagenti/kagenti-extensions) | Container images (authbridge-envoy, authbridge-light, proxy-init, client-registration, spiffe-helper) | `build.yaml` |
| [kagenti/kagenti-operator](https://github.com/kagenti/kagenti-operator) | Operator image, Helm chart (kagenti-operator-chart) | repo-specific |
| [kagenti/agent-examples](https://github.com/kagenti/agent-examples) | Sample agent/tool images | repo-specific |

## Release Order

The `kagenti/kagenti` Helm chart depends on sub-charts from other repos
(defined in `charts/kagenti/Chart.yaml`). Dependency repos must be tagged
**before** the main repo:

```
1. kagenti/kagenti-operator     →  tag & wait for CI
2. kagenti/kagenti-extensions   →  tag & wait for CI
3. kagenti/agent-examples       →  tag (if applicable)
4. kagenti/kagenti              →  update Chart.yaml, tag
```

## Cutting an Alpha Release

Alpha releases are tagged from `main` during active development.

### Steps (repeat for each repo)

1. Ensure CI passes on `main`.

2. Determine the next alpha number:

   ```bash
   git tag --list 'vX.Y.0-alpha.*' --sort=-v:refname | head -1
   ```

3. Create and push the tag:

   ```bash
   git tag -s vX.Y.0-alpha.N -m "vX.Y.0-alpha.N"
   git push origin vX.Y.0-alpha.N
   ```

4. Verify CI completes:
   - [ ] Container images pushed to `ghcr.io`
   - [ ] GitHub Release created and marked as **Pre-release**
   - [ ] Helm charts published (if applicable)

5. Release notes are auto-generated from the changelog. If there are known
   breaking changes or significant issues since the previous alpha, add a brief
   note to the GitHub Release body (even for alphas, this helps early testers).

### Updating kagenti/kagenti after dependency alphas

After tagging `kagenti-extensions` and `kagenti-operator`, update the sub-chart
versions in `charts/kagenti/Chart.yaml`:

```yaml
dependencies:
- name: kagenti-operator-chart
  version: X.Y.0-alpha.N    # <-- new version
  repository: oci://ghcr.io/kagenti/kagenti-operator
```

Run `helm dependency update charts/kagenti/` to regenerate `Chart.lock`, commit,
merge, then tag `kagenti/kagenti`.

## Pinning Image Tags Before Release

Both Helm charts (`charts/kagenti/` and `charts/kagenti-deps/`) reference
container images built by this repo. All image tags must be pinned to the
release version before cutting any tag (alpha, RC, or GA).

### Automated pinning (recommended)

Use the `pin-release-tags.sh` script to update all image tags in a single
command:

```bash
# Pin all images to v0.6.0-rc.6
bash scripts/pin-release-tags.sh v0.6.0-rc.6

# Preview changes without modifying files
bash scripts/pin-release-tags.sh v0.6.0-rc.6 --dry-run

# Also verify images exist in ghcr.io before pinning
bash scripts/pin-release-tags.sh v0.6.0-rc.6 --verify-images

# Also update Chart.yaml version
bash scripts/pin-release-tags.sh v0.6.0-rc.6 --chart-version v0.6.0-rc.6
```

The script updates tags across **both** charts:

| Chart | Image | values.yaml key |
|-------|-------|----------------|
| `kagenti` | ui-v2 | `ui.frontend.tag` |
| `kagenti` | backend | `ui.backend.tag` |
| `kagenti` | ui-oauth-secret | `uiOAuthSecret.tag` |
| `kagenti` | agent-oauth-secret | `agentOAuthSecret.tag` |
| `kagenti` | api-oauth-secret | `apiOAuthSecret.tag` |
| `kagenti` | mlflow-oauth-secret | `mlflowOAuthSecret.tag` |
| `kagenti-deps` | spiffe-idp-setup | `spiffeIdp.image.tag` |

### CI also pins at chart-publish time

The `build.yaml` workflow pins these same tags automatically when packaging
charts for OCI push (triggered by tag push). This means the OCI-published chart
is always correct — but since users typically install from a repo checkout (via
`setup-kagenti.sh`), the committed values must also be pinned before tagging.

### Why this matters

The Kind and OpenShift installers (`scripts/kind/setup-kagenti.sh` and
`scripts/ocp/setup-kagenti.sh`) use local charts from the repo checkout — they
do **not** pull from the OCI registry. If image tags in the checked-out
`values.yaml` files are stale, users get old images even on a new release tag.

### Validation

After pinning, validate with:

```bash
bash scripts/check-release-pins.sh
```

This checks both charts for `tag: latest` entries and warns if the
`spiffe-idp-setup` tag in `kagenti-deps` has drifted from the platform tags in
`kagenti`.

## Cutting a Release Candidate

Release candidates signal feature-complete code ready for broader testing.

### Prerequisites

- All planned features for `vX.Y.0` are merged.
- No known critical or blocking bugs.
- Feature freeze declared by maintainers.

### Steps

1. **Tag dependency repos first** with their RC tags (following the
   [release order](#release-order)).

2. **Update `charts/kagenti/Chart.yaml`** in `kagenti/kagenti` to reference
   the new sub-chart RC versions. Run `helm dependency update charts/kagenti/`
   to regenerate `Chart.lock`.

3. **Pin all image tags** in `charts/kagenti/values.yaml` to the RC tag.
   Replace any `tag: latest` entries with the RC version (see
   [Pinning Image Tags Before Release](#pinning-image-tags-before-release)).

4. **Create a release branch** for stabilization:

   ```bash
   git checkout -b release-X.Y main
   git push origin release-X.Y
   ```

   Release branches are the target for cherry-picks and patch releases. If no
   parallel work is planned, you may tag directly from `main`, but the release
   branch will still be needed for any future patches.

5. **Tag the RC:**

   ```bash
   git tag -s vX.Y.0-rc.1 -m "vX.Y.0-rc.1"
   git push origin vX.Y.0-rc.1
   ```

6. **Verify all artifacts:**
   - [ ] Container images pushed with the RC tag
   - [ ] Helm charts pushed to OCI registry
   - [ ] GitHub Release created as **Pre-release**
   - [ ] No `tag: latest` remains in `charts/kagenti/values.yaml`

7. **Test the RC:**
   - [ ] Clean Kind cluster install using the RC tag succeeds
   - [ ] OpenShift install (if applicable) succeeds
   - [ ] E2E tests pass
   - [ ] Upgrade from previous GA version works
   - [ ] Documentation reviewed and updated for new features

8. **If bugs are found:** Fix on the release branch (or `main`), cherry-pick as
   needed, bump to `rc.2`, and repeat from step 5.

## Cutting a GA Release

A GA release is the final, stable, production-ready version.

### Prerequisites

- At least one RC has been validated with no open release-blocking issues.
- Minimum soak period of 1 week since the last RC (recommended).
- At least one maintainer sign-off.

### Steps

1. **Tag dependency repos first** with their GA tags (following the
   [release order](#release-order)).

2. **Update `charts/kagenti/Chart.yaml`** to pin sub-chart versions to their
   GA versions. Run `helm dependency update charts/kagenti/` to regenerate
   `Chart.lock`.

3. **Pin all image tags** in `charts/kagenti/values.yaml` to the GA tag.
   Verify no `tag: latest` entries remain (see
   [Pinning Image Tags Before Release](#pinning-image-tags-before-release)).

4. **Tag the GA release:**

   ```bash
   git tag -s vX.Y.0 -m "vX.Y.0"
   git push origin vX.Y.0
   ```

5. **Write release notes** using the following template:

   ```markdown
   ## Highlights
   - <key feature or improvement>
   - <key feature or improvement>

   ## Breaking Changes
   - <any breaking changes, or "None">

   ## Component Versions

   | Component | Version |
   |-----------|---------|
   | kagenti (platform) | vX.Y.0 |
   | kagenti-extensions (webhook) | vA.B.0 |
   | kagenti-operator | vC.D.0 |
   | agent-examples | vE.F.0 |

   ## Upgrade Notes
   - <any special steps for upgrading from the previous GA>

   ## Full Changelog
   <auto-generated by GitHub>
   ```

   Use GitHub's auto-generated changelog as the base and prepend the sections
   above.

6. **Verify:**
   - [ ] GitHub Release is marked as **Latest** (not Pre-release)
   - [ ] All container images tagged and pushed
   - [ ] Helm charts published to OCI registry
   - [ ] No `tag: latest` remains in `charts/kagenti/values.yaml`
   - [ ] Installation guide version references are up to date

7. **Announce** the release:
   - [Slack](https://ibm.biz/kagenti-slack)
   - [Mailing list](mailto:kagenti-maintainers@googlegroups.com)
   - Consider a blog post for major releases

## Cutting a Patch Release

Patch releases deliver critical fixes against an existing GA version.

1. Cherry-pick the fix(es) into the `release-X.Y` branch.
2. Tag as `vX.Y.Z` (e.g., `v0.5.1`).
3. Follow the same verification steps as a GA release.
4. For non-trivial fixes, consider cutting a patch RC (`vX.Y.Z-rc.1`) first.

## Troubleshooting

### Stale `Chart.lock`

After updating dependency versions in `Chart.yaml`, always run
`helm dependency update` before committing:

```bash
helm dependency update charts/kagenti/
helm dependency update charts/kagenti-deps/
```

Forgetting this step causes Helm install failures because `Chart.lock` still
references the old versions.

### Pre-release detection

GoReleaser's `prerelease: auto` detects pre-release tags by the presence of a
hyphen after the version (e.g., `-alpha.1`, `-rc.2`). Tags like `v0.5.0` are
treated as stable. No workflow changes are needed to support new pre-release
stages.

### Helm chart version vs. app version

The `version` field in `Chart.yaml` should match the release tag (minus the `v`
prefix). The `appVersion` field may differ if it tracks a different cadence.

### `tag: latest` in values.yaml

If a GA release ships with `tag: latest` in `values.yaml`, users installing at
different times will get different image versions, making issues unreproducible.
Search for remaining `latest` references:

```bash
grep -n 'tag: latest' charts/kagenti/values.yaml
grep -rn ':latest' charts/kagenti/templates/
```

Fix any found before tagging.

## Using the Release Skill

The `.claude/skills/release/SKILL.md` skill (see [PR #1021](https://github.com/kagenti/kagenti/pull/1021))
provides an interactive, AI-assisted workflow that automates the steps in this
guide. It handles multi-repo coordination, artifact verification, and release
notes generation.

### Quick examples

**Check the current release state across all repos:**

```
/release status
```

This shows the latest tags for each repo, the current `Chart.yaml` dependency
versions, and flags any `tag: latest` entries in `values.yaml` that need
pinning.

**Cut an alpha release:**

```
/release alpha v0.6.0-alpha.1
```

The skill will:
1. Check CI status on `main` for each repo
2. Guide you through tagging dependency repos first (operator, extensions)
3. Prompt you to update `Chart.yaml` and tag `kagenti/kagenti` last
4. Verify all GitHub Releases and container images were produced

**Cut a release candidate:**

```
/release rc v0.6.0-rc.1
```

In addition to the alpha steps, the skill will:
1. Verify feature freeze prerequisites
2. Help pin all `tag: latest` entries in `values.yaml`
3. Create the `release-0.6` branch
4. Run the full verification suite (images, Helm charts, pre-release flags)
5. Generate an RC release notes template with a testing checklist

**Cut a GA release:**

```
/release ga v0.6.0
```

The skill will:
1. Verify an RC was validated and a maintainer has signed off
2. Pin all image and chart versions to GA tags
3. Tag all repos in order and verify artifacts
4. Generate full release notes with a component compatibility table
5. Draft an announcement for Slack and the mailing list

**Cut a patch release:**

```
/release patch v0.5.1
```

The skill guides cherry-picking fixes into the `release-0.5` branch and follows
the same verification and release notes flow.

---

## Future Work

The following items are recommended for CNCF project maturity but are not yet
implemented. Track these as separate issues:

- **Artifact signing and provenance** — Sign container images with
  Sigstore/cosign and generate SLSA provenance attestations
- **SBOM generation** — Produce SPDX or CycloneDX SBOMs for every release
  artifact
- **Support window / EOL policy** — Define how many minor releases are
  supported concurrently (e.g., N and N-1) and for how long
- **Security release process** — Document how CVEs and embargoed fixes are
  handled (private fork, coordinated disclosure, patch timeline)
