# C1 Memory Policy Checkpoint

Date: 2026-06-02  
Status: Completed / accepted  
Next phase: C2 Project Intelligence

## Summary

C1 established the memory safety, routing, review, retrieval, expiry, and status-reporting foundation for Jarvis v5.

C1 is now protected by automated smoke tests. The main smoke suite runs the C1 memory smoke suite.

## Completed Scope

- C1.1 Memory schema and routing
- C1.2 Review queue and conversation candidates
- C1.3 TTL expiry and non-destructive cleanup
- C1.4 Retrieval policy and safe recall
- C1.5 Route-aware approved write guard
- C1.6 Telegram memory status reporting
- C1.7 C1 memory smoke suite integration

## Runtime Snapshot

Last observed runtime state:

- Vector memory count: 170
- Candidate total: 14
- Pending: 1
- Stored: 6
- Rejected: 5
- Deferred: 2
- Expired: 0

Known pending candidate:

- mc_75ceb8e942f4598c
- source_type: web_research
- likely old metadata hotfix/test candidate
- not approved during C1 checkpoint

## Safety Rules Now Enforced

1. Nothing sensitive is silently written to vector memory.
2. Conversation memory candidates go through review queue first.
3. Sensitive/review_queue candidates remain blocked from vector memory even if approved.
4. Expired/deferred/rejected/pending candidates do not enter normal answer context.
5. Low-similarity memory does not enter normal answer context.
6. Vector recall is filtered before prompt context injection.
7. Candidate expiry is non-destructive.
8. Telegram has explicit memory visibility and maintenance commands.
9. C1 regression coverage runs through the main smoke suite.

## Important Commands

Manual C1 smoke:

```powershell
python .\tests\c1_memory_smoke_suite.py