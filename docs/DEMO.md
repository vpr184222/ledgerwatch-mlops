# Demo and interview notes

## Explain the project in 60 seconds

“LedgerWatch is an independent full-stack MLOps portfolio project. I generate synthetic
transactions, train a Random Forest with separate validation and test data, and select a
decision threshold using validation F1. FastAPI serves the active model and records its
version with each prediction. React provides scoring, CSV uploads, review filters, and an
audit trail. Candidate models can be logged to MLflow and promoted or rolled back through
a local version pointer. A PSI monitor compares recent features with the training baseline.”

## Walkthrough

1. Start backend and frontend using SETUP; startup seeds synthetic data.
2. Score the prefilled transaction and inspect the new queue record.
3. Review a flagged transaction, enter a reason, and save `investigating`.
4. Upload `data/sample-batch.csv` once. Reupload it to demonstrate duplicate-ID rollback.
5. Generate and score a shifted batch using the README commands; inspect PSI bars.
6. Train a candidate with `python train.py --track --candidate --seed 17`.
7. Note the old version, promote the candidate, refresh the dashboard, then roll back.
8. Run `python -m pytest -q`. Explain one batch atomicity test and one drift test.

## Decisions you should understand

- Why average precision? The positive label is uncommon; accuracy alone can conceal poor minority-class performance.
- Why a separate validation set? The threshold must not be tuned on the held-out test set.
- Why record the version? Reviewers need to know which model produced an older transaction score after promotion.
- Why upload atomicity? A malformed or duplicated row should not create a partially imported batch.
- Why optimistic review versions? Two reviewers should not silently overwrite each other's decisions.
- Why PSI by active version? Each model's recent inputs are compared with its own stored training baseline.
- Is PSI accuracy? No. Outcome labels are needed to evaluate live precision/recall.
- Are these fraud probabilities? No. The classifier scores are uncalibrated and trained on invented labels.
- Does MLflow serve the API? No. The app serves locally generated joblib bundles; MLflow tracks experiments and artifacts.

## Portfolio resume wording

Only add after running and understanding the project; use a **Projects** section.

- Developed a FastAPI and React transaction anomaly review app with validated online and CSV inference, versioned scores, and persistent review audit records.
- Built reproducible model training with validation-based threshold selection, MLflow experiment tracking, model promotion/rollback, and feature drift monitoring.

Do not describe this as work delivered for EdgeVerve or as a measured improvement on a real banking dataset.
