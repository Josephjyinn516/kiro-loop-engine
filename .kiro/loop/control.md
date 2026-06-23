# Loop Engineering Control File

<!-- Add instruction blocks below as H2 sections -->
<!-- Each block needs: type, status, priority metadata -->
<!-- Supported types: task, change-request, test, maintenance -->

<!-- Loop Engineering Metadata Fields:
     type: task | change-request | test | maintenance
     status: pending | in-progress | completed | failed | skipped | retrying | escalated
     priority: low | normal | high
     safety: confirmed (required for destructive operations)
     max-retries: 3 (override default retry count)
     verify: <command> (verification command to run after execution)
     accept: <criteria> (acceptance criteria for completion)
-->
