# Executed dependency review — 2026-10-23

This is scanner evidence, not an independent penetration test or exploitability decision.
Ignored raw reports are under `.local/`; no suppression file is configured.

| Command / scope | Actual result |
|---|---|
| `uvx pip-audit --requirement requirements.lock --format json --output .local/python-audit.json` | No known vulnerabilities after removing unused Pillow |
| `npm audit --prefix apps/web --audit-level=high` | 0 vulnerabilities |
| Docker Scout | Could not run: Docker account sign-in required; used Trivy fallback |
| Trivy 0.76.1, final `fdr-sentinel-api:local` | Debian 13.7: 1 CRITICAL, 71 HIGH, 109 MEDIUM, 158 LOW, 2 UNKNOWN; no fixed versions supplied for these findings. Python and embedded Node package scans: no findings |
| Trivy 0.76.1, `quay.io/keycloak/keycloak:26.8.1` | Red Hat 9.8: 1 CRITICAL, 1 HIGH, 55 MEDIUM, 35 LOW; Java package analysis: no additional findings |

Reproduce the image command with an isolated local Docker socket, a persistent cache
and an ignored reports mount:

```text
aquasec/trivy:0.76.1 image --quiet --timeout 10m --scanners vuln --format json --output /reports/result.json <image>
```

Do not run simultaneous scans against the same filesystem cache: one attempt failed
with cache-in-use timeout. The first Keycloak attempt timed out downloading its roughly
942 MiB Java database; rerunning from cache with 10-minute timeout completed. These
failed attempts are not counted as clean scans. The raw report records image identity
and package metadata; mutable image tags need rescanning when rebuilt/pulled.

Remediation performed: removed unused Pillow with reported advisories; upgraded the
application base from Bookworm to Trixie; updated the build installer to pip 26.2.2;
removed pip/ensurepip from the final runtime image because its bundled libraries had
separate scanner findings. The actual application urllib3 is locked at 2.8.0.
Updated Keycloak from 26.4.2 to the verified available 26.8.1 using preserved volumes.
No application runtime requires a package installer.

Unresolved blockers include API-image `CVE-2026-6653` in libxml2 and Keycloak-image
`CVE-2026-91403` / `CVE-2026-91415` in java-21-openjdk-headless. The scanner supplied
no fixed versions; the first JDK advisory was marked under investigation. Do not treat
that status as an exemption. All other reported findings also require current vendor
triage and remediation/approved disposition before production. No blanket risk acceptance
or false-positive claim is made. Other backing-service images were not comprehensively
scanned in this pass. Re-scan the complete deployment and verify vendor advisories.

Sources for tooling/release decisions: [Trivy release](https://github.com/aquasecurity/trivy/releases/tag/v0.76.1),
[Keycloak downloads](https://www.keycloak.org/downloads),
[Debian snapshot documentation](https://snapshot.debian.org/).
