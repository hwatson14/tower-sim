# Step1 FULLREPO split archive

The `tower-sim-step1_FULLREPO.part*` files are a split archive. To reassemble
into a single zip, use the helper script:

```bash
python tools/assemble_fullrepo_zip.py
```

If the script reports that the end-of-central-directory record is missing, the
split set is incomplete and the combined zip will not open until all parts are
present.
