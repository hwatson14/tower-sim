# Step1 dump recombination (local runbook)

This runbook reconstructs the full step1 dump (split across four zip files) into a
single working folder for local inspection or test runs.

## Recombine the dump into one folder

```bash
mkdir -p /tmp/tower_sim_step1_full
unzip -q reference/tower_sim_step1_part1_core.zip -d /tmp/tower_sim_step1_full
unzip -q reference/tower_sim_step1_part2_data.zip -d /tmp/tower_sim_step1_full
unzip -q reference/tower_sim_step1_part3_refs_tests_docs.zip -d /tmp/tower_sim_step1_full
unzip -q reference/tower_sim_step1_part4_legacy_quarantine.zip -d /tmp/tower_sim_step1_full
```

## Install dependencies (optional, for running tests)

```bash
cd /tmp/tower_sim_step1_full
python -m pip install -e .[dev]
```

## Run the bundled tests

```bash
pytest
```
