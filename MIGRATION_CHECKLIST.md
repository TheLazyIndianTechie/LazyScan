# LazyScan Improvement Implementation Checklist

## Phase 1: Critical Security Foundation ⚠️

### Step 1: Safe Deletion Module
- [x] Create SafeDeleter module template
- [x] Implement global kill switch check  
- [x] Add basic path validation
- [ ] Add comprehensive critical path detection
- [ ] Implement trash-first deletion with send2trash
- [ ] Add two-step confirmation for large directories
- [ ] Replace all direct shutil.rmtree/os.remove calls
- [ ] Add comprehensive tests

### Step 2: Path Validation Library  
- [ ] Create validators.py module
- [ ] Implement canonicalize_path() function
- [ ] Add is_within_allowed_roots() validation
- [ ] Add symlink/junction detection
- [ ] Add Windows reserved name detection
- [ ] Create allowed roots registry
- [ ] Add Unreal Engine non-default path support

### Step 3: Security Sentinel
- [ ] Create sentinel.py module
- [ ] Implement policy loading and validation
- [ ] Add fail-closed initialization
- [ ] Create default policy.json
- [ ] Wire SafeDeleter to require sentinel approval
- [ ] Add sentinel heartbeat logging

## Verification Commands

### Test the SafeDeleter:
```bash
python -c "from lazyscan.security.safe_delete import safe_delete; from pathlib import Path; safe_delete(Path('/tmp/test'), dry_run=True)"
```

### Test kill switch:
```bash
LAZYSCAN_DISABLE_DELETIONS=1 python -c "from lazyscan.security.safe_delete import SafeDeleter; SafeDeleter().delete(Path('/tmp/test'), dry_run=False)"
```

### Run basic tests:
```bash
python -m pytest tests/security/test_safe_delete.py -v
```

### Analyze current patterns:
```bash
./scripts/analyze_patterns.sh
```

## Next Steps

1. Install dependencies:
   ```bash
   pip install -r requirements-improvement.txt
   ```

2. Run the analysis script to see current state:
   ```bash
   ./scripts/analyze_patterns.sh
   ```

3. Test the SafeDeleter module:
   ```bash
   python -m pytest tests/security/ -v
   ```

4. Begin replacing direct deletion calls:
   ```bash
   # Find calls to replace
   ast-grep --pattern 'shutil.rmtree($_)' --lang python .
   
   # Use interactive replacement
   ast-grep --pattern 'shutil.rmtree($X)' --rewrite 'get_safe_deleter().delete(Path($X), mode=DeletionMode.PERMANENT, dry_run=False)' --interactive
   ```

5. Continue with remaining steps from IMPROVEMENT_PLAN.md
