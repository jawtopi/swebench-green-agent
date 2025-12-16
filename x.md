# SWE-bench Green Agent Demo Script

**Total Time: ~5 minutes**

---

## Part 1: Task Introduction (1 minute)

### What to Show
- Open the GitHub repo README or a slide with the architecture diagram

### Script (Narration)

> "Today I'm demonstrating our SWE-bench Green Agent, which evaluates AI coding agents on real-world software engineering tasks.
>
> **What is the task?**
> SWE-bench is a benchmark where AI agents must fix real bugs from popular open-source Python repositories like Django, Scikit-learn, and Matplotlib. Each task contains a GitHub issue description and the agent must produce a code patch that fixes the bug.
>
> **What does the environment look like?**
> The environment consists of:
> - A **Green Agent** (evaluator) that orchestrates the benchmark and runs tests
> - A **White Agent** (participant) that receives bug descriptions and generates patches
> - **Docker containers** that provide isolated test environments for each repository
>
> **What actions can each agent take?**
> - The White Agent receives a problem statement and returns a unified diff patch
> - The Green Agent sends tasks to the White Agent, receives patches, applies them to the codebase in Docker, runs the test suite, and determines pass/fail based on test results"

---

## Part 2: Live Demonstration (2.5 minutes)

### 2A: Show the Evaluation Flow

**What to Show:** Terminal with green agent logs

**Action:** Run a single task evaluation locally or show recent logs

```bash
# Option 1: Run locally (if you have Docker)
python main.py evaluate \
  --white-agent-url http://localhost:9002 \
  --task-ids django__django-10914 \
  --dataset verified

# Option 2: Show logs from a previous run
cat ~/swebench-green-agent/runs/django__django-10914-*/predictions.json
```

### Script (Narration)

> "Let me show you the evaluation flow in action.
>
> Here I'm sending a task to the white agent - this is Django issue 10914 about setting default file upload permissions.
>
> The green agent:
> 1. Loads the task from the SWE-bench dataset
> 2. Sends the problem statement to the white agent
> 3. Receives a patch in unified diff format
> 4. Applies the patch to the Django codebase in a Docker container
> 5. Runs the test suite
> 6. Checks if previously failing tests now pass
>
> **What is the green agent assessing?**
> The green agent assesses **correctness** - specifically whether the patch:
> - Applies cleanly to the codebase
> - Makes the failing tests pass (FAIL_TO_PASS)
> - Doesn't break existing passing tests (PASS_TO_PASS)"

---

### 2B: Show Concrete Examples

**What to Show:** Terminal output or logs showing different outcomes

**Action:** Display 2-3 example evaluations

```bash
# Show a PASS case (if available)
cat logs/run_evaluation/*/green-agent/sympy__sympy-22914/run_instance.log

# Show a FAIL case - malformed patch
cat ~/swebench-green-agent/runs/django__django-12273-*/predictions.json
```

### Script (Narration)

> "Let me show you concrete examples of different evaluation outcomes.
>
> **Example 1 - PASS:** Here's sympy-22914 where the white agent produced a correct patch. The patch applied successfully, and the tests that were failing now pass.
>
> **Example 2 - FAIL (Apply Error):** Here's a case where the white agent returned a malformed patch. The green agent correctly identifies this as a failure with failure_type 'apply_error'.
>
> **Example 3 - FAIL (Test Failure):** In this case, the patch applied but didn't fix the bug - the tests still fail. The green agent correctly marks this as failed."

---

## Part 3: Evaluation Reliability (1 minute)

### What to Show
- Run the validation script OR show its output

**Action:**
```bash
python scripts/validate_green_agent.py
```

### Script (Narration)

> "To verify our green agent evaluates reliably, we created a validation script with known test cases.
>
> **Test Case 1:** A partial patch that doesn't actually fix the bug - our green agent correctly returns FAIL.
>
> **Test Case 2:** An empty patch - correctly identified as FAIL.
>
> **Test Case 3:** A malformed patch that can't be applied - correctly returns FAIL with 'apply_error'.
>
> Our green agent uses the official SWE-bench Docker harness, ensuring we produce identical results to the official leaderboard. When we submit a patch that passes on our evaluation, it will pass on the official benchmark too."

---

## Part 4: Quantitative Results (30 seconds)

### What to Show
- Screenshot or terminal showing evaluation summary

**Action:** Show the summary output from a completed run

```
============================================================
GREEN AGENT: EVALUATION COMPLETE
============================================================
Dataset: verified
Total tasks: 10
Resolved: 1/10 (10.0%)
Failed: 7
Errors: 2
Total runtime: 607.9s
============================================================
```

### Script (Narration)

> "Here are quantitative results from running our benchmark on AgentBeats.
>
> On a sample of 10 tasks from SWE-bench Verified:
> - Resolution rate: 10% (1 out of 10 tasks solved)
> - 7 tasks failed due to incorrect or malformed patches
> - 2 tasks had connection errors to the white agent
>
> The resolution rate metric represents the percentage of real GitHub issues that the AI agent successfully fixed, verified by automated tests.
>
> Our green agent is deployed on GCP with Docker support and integrates with the AgentBeats platform for competitive evaluation."

---

## Closing (15 seconds)

### Script

> "In summary, our SWE-bench green agent provides reliable, reproducible evaluation of AI coding agents using Docker-isolated test environments. It correctly identifies both successful fixes and various failure modes.
>
> Thank you for watching!"

---

## Recording Tips

1. **Preparation:**
   - Have terminals pre-opened with relevant logs
   - Have the green agent already running if showing live demo
   - Pre-load any files you'll display

2. **Screen Layout:**
   - Use large font in terminal (14pt+)
   - Dark background recommended
   - Zoom in on relevant sections

3. **Timing:**
   - Part 1: 60 seconds
   - Part 2: 150 seconds
   - Part 3: 60 seconds
   - Part 4: 30 seconds
   - Total: ~5 minutes

4. **Fallback:**
   - If live demo fails, show pre-recorded logs
   - Have screenshots ready as backup
