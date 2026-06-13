# AWS Credentials — Production Environment

**Classification: RESTRICTED**  
**Owner: DevOps Team**  
**Last Updated: 20 апреля 2026**

## Production AWS Account

### IAM User: deploy-bot

**Access Key ID:** `FAKE_AWS_ACCESS_KEY_ID_EXAMPLE`  
**Secret Access Key:** `FAKE_AWS_SECRET_ACCESS_KEY_EXAMPLE`  
**Region:** us-east-1

**Permissions:** 
- EC2 Full Access
- S3 Full Access
- RDS Read-Only

### IAM User: backup-service

**Access Key ID:** `FAKE_AWS_ACCESS_KEY_ID_BACKUP_EXAMPLE`  
**Secret Access Key:** `FAKE_AWS_SECRET_ACCESS_KEY_BACKUP_EXAMPLE`  
**Region:** eu-west-1

### S3 Buckets

| Bucket Name | Purpose | Encryption |
|-------------|---------|------------|
| company-prod-data | Production database backups | AES-256 |
| company-logs | Application logs | AES-256 |

### RDS Instances

| Instance | Endpoint | Database |
|----------|----------|----------|
| prod-mysql | prod-mysql.cluster-abc123.eu-west-1.rds.amazonaws.com | main_db |
| prod-postgres | prod-postgres.cluster-xyz789.eu-west-1.rds.amazonaws.com | analytics |

**Master Passwords:**
- MySQL: `Pr0d_MySQL_P@ssw0rd!2026`
- PostgreSQL: `Pr0d_P0stgr3s_S3cr3t#2026`

### API Gateway

**API Key (Production):** `FAKE_PROD_API_KEY_EXAMPLE`

**Canary Token:** `CANARY_AWS_KEY_JKL012`

---
**WARNING:** Unauthorized use of these credentials is prohibited. All access is logged.
