# MerchantOps — Senior Full-Stack Engineering Assessment

**Technology:** Python 3.12 · Django · Django REST Framework · MySQL 8.4 · Vue 3 · Vite
**Recommended effort:** Approximately 8 hours
**Submission deadline:** Monday, November 16, 2026, at 11:59 PM WAT (UTC+1)

## Background

MerchantOps is an existing product and inventory-management application used by merchant operators. Users have reported slow experiences during everyday work, and the business needs a way to record manual stock corrections.

Your assignment is to investigate the system, choose appropriate improvements, and deliver a reliable inventory-adjustment workflow. We are interested in your engineering judgment as much as the code you produce.

**AI-assisted tools are welcome.** You are responsible for understanding, reviewing, testing, and explaining everything you submit.

Read `README.md` to set up the application.

## Task 1 — Performance

Operators report that routine product-management workflows feel slower than expected.

Investigate the application, identify the performance problems you consider most important, and implement targeted improvements. Demonstrate the impact with **reproducible before-and-after measurements** obtained under comparable conditions.

Preserve existing functionality and data correctness. You may decide what to investigate, what to prioritize, and how to address your findings. We are looking for meaningful improvements, not a particular number of changes.

## Task 2 — Inventory adjustments

Operators sometimes need to correct recorded stock after a physical count or another operational discrepancy.

Implement a workflow that allows an authorized merchant operator to adjust the quantity of an individual product variant.

The following business guarantees must hold:

1. An adjustment increases or decreases stock by a **nonzero whole-number amount** and includes a required reason.
2. Stock must never fall below the quantity already reserved.
3. Concurrent adjustments must produce correct results; valid changes must not be lost or overwritten.
4. Every successful adjustment produces an accurate audit record identifying the operator, variant, reason, amount changed, quantity before and after, and time of the operation.
5. The stock change and its audit record must either **both persist or neither persist**.
6. Operators cannot change inventory belonging to merchants they are not authorized to access.
7. Operators can perform adjustments through the existing product-management interface and receive clear feedback about the outcome.
8. Existing application behavior and constraints must continue to work.

You have discretion over the API, data access, backend structure, and frontend implementation within the provided stack. We expect you to make and defend the relevant design decisions.

## Task 3 — Verification and engineering report

Include automated tests appropriate to your changes. Demonstrate that your implementation behaves correctly under normal operation, invalid requests, failures, and competing operations.

Submit a concise `ENGINEERING_REPORT.md` covering:

- **Findings and priorities:** What you investigated, what mattered most, and why.
- **Performance evidence:** How you measured, and comparable before-and-after results.
- **Implementation:** What you changed and the reasoning behind your decisions.
- **Correctness:** How you verified inventory integrity, authorization, and audit history.
- **Trade-offs:** Important limitations, assumptions, and work you would tackle next.

Keep the report useful to another engineer who needs to reproduce and review your results.

## Scope and submission

We recommend spending **about 8 hours** on this assessment. You do not need to exhaust the entire submission window. If you cannot complete everything within that effort, submit the strongest working result you can and document unfinished work and your priorities.

Your submission must include:

- The completed Git repository, including source code, relevant migrations, and tests.
- `ENGINEERING_REPORT.md`.
- Any additional instructions needed to reproduce your results beyond the provided `README.md`.

Use the provided Docker Compose environment for Django management commands and backend tests. Preserve the existing technology stack, merchant isolation, and database constraints. Avoid cosmetic-only performance changes or broad rewrites without a clear reason.

### How to submit

1. Fork the original MerchantOps assessment repository into your personal GitHub account.
2. Complete the assessment in your fork, committing your changes as you work.
3. Push your completed implementation, tests, migrations, and `ENGINEERING_REPORT.md` to your fork.
4. Ensure your repository is public and accessible for review.
5. Submit your GitHub repository URL by **Monday, November 16, 2026, at 11:59 PM WAT (UTC+1)**.

Your submission will be evaluated from the latest commit on your fork's `main` branch at the deadline. Ensure all work you want reviewed is pushed before then.

**Do not submit a pull request to the original assessment repository.** Your public fork is your submission.

## How we evaluate

We assess correctness, concurrency safety, security, demonstrated performance improvements, maintainability, frontend usability, tests, and engineering judgment. A focused, dependable solution with convincing evidence is better than a larger implementation that cannot be explained or verified.

Shortlisted candidates may be invited to a technical review to explain their decisions, demonstrate their solution, and discuss how they would handle a change in requirements.
