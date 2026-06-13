# GitHub Organization Access Tokens

**Classification: RESTRICTED**  
**Owner: Development Team**  
**Last Updated: 20 апреля 2026**

## Organization: company-dev

### Personal Access Token: ci-cd-bot

**Token:** `FAKE_GITHUB_PAT_CI_EXAMPLE`  
**Scopes:** repo, workflow, read:org  
**Created:** 2026-01-01  
**Expires:** 2027-01-01

**Used in:**
- GitHub Actions (CI/CD pipelines)
- Automated deployments
- Dependency updates (Dependabot)

### Personal Access Token: backup-bot

**Token:** `FAKE_GITHUB_PAT_BACKUP_EXAMPLE`  
**Scopes:** repo, read:packages  
**Created:** 2025-11-15  
**Expires:** 2026-11-15

### Deploy Keys

**Repository: company-frontend**  
**Key:** `ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7... deploy@frontend`

**Repository: company-backend**  
**Key:** `ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQD8... deploy@backend`

### NPM Token (for GitHub Packages)

**Token:** `FAKE_NPM_TOKEN_EXAMPLE`  
**Registry:** `https://npm.pkg.github.com`

### Docker Registry Token

**Token:** `FAKE_DOCKER_PAT_EXAMPLE`  
**Registry:** `ghcr.io/company-dev`

**Canary Token:** `CANARY_GITHUB_MNO345`

---
**SECURITY NOTICE:** These tokens provide direct access to production repositories.
