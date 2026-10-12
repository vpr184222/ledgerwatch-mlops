# Validation record

Validated on October 12, 2026 with Python 3.12.14 and Node.js 24.15.0 on Windows.
The documented baseline is Python 3.12 / Node.js 22+; CI targets Python 3.12 / Node.js 22.

- Backend: **6 pytest tests passed**.
- Frontend: TypeScript check and Vite production build passed.
- Native browser workflow checked through the built frontend and proxy.
- Dependency manifests and npm lockfile are included; generated runtime files are ignored.

Verified in the UI: seeded queue → online scoring → persisted model version → review
with reason → updated status and audit record. A 200-row shifted CSV was generated and
scored against the running HTTP API. Tests cover validation, duplicate IDs, whole-batch
rollback, review conflicts, pagination, PSI shifts, active-version monitoring, candidate
training, promotion, and rollback.

Training with `--track --candidate` completed against the local MLflow file store and
logged parameters, test metrics, and the model bundle. The default seed-42 model produced
held-out average precision 0.099819 (positive prevalence/random-ranking baseline 0.043),
ROC AUC 0.710748, precision 0.117647, recall 0.093023, and F1 0.103896 at threshold
0.526217. These results are intentionally reported as measured; the noisy, rare synthetic
labels are not a high-performance fraud benchmark. Further modeling and threshold work
would be required for any real use.

Not executed: full MLflow UI, remote tracking server, or container startup.

Docker is not installed in the validation environment. Dockerfiles, Compose health checks,
persistent volumes, and a GitHub Actions container-build job are included, but local Docker
build/start was not run. No remote GitHub CI run or cloud deployment has occurred yet.
Dependencies emit non-failing upstream deprecation warnings during pytest.
