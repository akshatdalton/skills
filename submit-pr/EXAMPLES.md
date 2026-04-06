# PR Description Examples

## Example 1: Backend Data-Plane Change

### ✅ Good Summary
```markdown
## SUMMARY:
Implements Google Drive connector for data-plane ingestion with streaming support for large files. Adds delta query with RFC 3339 timestamps, pagination, MIME filtering, and Workspace file export. Updates BlobStorageClient interface to Iterator[bytes] for streaming.
```

**Why it's good**: 3 sentences, states what was implemented, includes key technical details, no bullet sections.

### ❌ Bad Summary
```markdown
## SUMMARY:
This PR implements a new Google Drive connector.

**Core Features:**
- Delta query using modifiedTime with RFC 3339 timestamps for incremental sync
- Pagination support with nextPageToken (100 items per page)
- MIME type filtering to exclude image files

**Error Handling:**
- Per-file try-catch to continue ingestion on failures
- Detailed FileError tracking

**Code Quality:**
- DriveFileMetadata dataclass for type-safe metadata
- All helper methods as @staticmethod
```

**Why it's bad**: Too verbose, bullet sections, implementation details that belong in code comments.

---

## Example 2: Backend Test Plan

### ✅ Good
```markdown
## TEST PLAN:
```bash
cd operator_platform && pytest connectors/tests/test_google_drive_connector.py -v
```
```
Just the command. Easy to copy and run.

### ❌ Bad
```markdown
## TEST PLAN:
```bash
# Run Google Drive connector tests
python3 -m pytest operator_platform/connectors/tests/test_google_drive_connector.py -v

# Run storage layer tests
python3 -m pytest operator_platform/storage/tests/test_blob_storage_client.py -v

# Lint check
ruff check operator_platform/connectors/
```

**Expected Results:**
- All 5 Google Drive connector tests pass
- No linting errors

**Manual Testing (Future):**
Once control plane integration is complete, test with real OAuth credentials.
```

**Why it's bad**: Too many commands (linting belongs in pre-push hooks), "Expected Results" section is noise, "Manual Testing" is future work — doesn't belong in the PR.

---

## Example 3: UI Change Test Plan

### ✅ Good
```markdown
## TEST PLAN:
- go to /careerhub with your demo user
- apply for a job
- check whether apply form loads without any error
```
Clear steps, specific action, simple verification.

### ❌ Bad
```markdown
## TEST PLAN:
**UI Testing:**
Navigate to the Career Hub application using your demo user credentials. Once logged in, proceed to apply for any available job position. During the application process, carefully observe the form loading behavior and verify that:
1. The form loads within 2 seconds
2. No JavaScript errors appear in console
3. Test on Chrome, Firefox, and Safari
```
Too verbose, performance SLAs don't belong here, browser compat should be automated.

---

## Example 4: Checklist — Product Areas

### ✅ Backend/Data-Plane
```markdown
- This change impacts the following product areas and test plan includes steps to test:
  - [ ] AI Platform
  - [ ] AI Recruiter
  - [ ] CI
  - [x] DP
  - [ ] Mobile Platform
  ...
```

### ✅ Frontend/TM
```markdown
- This change impacts the following product areas and test plan includes steps to test:
  - [ ] AI Platform
  - [ ] AI Recruiter
  - [ ] CI
  - [ ] DP
  - [ ] Mobile Platform
  - [ ] PCS
  - [ ] TA
  - [ ] TD
  - [x] TM
  - [ ] WFX
  - [ ] RM
```

---

## Example 5: Regression Testing

### ✅ Good (new module)
```markdown
- [x] Regression testing is not required because new data-plane module, no customer impact
```

### ✅ Good (gate cleanup)
```markdown
- [x] Regression testing is not required because this change only removes a deprecated gate and does not alter runtime behavior. Gate is already *:1.
```

### ❌ Bad
```markdown
- [x] Regression testing is not required because this is a new feature
```
Too generic — doesn't explain customer impact or deployment state.

---

## Example 6: Gate Control

### ✅ Not gated (no customer impact)
```markdown
- Gate Control
  - [ ] IF the change is gated, ...
  - IF the change is not gated, it is because:
    - [x] There is no UX/functionality change/no customer impact
    - [ ] Other reason (justify): _____
```

### ✅ Not gated (gate cleanup)
```markdown
- Gate Control
  - IF the change is not gated, it is because:
    - [x] Other reason (justify): old gate cleanup
```

---

## Key Takeaways

1. **Summaries**: 2–3 sentences, no bullet sections
2. **Test Plans**: command only for backend; numbered steps for UI
3. **Checklist**: check relevant product areas — look at recent similar PRs for the pattern
4. **Regression**: be specific about why it's not needed (module scope, customer impact, deployment state)
5. **Copy exactly**: never modify checklist item text
6. **Fill blanks**: use specific values or `N/A`, never leave `_____`
