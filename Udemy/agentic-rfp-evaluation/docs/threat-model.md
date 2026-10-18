Initial threat model:
- PDF prompt injection: treat documents as untrusted input; do not give the LLM tools that execute actions.
- Oversized/malformed PDFs: enforce upload and extraction limits and surface parse errors.
- Invalid model output: normalize schema, clip scores, and retain warnings.
- Secrets: .env is ignored by Git; use a secret manager for hosted production.
- Data exposure: synthetic data for demos; commercial deployment needs authentication, tenant isolation,
  encryption, retention/deletion controls, malware scanning, audit review, and security/privacy assessment.
