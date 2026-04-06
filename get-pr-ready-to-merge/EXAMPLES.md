# Examples for Get PR Ready to Merge

## Example 1: Mixed CI failures and review comments

**User:** "Fix CI on PR #12345"

**Agent diagnosis:**
- 2 failing CI checks: Mypy (104 errors in `intake_form/`), Test Suite (3 test failures)
- 5 unresolved review comments
- PR changes only touch `ijp_class.py`

**Agent output:**

```
Switched to `akshat/ENG-183462`, rebased onto `master`.
Found 7 blockers: 2 failing CI checks, 5 unresolved comments.
Mergeable state: `blocked`

### Group 1: Quick Wins (2 items)

1. [Review] @reviewer1 — "Typo in docstring line 45"

   Fix: Correct spelling from "submited" to "submitted"

   ```45:45:www/application/application_classes/ijp_class.py
   # Process submited application data
   ```

2. [Review] @reviewer2 — "Remove unused import"

   Fix: Remove import of `unused_module` from line 12

### Group 2: Medium Changes (3 items)

3. [Review] @reviewer1 — "Add type hints to validate_fields method"

   Add: Type annotations for parameters and return value

   ```120:125:www/application/application_classes/ijp_class.py
   def validate_fields(self, fields):
       # validation logic
       return result
   ```

... (continue for all items)

### Group 4: Not Our Problem (2 items)

7. [CI] Mypy (Python 3.13) — "104 errors in www/intake_form/"

   Skip: All errors are in intake_form/ which is not touched by this PR.
   These failures exist in master.

   Recommendation: Ask maintainer to fix intake_form mypy errors in
   master before merging, or merge with known master failures.

---

Summary:
- Quick wins (2): Mechanical fixes, ready to apply
- Medium (3): Straightforward improvements, can implement with your approval
- Not our problem (2): Mypy failures inherited from master — need upstream fix

Next steps: I can fix the Quick Wins and Medium items now, but the mypy
failures in intake_form/ are blocking from master. Options:
1. Fix all review comments and ask maintainer to merge despite mypy failures
2. Wait for someone to fix master's mypy errors first
3. Fix master's mypy errors ourselves (104 errors, will take significant time)

Which would you prefer?
```

---

## Example 2: Authentication-required CI logs

**User:** "Debug CI failure on PR #9876"

**Agent encounters:**
- CI Test Suite failed with log URL requiring authentication

**Agent output:**

```
I found a failing CI check: "CI Test Suite (Python 3.13)" but the logs
require authentication to access.

I need the log contents to diagnose the failure. Can you paste them from:
https://ci.internal/s3viewer?bucket=vs-ci&key=101568/abc123/test-suite.log

Once you share the logs, I can determine if the failures are related to
your changes or inherited from master.
```

---

## Example 3: Stale branch causing failures

**User:** "Why is CI failing? I didn't change anything related to those files"

**Agent diagnosis:**
- PR was created 2 weeks ago
- Master has moved forward 45 commits
- Test failures in unrelated modules due to API changes in master

**Agent output:**

```
Switched to `feature/add-auth`, rebased onto `master`.
Found 3 blockers: 3 failing test checks, 0 unresolved comments.
Mergeable state: `blocked`

### Analysis: Stale Branch Issue

Your branch was 45 commits behind master. The rebase exposed that master
changed AuthService.validate() — it now requires a 'scope' parameter your
code wasn't passing.

### Group 2: Medium Changes (3 items)

1. [CI] Test Suite — "test_authentication.py::test_login FAILED - missing required argument 'scope'"

   Fix: Update AuthService.validate() calls to include the new 'scope' parameter

   ```45:47:www/auth/auth_handler.py
   if not auth_service.validate(token):
       raise AuthError("Invalid token")
   ```

... (continue)

---

Summary:
Failures are caused by being out of sync with master (45 commits behind).
The rebase exposed that master changed AuthService's API.

Next steps: These are legitimate fixes needed due to master's evolution.
I can update all call sites to use the new API. Shall I proceed?
```
